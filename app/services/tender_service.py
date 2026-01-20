"""
Tender processing service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.repositories.tender_repo import TenderRepository
from app.processors.embedder import TextEmbedder
from app.processors.llm_extractor import GeminiExtractor
from app.processors.pdf_extractor import PDFExtractor
from app.scraper.pdf_downloader import download_with_retry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TenderService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.repo = TenderRepository(db)
        self.pdf_extractor = PDFExtractor()
        self.embedder = TextEmbedder()
        self._llm: Optional[GeminiExtractor] = None

    def _get_llm(self) -> GeminiExtractor:
        if self._llm is None:
            self._llm = GeminiExtractor()
        return self._llm

    async def create_or_update_from_scrape(self, bid: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        scraped_info = {
            "items": bid.get("items"),
            "quantity": bid.get("quantity"),
            "department": bid.get("department"),
            "department_address": bid.get("department_address"),
            "start_date": bid.get("start_date"),
            "end_date": bid.get("end_date"),
            "bid_type": bid.get("bid_type"),
            "bid_value_range": bid.get("bid_value_range"),
        }
        status = {
            "scrape_status": "completed",
            "pdf_downloaded": False,
            "llm_processed": False,
            "embedding_generated": False,
            "last_error": None,
        }
        data = {
            "bid_id": bid.get("bid_id"),
            "ra_no": bid.get("ra_no"),
            "gem_url": bid.get("gem_url"),
            "pdf_url": bid.get("pdf_url"),
            "scraped_info": scraped_info,
            "status": status,
            "scraped_at": now,
            "updated_at": now,
            "is_active": True,
            "expired": False,
        }
        return await self.repo.upsert_by_bid_id(bid.get("bid_id"), data)

    async def process_tender(self, bid_id: str) -> bool:
        tender = await self.repo.get_by_bid_id(bid_id)
        if not tender:
            return False

        status = tender.get("status", {})
        try:
            if not status.get("pdf_downloaded"):
                pdf_path = await download_with_retry(tender.get("pdf_url"), filename_hint=bid_id)
                if not pdf_path:
                    status.update({"last_error": "PDF download failed"})
                    await self.repo.set_status(bid_id, status)
                    return False
                await self.repo.update(str(tender["_id"]), {"pdf_local_path": pdf_path})
                status["pdf_downloaded"] = True

            text = self.pdf_extractor.extract_text(tender.get("pdf_local_path"))
            if not text:
                status.update({"last_error": "PDF extraction failed"})
                await self.repo.set_status(bid_id, status)
                return False

            metadata = self._get_llm().extract_tender(text)
            status["llm_processed"] = True

            summary = metadata.get("summary") if isinstance(metadata, dict) else None
            summary_embedding = self.embedder.embed(summary or "")
            status["embedding_generated"] = True

            await self.repo.update(
                str(tender["_id"]),
                {
                    "metadata": metadata,
                    "summary_embedding": summary_embedding,
                    "processed_at": datetime.now(timezone.utc),
                    "status": status,
                },
            )
            return True
        except Exception as exc:
            status.update({"last_error": str(exc)})
            await self.repo.set_status(bid_id, status)
            logger.info("tender.process_failed", bid_id=bid_id, error=str(exc))
            return False

    async def list_tenders(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        tenders = await self.repo.list(skip=skip, limit=limit)
        return [self._serialize(tender) for tender in tenders]

    async def get_tender(self, tender_id: str) -> Optional[Dict[str, Any]]:
        tender = await self.repo.get_by_id(tender_id)
        return self._serialize(tender) if tender else None

    async def get_stats(self) -> Dict[str, Any]:
        collection = self.repo.collection
        total = await collection.count_documents({})
        processed = await collection.count_documents({"status.llm_processed": True})
        pending = await collection.count_documents({"status.llm_processed": False})
        return {"total": total, "processed": processed, "pending": pending}

    def _serialize(self, tender: Dict[str, Any]) -> Dict[str, Any]:
        if not tender:
            return tender
        tender_id = tender.get("_id")
        if tender_id is not None:
            tender["id"] = str(tender_id)
            tender["_id"] = str(tender_id)
        return tender

    async def process_pending_tenders(self, limit: int = 50) -> int:
        processed = 0
        cursor = self.repo.collection.find({"status.llm_processed": False}).limit(limit)
        async for tender in cursor:
            bid_id = tender.get("bid_id")
            if bid_id and await self.process_tender(bid_id):
                processed += 1
        return processed
