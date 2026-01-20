"""
FastAPI application entry point.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import companies, search, tenders
from app.config import settings
from app.database.mongodb import create_indexes, close_client
from app.jobs.scheduler import shutdown_scheduler, start_scheduler
from app.utils.logger import configure_logging
from app.utils.exceptions import AppError


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenders.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.on_event("startup")
async def on_startup() -> None:
    configure_logging(settings.LOG_LEVEL)
    await create_indexes()
    if settings.ENABLE_SCHEDULER:
        start_scheduler()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if settings.ENABLE_SCHEDULER:
        shutdown_scheduler()
    await close_client()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
