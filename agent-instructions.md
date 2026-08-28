# Diagram Generation and Editing API — Agent Instructions

This document provides autonomous agents with a canonical specification for integrating with the Diagram Generation and Editing API.

---

## API Overview

The API generates and edits Mermaid, D2, PlantUML, and Graphviz diagrams from natural-language prompts and deterministic operations. Paid endpoints are protected with x402 USDC settlement on Base mainnet (xpay facilitator).

**Base URL:** `https://diagram-generation-api-production.up.railway.app`

---

## Endpoints

### Free Endpoints

#### `POST /diagrams/generate`
Generate a diagram from a natural-language prompt.

**Auth:** `X-API-Key` header

**Rate limit:** 5/day per IP

**Request:**
```json
{
  "prompt": "Create a login flow with success and retry paths",
  "diagram_type": "mermaid"
}
```

**Response:**
```json
{
  "diagram": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "Create a login flow...",
    "source": "graph TD\n  A[Login] --> B{Success?}\n  B -->|Yes| C[Dashboard]\n  B -->|No| A",
    "diagram_type": "mermaid",
    "created_at": "2026-08-21T10:00:00"
  },
  "rendered": "<svg>...</svg>",
  "format": "svg"
}
```

---

#### `POST /diagrams/edit`
Apply deterministic operations to diagram source code.

**Auth:** `X-API-Key` header

**Rate limit:** 5/day per IP

**Request:**
```json
{
  "diagram_source": "graph TD\nA[Login] --> B[Success]",
  "diagram_type": "mermaid",
  "format": "svg",
  "operations": [
    { "type": "replace_text", "from": "Login", "to": "Authentication" },
    { "type": "set_node_color", "node_id": "A", "fill": "#dbeafe", "stroke": "#1d4ed8" }
  ],
  "render_after_edit": true
}
```

**Response:**
```json
{
  "ok": true,
  "endpoint": "/diagrams/edit",
  "diagram_type": "mermaid",
  "format": "svg",
  "edited_diagram_source": "graph TD\nA[Authentication] --> B[Success]\nstyle A fill:#dbeafe,stroke:#1d4ed8",
  "rendered": "<svg>...</svg>",
  "metadata": {
    "operations_applied": 2,
    "render_after_edit": true
  }
}
```

---

### Paid Endpoints (x402 Settlement)

#### `POST /paid/diagrams/generate/svg`
Generate a diagram and render as SVG (0.05 USDC).

#### `POST /paid/diagrams/generate/png`
Generate a diagram and render as PNG (0.05 USDC).

#### `POST /paid/diagrams/edit/svg`
Edit diagram source and render as SVG (0.05 USDC).

#### `POST /paid/diagrams/edit/png`
Edit diagram source and render as PNG (0.05 USDC).

**Auth:** x402 USDC payment on Base mainnet

**Request:** Same as free endpoints (generate/edit)

**Payment Flow:**

1. Client calls endpoint without payment
2. Server returns `402 Payment Required` with `PAYMENT-REQUIRED` header (base64-encoded challenge)
3. Client decodes challenge and signs with EVM wallet (Base mainnet USDC)
4. Client retries with `PAYMENT-SIGNATURE` header
5. Server verifies signature via xpay facilitator
6. Endpoint proceeds and returns result

---

## Edit Operations

Each edit request accepts a list of operations (max 100) applied in sequence.

### Text Operations

**`replace_text`**
```json
{ "type": "replace_text", "from": "old text", "to": "new text" }
```

**`rename_node`**
```json
{ "type": "rename_node", "from": "A", "to": "B" }
```

**`add_line`**
```json
{ "type": "add_line", "line": "C --> D[New Node]" }
```

**`remove_line_contains`**
```json
{ "type": "remove_line_contains", "contains": "substring" }
```

**`prepend_text`**
```json
{ "type": "prepend_text", "text": "%%{init: {...}}%%" }
```

**`append_text`**
```json
{ "type": "append_text", "text": "Additional content" }
```

### Style Operations

**`set_node_shape`**
```json
{
  "type": "set_node_shape",
  "node_id": "A",
  "shape": "rectangle|round|stadium|subroutine|cylindrical|circle|asymmetric|rhombus|hexagon|parallelogram|parallelogram_alt|trapezoid|trapezoid_alt",
  "label": "optional custom label"
}
```

**`set_node_color`** (at least one required)
```json
{
  "type": "set_node_color",
  "node_id": "A",
  "fill": "#dbeafe",
  "stroke": "#1d4ed8",
  "text_color": "#1e3a8a",
  "stroke_width_px": 2
}
```

**`set_node_font_size`**
```json
{
  "type": "set_node_font_size",
  "node_id": "A",
  "font_size_px": 14
}
```

**`set_node_size`** (at least one required)
```json
{
  "type": "set_node_size",
  "node_id": "A",
  "font_size_px": 14,
  "padding_px": 8
}
```

**`set_link_color`** (at least one required)
```json
{
  "type": "set_link_color",
  "stroke": "#ff0000",
  "text_color": "#000000",
  "stroke_width_px": 2
}
```

**`set_theme`**
```json
{
  "type": "set_theme",
  "theme": "default|neutral|dark|forest|base"
}
```

**`set_global_font_size`**
```json
{
  "type": "set_global_font_size",
  "font_size_px": 12
}
```

---

## Diagram Types and Formats

**Diagram Types:** `mermaid`, `d2`, `plantuml`, `graphviz`

**Output Formats:** `svg`, `png`

---

## Error Responses

All error responses follow this structure:

```json
{
  "ok": false,
  "status_code": 400,
  "endpoint": "/diagrams/edit",
  "error": "set_node_color requires at least one style field",
  "user_action": "Provide fill, stroke, text_color, or stroke_width_px."
}
```

**Common Status Codes:**
- `400` Invalid request schema or operation
- `401` Authentication failed (missing/invalid API key)
- `402` Payment required (x402 challenge issued)
- `429` Rate limit exceeded
- `503` Upstream service unavailable (OpenAI/renderer failure)

---

## Pricing

| Endpoint | Price | Limit |
|---|---|---|
| `/diagrams/generate` | Free | 5/day per IP |
| `/diagrams/edit` | Free | 5/day per IP |
| `/paid/diagrams/generate/*` | $0.05 USDC | Unlimited |
| `/paid/diagrams/edit/*` | $0.05 USDC | Unlimited |

Each API call (one edit or one generation) = one USDC settlement.

---

## Implementation Notes for Agents

1. **Batch operations:** Users can combine multiple style/text changes into one edit call to minimize cost.

2. **Rendering optional:** Pass `render_after_edit: false` to get edited source without rendering (free, fast).

3. **Deterministic:** All edit operations are deterministic (same input → same output). Safe for idempotency.

4. **Mermaid primary:** Mermaid diagrams render via mermaid.ink; all others use Kroki.

5. **API key:** Set `X-API-Key` header for free endpoints. Use any non-empty string for local dev (`X-API-Key: test`).

6. **x402 Payment:** xpay facilitator handles wallets automatically. Only the seller wallet (`X402_PAY_TO`) receives USDC; buyer wallet must hold USDC on Base mainnet.

---

## Links

- **OpenAPI Spec:** `https://diagram-generation-api-production.up.railway.app/openapi.json`
- **Health Check:** `https://diagram-generation-api-production.up.railway.app/health`
- **Browser Visualizer:** `https://diagram-generation-api-production.up.railway.app/visualizer`
- **Facilitator:** `https://facilitator.xpay.sh`
- **x402 Protocol:** `https://x402.org`
- **xpay:** `https://xpay.sh`
