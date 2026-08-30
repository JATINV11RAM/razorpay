from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import uuid
import time
import os
from dotenv import load_dotenv
import razorpay

load_dotenv()

app = FastAPI(title="RazorACP — Combined Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Clients ──
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ── In-memory stores ──
TOKENS = {}
SESSIONS = {}

# ── Product catalog ──
PRODUCTS = [
    {"id": "SKU001", "name": "Handloom Cotton Kurta", "description": "Traditional handloom cotton kurta", "price": 899, "currency": "INR", "category": "Clothing", "inventory": 50},
    {"id": "SKU002", "name": "Banarasi Silk Saree", "description": "Premium Banarasi silk saree with gold zari work", "price": 4999, "currency": "INR", "category": "Clothing", "inventory": 20},
    {"id": "SKU003", "name": "Brass Pooja Thali Set", "description": "Handcrafted brass pooja thali with diyas", "price": 1299, "currency": "INR", "category": "Home & Decor", "inventory": 35},
    {"id": "SKU004", "name": "Darjeeling First Flush Tea", "description": "Premium Darjeeling first flush loose leaf tea, 250g", "price": 599, "currency": "INR", "category": "Food & Beverages", "inventory": 100},
    {"id": "SKU005", "name": "Rajasthani Juti Shoes", "description": "Handcrafted traditional Rajasthani mojari shoes", "price": 1499, "currency": "INR", "category": "Footwear", "inventory": 25},
    {"id": "SKU006", "name": "Organic Turmeric Powder", "description": "Pure organic turmeric powder from Kerala farms, 500g", "price": 299, "currency": "INR", "category": "Food & Beverages", "inventory": 200},
]

# ════════════════════════════════
# HEALTH
# ════════════════════════════════
@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "service": "RazorACP Combined Service", "version": "2.0"}


# ════════════════════════════════
# MERCHANT ENDPOINTS
# ════════════════════════════════
@app.get("/products")
def get_products():
    return {"products": PRODUCTS, "merchant": "Desi Bazaar", "currency": "INR"}


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
        raise HTTPException(status_code=400, detail=f"Total {total} exceeds authorized amount {req.max_authorized_amount}")
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "session_id": session_id,
        "product": product,
        "quantity": req.quantity,
        "total": total,
        "buyer_agent_id": req.buyer_agent_id,
        "status": "pending",
        "created_at": time.time(),
        "audit_trail": [{"event": "session_created", "timestamp": time.time(), "details": f"Checkout for {product['name']} x{req.quantity}"}]
    }
    return {"session_id": session_id, "total": total, "currency": "INR", "status": "pending"}


class CompleteRequest(BaseModel):
    shared_payment_token: str

@app.post("/checkouts/{session_id}/complete")
def complete_checkout(session_id: str, req: CompleteRequest):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Session already {session['status']}")
    token = TOKENS.get(req.shared_payment_token)
    if not token:
        raise HTTPException(status_code=402, detail="invalid_token: Token not found")
    if token["used"]:
        raise HTTPException(status_code=402, detail="token_already_used: This token has already been used")
    if time.time() > token["expires_at"]:
        raise HTTPException(status_code=402, detail="token_expired: Payment token has expired")
    if session["total"] > token["max_amount"]:
        raise HTTPException(status_code=402, detail=f"amount_exceeded: Charge {session['total']} exceeds authorized {token['max_amount']}")
    try:
        order = razorpay_client.order.create({
            "amount": int(session["total"] * 100),
            "currency": "INR",
            "receipt": session_id[:40],
            "notes": {"buyer_agent_id": token["buyer_agent_id"], "acp_session_id": session_id}
        })
        token["used"] = True
        session["status"] = "completed"
        session["razorpay_order_id"] = order["id"]
        session["audit_trail"].append({"event": "payment_completed", "timestamp": time.time(), "details": f"Razorpay order: {order['id']}"})
        return {"status": "completed", "session_id": session_id, "razorpay_order_id": order["id"]}
    except Exception as e:
        session["status"] = "failed"
        session["audit_trail"].append({"event": "payment_failed", "timestamp": time.time(), "details": str(e)})
        raise HTTPException(status_code=402, detail=f"razorpay_error: {str(e)}")

