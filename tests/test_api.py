"""
API endpoint tests.
"""

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app


class FakeCursor:
    def __init__(self, items):
        self.items = items

    def skip(self, _):
        return self

    def limit(self, _):
        return self

    def sort(self, *_):
        return self

    async def to_list(self, length=50):
        return self.items[:length]


class FakeCollection:
    def __init__(self, items):
        self.items = items

    def find(self, *_args, **_kwargs):
        return FakeCursor(self.items)


class FakeDB:
    def __init__(self):
        self.tenders = FakeCollection(
            [
                {"_id": "abc123", "bid_id": "GEM/2025/B/7028956", "created_at": None},
            ]
        )

    def get_collection(self, name):
        if name == "tenders":
            return self.tenders
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
    assert isinstance(data, list)
    assert data[0]["bid_id"] == "GEM/2025/B/7028956"
