from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import razorpay
import uuid
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Razorpay ACP PSP Adapter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Razorpay client
client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

# Token store (simulates SPT - Shared Payment Token)
TOKENS = {}

# ACP PSP Endpoint 1: Create Shared Payment Token
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
    return {
        "shared_payment_token": token_id,
        "max_amount": req.max_amount,
        "currency": req.currency,
        "expires_at": TOKENS[token_id]["expires_at"]
    }

# ACP PSP Endpoint 2: Charge using token
class ChargeRequest(BaseModel):
    shared_payment_token: str
    amount: float
    currency: str = "INR"
    session_id: str
    description: str

@app.post("/v1/charges")
def create_charge(req: ChargeRequest):
    # Validate token
    token = TOKENS.get(req.shared_payment_token)

    if not token:
        raise HTTPException(status_code=402, detail="invalid_token: Token not found")

    if token["used"]:
        raise HTTPException(status_code=402, detail="token_already_used: This token has already been used")

    if time.time() > token["expires_at"]:
        raise HTTPException(status_code=402, detail="token_expired: Payment token has expired")

    if req.amount > token["max_amount"]:
        raise HTTPException(
            status_code=402,
            detail=f"amount_exceeded: Charge amount {req.amount} exceeds authorized {token['max_amount']}"
        )

    # Create Razorpay order (test mode)
    try:
        order = client.order.create({
            "amount": int(req.amount * 100),  # Razorpay uses paise
            "currency": req.currency,
            "receipt": req.session_id[:40],
            "notes": {
                "description": req.description,
                "buyer_agent_id": token["buyer_agent_id"],
                "acp_session_id": req.session_id
            }
        })

        # Mark token as used
        token["used"] = True

        return {
            "status": "success",
            "razorpay_order_id": order["id"],
            "amount": req.amount,
            "currency": req.currency,
            "session_id": req.session_id,
            "audit": {
                "token_id": req.shared_payment_token,
                "buyer_agent_id": token["buyer_agent_id"],
                "charged_at": time.time(),
                "description": req.description
            }
        }

    except Exception as e:
        raise HTTPException(status_code=402, detail=f"razorpay_error: {str(e)}")

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "service": "Razorpay ACP PSP Adapter"}