@app.get("/checkouts/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ════════════════════════════════
# PSP ENDPOINTS
# ════════════════════════════════
class TokenRequest(BaseModel):
    buyer_agent_id: str
    max_amount: float
    currency: str = "INR"
    expiry_seconds: int = 300

@app.post("/v1/tokens")
def create_token(req: TokenRequest):
    token_id = f"spt_{str(uuid.uuid4())[:8]}"
    TOKENS[token_id] = {
        "token_id": token_id,
        "buyer_agent_id": req.buyer_agent_id,
        "max_amount": req.max_amount,
        "currency": req.currency,
        "created_at": time.time(),
        "expires_at": time.time() + req.expiry_seconds,
        "used": False
    }
    return {"shared_payment_token": token_id, "max_amount": req.max_amount, "currency": req.currency, "expires_at": TOKENS[token_id]["expires_at"]}


class ChargeRequest(BaseModel):
    shared_payment_token: str
    amount: float
    currency: str = "INR"
    session_id: str
    description: str

@app.post("/v1/charges")
def create_charge(req: ChargeRequest):
    token = TOKENS.get(req.shared_payment_token)
    if not token:
        raise HTTPException(status_code=402, detail="invalid_token: Token not found")
    if token["used"]:
        raise HTTPException(status_code=402, detail="token_already_used: This token has already been used")
    if time.time() > token["expires_at"]:
        raise HTTPException(status_code=402, detail="token_expired: Payment token has expired")
    if req.amount > token["max_amount"]:
        raise HTTPException(status_code=402, detail=f"amount_exceeded: Charge {req.amount} exceeds authorized {token['max_amount']}")
    try:
        order = razorpay_client.order.create({
            "amount": int(req.amount * 100),
            "currency": req.currency,
            "receipt": req.session_id[:40],
            "notes": {"description": req.description, "buyer_agent_id": token["buyer_agent_id"], "acp_session_id": req.session_id}
        })
        token["used"] = True
        return {
            "status": "success",
            "razorpay_order_id": order["id"],
            "amount": req.amount,
            "currency": req.currency,
            "session_id": req.session_id,
            "audit": {"token_id": req.shared_payment_token, "buyer_agent_id": token["buyer_agent_id"], "charged_at": time.time(), "description": req.description}
        }
    except Exception as e:
        raise HTTPException(status_code=402, detail=f"razorpay_error: {str(e)}")


# ════════════════════════════════
# DECIDE / AI ENDPOINTS
# ════════════════════════════════
def ask_gemini(prompt: str) -> str:
    res = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]


def search_shopping(query: str, budget: float) -> list:
    response = requests.post(
        "https://google.serper.dev/shopping",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query + f" under ₹{int(budget)} buy online india amazon flipkart", "gl": "in", "hl": "en", "num": 10}
    )
    data = response.json()
    products = []
    min_price = budget * 0.3
    for item in data.get("shopping", []):
        price_str = item.get("price", "0").replace("₹", "").replace(",", "").replace(" ", "").strip()
        try:
            price = float(price_str)
        except:
            continue
        if price <= 0 or price > budget or price < min_price:
            continue
        products.append({
            "title": item.get("title", ""),
            "price": price,
            "source": item.get("source", "Unknown"),
            "rating": item.get("rating", 0),
            "reviews": item.get("ratingCount", 0),
            "link": item.get("link", ""),
        })
    return products


class SmartDecideRequest(BaseModel):
    goal: str
    budget: float

@app.post("/smart-decide")
def smart_decide(req: SmartDecideRequest):
    products = search_shopping(req.goal, req.budget)
    if not products:
        raise HTTPException(status_code=404, detail=f"No products found within budget ₹{req.budget}")

    TRUSTED_BRANDS = ["boat", "sony", "jbl", "samsung", "apple", "noise", "realme", "oneplus", "mi", "xiaomi", "bose", "sennheiser", "anker", "ptron", "philips", "lg", "motorola", "oppo", "vivo", "lenovo", "hp", "dell", "asus", "acer", "logitech", "nike", "adidas", "puma", "woodland", "fastrack", "titan"]
    TRUSTED_SOURCES = ["amazon", "flipkart", "myntra", "croma", "reliance", "tata"]

    for p in products:
        score = 0
        if p["rating"]: score += p["rating"] * 8
        if p["reviews"] and p["reviews"] > 100: score += 20
        elif p["reviews"] and p["reviews"] > 10: score += 10
        utilization = p["price"] / req.budget
        if utilization > 0.5: score += 20
        elif utilization > 0.3: score += 10
        if any(brand in p["title"].lower() for brand in TRUSTED_BRANDS): score += 10
        if any(src in p["source"].lower() for src in TRUSTED_SOURCES): score += 10
        p["value_score"] = round(score, 1)

    products.sort(key=lambda x: x["value_score"], reverse=True)

    product_list = "\n".join([
        f"- [{i+1}] {p['title']} | ₹{p['price']} | {p['source']} | Rating: {p['rating']} | Reviews: {p['reviews']} | ValueScore: {p['value_score']}/100"
        for i, p in enumerate(products[:10])
    ])

    prompt = f"""You are an expert AI shopping agent for Indian consumers.
User goal: "{req.goal}"
Budget: ₹{req.budget}

Products ranked by ValueScore (combines rating, reviews, budget utilization, brand trust):
{product_list}

Pick the product with the HIGHEST ValueScore that best matches the user's goal.
Do NOT pick the cheapest — pick the best quality within budget.
If the user asks for latest model, reject older generation products.
Prefer Amazon/Flipkart over unknown sources.

Reply ONLY in this exact JSON format:
{{
  "index": 1,
  "title": "product title",
  "price": 999,
  "source": "Amazon",
  "reason": "specific reason mentioning brand quality, ratings, and value for money",
  "confidence": "high"
}}"""

    raw = ask_gemini(prompt)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    decision = json.loads(raw)
    return {"decision": decision, "all_products": products}