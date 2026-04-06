from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app.db.init_indexes import ensure_fts_index
from app.models import models  


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_fts_index(engine)
    yield
    await engine.dispose()


app = FastAPI(
    title="Multi-Tenant Org Manager",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)



@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Multi-Tenant Organization Manager API",
        "documentation": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Root"])
async def health():
    return {"status": "ok"}