
# Diagram Generation API

Create editable, rendered technical diagrams from natural-language instructions.

Diagram Generation API gives AI agents and developers a single API for turning a specification, workflow, schema, system description, or plan into:

- Editable Mermaid, D2, PlantUML, or Graphviz source code
- A rendered SVG artifact for web pages and documentation
- A rendered PNG artifact for reports, presentations, and external deliverables

The API supports API-key-protected evaluation routes and paid, pay-per-call x402 routes on Base mainnet using USDC.

## Why use this API?

Use this API when an application or autonomous agent needs a complete diagram artifact—not merely diagram-language source code.

A successful generation request handles this workflow:

```text
Natural-language requirement
  → diagram source generation
  → diagram rendering
  → SVG or PNG output
  → stored diagram record and cached repeat result
```

The API is useful when you want to avoid separately orchestrating prompting, diagram-language generation, renderer selection, format conversion, caching, persistent storage, and payment handling.

## Best use cases

- Technical architecture diagrams
- System and cloud infrastructure diagrams
- Flowcharts and business-process maps
- Sequence diagrams
- Entity-relationship diagrams
- Dependency and relationship graphs
- Codebase and service-topology documentation
- Automated technical reports, proposals, runbooks, and design documents
- Agent workflows that need reusable visual output

## When to call this API

Call this API when all of the following are true:

1. The task requires a visual diagram rather than text alone.
2. The input can be expressed as a natural-language prompt, workflow, plan, schema, or system description.
3. The caller needs editable diagram source, a rendered SVG/PNG artifact, or both.
4. The value of a complete visual artifact exceeds the request cost.

Do not use this API for:

- Freeform image generation or illustrations
- Interactive whiteboarding
- UI mockups or pixel-perfect visual design
- Hand-drawn artwork
- Handling wallet seeds, private keys, passwords, or other secrets
- Sensitive or regulated data unless you have independently reviewed the privacy and upstream-provider implications

## Features

- Generate diagrams from natural-language prompts
- Choose Mermaid, D2, PlantUML, or Graphviz source
- Render final output as inline SVG or base64-encoded PNG
- Return editable source with generated output
- Retrieve stored diagrams by ID
- Cache results in Redis to reduce redundant generation work
- Apply deterministic edits to existing supported diagram source
- Batch multiple edits into one request
- Use x402 pay-per-call payments with USDC on Base mainnet
- Test limited free/API-key routes through the API and browser visualizer

## Supported diagram types

| Diagram type | API key | Best use |
|---|---|---|
| Mermaid | `mermaid` | Default choice for flowcharts, sequences, documentation diagrams, and straightforward architecture diagrams |
| D2 | `d2` | Software architecture, infrastructure, and readable system diagrams |
| PlantUML | `plantuml` | UML-oriented class, sequence, component, and deployment diagrams |
| Graphviz | `graphviz` | Dependency graphs, directed graphs, relationship networks, and graph-oriented layouts |

If no diagram type is required, use `mermaid` as the default.

## Supported output formats

| Format | Returned value | Recommended use |
|---|---|---|
| `svg` | Inline SVG string in `rendered` | Documentation, websites, scalable visual output, and downstream SVG processing |
| `png` | Base64-encoded PNG string in `rendered` | Reports, presentations, messaging attachments, and raster-image workflows |

## Quickstart

### Generate an SVG diagram

```bash
curl -X POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/svg \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a Mermaid architecture diagram showing a browser, API server, PostgreSQL database, Redis cache, and payment facilitator.",
    "diagram_type": "mermaid"
  }'
```

### Generate a PNG diagram

```bash
curl -X POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/png \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a sequence diagram for OAuth login from a browser to an identity provider and then to an API.",
    "diagram_type": "mermaid"
  }'
```

Paid requests initially return `402 Payment Required` unless a valid x402 payment is supplied. Follow the payment flow below, then retry the same request with a `PAYMENT-SIGNATURE` header.

## Agent quickstart

Use the paid routes when an agent is authorized to spend USDC through x402:

- `POST /paid/diagrams/generate/svg` — returns editable source and inline SVG
- `POST /paid/diagrams/generate/png` — returns editable source and base64 PNG
- `POST /paid/diagrams/edit/svg` — applies validated edits and renders SVG
- `POST /paid/diagrams/edit/png` — applies validated edits and renders PNG

Required generation input:

```json
{
  "prompt": "Create a diagram of a browser calling an API which queries a database.",
  "diagram_type": "mermaid"
}
```

`prompt` is required and must be 1–4,000 characters. `diagram_type` is optional; use `mermaid` when uncertain.

## x402 payment model

Paid endpoints use x402 with the Exact EVM payment scheme.

| Item | Value |
|---|---|
| Network | Base mainnet |
| CAIP-2 network ID | `eip155:8453` |
| Asset | USDC |
| USDC contract | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Facilitator | `https://facilitator.xpay.sh` |
| Settlement | On-chain verification through the xpay facilitator |

### Pricing

