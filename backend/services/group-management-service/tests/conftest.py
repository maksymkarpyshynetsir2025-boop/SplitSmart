import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-with-at-least-32-bytes")
os.environ.setdefault("JWT_ALG", "HS256")
os.environ.setdefault("AUTH_SERVICE_API_KEY", "test-internal-key")
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth.test")

from app.core.user_client import auth_user_client
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Group, GroupInvitation, GroupMembership


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def client(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    profiles = {
        1: {"id": 1, "email": "owner@example.com"},
        2: {"id": 2, "email": "member@example.com"},
        3: {"id": 3, "email": "other@example.com"},
    }

    async def get_user(user_id: int):
        if user_id not in profiles:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="User not found")
        return profiles[user_id]

    async def get_user_by_email(email: str):
        for profile in profiles.values():
            if profile["email"].lower() == str(email).lower():
                return profile
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")

    monkeypatch.setattr(auth_user_client, "get_user", get_user)
    monkeypatch.setattr(auth_user_client, "get_user_by_email", get_user_by_email)
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client
    app.dependency_overrides.clear()


def auth_headers(user_id: int) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        "test-secret-key-with-at-least-32-bytes",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def created_group(client):
    response = await client.post(
        "/api/v1/groups",
        json={"name": "  Trip group  ", "description": "  Summer trip  "},
        headers=auth_headers(1),
    )
    assert response.status_code == 201
    return response.json()


__all__ = [
    "Group",
    "GroupInvitation",
    "GroupMembership",
    "auth_headers",
    "uuid",
]
