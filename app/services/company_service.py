"""
Company profile processing service.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiofiles
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.repositories.company_repo import CompanyRepository
from app.processors.embedder import TextEmbedder
from app.processors.llm_extractor import GeminiExtractor
from app.processors.pdf_extractor import PDFExtractor
from app.utils.helpers import ensure_dir, safe_filename, sha256_file
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompanyService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.repo = CompanyRepository(db)
        self.pdf_extractor = PDFExtractor()
        self.embedder = TextEmbedder()
        self._llm: Optional[GeminiExtractor] = None

    def _get_llm(self) -> GeminiExtractor:
        if self._llm is None:
            self._llm = GeminiExtractor()
        return self._llm

    async def create_profile(self, files: List[UploadFile], company_name: Optional[str] = None) -> Dict[str, Any]:
        if not files:
            raise ValueError("No files provided")

        company_id = str(uuid.uuid4())
        company_dir = os.path.join(settings.PROFILE_UPLOAD_DIR, company_id)
        ensure_dir(company_dir)

        uploaded_files = []
        texts = []
        total_files = len(files)

        for index, file in enumerate(files, start=1):
            if not file.filename or (not file.filename.lower().endswith(".pdf")):
                raise ValueError("Only PDF files are supported")

            safe_name = safe_filename(file.filename, default=f"profile_{index}.pdf")
            local_path = os.path.join(company_dir, safe_name)

            size = 0
            async with aiofiles.open(local_path, "wb") as handle:
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > settings.MAX_UPLOAD_SIZE:
                        raise ValueError("File exceeds maximum upload size")
                    await handle.write(chunk)

            file_hash = sha256_file(local_path)
            uploaded_files.append(
                {
                    "file_hash": file_hash,
                    "original_name": file.filename,
                    "local_path": local_path,
                    "uploaded_at": datetime.now(timezone.utc),
                }
            )

            extracted = self.pdf_extractor.extract_text(local_path)
            if extracted:
                texts.append(extracted)

        status = {
            "processing_status": "processing",
            "files_processed": len(texts),
            "total_files": total_files,
            "last_error": None,
        }

        metadata: Dict[str, Any] = {}
        summary_embedding: List[float] = []
        try:
            combined_text = "\n".join(texts)
            if combined_text:
                metadata = self._get_llm().extract_company(combined_text)
            summary_embedding = self.embedder.embed(metadata.get("summary") if metadata else "")
            status["processing_status"] = "ready"
        except Exception as exc:
            status["processing_status"] = "failed"
            status["last_error"] = str(exc)
            logger.info("company.process_failed", error=str(exc))

        profile = {
            "company_id": company_id,
            "name": company_name,
            "uploaded_files": uploaded_files,
            "metadata": metadata,
            "summary_embedding": summary_embedding,
            "status": status,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        profile_id = await self.repo.create(profile)
        profile["id"] = profile_id
        return profile

    async def get_profile(self, company_id: str) -> Optional[Dict[str, Any]]:
        profile = await self.repo.get_by_id(company_id)
        return self._serialize(profile) if profile else None

    async def list_companies(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if status:
            filters["status.processing_status"] = status
        if search:
            regex = {"$regex": search, "$options": "i"}
            filters["$or"] = [
                {"name": regex},
                {"metadata.company_name": regex},
                {"metadata.domains": regex},
            ]

        total = await self.repo.collection.count_documents(filters)
        cursor = self.repo.collection.find(filters).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for profile in cursor:
            items.append(self._serialize(profile))
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get_search_history(self, company_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = (
            self.repo.collection.database.get_collection("search_history")
            .find({"company_id": company_id})
            .sort("searched_at", -1)
            .limit(limit)
        )
        items = []
        async for entry in cursor:
            entry_id = entry.get("_id")
            if entry_id is not None:
                entry["id"] = str(entry_id)
                entry["_id"] = str(entry_id)
            items.append(entry)
        return items

    async def delete_profile(self, company_id: str) -> bool:
        profile = await self.repo.get_by_id(company_id)
        if not profile:
            return False
        for file_info in profile.get("uploaded_files", []):
            path = file_info.get("local_path")
            if path and os.path.exists(path):
                os.remove(path)
        return await self.repo.delete(company_id)

    def _serialize(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if not profile:
            return profile
        profile_id = profile.get("_id")
        if profile_id is not None:
            profile["id"] = str(profile_id)
            profile["_id"] = str(profile_id)
        return profile
