# RazorACP — India's First ACP-Compliant Agentic Payment System

> **Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

---

## The Problem

Every major Western merchant — on Shopify, Amazon, eBay — can now be purchased from by an AI agent. ChatGPT can browse a catalog, pick a product, and complete a payment autonomously using the Agentic Commerce Protocol (ACP), developed by OpenAI and Stripe.

**No Indian merchant can do this today.**

There is no ACP-compliant Payment Service Provider (PSP) for India. Razorpay processes ₹28.92 trillion in monthly UPI transactions — but none of that infrastructure speaks the protocol that AI agents use to transact. Indian merchants are invisible to the agentic commerce ecosystem.

This is the gap RazorACP fills.

---

## What RazorACP Does

RazorACP is an ACP-compliant PSP adapter built on Razorpay's test-mode API. It makes any Indian merchant transactable by AI agents — with no changes to their existing Razorpay setup.

An AI agent (powered by Google Gemini) can:

1. Search real products from Amazon, Flipkart, Myntra via Google Shopping
2. Analyze results by value score — combining ratings, reviews, brand trust, and budget utilization
3. Pick the best product autonomously based on the user's goal
4. Request a Shared Payment Token (SPT) from the PSP — bounded by the user's budget
5. Create a checkout session with the merchant
6. Complete payment via Razorpay — generating a real, verifiable order ID
7. Log every action in a tamper-evident audit trail

No human clicks anything after the agent starts. Every money action is explainable, bounded, and gated.

---

## Why This Matters

### The Global Context

The Agentic Commerce Protocol (ACP) is an open standard co-developed by OpenAI and Stripe. It defines how AI agents discover products, negotiate prices, and complete payments on behalf of users. ACP is already live in ChatGPT and being adopted by PayPal, Salesforce, and Shopify — all Western platforms.

### The Indian Gap

NPCI is developing the Unified Agent Protocol (UAP) — India's sovereign AI payment rail. But UAP requires RBI regulatory approval and is months away from launch. In the meantime, Indian merchants have no path into agentic commerce.

### The Razorpay Opportunity

Razorpay already processes billions of transactions and operates Razorpay Capital for merchant lending. RazorACP positions Razorpay as the PSP layer for India's agentic commerce stack — exactly what Agent Studio needs to serve Zomato, PVR INOX, Bluestone, and the 10 million merchants on Razorpay's platform.

### Why Now

- March 2026: Razorpay launches Agent Studio at FTX 2026
- July 2026: NPCI announces UAP framework
- August 2026: ACP v2026-04-17 released with MCP integration
- **Today:** No Indian PSP speaks ACP. RazorACP is the bridge.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    SMART AI BUYER AGENT                       │
│         Google Gemini 3.6 Flash + Serper Google Shopping      │
│   Searches real products · Scores by value · Decides & pays  │
└───────────────────────────┬──────────────────────────────────┘
                            │ ACP Protocol
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    GET /products    POST /checkouts   POST /checkouts
                                       /{id}/complete
           │                │                │
┌──────────▼────────────────▼────────────────▼──────────┐
│                  MERCHANT API (Port 8000)               │
│              FastAPI — ACP Merchant Layer               │
│   • Product Feed Spec (ACP)                            │
│   • Stateful Checkout Session Spec (ACP)               │
│   • In-memory session store with full audit trail      │
└─────────────────────────┬──────────────────────────────┘
                          │ POST /v1/charges
                          ▼
┌─────────────────────────────────────────────────────────┐
│              RAZORPAY PSP ADAPTER (Port 8001)            │
│           FastAPI — ACP-Compliant PSP Layer              │
│   • POST /v1/tokens  → Issues Shared Payment Token (SPT)│
│   • POST /v1/charges → Creates Razorpay Order           │
│   • Token validation: amount bounds · expiry · one-use  │
└─────────────────────────┬───────────────────────────────┘
                          │ Razorpay Python SDK
                          ▼
