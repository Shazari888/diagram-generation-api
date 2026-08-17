# Diagram Generation API

AI-powered diagram generation API (FastAPI, PostgreSQL, Redis, OpenAI, Kroki).

Supported diagram types:

- `mermaid`
- `d2`
- `plantuml`
- `graphviz`

Supported output formats:

- `svg` (returned as raw SVG text)
- `png` (returned as base64-encoded PNG bytes)
- `pdf` (returned as base64-encoded PDF bytes)

When Kroki does not directly support a requested `diagram_type` + `format` pair,
the API renders SVG first and converts it to PNG/PDF.

If Kroki Mermaid rendering fails due transient Chromium launch issues, the API
automatically falls back to Mermaid Ink for Mermaid outputs.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # then fill in values
```

## Run

Python API:

```bash
uvicorn app.main:app --reload
```

MPP gateway (for Stripe SPTs and Tempo crypto):

```bash
npm install
npm run mpp:dev
```

## API

| Method | Path                            | Auth        | Description                                     |
| ------ | ------------------------------- | ----------- | ------------------------------------------------ |
| GET    | `/health`                       | No          | Liveness check                                  |
| GET    | `/visualizer`                   | No          | Browser UI to test prompts and preview diagrams |
| POST   | `/diagrams/generate`            | `X-API-Key` | Generate and store a diagram                    |
| POST   | `/paid`                         | MPP         | Stripe SPT + Tempo crypto payment gate           |
| POST   | `/paid/diagrams/generate/svg`   | x402        | x402 paid generation, SVG format ($0.03)        |
| POST   | `/paid/diagrams/generate/png`   | x402        | x402 paid generation, PNG format ($0.05)        |
| POST   | `/paid/diagrams/generate/pdf`   | x402        | x402 paid generation, PDF format ($0.07)        |
| GET    | `/diagrams/{diagram_id}`        | `X-API-Key` | Fetch a stored diagram                          |

### Generate diagram

```bash
curl -X POST http://localhost:8000/diagrams/generate \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "flowchart for user login", "diagram_type": "mermaid", "format": "svg"}'
```

## Stripe MPP monetization

This project now includes a lightweight Node MPP gateway that exposes the protocol-native payment challenge your customer-facing client can use.

1. Create a Stripe profile in the Dashboard and set `STRIPE_PROFILE_ID`.
2. Set `STRIPE_SECRET_KEY` to either your sandbox or live secret key.
3. Optionally set `TEMPO_DEPOSIT_ADDRESS` to a fixed Tempo address. If omitted, the Stripe MPP service can create or fetch one automatically.
4. Start the gateway:

```bash
npm install
npm run mpp:dev
```

5. Validate the gateway:

```bash
npx mppx@latest validate http://localhost:4242
```

The gateway exposes `/paid` and returns a `402` challenge with both Stripe SPT and Tempo options until the client completes payment. The example pricing is:

- Tempo: `0.01` USD-equivalent
- Stripe SPT: `0.50` USD

Use sandbox keys for local validation and live keys only after you have verified the flow in test mode.

## Environment variables

See [.env.example](.env.example).

Optional override:

- `MERMAID_INK_BASE_URL` (default: `https://mermaid.ink`)
- `BASE_APP_ID` (adds `<meta name="base:app_id" ...>` to `/` for Base domain verification)

x402 seller mode (Base Builder Code attribution):

- `X402_ENABLED=true`
- `X402_FACILITATOR_URL` (default: `https://x402.org/facilitator`)
- `X402_NETWORK` (default: `eip155:84532` for Base Sepolia testnet)
- `X402_PAY_TO` (wallet that receives payment)
- `X402_PRICE_SVG` (default: `$0.03`)
- `X402_PRICE_PNG` (default: `$0.05`)
- `X402_PRICE_PDF` (default: `$0.07`)
- `X402_BUILDER_CODE` (example: `bc_b7k3p9da`, optional — attribution only, not required for settlement)

When enabled, each format has its own paid route so the x402 payment
challenge can quote the correct price before the request body is read:

- `POST /paid/diagrams/generate/svg`
- `POST /paid/diagrams/generate/png`
- `POST /paid/diagrams/generate/pdf`

The `format` field in the request body is optional on these routes — the
path segment always determines the rendered format and price.

For Base mainnet production, use:

- `X402_FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402`
- `X402_NETWORK=eip155:8453`
- `CDP_API_KEY_ID=organizations/.../apiKeys/...`
- `CDP_API_KEY_SECRET=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----`

`CDP_API_KEY_SECRET` may be pasted with escaped `\n` newlines (recommended for env vars).

Get your real Builder Code at:

- https://dashboard.base.org → log in → select your app → **Settings → Builder Codes**

x402 buyer payment test (to verify you can receive settled payments):

1. Set buyer env vars in `.env`:
   - `X402_PAID_ENDPOINT_URL=http://127.0.0.1:8000/paid/diagrams/generate/svg`
   - `EVM_PRIVATE_KEY=0x...` (funded buyer wallet key)
   - `X402_TEST_FORMAT=svg` (optional, defaults to `svg`; use `png` or `pdf` to test other prices — must match the endpoint path)
2. Run:
   - `.\.venv\Scripts\python.exe scripts\x402_buyer_payment_test.py`
3. Success criteria:
   - script prints `status 200`
   - script prints `payment_settled ...`

For testnet settlement (x402.org facilitator), buyer wallet must be funded on Base Sepolia with:
- testnet USDC (asset in the 402 challenge)
- enough ETH for gas/approval flow

## Deployment + migration notes (important)

### 1. Ensure old code is fully replaced in production

Use this release flow every time:

1. Push feature branch updates.
2. Merge/push latest commit to `main`.
3. Confirm Vercel production is deploying `main` (not an older branch).
4. Redeploy and verify `/health` returns `200`.

If Vercel points to an old branch or old commit, you can still get startup errors
even when local code is fixed.

### 2. SQLite path behavior and `test.db`

The API now auto-normalizes SQLite paths on Vercel:

- Local/dev default fallback: `sqlite+aiosqlite:///./test.db`
- Vercel runtime fallback: `sqlite+aiosqlite:////tmp/test.db`

Why: Vercel's `/var/task` is read-only at runtime, but `/tmp` is writable.

### 3. When you should change `test.db`

Usually, you do **not** need to rename it.

Change the DB path only when:

- You want a different local filename, or
- You migrate to managed Postgres and set a real `DATABASE_URL`.

For production, preferred setup is managed Postgres (`postgresql+asyncpg://...`)
instead of SQLite.

### 4. Vercel environment minimum

At minimum set:

- `API_KEY`
- `OPENAI_API_KEY`
- `DATABASE_URL` (quickstart: `sqlite+aiosqlite:////tmp/test.db`)

If `X402_ENABLED=true`, also set all required x402 vars:

- `X402_FACILITATOR_URL`
- `X402_NETWORK`
- `X402_PAY_TO`
- `X402_PRICE_SVG`
- `X402_PRICE_PNG`
- `X402_PRICE_PDF`
- `X402_BUILDER_CODE`

If `X402_FACILITATOR_URL` uses `api.cdp.coinbase.com`, also set:

- `CDP_API_KEY_ID`
- `CDP_API_KEY_SECRET`

## Visual preview in VS Code (Simple Browser)

1. Run the API: `uvicorn app.main:app --reload`
2. In VS Code: `Ctrl+Shift+P` → **Simple Browser: Show**
3. Enter: `http://127.0.0.1:8000/visualizer`
4. Paste your API key, choose type/format, enter text prompt, click **Generate**
