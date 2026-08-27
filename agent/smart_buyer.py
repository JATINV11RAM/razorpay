import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
PSP_URL = "http://localhost:8001"
BUYER_AGENT_ID = "razorpacp-smart-agent-v2"
MAX_RETRIES = 2


def log(event, details):
    print(f"\n[{time.strftime('%H:%M:%S')}] [{event}] {details}")


def ask_gemini(prompt: str) -> str:
    """Call Gemini via REST API directly."""
    res = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]


def search_google_shopping(query: str, budget: float) -> list:
    """Search Google Shopping via Serper API for real product prices."""
    log("SEARCH", f"Searching Google Shopping for: {query}")

    response = requests.post(
        "https://google.serper.dev/shopping",
        headers={
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "q": query + " india",
            "gl": "in",
            "hl": "en",
            "num": 10
        }
    )

    data = response.json()
    products = []

    for item in data.get("shopping", []):
        price_str = item.get("price", "0")
        price_str = price_str.replace("₹", "").replace(",", "").replace(" ", "").strip()
        try:
            price = float(price_str)
        except:
            continue

        if price <= 0 or price > budget:
            continue

        products.append({
            "title": item.get("title", ""),
            "price": price,
            "source": item.get("source", "Unknown"),
            "rating": item.get("rating", 0),
            "reviews": item.get("ratingCount", 0),
            "link": item.get("link", ""),
            "thumbnail": item.get("imageUrl", "")
        })

    log("SEARCH", f"Found {len(products)} products within budget ₹{budget}")
    return products


def ai_pick_best_product(goal: str, budget: float, products: list) -> dict:
    """Use Gemini to pick the best product from search results."""
    log("DECIDE", "Asking Gemini AI to analyze and pick best product...")

    product_list = "\n".join([
        f"- [{i+1}] {p['title']} | ₹{p['price']} | {p['source']} | Rating: {p['rating']} ({p['reviews']} reviews)"
        for i, p in enumerate(products[:10])
    ])

    prompt = f"""You are an expert AI shopping agent for Indian consumers.

User goal: "{goal}"
Budget: ₹{budget}

Available products from Google Shopping (real prices from Amazon, Flipkart, Meesho etc):
{product_list}

Analyze these products and pick the BEST one considering:
1. How well it matches the user's goal
2. Value for money (price vs quality)
3. Seller reliability (prefer Amazon, Flipkart over unknown sources)
4. Rating and reviews

Reply ONLY in this exact JSON format, nothing else:
{{
  "index": 1,
  "title": "product title",
  "price": 999,
  "source": "Amazon",
  "reason": "why this is the best choice for the user",
  "confidence": "high/medium/low"
}}"""

    raw = ask_gemini(prompt)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    decision = json.loads(raw)

    # Get full product details
    idx = decision["index"] - 1
    if 0 <= idx < len(products):
        decision["full_product"] = products[idx]

    return decision


def create_razorpay_payment(product: dict, budget: float) -> dict:
    """Create a Razorpay payment via PSP."""

    # Step 1: Get Shared Payment Token
    log("TOKEN", f"Requesting SPT for ₹{product['price']}...")
    token_res = requests.post(f"{PSP_URL}/v1/tokens", json={
        "buyer_agent_id": BUYER_AGENT_ID,
        "max_amount": budget,
        "currency": "INR",
        "expiry_seconds": 300
    })

    if token_res.status_code != 200:
        raise Exception(f"Token creation failed: {token_res.text}")

    token_data = token_res.json()
    spt = token_data["shared_payment_token"]
    log("TOKEN", f"Got token: {spt} | Max: ₹{token_data['max_amount']}")

    # Step 2: Charge via PSP
    log("PAYMENT", f"Creating Razorpay order for ₹{product['price']}...")
    charge_res = requests.post(f"{PSP_URL}/v1/charges", json={
        "shared_payment_token": spt,
        "amount": product["price"],
        "currency": "INR",
        "session_id": f"smart-{int(time.time())}",
        "description": f"AI Purchase: {product['title'][:50]} from {product['source']}"
    })

    if charge_res.status_code == 200:
        return charge_res.json()
    else:
        raise Exception(charge_res.json().get("detail", "Payment failed"))


def run_smart_agent(user_goal: str, budget: float):
    print("\n" + "="*65)
    print(f"  RAZORPAY ACP — SMART AI BUYER AGENT v2")
    print(f"  Goal:   {user_goal}")
    print(f"  Budget: ₹{budget}")
    print("="*65)

    # STEP 1: Search real products
    products = search_google_shopping(user_goal, budget)

    if not products:
        log("ERROR", f"No products found within budget ₹{budget}")
        return

    # Show top results
    print(f"\n  TOP RESULTS FROM GOOGLE SHOPPING:")
    for i, p in enumerate(products[:5]):
        print(f"  [{i+1}] ₹{p['price']:,} | {p['source']:15} | {p['title'][:45]}")

    # STEP 2: AI picks best product
    decision = ai_pick_best_product(user_goal, budget, products)

    log("DECIDE", f"AI selected: {decision['title']}")
    log("DECIDE", f"Price: ₹{decision['price']} | Source: {decision['source']}")
    log("DECIDE", f"Reason: {decision['reason']}")
    log("DECIDE", f"Confidence: {decision['confidence'].upper()}")

    # STEP 3: Create payment with retry logic
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = create_razorpay_payment(decision, budget)

            log("SUCCESS", f"Payment completed!")
            log("SUCCESS", f"Razorpay Order ID: {result['razorpay_order_id']}")

            print("\n" + "="*65)
            print("  PURCHASE SUMMARY")
            print("="*65)
            print(f"  Product:     {decision['title'][:55]}")
            print(f"  Source:      {decision['source']}")
            print(f"  Amount Paid: ₹{decision['price']:,}")
            print(f"  Order ID:    {result['razorpay_order_id']}")
            print(f"  Token Used:  {result['audit']['token_id']}")
            print(f"  AI Reason:   {decision['reason'][:60]}")
            print("="*65)
            print(f"\n  ✓ Verify at: dashboard.razorpay.com → Test Mode → Orders")
            print("="*65)
            return

        except Exception as e:
            log("RETRY", f"Attempt {attempt} failed: {str(e)}")
            if attempt < MAX_RETRIES:
                log("RETRY", "Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                log("FAILED", f"Payment failed after {MAX_RETRIES} attempts")
                log("ESCALATE", "Escalating to human operator. No further retries.")


if __name__ == "__main__":
    print("\n" + "🛒 " * 20)
    print("DEMO 1: Electronics search")
    run_smart_agent(
        user_goal="I want wireless bluetooth earphones with good bass",
        budget=2000
    )

    print("\n" + "🛒 " * 20)
    print("DEMO 2: Budget too low — failure demo")
    run_smart_agent(
        user_goal="I want an iPhone 15 Pro Max",
        budget=500
    )