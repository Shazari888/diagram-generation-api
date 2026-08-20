from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from x402 import x402ResourceServer
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.http.types import PaymentOption, RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from app.api.routes import router
from app.config import settings
from app.security import (
    https_redirect_middleware,
    install_log_filter,
    limiter,
    record_payment_failure,
)
from app.services import cache, db

install_log_filter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await cache.connect()
    yield
    await cache.disconnect()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Rate limiter state
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Please slow down."})

app.include_router(router)

def _build_cdp_facilitator_config() -> dict[str, object]:
    if not settings.cdp_api_key_id or not settings.cdp_api_key_secret:
        raise ValueError(
            "CDP_API_KEY_ID and CDP_API_KEY_SECRET are required for CDP x402 facilitator."
        )

    try:
        from cdp.auth.utils.jwt import JwtOptions, generate_jwt
    except ImportError as exc:
        raise ValueError(
            "cdp-sdk is required to authenticate with CDP x402 facilitator."
        ) from exc

    parsed = urlparse(settings.x402_facilitator_url)
    request_host = parsed.netloc
    base_path = parsed.path.rstrip("/")
    if not request_host or not base_path:
        raise ValueError("X402_FACILITATOR_URL must include host and path.")

    key_secret = settings.cdp_api_key_secret.replace("\\n", "\n")

    def _jwt_for(method: str, path: str) -> str:
        return generate_jwt(
            JwtOptions(
                api_key_id=settings.cdp_api_key_id,
                api_key_secret=key_secret,
                request_method=method,
                request_host=request_host,
                request_path=path,
                expires_in=120,
            )
        )

    def _create_headers() -> dict[str, dict[str, str]]:
        return {
            "supported": {
                "Authorization": f"Bearer {_jwt_for('GET', f'{base_path}/supported')}"
            },
            "verify": {
                "Authorization": f"Bearer {_jwt_for('POST', f'{base_path}/verify')}"
            },
            "settle": {
                "Authorization": f"Bearer {_jwt_for('POST', f'{base_path}/settle')}"
            },
        }

    return {"url": settings.x402_facilitator_url, "create_headers": _create_headers}


if settings.x402_enabled:
    if not settings.x402_pay_to:
        raise ValueError("X402_PAY_TO is required when X402_ENABLED=true")

    if "api.cdp.coinbase.com" in settings.x402_facilitator_url:
        facilitator = HTTPFacilitatorClient(_build_cdp_facilitator_config())
    else:
        facilitator = HTTPFacilitatorClient(
            FacilitatorConfig(url=settings.x402_facilitator_url)
        )
    x402_server = x402ResourceServer(facilitator).register(
        settings.x402_network, ExactEvmServerScheme()
    )

    route_extensions = None

    _format_prices = {
        "svg": settings.x402_price_svg,
        "png": settings.x402_price_png,
    }

    x402_routes = {
        f"POST /paid/diagrams/generate/{fmt}": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                network=settings.x402_network,
                pay_to=settings.x402_pay_to,
                price=price,
            ),
            description=f"Generate and store a diagram ({fmt} format)",
            mime_type="application/json",
            **({"extensions": route_extensions} if route_extensions else {}),
        )
        for fmt, price in _format_prices.items()
    }
    _x402_middleware = payment_middleware(x402_routes, x402_server)

    _PAID_PATHS = {f"/paid/diagrams/generate/{fmt}" for fmt in _format_prices}

    @app.middleware("http")
    async def x402_http_middleware(request: Request, call_next):
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()

        # Rate-limit paid endpoints before x402 even issues a challenge
        if request.method == "POST" and request.url.path in _PAID_PATHS:
            from app.services.cache import increment_counter
            count = await increment_counter(f"ratelimit:paid:{client_ip}", 60)
            if count > 20:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Please slow down."})

        response = await _x402_middleware(request, call_next)
        if response.status_code == 402:
            record_payment_failure(client_ip, request.url.path)
        return response


# HTTPS enforcement — outermost layer, registered after x402 so it runs first
@app.middleware("http")
async def enforce_https_middleware(request: Request, call_next):
    return await https_redirect_middleware(request, call_next)
