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

RazorACP is an ACP-compliant PSP adapter built on top of Razorpay's test-mode API. It makes any Indian merchant transactable by AI agents — with no changes to the merchant's existing Razorpay setup.

An AI agent (Gemini, Claude, GPT) can:
1. Discover a merchant's product catalog
2. Make an autonomous purchase decision based on a user's goal and budget
3. Request a Shared Payment Token (SPT) from the PSP
4. Create a checkout session with the merchant
5. Complete payment via Razorpay — with a real order ID
6. Log every action in a tamper-evident audit trail

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
┌─────────────────────────────────────────────────────────┐
│                    AI BUYER AGENT                        │
│              (Gemini 3.6 Flash via Google API)           │
└────────────────────────┬────────────────────────────────┘
                         │ ACP Protocol
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
   GET /products   POST /checkouts  POST /checkouts
                                    /{id}/complete
          │              │              │
┌─────────▼──────────────▼──────────────▼─────────┐
│              MERCHANT API (Port 8000)             │
│           FastAPI — Desi Bazaar Demo Store        │
│  • Product Feed Spec (ACP)                        │
│  • Checkout Session Spec (ACP)                    │
│  • In-memory session store with audit trail       │
└──────────────────────┬──────────────────────────┘
                       │ POST /v1/charges
                       ▼
┌──────────────────────────────────────────────────┐
│           RAZORPAY PSP ADAPTER (Port 8001)        │
│        FastAPI — ACP-Compliant PSP Layer          │
│  • POST /v1/tokens   → Issues Shared Payment      │
│                        Token (SPT)                │
│  • POST /v1/charges  → Creates Razorpay Order     │
│  • Token validation  → Amount bounds, expiry,     │
│                        single-use enforcement     │
└──────────────────────┬──────────────────────────┘
                       │ Razorpay Python SDK
                       ▼
┌──────────────────────────────────────────────────┐
│           RAZORPAY TEST-MODE API                  │
│         Real order created. Real order ID.        │
│         Verifiable on dashboard.razorpay.com      │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│           DECIDE SERVICE (Port 8002)              │
│     FastAPI — Gemini AI Decision Endpoint         │
│  • Accepts: user goal + budget + product list     │
│  • Returns: product_id + quantity + reason        │
│  • Used by: browser-based frontend agent          │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│           FRONTEND (Port 5500)                    │
│     HTML/CSS/JS — RazorACP Demo Dashboard         │
│  • Live agent log with step-by-step flow          │
│  • Product catalog with AI selection highlight    │
│  • Real-time audit trail                          │
│  • Session stats (orders created, value processed)│
└──────────────────────────────────────────────────┘
```

---

## ACP Compliance

RazorACP implements all three ACP specifications:

| Spec | Endpoint | Description |
|------|----------|-------------|
| **Product Feed Spec** | `GET /products` | Structured catalog with SKU, price, inventory, category |
| **Agentic Checkout Spec** | `POST /checkouts` | Stateful checkout session with tax, total, bounds check |
| **Delegated Payment Spec** | `POST /v1/tokens` + `POST /v1/charges` | SPT issuance and single-use token enforcement |

**Track 01 Bar — Every requirement met:**

| Requirement | Implementation |
|-------------|----------------|
| Every money action explainable | Every decision logged with timestamp, reason, and actor |
| Bounded | SPT enforces max_amount — agent cannot exceed user's budget |
| Gated | Token is single-use, expires in 5 minutes, tied to buyer_agent_id |
| Audit trail | Full session audit trail returned on every checkout GET |
| One failure handled gracefully | Token expiry, amount exceeded, and invalid token all return structured errors with escalation |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Merchant API | Python 3.11 + FastAPI |
| PSP Adapter | Python 3.11 + FastAPI + Razorpay Python SDK |
| AI Buyer Agent | Google Gemini 3.6 Flash (google-genai SDK) |
| Decide Service | Python 3.11 + FastAPI |
| Frontend | Vanilla HTML/CSS/JS |
| Payment Rail | Razorpay Test-Mode API (real orders, zero real money) |
| Protocol | ACP v2026-04-17 (OpenAI + Stripe open standard) |

---

## Project Structure

```
razorpay/
├── merchant/
│   └── main.py          # ACP Merchant API (Product Feed + Checkout)
├── psp/
│   └── main.py          # Razorpay ACP PSP Adapter (Token + Charge)
├── agent/
│   ├── buyer.py         # CLI AI Buyer Agent (Gemini)
│   └── decide.py        # Decide microservice for browser frontend
├── frontend/
│   └── index.html       # RazorACP Demo Dashboard
├── data/
│   └── products.json    # Desi Bazaar product catalog
├── .env                 # API keys (not committed)
└── README.md
```

---

## How to Run

### Prerequisites
- Python 3.11
- Razorpay test-mode account (free at razorpay.com)
- Google Gemini API key (free at aistudio.google.com)

### Setup

```bash
git clone https://github.com/your-username/razorpay
cd razorpay
python3.11 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn requests google-genai python-dotenv razorpay
```

### Configure

Create `.env` in the root:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxx
```

### Run All Services

Open 4 terminal tabs:

```bash
# Tab 1 — Merchant API
uvicorn merchant.main:app --port 8000 --reload

# Tab 2 — Razorpay PSP Adapter
uvicorn psp.main:app --port 8001 --reload

# Tab 3 — Decide Service
PYTHONPATH=. uvicorn agent.decide:app --port 8002 --reload

# Tab 4 — Open frontend/index.html with Live Server (VS Code)
# or open directly: file:///path/to/razorpay/frontend/index.html
```

### Run CLI Agent (Terminal Demo)

```bash
python agent/buyer.py
```

### Verify

Go to `dashboard.razorpay.com` → Test Mode → Orders. Every agent run creates a real Razorpay order.

---

## Demo Flow

1. Open the frontend at `http://127.0.0.1:5500/frontend/index.html`
2. Enter a user goal (e.g. "I want something traditional Indian for gifting")
3. Set a budget (e.g. ₹2000)
4. Click **Run AI Buyer Agent**
5. Watch the agent discover products, decide autonomously, create a token, checkout, and pay
6. See the Razorpay Order ID appear — verifiable on the dashboard
7. Read the full audit trail below

**Failure scenario:** Set budget to ₹100 — the agent selects a product but the checkout fails with `amount_exceeded`. The agent logs the failure, escalates, and stops. No retry loop. No silent failure.

---

## Scope and Future Work

RazorACP is a proof-of-concept demonstrating the full ACP flow on Razorpay's infrastructure. In production, this adapter could:

- Be integrated into Razorpay Agent Studio as a native PSP layer
- Support UPI, cards, netbanking, and wallets via Razorpay's existing payment methods
- Be extended with UAP compliance once NPCI's protocol launches
- Enable every Razorpay merchant to be discoverable and transactable by AI agents globally

The gap this solves — no ACP-compliant Indian PSP — is real, current, and growing. Every day that passes without this bridge, Indian merchants fall further behind in the agentic commerce ecosystem.

---

## Built For

**Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

> *"Build an agent that grows revenue for a merchant on Razorpay test-mode APIs, or that makes a merchant transactable by an AI buyer end to end."*

RazorACP does exactly that — and builds the infrastructure every Indian merchant will need when agentic commerce goes mainstream.

---

*Built by Jatin Verma | B.Tech CSE + B.Sc AI & Data Science | JIET Jodhpur + IIT Jodhpur*