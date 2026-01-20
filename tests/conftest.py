"""
Pytest configuration and fixtures.
"""

import asyncio

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database connection."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[f"{settings.DB_NAME}_test"]
    yield db
    await client.drop_database(f"{settings.DB_NAME}_test")
    client.close()


@pytest.fixture
async def clean_db(test_db):
    """Clean database before each test."""
    collections = await test_db.list_collection_names()
    for coll in collections:
        await test_db[coll].delete_many({})
    return test_db
