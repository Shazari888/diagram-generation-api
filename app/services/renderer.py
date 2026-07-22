import asyncio
import base64

import httpx

from app.config import settings


def _convert_svg(svg_bytes: bytes, output_format: str) -> bytes:
    try:
        import cairosvg
    except Exception as exc:  # pragma: no cover - depends on runtime system libs
        raise RuntimeError(
            "SVG conversion requires CairoSVG and system cairo libraries."
        ) from exc

    if output_format == "png":
        return cairosvg.svg2png(bytestring=svg_bytes)
    if output_format == "pdf":
        return cairosvg.svg2pdf(bytestring=svg_bytes)
    raise ValueError(f"Unsupported conversion format: {output_format}")


def _is_retryable_kroki_failure(response: httpx.Response) -> bool:
    if response.status_code in {429, 500, 502, 503, 504}:
        return True
    if response.status_code != 400:
        return False
    body = response.text.lower()
    return "failed to launch the browser process" in body or "resource temporarily unavailable" in body


async def _post_kroki(client: httpx.AsyncClient, url: str, source: str) -> httpx.Response:
    delays = [0.4, 1.0, 2.0]
    attempt = 0
    while True:
        try:
            response = await client.post(
                url,
                content=source.encode(),
                headers={"Content-Type": "text/plain"},
                timeout=30.0,
            )
        except httpx.TransportError:
            if attempt >= len(delays):
                raise
            await asyncio.sleep(delays[attempt])
            attempt += 1
            continue

        if response.is_success or not _is_retryable_kroki_failure(response) or attempt >= len(delays):
            return response

        await asyncio.sleep(delays[attempt])
        attempt += 1


async def render(source: str, diagram_type: str, output_format: str = "svg") -> str:
    url = f"{settings.kroki_base_url}/{diagram_type}/{output_format}"
    async with httpx.AsyncClient() as client:
        response = await _post_kroki(client, url, source)
    if response.is_success:
        if output_format == "svg":
            return response.text
        return base64.b64encode(response.content).decode("ascii")

    if output_format in {"png", "pdf"} and response.status_code == 400:
        svg_url = f"{settings.kroki_base_url}/{diagram_type}/svg"
        async with httpx.AsyncClient() as client:
            svg_response = await _post_kroki(client, svg_url, source)
        svg_response.raise_for_status()
        converted_bytes = _convert_svg(svg_response.content, output_format)
        return base64.b64encode(converted_bytes).decode("ascii")

    response.raise_for_status()
    return response.text
