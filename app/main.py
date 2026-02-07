import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

from app.api.callbacks import router as callbacks_router
from app.api.media_stream import router as media_stream_router
from app.api.tools import router as tools_router
from app.api.whatsapp import router as whatsapp_router
from app.db.session import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        logging.getLogger(__name__).warning("DB not available — running without database")
    yield
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(title="Vocero", version="0.1.0", lifespan=lifespan)

app.include_router(whatsapp_router)
app.include_router(callbacks_router)
app.include_router(tools_router)
app.include_router(media_stream_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
