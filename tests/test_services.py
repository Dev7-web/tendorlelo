"""
Service tests.
"""

import pytest

from app.services.search_service import SearchService


class DummyDB:
    def get_collection(self, name):
        return None


class TestSearchService:
    def test_metadata_score(self):
        service = SearchService(DummyDB())

        tender = {
            "metadata": {
                "domains": ["IT Services"],
                "required_certifications": ["ISO 27001"],
                "required_technologies": ["Java"],
                "sector": "government",
            }
        }

        profile = {
            "metadata": {
                "domains": ["IT Services", "Software"],
                "certifications": ["ISO 27001", "ISO 9001"],
                "technologies": ["Java", "Python"],
                "government_experience": True,
            }
        }

        score, reasons = service._metadata_score(tender, profile)
        assert score > 0
        assert any("ISO 27001" in reason for reason in reasons)
