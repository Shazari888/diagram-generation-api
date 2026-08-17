# Diagram Generation API

AI-powered diagram generation API (FastAPI, PostgreSQL, Redis, OpenAI, Kroki).

## Supported diagram types

- `mermaid`
- `d2`
- `plantuml`
- `graphviz`

## Supported output formats

- `svg` — returned as raw SVG text
- `png` — returned as base64-encoded PNG bytes

When Kroki does not directly support a requested `diagram_type` + `format` pair, the API renders SVG first and converts to PNG automatically.

If Kroki Mermaid rendering fails due to transient issues, the API falls back to Mermaid Ink automatically.

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # then fill in values
```

## Run

```bash
uvicorn app.main:app --reload
```

---

## API Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness check |
| GET | `/visualizer` | None | Browser UI to test prompts and preview diagrams |
| POST | `/paid/diagrams/generate/svg` | Stripe MPP | Payment-gated SVG generation ($0.05) |
| POST | `/paid/diagrams/generate/png` | Stripe MPP | Payment-gated PNG generation ($0.07) |

### Generate a diagram (paid)

Paid endpoints use [Stripe MPP](https://docs.stripe.com/payments/machine/mpp) for machine-to-machine payments. When called without a valid credential, the API returns a `402 Payment Required` with a `WWW-Authenticate: Payment` challenge the client uses to complete payment via Stripe.

```bash
curl -X POST https://diagram-generation-api.vercel.app/paid/diagrams/generate/svg \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a database schema", "diagram_type": "mermaid"}'
# Returns: 402 Payment Required + WWW-Authenticate: Payment challenge
```

---

## Payment — Stripe MPP

This API uses the [Stripe Machine Payment Protocol (MPP)](https://docs.stripe.com/payments/machine/mpp) to gate paid endpoints. Clients pay using Stripe SPTs (fiat) without any manual checkout flow.

### Pricing

| Format | Price |
|--------|-------|
| SVG | $0.05 |
| PNG | $0.07 |

### How it works

1. Client calls `POST /paid/diagrams/generate/svg` (or `/png`)
2. API returns `402 Payment Required` with a signed Stripe MPP challenge
3. Client completes payment using a Stripe MPP-compatible SDK
4. Client retries the request with the payment credential in the `Authorization` header
5. API validates the credential and returns the rendered diagram

### Required environment variables

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Your Stripe live or test secret key |
| `STRIPE_PROFILE_ID` | Your Stripe MPP profile ID |
| `TEMPO_DEPOSIT_ADDRESS` | Your Stripe-generated Tempo deposit address |

---

## Environment variables

See [.env.example](.env.example) for the full list.

### Minimum required (Vercel)

| Variable | Description |
|----------|-------------|
| `API_KEY` | Secret key for `X-API-Key` header on free endpoints |
| `OPENAI_API_KEY` | OpenAI API key for diagram source generation |
| `DATABASE_URL` | PostgreSQL connection string (or `sqlite+aiosqlite:////tmp/test.db` for quickstart) |
| `STRIPE_SECRET_KEY` | Stripe secret key for MPP payment gating |
| `STRIPE_PROFILE_ID` | Stripe MPP profile ID |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `KROKI_BASE_URL` | `https://kroki.io` | Kroki rendering service URL |
| `MERMAID_INK_BASE_URL` | `https://mermaid.ink` | Fallback renderer for Mermaid |
| `REDIS_URL` | `redis://localhost:6379` | Redis for response caching |
| `BASE_APP_ID` | — | Adds `<meta name="base:app_id">` to `/` for Base domain verification |

---

## Deployment

### Vercel (recommended)

1. Connect this repo to Vercel
2. Set the required environment variables in **Settings → Environment Variables**
3. Vercel auto-deploys on every push to `main`
4. Verify with: `curl https://your-deployment.vercel.app/health`

### Release flow

1. Push changes to a feature branch
2. Open a PR → merge to `main`
3. Vercel auto-deploys `main`
4. Confirm `/health` returns `{"status": "ok"}`

---

## Visual preview (VS Code)

1. Run the API: `uvicorn app.main:app --reload`
2. In VS Code: `Ctrl+Shift+P` → **Simple Browser: Show**
3. Enter: `http://127.0.0.1:8000/visualizer`
4. Paste your API key, choose type and format, enter a prompt, click **Generate**

