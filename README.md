
# Diagram Generation API

AI-powered diagram generation API that renders Mermaid, D2, PlantUML, and Graphviz diagrams to SVG or PNG. Paid endpoints are protected with [x402](https://x402.org) and settle on **Base mainnet** (`eip155:8453`) using USDC via the [xpay facilitator](https://xpay.sh) — zero-fee and gas-sponsored.

## What this API does

- Accepts a natural-language prompt and a diagram type
- Generates diagram source code with OpenAI
- Renders the final output as SVG or PNG
- Caches results in Redis to avoid redundant generation
- Exposes a public health check and a browser-based visualizer
- Gates paid generation routes behind x402 on-chain payment verification

## Supported diagram types

| Type | Key |
|---|---|
| Mermaid | `mermaid` |
| D2 | `d2` |
| PlantUML | `plantuml` |
| Graphviz | `graphviz` |

## Supported output formats

| Format | Notes |
|---|---|
| `svg` | Returned as an inline SVG string |
| `png` | Returned as a base64-encoded PNG |

Mermaid diagrams are rendered via [mermaid.ink](https://mermaid.ink) for speed and reliability. All other diagram types use [Kroki](https://kroki.io). When a renderer does not natively support PNG, the app renders SVG first and converts.

## Architecture

```
Client
  └─► POST /paid/diagrams/generate/svg (or /png)
        │
        ├─ [no payment] ──► 402 Payment Required  ◄── x402 challenge (xpay facilitator)
        │
        └─ [with PAYMENT-SIGNATURE header]
              │
              ├─ x402 middleware verifies signature on-chain (Base mainnet)
              ├─ OpenAI generates diagram source from prompt
              ├─ Renderer (mermaid.ink / Kroki) produces SVG or PNG
              ├─ Result stored in Postgres + cached in Redis
              └─► 200 OK  { diagram, rendered, format }
```

## Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| `GET` | `/visualizer` | None | Browser-based visualizer UI |Generate a diagram (5/day per IP, requires API key)
| `POST` | `/paid/diagrams/generate/svg` | x402 payment | Generate SVG diagram |
| `POST` | `/paid/diagrams/generate/png` | x402 payment | Generate PNG diagram |
| `POST` | `/diagrams/generate` | `X-API-Key` header | Admin/internal endpoint |
| `GET` | `/diagrams/{id}` | `X-API-Key` header | Retrieve a stored diagram |

## x402 payment model

The paid endpoints use the [x402 protocol](https://x402.org) with the `exact` EVM scheme on Base mainnet.

### Pricing

| Format | Price |
|---|---|
| SVG | $0.05 USDC |
| PNG | $0.07 USDC |

### Payment flow

1. Client calls `POST /paid/diagrams/generate/svg` (or `/png`) — no payment yet
2. Server returns `402 Payment Required` with an x402 challenge in the `PAYMENT-REQUIRED` header
3. Client signs the payment payload using the `exact` EVM scheme (USDC on Base mainnet)
4. Client retries the same request with the signed `PAYMENT-SIGNATURE` header
5. Server verifies the signature via the xpay facilitator on Base mainnet
6. Diagram is generated and returned

### Facilitator

- **URL:** `https://facilitator.xpay.sh`
- **Network:** `eip155:8453` (Base mainnet)
- **Asset:** USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- **Fees:** Zero — xpay sponsors gas and charges no fee

## Local setup

### Prerequisites

- Python 3.11+
- A running PostgreSQL instance (or SQLite for local dev)
- A running Redis instance
- An OpenAI API key
- An EVM wallet with USDC on Base mainnet (for buyer testing)

### Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Fill in all values in `.env` before running.

### Run locally

```bash
uvicorn app.main:app --reload
```

App listens on `http://127.0.0.1:8000` by default.

### Local x402 buyer test

```bash
# Set your buyer wallet key in .env (EVM_PRIVATE_KEY) then run:
python scripts/x402_buyer_payment_test.py
```

> The buyer key must be different from the seller wallet (`X402_PAY_TO`). The buyer wallet needs USDC on Base mainnet.

## Railway deployment

The app runs on [Railway](https://railway.app).

### Deploy steps

1. **Create a new Railway project** and connect this GitHub repository
2. **Add a Postgres service** — copy the `DATABASE_URL` into your environment variables
3. **Add a Redis service** — copy the `REDIS_URL` into your environment variables
4. **Set all environment variables** from the table below
5. **Deploy** — Railway will build from the `Dockerfile` automatically
6. **Confirm** — `GET /health` should return `{"status": "ok"}`

### Required Railway environment variables

| Variable | Value |
|---|---|
| `API_KEY` | Any strong secret string |
| `OPENAI_API_KEY` | Your OpenAI key |
| `DATABASE_URL` | Postgres connection string (Railway provides this) |
| `REDIS_URL` | Redis connection string (Railway provides this) |
| `X402_ENABLED` | `true` |
| `X402_FACILITATOR_URL` | `https://facilitator.xpay.sh` |
| `X402_NETWORK` | `eip155:8453` |
| `X402_PAY_TO` | Your seller wallet address (receives USDC) |
| `X402_PRICE_SVG` | `$0.05` |
| `X402_PRICE_PNG` | `$0.07` |

### Optional Railway environment variables

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | Use `gpt-4o` for better diagram quality |
| `KROKI_BASE_URL` | `https://kroki.io` | Override to self-hosted Kroki instance |
| `MERMAID_INK_BASE_URL` | `https://mermaid.ink` | Override to self-hosted mermaid.ink |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL in seconds |
| `LOGTAIL_TOKEN` | *(unset)* | Better Stack source token for structured logging |

### Live URL

```
https://diagram-generation-api-production.up.railway.app
```

### Health check

```bash
curl https://diagram-generation-api-production.up.railway.app/health
# {"status":"ok"}
```

## Rendering pipeline

| Diagram type | SVG renderer | PNG renderer |
|---|---|---|
| `mermaid` | mermaid.ink (primary) → Kroki (fallback) | mermaid.ink → convert |
| `d2` | Kroki | Kroki |
| `plantuml` | Kroki | Kroki |
| `graphviz` | Kroki | Kroki |

Mermaid diagrams go to mermaid.ink first because Kroki's mermaid renderer requires a headless Chromium browser, which is unreliable on shared cloud infrastructure and causes long timeouts. mermaid.ink handles this in ~1–3 seconds.

## Visualizer

1. Run the app: `uvicorn app.main:app --reload`
2. Open: `http://127.0.0.1:8000/visualizer`
3. Enter your API key and a prompt
4. Select diagram type and format
5. Click **Generate** to preview the result



## API Endpoints

### Free (rate-limited) (Visualizer Only)

| Method | Path | Description |
|---|---|---|
| `POST` | `/diagrams/generate` | Generate a diagram (5/day per IP, requires API key) |
| `GET` | `/health` | Health check |

### Paid (x402 — USDC on Base)

| Method | Path | Price | Description |
|---|---|---|---|
| `POST` | `/paid/diagrams/generate/svg` | $0.05 | Generate diagram as SVG | 20/minute
| `POST` | `/paid/diagrams/generate/png` | $0.07 | Generate diagram as PNG | 20/minute

## Environment variable reference

See [`.env.example`](.env.example) for the full configuration template with all variable names and example values.

