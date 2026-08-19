# Diagram Generation API

AI-powered diagram generation API that renders Mermaid, D2, PlantUML, and Graphviz diagrams to SVG or PNG. Paid endpoints are protected with x402 and settle on Base Sepolia using USDC.

## What this API does

- accepts a prompt and a diagram type
- generates diagram source with OpenAI
- renders the final output as SVG or PNG
- exposes a public health check and a browser-based visualizer
- gates paid generation routes behind x402 payment verification

## Supported diagram types

- `mermaid`
- `d2`
- `plantuml`
- `graphviz`

## Supported output formats

- `svg`
- `png`

When a renderer does not support the requested pair directly, the app renders SVG first and converts to PNG where needed.

## Project status

This repo is configured for the x402-only payment flow on Railway. The app no longer relies on Stripe MPP or Vercel serverless function constraints for paid generation.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
```

Then fill in the values in `.env` before running the app.

## Run locally

```bash
uvicorn app.main:app --reload
```

The app listens on `http://127.0.0.1:8000` by default.

## Routes

- `GET /health` — health check
- `GET /visualizer` — browser visualizer for manual testing
- `POST /paid/diagrams/generate/svg` — x402-gated SVG generation
- `POST /paid/diagrams/generate/png` — x402-gated PNG generation

## x402 payment model

The paid endpoints require an x402 payment before the diagram is generated.

### Pricing

- SVG: $0.05
- PNG: $0.07

### How it works

1. Client calls `POST /paid/diagrams/generate/svg` or `/png` without payment
2. Server returns `402 Payment Required` with an x402 challenge
3. Client constructs and signs the payment payload using the exact EVM scheme
4. Client retries with `PAYMENT-SIGNATURE` in the request headers
5. Server verifies the signature and returns the generated diagram

### Required live environment variables

- `X402_ENABLED=true`
- `X402_FACILITATOR_URL=https://dexter.cash/facilitator/base`
- `X402_NETWORK=eip155:84532`
- `X402_PAY_TO=0xC4b867EAeeDcFCe9B794a3f791F48f82ecc1350C`
- `X402_PRICE_SVG=$0.05`
- `X402_PRICE_PNG=$0.07`
- `OPENAI_API_KEY=...`
- `DATABASE_URL=...`
- `REDIS_URL=...`

Note: the builder-code extension is intentionally disabled for the exact EVM signature flow because it invalidates the signed payload.

## Railway deployment

This repo is currently intended to run on Railway instead of Vercel because paid generation includes a real x402 verification step and can exceed Vercel Hobby time limits.

### Deploy to Railway

1. Create a new Railway project
2. Import this repository from GitHub
3. Add the environment variables from `.env.example`
4. Deploy the project
5. Confirm `/health` returns `{"status": "ok"}`

### Example production URL

```text
https://diagram-generation-api-production.up.railway.app
```

## Environment variables

See [.env.example](.env.example) for the full configuration template.

### Required local values

- `API_KEY` — secret key for admin/internal endpoints
- `OPENAI_API_KEY` — API access for diagram source generation
- `DATABASE_URL` — Postgres or SQLite fallback
- `REDIS_URL` — Redis connection string
- `X402_ENABLED` — set to `true` for the paid endpoint flow
- `X402_PAY_TO` — wallet receiving USDC payments
- `X402_FACILITATOR_URL` — usually `https://x402.org/facilitator`
- `X402_NETWORK` — `eip155:84532` for Base Sepolia

### Optional values

- `KROKI_BASE_URL`
- `MERMAID_INK_BASE_URL`
- `BASE_APP_ID`
- `CACHE_TTL_SECONDS`

## Local testing

```bash
# health check
curl http://127.0.0.1:8000/health

# x402 buyer test
X402_PAID_ENDPOINT_URL=http://127.0.0.1:8000/paid/diagrams/generate/svg \
EVM_PRIVATE_KEY=your_private_key \
python scripts/x402_buyer_payment_test.py
```

## Visualizer

1. Run the app: `uvicorn app.main:app --reload`
2. Open: `http://127.0.0.1:8000/visualizer`
3. Enter your API key and prompt
4. Generate the diagram preview
