from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import uuid
import time
import requests
import os

app = FastAPI(title="Desi Bazaar - ACP Merchant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load products
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "products.json")) as f:
    PRODUCTS = json.load(f)

# In-memory session store
SESSIONS = {}

# ACP Endpoint 1: Product Feed
@app.get("/products")
def get_products():
    return {"products": PRODUCTS, "merchant": "Desi Bazaar", "currency": "INR"}

# ACP Endpoint 2: Create Checkout Session
class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int = 1
    buyer_agent_id: str
    max_authorized_amount: float

@app.post("/checkouts")
def create_checkout(req: CheckoutRequest):
    product = next((p for p in PRODUCTS if p["id"] == req.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    total = product["price"] * req.quantity

    if total > req.max_authorized_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Total {total} exceeds authorized amount {req.max_authorized_amount}"
        )

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "session_id": session_id,
        "product": product,
        "quantity": req.quantity,
        "total": total,
        "buyer_agent_id": req.buyer_agent_id,
        "status": "pending",
        "created_at": time.time(),
        "audit_trail": [
            {
                "event": "session_created",
                "timestamp": time.time(),
                "details": f"Checkout for {product['name']} x{req.quantity}"
            }
        ]
    }

    return {
        "session_id": session_id,
        "total": total,
        "currency": "INR",
        "status": "pending"
    }

# ACP Endpoint 3: Complete Checkout
class CompleteRequest(BaseModel):
    shared_payment_token: str

@app.post("/checkouts/{session_id}/complete")
def complete_checkout(session_id: str, req: CompleteRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Session already {session['status']}")

    # Call PSP to charge
    psp_response = requests.post("http://localhost:8001/v1/charges", json={
        "shared_payment_token": req.shared_payment_token,
        "amount": session["total"],
        "currency": "INR",
        "session_id": session_id,
        "description": f"Payment for {session['product']['name']}"
    })

    if psp_response.status_code == 200:
        psp_data = psp_response.json()
        session["status"] = "completed"
        session["razorpay_order_id"] = psp_data.get("razorpay_order_id")
        session["audit_trail"].append({
            "event": "payment_completed",
            "timestamp": time.time(),
            "details": f"Razorpay order: {psp_data.get('razorpay_order_id')}"
        })
        return {
            "status": "completed",
            "session_id": session_id,
            "razorpay_order_id": psp_data.get("razorpay_order_id")
        }
    else:
        error = psp_response.json().get("detail", "Payment failed")
        session["status"] = "failed"
        session["audit_trail"].append({
            "event": "payment_failed",
            "timestamp": time.time(),
            "details": error
        })
        raise HTTPException(status_code=402, detail=error)

# ACP Endpoint 4: Get Session Status
@app.get("/checkouts/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session