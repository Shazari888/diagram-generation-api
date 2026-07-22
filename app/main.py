from contextlib import asynccontextmanager

from fastapi import FastAPI
from x402 import x402ResourceServer
from x402.extensions.builder_code.server import declare_builder_code_extension
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.http.types import PaymentOption, RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from app.api.routes import router
from app.config import settings
from app.services import cache, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await cache.connect()
    yield
    await cache.disconnect()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

if settings.x402_enabled:
    if not settings.x402_pay_to:
        raise ValueError("X402_PAY_TO is required when X402_ENABLED=true")
    if not settings.x402_builder_code:
        raise ValueError("X402_BUILDER_CODE is required when X402_ENABLED=true")

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=settings.x402_facilitator_url)
    )
    x402_server = x402ResourceServer(facilitator).register(
        settings.x402_network, ExactEvmServerScheme()
    )
    x402_routes = {
        "POST /paid/diagrams/generate": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                network=settings.x402_network,
                pay_to=settings.x402_pay_to,
                price=settings.x402_price,
            ),
            description="Generate and store a diagram",
            mime_type="application/json",
            extensions=declare_builder_code_extension(settings.x402_builder_code),
        )
    }
    _x402_middleware = payment_middleware(x402_routes, x402_server)

    @app.middleware("http")
    async def x402_http_middleware(request, call_next):
        return await _x402_middleware(request, call_next)
