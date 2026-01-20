"""
Search API routes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/tenders/{company_id}", response_model=Dict[str, Any])
async def search_tenders(
    company_id: str,
    query: Optional[str] = None,
    domains: Optional[str] = Query(None, description="Comma-separated domains"),
    certifications: Optional[str] = Query(None, description="Comma-separated certifications"),
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    filters = {}
    if domains:
        filters["domains"] = [item.strip() for item in domains.split(",") if item.strip()]
    if certifications:
        filters["required_certifications"] = [
            item.strip() for item in certifications.split(",") if item.strip()
        ]

    service = SearchService(db)
    try:
        return await service.search_tenders(
            company_id=company_id,
            query=query,
            filters=filters or None,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
