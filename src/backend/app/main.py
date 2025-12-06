from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.molecules import router as molecules_router
from app.api.research import router as research_router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    yield


app = FastAPI(
    title="Molecule Research API",
    version="0.1.0",
    description="Small molecule research pipeline backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Include API routers
app.include_router(research_router, prefix=settings.api_v1_prefix)
app.include_router(molecules_router, prefix=settings.api_v1_prefix)
