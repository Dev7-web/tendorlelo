"""
Scrape job for GeM portal.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import settings
from app.database.mongodb import get_database
from app.scraper.gem_scraper import GemScraper
from app.services.tender_service import TenderService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_scrape_job() -> None:
    db = get_database()
    service = TenderService(db)
    job_id = str(uuid.uuid4())
    scrape_logs = db.get_collection("scrape_logs")

    log_entry = {
        "job_id": job_id,
        "started_at": datetime.now(timezone.utc),
        "status": "running",
        "stats": {
            "pages_scraped": 0,
            "tenders_found": 0,
            "new_tenders": 0,
            "pdfs_downloaded": 0,
            "llm_processed": 0,
            "errors": 0,
        },
        "errors": [],
    }
    await scrape_logs.insert_one(log_entry)

    stats = log_entry["stats"]
    errors: List[Dict[str, Any]] = []

    try:
        async with GemScraper() as scraper:
            bids = await scraper.scrape_bids()
            stats["tenders_found"] = len(bids)

            for bid in bids:
                try:
                    await service.create_or_update_from_scrape(bid)
                    stats["new_tenders"] += 1
                    if await service.process_tender(bid.get("bid_id")):
                        stats["pdfs_downloaded"] += 1
                        stats["llm_processed"] += 1
                except Exception as exc:
                    stats["errors"] += 1
                    errors.append(
                        {
                            "bid_id": bid.get("bid_id"),
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc),
                        }
                    )

        await scrape_logs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "completed_at": datetime.now(timezone.utc),
                    "status": "completed",
                    "stats": stats,
                    "errors": errors,
                }
            },
        )
    except Exception as exc:
        await scrape_logs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "completed_at": datetime.now(timezone.utc),
                    "status": "failed",
                    "stats": stats,
                    "errors": errors + [{"error": str(exc), "timestamp": datetime.now(timezone.utc)}],
                }
            },
        )
        logger.info("scrape.job_failed", error=str(exc))


def run_scrape_job_sync() -> None:
    asyncio.run(run_scrape_job())


async def run_process_job() -> None:
    db = get_database()
    service = TenderService(db)
    processed = await service.process_pending_tenders()
    logger.info("process.job_completed", processed=processed)


def run_process_job_sync() -> None:
    asyncio.run(run_process_job())