| Operation | Price |
|---|---:|
| Generate SVG | $0.05 USDC |
| Generate PNG | $0.07 USDC |
| Edit and render SVG | $0.05 USDC |
| Edit and render PNG | $0.05 USDC |

### Payment flow

1. Call a paid generation or editing endpoint without payment.
2. Receive `402 Payment Required`.
3. Read the base64-encoded `PAYMENT-REQUIRED` response header.
4. Create and sign a payment using one accepted payment option from the challenge.
5. Retry the same request with the signed `PAYMENT-SIGNATURE` header.
6. Receive the generated or edited diagram response on successful verification.

Do not send private keys, wallet seeds, passwords, or facilitator secrets to this API.

## API routes

| Method | Path | Authentication / payment | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| `GET` | `/visualizer` | None | Browser-based visualizer UI |
| `POST` | `/diagrams/generate` | `X-API-Key` | Generate a diagram; limited free evaluation route |
| `POST` | `/diagrams/edit` | `X-API-Key` | Edit supported diagram source; limited free evaluation route |
| `POST` | `/paid/diagrams/generate/svg` | x402 payment | Generate editable source and rendered SVG |
| `POST` | `/paid/diagrams/generate/png` | x402 payment | Generate editable source and rendered PNG |
| `POST` | `/paid/diagrams/edit/svg` | x402 payment | Edit source and render SVG |
| `POST` | `/paid/diagrams/edit/png` | x402 payment | Edit source and render PNG |
| `GET` | `/diagrams/{id}` | `X-API-Key` | Retrieve a stored diagram |

Free generation and editing routes are limited to 5 requests per day per IP. Paid routes are rate-limited per IP.

## Generation response

### SVG response

```json
{
  "diagram": {
    "id": "example-uuid",
    "prompt": "Create a simple client-server architecture diagram.",
    "source": "graph TD; Client --> API; API --> Database;",
    "diagram_type": "mermaid",
    "created_at": "2026-01-01T00:00:00Z"
  },
  "rendered": "<svg xmlns=\"http://www.w3.org/2000/svg\">...</svg>",
  "format": "svg"
}
```

### PNG response

```json
{
  "diagram": {
    "id": "example-uuid",
    "prompt": "Create a simple client-server architecture diagram.",
    "source": "graph TD; Client --> API; API --> Database;",
    "diagram_type": "mermaid",
    "created_at": "2026-01-01T00:00:00Z"
  },
  "rendered": "iVBORw0KGgoAAAANSUhEUgAA...",
  "format": "png"
}
```

### Output interpretation

- `diagram.source` contains editable diagram source.
- `rendered` contains inline SVG text when `format` is `svg`.
- `rendered` contains base64-encoded PNG data when `format` is `png`.
- `diagram.id` identifies the persisted diagram record.

## Diagram editing

Use editing routes when you already have supported diagram source and need controlled changes rather than a new AI-generated diagram.

Each editing request accepts an ordered `operations` array. Operations are applied in sequence and validated using a discriminated union.

### Supported edit operations

| Category | Operation | Description |
|---|---|---|
| Text | `replace_text` | Replace all occurrences of a substring |
| Text | `rename_node` | Rename a node ID, such as `A` to `B` |
| Text | `add_line` | Append a line to the source |
| Text | `remove_line_contains` | Remove source lines containing a substring |
| Text | `prepend_text` | Add text to the beginning of the source |
| Text | `append_text` | Add text to the end of the source |
| Style | `set_node_shape` | Set a node shape, such as rectangle, round, or rhombus |
| Style | `set_node_color` | Set fill, stroke, text color, or stroke width |
| Style | `set_node_font_size` | Set a node font size |
| Style | `set_node_size` | Set node font size and/or padding |
| Style | `set_link_color` | Set link or edge colors globally |
| Style | `set_theme` | Apply `default`, `neutral`, `dark`, `forest`, or `base` |
| Style | `set_global_font_size` | Set a global font size |

### Editing example

```bash
curl -X POST https://diagram-generation-api-production.up.railway.app/diagrams/edit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{
    "diagram_source": "graph TD\nA[Login] --> B[Check]\nB --> C[Success]",
    "diagram_type": "mermaid",
    "format": "svg",
    "operations": [
      {
        "type": "replace_text",
        "from": "Check",
        "to": "Verify"
      },
      {
        "type": "set_node_color",
        "node_id": "A",
        "fill": "#dbeafe",
        "stroke": "#1d4ed8"
      }
    ],
    "render_after_edit": true
  }'
```

### Editing response

```json
{
  "ok": true,
  "endpoint": "/diagrams/edit",
  "diagram_type": "mermaid",
  "format": "svg",
  "edited_diagram_source": "graph TD\nA[Login] --> B[Verify]\nB --> C[Success]",
  "rendered": "<svg>...</svg>",
  "metadata": {
    "operations_applied": 2,
    "render_after_edit": true
  }
}
```

Batch operations in one edit request when possible. This reduces repeated calls and, on paid routes, reduces the number of x402 settlements.

## Error handling

