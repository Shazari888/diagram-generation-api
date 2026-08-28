# Diagram Generation API

Pay-per-call diagram generation for autonomous agents: convert a natural-language specification, plan, schema, or workflow into Mermaid, D2, PlantUML, or Graphviz source and a rendered SVG or PNG artifact.

## Agent quickstart

Use `POST /paid/diagrams/generate/svg` for inline SVG output or `POST /paid/diagrams/generate/png` for base64 PNG output. Send a JSON body with `prompt` and optionally `diagram_type`; the server returns editable source in `diagram.source` and the rendered artifact in `rendered`.

Paid requests use x402 v2 on Base mainnet (`eip155:8453`) with USDC. An unpaid request receives HTTP `402` and a `PAYMENT-REQUIRED` challenge header. The buyer signs the advertised payment and retries the same request with `PAYMENT-SIGNATURE`.

## Supported capabilities

- Diagram types: `mermaid`, `d2`, `plantuml`, `graphviz`
- Output formats: `svg`, `png`
- Prompt limit: 1–4000 characters
- Use cases: architecture diagrams, flowcharts, sequence diagrams, ER diagrams, dependency graphs, and technical workflow documentation

## x402 payment flow

1. Call the paid SVG or PNG route without payment.
2. Receive `402 Payment Required` and the base64-encoded `PAYMENT-REQUIRED` challenge header.
3. Create and sign a payment from one of the advertised `accepts` entries.
4. Retry the same request with `PAYMENT-SIGNATURE`.
5. On success, the response includes `diagram.source`, `rendered`, and `format`.

### Pricing

| Format | Price |
|---|---|
| SVG | $0.05 USDC |
| PNG | $0.07 USDC |

### Network

- Base mainnet: `eip155:8453`
- Asset: USDC
- USDC contract: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

## Request examples

### SVG architecture example

```bash
curl -X POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/svg \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create an architecture diagram for a browser, API server, PostgreSQL database, Redis cache, and payment facilitator.","diagram_type":"mermaid"}'
```

### PNG sequence example

```bash
curl -X POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/png \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a sequence diagram for OAuth login from browser to identity provider to API.","diagram_type":"mermaid"}'
```

## Response examples

### SVG

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

### PNG

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

## Error handling

- `400` / `422`: invalid prompt or schema
- `402`: payment required; read `PAYMENT-REQUIRED`, sign it, and retry with `PAYMENT-SIGNATURE`
- `429`: rate limit exceeded
- `503`: upstream renderer or LLM unavailable; retry later

## Output interpretation

- `diagram.source` is editable source code
- `rendered` is inline SVG text when `format` is `svg`
- `rendered` is base64-encoded PNG when `format` is `png`

## Agent/MCP integration

The service is suitable for agent workflows that need pay-per-call diagram generation. Use the paid routes directly and preserve the returned source for later edits or regeneration.

## OpenAPI and docs

- OpenAPI: `https://diagram-generation-api-production.up.railway.app/openapi.json`
- Swagger UI: `https://diagram-generation-api-production.up.railway.app/docs`
- Health: `https://diagram-generation-api-production.up.railway.app/health`
- Repository: `https://github.com/Shazari888/diagram-generation-api`

## Reliability and limits

- Free visualizer requests are capped at 5/day per IP
- Paid routes are rate-limited per IP
- Mermaid uses mermaid.ink first; other diagram types use Kroki
- Prompt length is capped at 4000 characters

## Data and privacy

- Do not send private keys, wallet seeds, or facilitator secrets
- Prompts, generated source, and rendered artifacts may be stored for retrieval
- Logs may include request metadata for debugging and audit purposes

## Support and security

- Issues: `https://github.com/Shazari888/diagram-generation-api/issues`
- Never submit private keys or wallet seeds to the API

## Changelog

- v1.0.0: production launch with x402 pay-per-call diagram generation, SVG/PNG output, and agent-oriented metadata
