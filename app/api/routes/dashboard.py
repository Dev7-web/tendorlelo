"""
Dashboard API routes.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    service = DashboardService(db)
    return await service.get_stats()


@router.get("/activity", response_model=List[Dict[str, Any]])
async def get_recent_activity(limit: int = 10, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = DashboardService(db)
    return await service.get_activity(limit=limit)


@router.get("/queue", response_model=List[Dict[str, Any]])
async def get_processing_queue(limit: int = 20, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = DashboardService(db)
    return await service.get_queue(limit=limit)
