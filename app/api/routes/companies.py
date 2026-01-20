"""
Company profile API routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.dependencies import get_db
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_company_profile(
    files: List[UploadFile] = File(...),
    company_name: Optional[str] = Form(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = CompanyService(db)
    try:
        return await service.create_profile(files=files, company_name=company_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{company_id}", response_model=Dict[str, Any])
async def get_company_profile(company_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = CompanyService(db)
    profile = await service.get_profile(company_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return profile


@router.delete("/{company_id}", response_model=Dict[str, Any])
async def delete_company_profile(company_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    service = CompanyService(db)
    deleted = await service.delete_profile(company_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return {"deleted": True}
