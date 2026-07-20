import httpx

from app.config import settings


async def render(source: str, diagram_type: str, output_format: str = "svg") -> str:
    url = f"{settings.kroki_base_url}/{diagram_type}/{output_format}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            content=source.encode(),
            headers={"Content-Type": "text/plain"},
            timeout=30.0,
        )
        response.raise_for_status()
    return response.text
