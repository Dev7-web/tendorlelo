"""
Scraper tests.
"""

import pytest

from app.scraper.parser import parse_bid_cards
from app.scraper.pdf_downloader import PDFDownloader


class TestGemScraper:
    def test_parse_bid_cards(self):
        html = """
        <html>
          <body>
            <div class="card">
              <a href="/showbidDocument/123">GEM/2025/B/7028956</a>
              <div>Items: Desktop Computers</div>
              <div>Quantity: 6</div>
              <div>Department Name And Address: Ministry of Defence</div>
              <div>Start Date: 17-01-2026 1:00 PM</div>
              <div>End Date: 19-01-2026 3:53 PM</div>
            </div>
          </body>
        </html>
        """
        bids = parse_bid_cards(html)
        assert len(bids) == 1
        assert bids[0]["bid_id"] == "GEM/2025/B/7028956"
        assert bids[0]["quantity"] == 6

    def test_pdf_validation(self, tmp_path):
        downloader = PDFDownloader()
        valid_path = tmp_path / "valid.pdf"
        valid_path.write_bytes(b"%PDF-1.4 test content")
        invalid_path = tmp_path / "invalid.pdf"
        invalid_path.write_bytes(b"not a pdf")

        assert downloader._is_valid_pdf(str(valid_path)) is True
        assert downloader._is_valid_pdf(str(invalid_path)) is False
