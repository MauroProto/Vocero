from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.callbacks import router as callbacks_router
from app.api.whatsapp import router as whatsapp_router
from app.db.session import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Vocero", version="0.1.0", lifespan=lifespan)

app.include_router(whatsapp_router)
app.include_router(callbacks_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
