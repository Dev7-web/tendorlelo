"""
Dashboard aggregation service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase


class DashboardService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.tenders = db.get_collection("tenders")
        self.companies = db.get_collection("company_profiles")
        self.searches = db.get_collection("search_history")
        self.jobs = db.get_collection("scrape_logs")

    async def get_stats(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        tenders_total = await self.tenders.count_documents({})
        tenders_processed = await self.tenders.count_documents({"status.llm_processed": True})
        tenders_pending = await self.tenders.count_documents({"status.llm_processed": False})
        tenders_failed = await self.tenders.count_documents({"status.last_error": {"$ne": None}})

        companies_total = await self.companies.count_documents({})

        jobs_running = await self.jobs.count_documents({"status": "running"})
        jobs_completed_today = await self.jobs.count_documents({"completed_at": {"$gte": start_day}})
        last_scrape = await self.jobs.find_one(
            {"job_type": "scrape", "status": "completed"},
            sort=[("completed_at", -1)],
        )

        searches_today = await self.searches.count_documents({"searched_at": {"$gte": start_day}})
        searches_total = await self.searches.count_documents({})

        return {
            "tenders": {
                "total": tenders_total,
                "processed": tenders_processed,
                "pending": tenders_pending,
                "failed": tenders_failed,
            },
            "companies": {"total": companies_total},
            "jobs": {
                "running": jobs_running,
                "completed_today": jobs_completed_today,
                "last_scrape": last_scrape.get("completed_at") if last_scrape else None,
            },
            "searches": {"today": searches_today, "total": searches_total},
        }

    async def get_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        activity: List[Dict[str, Any]] = []

        async for tender in self.tenders.find().sort("created_at", -1).limit(limit):
            activity.append(
                {
                    "type": "tender",
                    "message": f"Tender scraped: {tender.get('bid_id')}",
                    "timestamp": tender.get("scraped_at") or tender.get("created_at"),
                    "data": {"bid_id": tender.get("bid_id")},
                }
            )

        async for company in self.companies.find().sort("created_at", -1).limit(limit):
            activity.append(
                {
                    "type": "company",
                    "message": f"Company uploaded: {company.get('name') or company.get('company_id')}",
                    "timestamp": company.get("created_at"),
                    "data": {"company_id": company.get("company_id")},
                }
            )

        async for search in self.searches.find().sort("searched_at", -1).limit(limit):
            activity.append(
                {
                    "type": "search",
                    "message": f"Search run for company: {search.get('company_id')}",
                    "timestamp": search.get("searched_at"),
                    "data": {"company_id": search.get("company_id")},
                }
            )

        async for job in self.jobs.find().sort("started_at", -1).limit(limit):
            activity.append(
                {
                    "type": "job",
                    "message": f"Job {job.get('job_type')} {job.get('status')}",
                    "timestamp": job.get("completed_at") or job.get("started_at"),
                    "data": {"job_id": job.get("job_id")},
                }
            )

        activity = [item for item in activity if item.get("timestamp")]
        activity.sort(key=lambda item: item["timestamp"], reverse=True)
        return activity[:limit]

    async def get_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.tenders.find({"status.llm_processed": False}).sort("created_at", -1).limit(limit)
        items: List[Dict[str, Any]] = []
        async for tender in cursor:
            items.append(
                {
                    "bid_id": tender.get("bid_id"),
                    "status": tender.get("status"),
                    "scraped_info": tender.get("scraped_info"),
                    "created_at": tender.get("created_at"),
                }
            )
        return items
