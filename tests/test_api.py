"""
API endpoint tests.
"""

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app


class FakeCursor:
    def __init__(self, items):
        self.items = items
        self._index = 0

    def skip(self, _):
        if _:
            self.items = self.items[_:]
        return self

    def limit(self, _):
        if _:
            self.items = self.items[:_]
        return self

    def sort(self, *_):
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self._index]
        self._index += 1
        return item

    async def to_list(self, length=50):
        return self.items[:length]


class FakeCollection:
    def __init__(self, items):
        self.items = items

    def find(self, *_args, **_kwargs):
        return FakeCursor(self.items)

    async def count_documents(self, _):
        return len(self.items)

    async def update_many(self, *_args, **_kwargs):
        return None

    async def find_one(self, filter=None, sort=None):
        if not filter:
            return self.items[0] if self.items else None
        for item in self.items:
            if all(item.get(key) == value for key, value in filter.items()):
                return item
        return None


class FakeDB:
    def __init__(self):
        self.tenders = FakeCollection(
            [
                {"_id": "abc123", "bid_id": "GEM/2025/B/7028956", "created_at": None},
            ]
        )
        self.company_profiles = FakeCollection(
            [
                {"_id": "comp1", "company_id": "company-1", "created_at": None},
            ]
        )
        self.search_history = FakeCollection(
            [
                {"_id": "search1", "company_id": "company-1", "searched_at": None},
            ]
        )
        self.scrape_logs = FakeCollection(
            [
                {"_id": "job1", "job_id": "job-1", "job_type": "scrape", "status": "completed"},
            ]
        )

    def get_collection(self, name):
        if name == "tenders":
            return self.tenders
        if name == "company_profiles":
            return self.company_profiles
        if name == "search_history":
            return self.search_history
        if name == "scrape_logs":
            return self.scrape_logs
        return FakeCollection([])


client = TestClient(app)


def override_db():
    yield FakeDB()


app.dependency_overrides[get_db] = override_db


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_list_tenders():
    response = client.get("/api/v1/tenders/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["items"][0]["bid_id"] == "GEM/2025/B/7028956"


def test_dashboard_stats():
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "tenders" in data
    assert "companies" in data


def test_jobs_list():
    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["items"][0]["job_id"] == "job-1"
