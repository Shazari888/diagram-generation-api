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

```bash
uvicorn app.main:app --reload
```

## API

| Method | Path                     | Auth        | Description                                     |
| ------ | ------------------------ | ----------- | ----------------------------------------------- |
| GET    | `/health`                | No          | Liveness check                                  |
| GET    | `/visualizer`            | No          | Browser UI to test prompts and preview diagrams |
| POST   | `/diagrams/generate`     | `X-API-Key` | Generate and store a diagram                    |
| POST   | `/paid/diagrams/generate`| x402        | x402 paid generation endpoint                   |
| GET    | `/diagrams/{diagram_id}` | `X-API-Key` | Fetch a stored diagram                          |

### Generate diagram

```bash
curl -X POST http://localhost:8000/diagrams/generate \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "flowchart for user login", "diagram_type": "mermaid", "format": "svg"}'
```

## Environment variables

See [.env.example](.env.example).

Optional override:

- `MERMAID_INK_BASE_URL` (default: `https://mermaid.ink`)

x402 seller mode (Base Builder Code attribution):

- `X402_ENABLED=true`
- `X402_FACILITATOR_URL` (default: `https://x402.org/facilitator`)
- `X402_NETWORK` (default: `eip155:84532` for Base Sepolia testnet)
- `X402_PAY_TO` (wallet that receives payment)
- `X402_PRICE` (example: `$0.01`)
- `X402_BUILDER_CODE` (example: `bc_b7k3p9da`)

When enabled, `POST /paid/diagrams/generate` is payment-gated by x402 and
declares your Builder Code on the route for seller-side attribution.

For Base mainnet production, use:

- `X402_FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402`
- `X402_NETWORK=eip155:8453`

Get your real Builder Code at:

- https://dashboard.base.org → log in → select your app → **Settings → Builder Codes**

x402 buyer payment test (to verify you can receive settled payments):

1. Set buyer env vars in `.env`:
   - `X402_PAID_ENDPOINT_URL=http://127.0.0.1:8000/paid/diagrams/generate`
   - `EVM_PRIVATE_KEY=0x...` (funded buyer wallet key)
2. Run:
   - `.\.venv\Scripts\python.exe scripts\x402_buyer_payment_test.py`
3. Success criteria:
   - script prints `status 200`
   - script prints `payment_settled ...`

For testnet settlement (x402.org facilitator), buyer wallet must be funded on Base Sepolia with:
- testnet USDC (asset in the 402 challenge)
- enough ETH for gas/approval flow

## Visual preview in VS Code (Simple Browser)

1. Run the API: `uvicorn app.main:app --reload`
2. In VS Code: `Ctrl+Shift+P` → **Simple Browser: Show**
3. Enter: `http://127.0.0.1:8000/visualizer`
4. Paste your API key, choose type/format, enter text prompt, click **Generate**
