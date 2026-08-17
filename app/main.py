from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI
from x402 import x402ResourceServer
from x402.extensions.builder_code.server import declare_builder_code_extension
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.http.types import PaymentOption, RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from app.api.routes import router
from app.config import settings
from app.mpp import StripeMppMiddleware
from app.services import cache, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await cache.connect()
    yield
    await cache.disconnect()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

# Stripe MPP payment gating for /paid/diagrams/generate/*
if settings.stripe_secret_key and settings.stripe_profile_id:
    app.add_middleware(
        StripeMppMiddleware,
        stripe_secret_key=settings.stripe_secret_key,
        stripe_profile_id=settings.stripe_profile_id,
    )


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

    route_extensions = (
        declare_builder_code_extension(settings.x402_builder_code)
        if settings.x402_builder_code
        else None
    )

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

    @app.middleware("http")
    async def x402_http_middleware(request, call_next):
        return await _x402_middleware(request, call_next)
