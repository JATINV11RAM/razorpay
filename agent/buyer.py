from google import genai
import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
client_ai = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MERCHANT_URL = "http://localhost:8000"
PSP_URL = "http://localhost:8001"
BUYER_AGENT_ID = "gemini-buyer-agent-v1"
MAX_RETRIES = 2

def log(event, details):
    print(f"\n[{time.strftime('%H:%M:%S')}] [{event}] {details}")

def run_buyer_agent(user_goal: str, budget: float):
    print("\n" + "="*60)
    print(f"  RAZORPAY ACP - AI BUYER AGENT")
    print(f"  Goal: {user_goal}")
    print(f"  Budget: ₹{budget}")
    print("="*60)

    # STEP 1: Discover products
    log("DISCOVER", "Fetching merchant catalog...")
    response = requests.get(f"{MERCHANT_URL}/products")
    catalog = response.json()
    products = catalog["products"]
    log("DISCOVER", f"Found {len(products)} products at {catalog['merchant']}")

    # STEP 2: Ask Gemini which product to buy
    log("DECIDE", "Asking AI to select best product...")
    product_list = "\n".join([
        f"- {p['id']}: {p['name']} | ₹{p['price']} | {p['description']}"
        for p in products
    ])

    prompt = f"""You are an AI shopping agent. A user wants to: "{user_goal}"
Their budget is ₹{budget}.

Available products:
{product_list}

Pick the single best product that matches the user's goal and fits within budget.
Reply in this exact JSON format:
{{
  "product_id": "SKU001",
  "quantity": 1,
  "reason": "why this product fits the goal"
}}
Only reply with JSON, nothing else."""

    ai_response = client_ai.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    raw = ai_response.text.strip().replace("```json", "").replace("```", "").strip()
    decision = json.loads(raw)

    log("DECIDE", f"AI selected: {decision['product_id']} | Reason: {decision['reason']}")

    # STEP 3: Get token from PSP
    log("TOKEN", "Requesting Shared Payment Token from PSP...")
    token_response = requests.post(f"{PSP_URL}/v1/tokens", json={
        "buyer_agent_id": BUYER_AGENT_ID,
        "max_amount": budget,
        "currency": "INR",
        "expiry_seconds": 300
    })

    if token_response.status_code != 200:
        log("ERROR", f"Token creation failed: {token_response.text}")
        return

    token_data = token_response.json()
    spt = token_data["shared_payment_token"]
    log("TOKEN", f"Got token: {spt} | Max: ₹{token_data['max_amount']} | Expires in 5 min")

    # STEP 4: Create checkout session
    log("CHECKOUT", "Creating checkout session with merchant...")
    checkout_response = requests.post(f"{MERCHANT_URL}/checkouts", json={
        "product_id": decision["product_id"],
        "quantity": decision["quantity"],
        "buyer_agent_id": BUYER_AGENT_ID,
        "max_authorized_amount": budget
    })

    if checkout_response.status_code != 200:
        log("ERROR", f"Checkout failed: {checkout_response.json().get('detail')}")
        return

    checkout = checkout_response.json()
    session_id = checkout["session_id"]
    total = checkout["total"]
    log("CHECKOUT", f"Session created: {session_id} | Total: ₹{total}")

    # STEP 5: Complete payment with retry logic
    log("PAYMENT", f"Completing payment via Razorpay PSP...")

    for attempt in range(1, MAX_RETRIES + 1):
        complete_response = requests.post(
            f"{MERCHANT_URL}/checkouts/{session_id}/complete",
            json={"shared_payment_token": spt}
        )

        if complete_response.status_code == 200:
            result = complete_response.json()
            log("SUCCESS", f"Payment completed!")
            log("SUCCESS", f"Razorpay Order ID: {result['razorpay_order_id']}")

            # STEP 6: Show audit trail
            session_response = requests.get(f"{MERCHANT_URL}/checkouts/{session_id}")
            session = session_response.json()

            print("\n" + "="*60)
            print("  AUDIT TRAIL")
            print("="*60)
            for entry in session["audit_trail"]:
                t = time.strftime('%H:%M:%S', time.localtime(entry["timestamp"]))
                print(f"  [{t}] {entry['event'].upper()}: {entry['details']}")
            print("="*60)
            print(f"\n  RESULT: ₹{total} paid for {decision['product_id']}")
            print(f"  Razorpay Order: {result['razorpay_order_id']}")
            print("="*60)
            return

        else:
            error = complete_response.json().get("detail", "Unknown error")
            log("RETRY", f"Attempt {attempt} failed: {error}")

            if attempt < MAX_RETRIES:
                log("RETRY", f"Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                log("FAILED", f"Payment failed after {MAX_RETRIES} attempts")
                log("ESCALATE", "Escalating to human operator — no further retries")

                print("\n" + "="*60)
                print("  PAYMENT FAILED - AUDIT TRAIL")
                print("="*60)
                session_response = requests.get(f"{MERCHANT_URL}/checkouts/{session_id}")
                session = session_response.json()
                for entry in session["audit_trail"]:
                    t = time.strftime('%H:%M:%S', time.localtime(entry["timestamp"]))
                    print(f"  [{t}] {entry['event'].upper()}: {entry['details']}")
                print("="*60)


if __name__ == "__main__":
    run_buyer_agent(
        user_goal="I want to buy something traditional and Indian for gifting",
        budget=2000
    )