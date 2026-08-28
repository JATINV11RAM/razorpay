from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="RazorACP Decide Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


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
                json={
            "q": query + f"under ₹{int(budget)} buy online india amazon flipkart",
            "gl": "in",
            "hl": "en", 
            "num": 10
        }
    )
    data = response.json()
    products = []
    for item in data.get("shopping", []):
        price_str = item.get("price", "0").replace("₹", "").replace(",", "").replace(" ", "").strip()
        try:
            price = float(price_str)
        except:
            continue
        min_price = budget * 0.3  # product must cost at least 30% of budget
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


# Original endpoint for old frontend
class Product(BaseModel):
    id: str
    name: str
    price: float
    description: str
    category: str
    inventory: int

class DecideRequest(BaseModel):
    goal: str
    budget: float
    products: List[Product]

@app.post("/decide")
def decide(req: DecideRequest):
    product_list = "\n".join([
        f"- {p.id}: {p.name} | ₹{p.price} | {p.description}"
        for p in req.products
    ])
    prompt = f"""You are an AI shopping agent. A user wants to: "{req.goal}"
Their budget is ₹{req.budget}.
Available products:
{product_list}
Pick the single best product that matches the user's goal and fits within budget.
Reply in this exact JSON format:
{{"product_id": "SKU001", "quantity": 1, "reason": "why this product fits the goal"}}
Only reply with JSON, nothing else."""
    raw = ask_gemini(prompt)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# New smart endpoint for updated frontend
class SmartDecideRequest(BaseModel):
    goal: str
    budget: float

@app.post("/smart-decide")
def smart_decide(req: SmartDecideRequest):
    products = search_shopping(req.goal, req.budget)

    if not products:
        raise HTTPException(status_code=404, detail=f"No products found within budget ₹{req.budget}")

    # Compute value score for each product
    TRUSTED_BRANDS = ["boat", "sony", "jbl", "samsung", "apple", "noise", "realme", 
                      "oneplus", "mi", "xiaomi", "bose", "sennheiser", "anker", "ptron",
                      "philips", "lg", "motorola", "oppo", "vivo", "lenovo", "hp", "dell",
                      "asus", "acer", "logitech", "corsair", "razer", "nike", "adidas",
                      "puma", "woodland", "red tape", "fastrack", "titan", "fossil"]
    TRUSTED_SOURCES = ["amazon", "flipkart", "myntra", "croma", "reliance", "tata"]

    for p in products:
        score = 0
        # Rating score (0-40 points)
        if p["rating"]: score += p["rating"] * 8
        # Review count score (0-20 points)
        if p["reviews"] and p["reviews"] > 100: score += 20
        elif p["reviews"] and p["reviews"] > 10: score += 10
        # Budget utilization score (0-20 points) — reward using more of the budget
        utilization = p["price"] / req.budget
        if utilization > 0.5: score += 20
        elif utilization > 0.3: score += 10
        # Trusted brand score (0-10 points)
        if any(brand in p["title"].lower() for brand in TRUSTED_BRANDS): score += 10
        # Trusted source score (0-10 points)
        if any(src in p["source"].lower() for src in TRUSTED_SOURCES): score += 10
        p["value_score"] = round(score, 1)

    # Sort by value score
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
Do NOT pick the cheapest — pick the best quality within budget.If the user asks for a "latest" or specific model, reject older generation products even if cheaper.
Prefer products sold directly by the brand or on Amazon/Flipkart over third-party sellers.
If the user has a budget of ₹{req.budget}, they expect a product worth close to that amount.

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

    return {
        "decision": decision,
        "all_products": products
    }