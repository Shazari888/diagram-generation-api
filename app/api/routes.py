import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    DiagramResponse,
    GenerateDiagramRequest,
    GenerateDiagramResponse,
    HealthResponse,
)
from app.auth import verify_api_key
from app.services import cache, db, llm, renderer

router = APIRouter()


VISUALIZER_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Diagram API Visualizer</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; color: #111; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
    input, select, textarea, button { font-size: 14px; padding: 8px; }
    textarea { width: 100%; min-height: 90px; }
    #preview { border: 1px solid #ddd; border-radius: 6px; padding: 12px; min-height: 200px; background: #fafafa; }
    #status { margin: 10px 0; white-space: pre-wrap; }
    #source { margin-top: 12px; width: 100%; min-height: 120px; font-family: Consolas, monospace; }
    .hint { margin: 8px 0 12px; padding: 10px; border-radius: 6px; background: #eef6ff; border: 1px solid #c8ddff; }
    .hint a { margin-right: 12px; }
    iframe, img, svg { max-width: 100%; }
  </style>
</head>
<body>
  <h2>Diagram API Visualizer</h2>
  <div class="row">
    <input id="apiKey" placeholder="X-API-Key" style="min-width: 280px;" />
    <select id="diagramType">
      <option value="mermaid">mermaid</option>
      <option value="d2">d2</option>
      <option value="plantuml">plantuml</option>
      <option value="graphviz">graphviz</option>
    </select>
    <select id="format">
      <option value="svg">svg</option>
      <option value="png">png</option>
      <option value="pdf">pdf</option>
    </select>
    <button id="generateBtn">Generate</button>
  </div>
  <textarea id="prompt">Create a login flow with success and retry paths.</textarea>
  <div id="status"></div>
  <div id="preview"></div>
  <textarea id="source" readonly placeholder="Generated diagram source appears here"></textarea>

  <script>
    const statusEl = document.getElementById("status");
    const previewEl = document.getElementById("preview");
    const sourceEl = document.getElementById("source");
    let currentPdfObjectUrl = null;

    function base64ToBlobUrl(base64Data, mimeType) {
      const raw = atob(base64Data);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) {
        bytes[i] = raw.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: mimeType });
      return URL.createObjectURL(blob);
    }

    function setStatus(text, isError) {
      statusEl.style.color = isError ? "#b00020" : "#0b5";
      statusEl.textContent = text;
    }

    async function generate() {
      setStatus("Generating...", false);
      previewEl.innerHTML = "";
      sourceEl.value = "";
      if (currentPdfObjectUrl) {
        URL.revokeObjectURL(currentPdfObjectUrl);
        currentPdfObjectUrl = null;
      }

      const body = {
        prompt: document.getElementById("prompt").value,
        diagram_type: document.getElementById("diagramType").value,
        format: document.getElementById("format").value,
      };

      try {
        const res = await fetch("/diagrams/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": document.getElementById("apiKey").value,
          },
          body: JSON.stringify(body),
        });

        const raw = await res.text();
        let data = null;
        try {
          data = JSON.parse(raw);
        } catch {
          data = null;
        }

        if (!res.ok) {
          const errorText = (data && data.detail)
            ? data.detail
            : (raw || ("HTTP " + res.status));
          throw new Error(errorText);
        }

        if (!data) {
          throw new Error("Server returned a non-JSON success response.");
        }

        sourceEl.value = data.diagram.source || "";

        if (data.format === "svg") {
          previewEl.innerHTML = data.rendered;
        } else if (data.format === "png") {
          previewEl.innerHTML = '<img alt="PNG diagram preview" src="data:image/png;base64,' + data.rendered + '" />';
        } else if (data.format === "pdf") {
          const pdfUrl = base64ToBlobUrl(data.rendered, "application/pdf");
          currentPdfObjectUrl = pdfUrl;
          previewEl.innerHTML =
            '<div class="hint">' +
            'PDF generated successfully. If preview is blank in this embedded browser, use this link: ' +
            '<a href="' + pdfUrl + '" download="diagram.pdf">Download PDF</a>' +
            '</div>' +
            '<iframe title="PDF diagram preview" style="width:100%;height:700px;border:0;" src="' + pdfUrl + '"></iframe>';
        }

        setStatus("Success: " + data.diagram.id, false);
      } catch (err) {
        setStatus("Error: " + err.message, true);
      }
    }

    document.getElementById("generateBtn").addEventListener("click", generate);
  </script>
</body>
</html>
"""


@router.get("/visualizer", response_class=HTMLResponse)
async def visualizer() -> HTMLResponse:
    return HTMLResponse(content=VISUALIZER_HTML)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


async def _generate_diagram(
    body: GenerateDiagramRequest,
    session: AsyncSession,
) -> GenerateDiagramResponse:
    cache_payload = {
        "prompt": body.prompt,
        "diagram_type": body.diagram_type,
        "format": body.format,
    }

    cached = await cache.get_cached("diagram", cache_payload)
    if cached:
        data = json.loads(cached)
        diagram = await db.get_diagram(session, UUID(data["id"]))
        if diagram:
            return GenerateDiagramResponse(
                diagram=DiagramResponse.model_validate(diagram),
                rendered=data["rendered"],
                format=body.format,
            )

    source = await llm.generate_source(body.prompt, body.diagram_type)
    try:
        rendered = await renderer.render(source, body.diagram_type, body.format)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    diagram = await db.create_diagram(
        session,
        prompt=body.prompt,
        source=source,
        diagram_type=body.diagram_type,
    )

    await cache.set_cached(
        "diagram",
        cache_payload,
        json.dumps({"id": str(diagram.id), "rendered": rendered}),
    )

    return GenerateDiagramResponse(
        diagram=DiagramResponse.model_validate(diagram),
        rendered=rendered,
        format=body.format,
    )


@router.post("/diagrams/generate", response_model=GenerateDiagramResponse)
async def generate_diagram(
    body: GenerateDiagramRequest,
    session: AsyncSession = Depends(db.get_session),
    _: str = Depends(verify_api_key),
) -> GenerateDiagramResponse:
    return await _generate_diagram(body, session)


@router.post("/paid/diagrams/generate", response_model=GenerateDiagramResponse)
async def generate_diagram_paid(
    body: GenerateDiagramRequest,
    session: AsyncSession = Depends(db.get_session),
) -> GenerateDiagramResponse:
    return await _generate_diagram(body, session)


@router.get("/diagrams/{diagram_id}", response_model=DiagramResponse)
async def get_diagram(
    diagram_id: UUID,
    session: AsyncSession = Depends(db.get_session),
    _: str = Depends(verify_api_key),
) -> DiagramResponse:
    diagram = await db.get_diagram(session, diagram_id)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return DiagramResponse.model_validate(diagram)
