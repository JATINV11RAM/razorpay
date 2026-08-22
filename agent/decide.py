from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from google import genai
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

client_ai = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
{{
  "product_id": "SKU001",
  "quantity": 1,
  "reason": "why this product fits the goal"
}}
Only reply with JSON, nothing else."""

    response = client_ai.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

@app.get("/health")
def health():
    return {"status": "ok", "service": "RazorACP Decide"}