| Status | Meaning | Recommended client action |
|---|---|---|
| `400` / `422` | Invalid prompt, format, diagram type, or request schema | Correct the input; do not repeatedly submit the same invalid request |
| `402` | Payment required | Parse `PAYMENT-REQUIRED`, sign an accepted payment, and retry the same request with `PAYMENT-SIGNATURE` |
| `429` | Rate limit exceeded | Respect `Retry-After` when supplied; otherwise use bounded exponential backoff |
| `503` | Upstream LLM or renderer unavailable | Retry later with bounded exponential backoff |
| Other `5xx` | Unexpected server error | Retry only a limited number of times and preserve request/payment context |

Clients should avoid uncontrolled retries on paid routes. Confirm your payment and idempotency handling before retrying a request that may already have settled.

## Rendering pipeline

| Diagram type | SVG renderer | PNG renderer |
|---|---|---|
| Mermaid | mermaid.ink primary, Kroki fallback | mermaid.ink, then conversion when required |
| D2 | Kroki | Kroki |
| PlantUML | Kroki | Kroki |
| Graphviz | Kroki | Kroki |

Mermaid uses mermaid.ink first because it is typically faster and avoids the headless-browser limitations that can affect some Mermaid rendering environments. Other supported types render through Kroki. If a renderer does not natively produce PNG, the service renders SVG first and converts it.

## OpenAPI, docs, and live service

- Live API: https://diagram-generation-api-production.up.railway.app
- OpenAPI: https://diagram-generation-api-production.up.railway.app/openapi.json
- Swagger UI: https://diagram-generation-api-production.up.railway.app/docs
- Health check: https://diagram-generation-api-production.up.railway.app/health
- Visualizer: https://diagram-generation-api-production.up.railway.app/visualizer
- Repository: https://github.com/Shazari888/diagram-generation-api

## Local setup

### Prerequisites

- Python 3.11+
- PostgreSQL, or SQLite for local development
- Redis
- OpenAI API key
- EVM wallet with USDC on Base mainnet for paid-route buyer testing

### Install

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Fill in the required `.env` values before starting the application.

### Run locally

```bash
uvicorn app.main:app --reload
```

The default local URL is `http://127.0.0.1:8000`.

### Test a local x402 buyer payment

```bash
python scripts/x402_buyer_payment_test.py
```

Set the buyer wallet private key in `.env` as `EVM_PRIVATE_KEY`.

The buyer wallet must be different from the seller wallet configured in `X402_PAY_TO` and must have USDC on Base mainnet.

## Railway deployment

1. Create a Railway project and connect this repository.
2. Add a PostgreSQL service and copy its `DATABASE_URL`.
3. Add a Redis service and copy its `REDIS_URL`.
4. Configure the required environment variables.
5. Deploy. Railway builds from the repository `Dockerfile`.
6. Confirm deployment through `GET /health`, which should return `{"status":"ok"}`.

### Required environment variables

| Variable | Description |
|---|---|
| `API_KEY` | Strong secret for API-key-protected routes |
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `X402_ENABLED` | Set to `true` to enable paid x402 routes |
| `X402_FACILITATOR_URL` | `https://facilitator.xpay.sh` |
| `X402_NETWORK` | `eip155:8453` |
| `X402_PAY_TO` | Seller wallet address that receives USDC |
| `X402_PRICE_SVG` | `$0.05` |
| `X402_PRICE_PNG` | `$0.07` |

### Optional environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | Set a higher-capability model if required |
| `KROKI_BASE_URL` | `https://kroki.io` | Override for a self-hosted Kroki deployment |
| `MERMAID_INK_BASE_URL` | `https://mermaid.ink` | Override Mermaid renderer base URL |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL in seconds |
| `LOGTAIL_TOKEN` | Unset | Better Stack structured-logging token |

See [`.env.example`](https://github.com/Shazari888/diagram-generation-api/blob/main/.env.example) for the full configuration template.

## Data and privacy

- Never send private keys, wallet seeds, passwords, or other secrets.
- Prompts, generated source, rendered artifacts, and request metadata may be stored for retrieval, caching, debugging, and audit purposes.
- Generation and rendering may involve third-party AI and diagram-rendering providers.
- Mermaid requests may be sent to mermaid.ink. Other supported diagram types use Kroki unless you configure alternative renderer URLs.
- Review the data-handling practices of all applicable providers before sending confidential, personal, regulated, or proprietary information.
- Do not treat the public hosted service as approved for sensitive data without an independent security and privacy review.

## Support and security

- GitHub Issues: https://github.com/Shazari888/diagram-generation-api/issues
- Email: internetprosperity888@gmail.com
- Never submit secrets in GitHub issues, prompts, API requests, or support messages.

## Changelog

### v1.0.0

- Production launch
- x402 pay-per-call diagram generation on Base mainnet
- USDC payment support
- Mermaid, D2, PlantUML, and Graphviz generation
- SVG and PNG rendered output
- Deterministic diagram editing
- Agent-oriented documentation and metadata

