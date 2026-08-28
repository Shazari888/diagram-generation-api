# Agent Instructions

Canonical service: Diagram Generation API

Use the paid SVG route for inline SVG output:
POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/svg

Use the paid PNG route for base64 PNG output:
POST https://diagram-generation-api-production.up.railway.app/paid/diagrams/generate/png

Request body:
{"prompt":"...","diagram_type":"mermaid|d2|plantuml|graphviz"}

Payment: x402 v2 exact EVM on Base mainnet (eip155:8453), USDC. Call without payment to obtain PAYMENT-REQUIRED, sign the advertised payment, and retry with PAYMENT-SIGNATURE. Do not guess payment fields; use the challenge returned by the server.

SVG response: rendered is inline SVG text.
PNG response: rendered is base64-encoded PNG data.
Both responses include editable source in diagram.source.

Health: GET https://diagram-generation-api-production.up.railway.app/health
OpenAPI: https://diagram-generation-api-production.up.railway.app/openapi.json
Docs: https://diagram-generation-api-production.up.railway.app/docs

Do not assume endpoint paths, fields, prices, or payment values if the live OpenAPI or x402 challenge differs; verify the live contract first.
Update this file when the live API changes. Keep it synchronized with OpenAPI and README.
