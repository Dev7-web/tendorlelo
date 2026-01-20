"""
Tender API routes.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db
from app.services.tender_service import TenderService

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_tenders(skip: int = 0, limit: int = 50, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    return await service.list_tenders(skip=skip, limit=limit)


@router.get("/{tender_id}", response_model=Dict[str, Any])
async def get_tender(tender_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    tender = await service.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.get("/stats/summary", response_model=Dict[str, Any])
async def tender_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    return await service.get_stats()
