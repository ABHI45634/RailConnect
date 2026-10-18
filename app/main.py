import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine
from app.routers import auth, stations, trains, bookings, pnr, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dispose the async engine cleanly when the API process exits."""
    yield
    await engine.dispose()

app = FastAPI(title=settings.app_name, version="1.0.0", description="Asynchronous train booking REST API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router); app.include_router(stations.router); app.include_router(trains.router); app.include_router(bookings.router); app.include_router(pnr.router); app.include_router(admin.router)

@app.get("/health", tags=["Health"])
async def health():
    """Lightweight container health check."""
    from sqlalchemy import text
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected failures and return a generic message without leaking internals."""
    logger.exception("Unhandled exception method=%s path=%s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
