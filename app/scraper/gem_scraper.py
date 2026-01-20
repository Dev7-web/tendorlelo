"""
GeM Portal Scraper using Playwright.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, Page

from app.config import settings
from app.scraper.parser import parse_bid_cards
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GemScraper:
    """Scraper for GeM bid listings."""

    BASE_URL = "https://bidplus.gem.gov.in/all-bids"

    PAGE_LOAD_TIMEOUT = 60000
    ELEMENT_TIMEOUT = 30000

    def __init__(self) -> None:
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.SCRAPER_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self.page = await self.browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

    async def close(self) -> None:
        if self.page is not None:
            await self.page.close()
        if self.browser is not None:
            await self.browser.close()
        if self.playwright is not None:
            await self.playwright.stop()

    async def scrape_bids(self, max_pages: Optional[int] = None, max_bids: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape bids from GeM listing pages."""
        if self.page is None:
            raise RuntimeError("Scraper not initialized")

        max_pages = max_pages or settings.SCRAPE_MAX_PAGES
        max_bids = max_bids or settings.SCRAPE_MAX_BIDS

        logger.info("scraper.start", max_pages=max_pages, max_bids=max_bids)
        await self.page.goto(self.BASE_URL, timeout=self.PAGE_LOAD_TIMEOUT, wait_until="networkidle")

        collected: List[Dict[str, Any]] = []
        seen = set()

        for page_index in range(max_pages):
            await self._random_delay()
            html = await self.page.content()
            bids = parse_bid_cards(html)

            for bid in bids:
                bid_id = bid.get("bid_id")
                if not bid_id or bid_id in seen:
                    continue
                seen.add(bid_id)
                collected.append(bid)
                if len(collected) >= max_bids:
                    logger.info("scraper.max_bids_reached", count=len(collected))
                    return collected

            logger.info("scraper.page_parsed", page=page_index + 1, bids=len(bids), total=len(collected))

            if not await self._try_next_page():
                if not await self._try_scroll():
                    break

        return collected

    async def _try_next_page(self) -> bool:
        if self.page is None:
            return False
        try:
            next_button = await self.page.query_selector("text=Next")
            if next_button:
                await next_button.click()
                await self.page.wait_for_load_state("networkidle", timeout=self.PAGE_LOAD_TIMEOUT)
                return True
        except Exception as exc:
            logger.info("scraper.next_failed", error=str(exc))
        return False

    async def _try_scroll(self) -> bool:
        if self.page is None:
            return False
        try:
            previous_height = await self.page.evaluate("document.body.scrollHeight")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            new_height = await self.page.evaluate("document.body.scrollHeight")
            return new_height > previous_height
        except Exception as exc:
            logger.info("scraper.scroll_failed", error=str(exc))
            return False

    async def _random_delay(self) -> None:
        delay = random.uniform(settings.SCRAPE_MIN_DELAY, settings.SCRAPE_MAX_DELAY)
        await asyncio.sleep(delay)