┌─────────────────────────────────────────────────────────┐
│               RAZORPAY TEST-MODE API                     │
│          Real order created. Real order ID.              │
│       Verifiable at dashboard.razorpay.com               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              DECIDE SERVICE (Port 8002)                  │
│         FastAPI — AI Decision + Product Search           │
│   • /smart-decide: Serper search + Gemini analysis      │
│   • Value scoring: rating + reviews + brand + budget    │
│   • Returns ranked decision with reasoning              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              FRONTEND (Port 5500)                        │
│          HTML/CSS/JS — RazorACP Dashboard                │
│   • Live agent log with 5-step flow visualization       │
│   • Real-time product results from Google Shopping      │
│   • Razorpay order confirmation + audit trail           │
│   • Failure demo with graceful escalation               │
└─────────────────────────────────────────────────────────┘
```

---

## ACP Compliance

RazorACP implements all three ACP specifications:

| Spec | Endpoint | Description |
|------|----------|-------------|
| **Product Feed Spec** | `GET /products` | Structured catalog with SKU, price, inventory, category |
| **Agentic Checkout Spec** | `POST /checkouts` | Stateful checkout session with total calculation and bounds check |
| **Delegated Payment Spec** | `POST /v1/tokens` + `POST /v1/charges` | SPT issuance and single-use token enforcement |

**Track 01 Bar — Every requirement met:**

| Requirement | Implementation |
|-------------|----------------|
| Every money action explainable | Every decision logged with timestamp, reason, and actor ID |
| Bounded | SPT enforces `max_amount` — agent cannot exceed user's budget under any condition |
| Gated | Token is single-use, expires in 5 minutes, tied to `buyer_agent_id` |
| Audit trail | Full session audit trail returned on every `GET /checkouts/{id}` |
| One failure handled gracefully | Token expiry, amount exceeded, and invalid token all return structured errors with automatic escalation |

---

## Smart Value Scoring

Unlike a naive agent that picks the cheapest product, RazorACP's agent scores every search result across five dimensions:

| Dimension | Weight | Logic |
|-----------|--------|-------|
| Rating | 40 pts | `rating × 8` |
| Review count | 20 pts | >100 reviews = full score |
| Budget utilization | 20 pts | Rewards using >50% of budget |
| Trusted brand | 10 pts | boAt, Sony, Samsung, Apple, JBL etc. |
| Trusted source | 10 pts | Amazon, Flipkart, Myntra, Croma |

Gemini then receives the pre-scored ranked list and makes a final decision with explicit reasoning. A ₹2,000 budget buys the best ₹1,800 product — not the cheapest ₹400 one.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Merchant API | Python 3.11 + FastAPI |
| PSP Adapter | Python 3.11 + FastAPI + Razorpay Python SDK |
| AI Buyer Agent (CLI) | Google Gemini 3.6 Flash + Serper Google Shopping API |
| Decide Service | Python 3.11 + FastAPI |
| Frontend | Vanilla HTML/CSS/JS |
| Payment Rail | Razorpay Test-Mode API |
| Protocol | ACP v2026-04-17 (OpenAI + Stripe open standard) |

---

## Project Structure

```
razorpay/
├── merchant/
│   └── main.py           # ACP Merchant API — Product Feed + Checkout
├── psp/
│   └── main.py           # Razorpay PSP Adapter — Token issuance + Charge
├── agent/
│   ├── __init__.py
│   ├── buyer.py          # CLI AI Buyer Agent (Gemini + Razorpay)
│   ├── smart_buyer.py    # Smart Buyer with real Google Shopping search
│   └── decide.py         # Decide microservice — AI decision + Serper search
├── frontend/
│   └── index.html        # RazorACP Demo Dashboard
├── data/
│   └── products.json     # Demo merchant catalog (Desi Bazaar)
├── .env                  # API keys — never committed
├── requirements.txt      # Python dependencies
└── README.md
```

---

## How to Run

### Prerequisites

- Python 3.11
- Razorpay test-mode account — free at [razorpay.com](https://razorpay.com)
- Google Gemini API key — free at [aistudio.google.com](https://aistudio.google.com/apikey)
- Serper API key — free tier (2,500 searches) at [serper.dev](https://serper.dev)

### Setup

```bash
git clone https://github.com/JATINV11RAM/razorpay
cd razorpay
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure

Create `.env` in the root:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxx
SERPER_API_KEY=xxxxxxxxxxxxxxxxxxxx
```

### Run All Services

Open 3 terminal tabs:

```bash
# Tab 1 — Merchant API
uvicorn merchant.main:app --port 8000 --reload

# Tab 2 — Razorpay PSP Adapter
uvicorn psp.main:app --port 8001 --reload

# Tab 3 — Decide Service (AI + Search)
PYTHONPATH=. uvicorn agent.decide:app --port 8002 --reload
```

Then open `frontend/index.html` with VS Code Live Server.

### Run CLI Smart Agent

```bash
python agent/smart_buyer.py
```

### Verify

Go to `dashboard.razorpay.com` → Test Mode → Orders. Every agent run creates a real Razorpay order with a verifiable order ID.

---

## Demo Flow

**Success scenario:**
1. Open the frontend
2. Type a goal — e.g. "wireless bluetooth earphones with good bass"
3. Set a budget — e.g. ₹2,000
4. Click **Run AI Buyer Agent**
5. Watch the agent search Google Shopping in real time, score results, pick the best product, create a payment token, and complete the Razorpay order
6. Verify the order ID on the Razorpay dashboard

**Failure scenario:**
Click **Demo: Payment Failure + Escalation** — the agent requests a token, waits for it to expire, attempts to charge it, receives `token_expired`, retries once, then escalates to human with a full audit trail. No silent failures. No infinite loops.

---

## Verified Orders

These Razorpay test-mode orders were created by the RazorACP agent during development:

| Order ID | Product | Amount | Source |
|----------|---------|--------|--------|
| `order_TSwn4BJPb26pk4` | Brass Pooja Thali Set | ₹1,299 | Desi Bazaar |
| `order_TUez0CIZN4n2du` | boAt Rockerz 255 Pro Plus | ₹1,029 | Gadgets Now |

Verifiable at `dashboard.razorpay.com` → Test Mode → Orders.

---

## Scope and Future Work

In production, RazorACP could:

- Be integrated into Razorpay Agent Studio as a native PSP layer
- Support UPI, cards, netbanking, and wallets via Razorpay's existing payment methods
- Be extended with UAP compliance once NPCI's protocol launches
- Enable every Razorpay merchant to be discoverable and transactable by AI agents globally
- Power Razorpay's position as India's default PSP in the agentic commerce stack

---

## Built For

**Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

> *"Build an agent that grows revenue for a merchant on Razorpay test-mode APIs, or that makes a merchant transactable by an AI buyer end to end."*

RazorACP does exactly that — and builds the infrastructure every Indian merchant will need when agentic commerce goes mainstream.

---

*Built by Jatin Verma | B.Tech CSE (Cyber Security) + B.Sc AI & Data Science | JIET Jodhpur + IIT Jodhpur*
