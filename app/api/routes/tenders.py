"""
Tender API routes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db
from app.services.search_service import SearchService
from app.services.tender_service import TenderService

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("/", response_model=Dict[str, Any])
async def list_tenders(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    domains: Optional[str] = Query(None, description="Comma-separated domains"),
    search: Optional[str] = None,
    expired: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = TenderService(db)
    domain_list = [item.strip() for item in domains.split(",") if item.strip()] if domains else None
    return await service.list_tenders(
        skip=skip,
        limit=limit,
        status=status,
        domains=domain_list,
        search=search,
        expired=expired,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/stats/summary", response_model=Dict[str, Any])
async def tender_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    return await service.get_stats()


@router.get("/{tender_id}", response_model=Dict[str, Any])
async def get_tender(tender_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    tender = await service.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.post("/{tender_id}/reprocess", response_model=Dict[str, Any])
async def reprocess_tender(tender_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = TenderService(db)
    success = await service.reprocess_tender(tender_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tender not found")
    return {"reprocessed": True}


@router.get("/{tender_id}/matches", response_model=Dict[str, Any])
async def match_companies(tender_id: str, limit: int = 5, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = SearchService(db)
    try:
        return await service.match_companies_for_tender(tender_id=tender_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
