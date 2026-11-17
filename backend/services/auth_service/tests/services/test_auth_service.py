import asyncio

import pytest
import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.core.config import settings
from app.db.base import Base
from app.models.auth import User
from app.schemas.auth import UserCreate
from app.services import auth_service


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    db_user = User(
        username="tester",
        email="tester@example.com",
        password=hash_password("password123"),
    )
    db_session.add(db_user)
    await db_session.commit()
    await db_session.refresh(db_user)
    return db_user


@pytest.mark.asyncio
async def test_login_user_success(db_session: AsyncSession, user: User):
    result = await auth_service.login_user(
        db_session,
        email="tester@example.com",
        password="password123",
    )

    assert "access_token" in result and "refresh_token" in result
    assert result["token_type"] == "bearer"
    access_claims = jwt.decode(
        result["access_token"], settings.JWT_SECRET, algorithms=[settings.JWT_ALG]
    )
    refresh_claims = jwt.decode(
        result["refresh_token"], settings.JWT_SECRET, algorithms=[settings.JWT_ALG]
    )
    assert access_claims["type"] == "access"
    assert refresh_claims["type"] == "refresh"


@pytest.mark.asyncio
async def test_login_user_invalid_password(db_session: AsyncSession, user: User):
    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(db_session, user.email, "wrong")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_register_user_creates_user(db_session: AsyncSession):
    payload = UserCreate(
        username="newbie",
        email="new@example.com",
        password="StrongPassword123!",
    )

    tokens = await auth_service.register_user(
        db_session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )

    assert "access_token" in tokens
    saved_user = await db_session.execute(
        User.__table__.select().where(User.email == payload.email)
    )
    assert saved_user.first() is not None


@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session: AsyncSession, user: User):
    with pytest.raises(HTTPException) as exc:
        await auth_service.register_user(
            db_session,
            username="tester",
            email=user.email,
            password="StrongPassword123!",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_username_index_enforces_case_insensitive_uniqueness(
    db_session: AsyncSession,
    user: User,
):
    db_session.add(
        User(
            username=" TESTER ",
            email="another@example.com",
            password=hash_password("StrongPassword123!"),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_concurrent_registration_rejects_duplicate_username(tmp_path):
    database_path = tmp_path / "concurrent-registration.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def register(email: str):
        async with SessionLocal() as session:
            return await auth_service.register_user(
                session,
                username="ConcurrentUser",
                email=email,
                password="StrongPassword123!",
            )

    outcomes = await asyncio.gather(
        register("first@example.com"),
        register("second@example.com"),
        return_exceptions=True,
    )

    successful = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    conflicts = [
        outcome
        for outcome in outcomes
        if isinstance(outcome, HTTPException)
        and outcome.status_code == 409
        and outcome.detail == "Username is already taken"
    ]
    unexpected = [
        outcome
        for outcome in outcomes
        if isinstance(outcome, BaseException)
        and outcome not in conflicts
    ]

    async with SessionLocal() as session:
        saved_users = await session.execute(select(User))
        users = saved_users.scalars().all()

    await engine.dispose()

    assert not unexpected
    assert len(successful) == 1
    assert len(conflicts) == 1
    assert len(users) == 1
