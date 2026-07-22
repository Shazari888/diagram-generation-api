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

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness check |
| POST | `/diagrams/generate` | `X-API-Key` | Generate and store a diagram |
| GET | `/diagrams/{diagram_id}` | `X-API-Key` | Fetch a stored diagram |

### Generate diagram

```bash
curl -X POST http://localhost:8000/diagrams/generate \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "flowchart for user login", "diagram_type": "mermaid", "format": "svg"}'
```

## Environment variables

See [.env.example](.env.example).
