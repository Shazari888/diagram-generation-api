import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/diagrams/generate", response_model=GenerateDiagramResponse)
async def generate_diagram(
    body: GenerateDiagramRequest,
    session: AsyncSession = Depends(db.get_session),
    _: str = Depends(verify_api_key),
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
