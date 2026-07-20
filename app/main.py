from contextlib import asynccontextmanager

from fastapi import FastAPI

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
