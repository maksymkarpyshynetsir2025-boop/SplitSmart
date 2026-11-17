import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import get_db
from app.core.security import hash_password
from app.models.auth import User
from app.schemas.auth import UserLogin
from app.core.config import settings


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_endpoint_creates_user(client, db_session):
    payload = {
        "username": "  apiuser  ",
        "email": "api@example.com",
        "password": "StrongPassword123!",
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"

    saved = await db_session.execute(
        User.__table__.select().where(User.email == payload["email"])
    )
    saved_user = saved.first()
    assert saved_user is not None
    assert saved_user.username == "apiuser"
    assert "password" not in data


@pytest.mark.parametrize(
    ("password", "missing_requirement"),
    [
        ("Sh1!", "at least 8 characters"),
        ("strongpass123!", "at least one uppercase letter"),
        ("STRONGPASS123!", "at least one lowercase letter"),
        ("StrongPassword!", "at least one digit"),
        ("StrongPassword123", "at least one special character"),
        ("Strong Password123!", "no whitespace characters"),
    ],
)
@pytest.mark.asyncio
async def test_register_endpoint_rejects_weak_passwords(
    client,
    db_session,
    password,
    missing_requirement,
):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "apiuser",
            "email": "api@example.com",
            "password": password,
        },
    )

    assert response.status_code == 422
    assert any(
        missing_requirement in error["msg"]
        for error in response.json()["detail"]
    )
    saved_users = await db_session.execute(User.__table__.select())
    assert saved_users.first() is None


@pytest.mark.parametrize("username", ["taken", "TAKEN", "TaKeN"])
@pytest.mark.asyncio
async def test_register_endpoint_rejects_existing_username(
    client,
    db_session,
    username,
):
    db_session.add(
        User(
            username="Taken",
            email="existing@example.com",
            password=hash_password("StrongPassword123!"),
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "new@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username is already taken"
    saved_users = await db_session.execute(User.__table__.select())
    assert len(saved_users.all()) == 1


@pytest.mark.asyncio
async def test_login_endpoint_returns_tokens(client, db_session):
    user = User(
        username="apilogin",
        email="login@example.com",
        password=hash_password("pass123"),
    )
    db_session.add(user)
    await db_session.commit()

    payload = UserLogin(email=user.email, password="pass123")

    response = await client.post("/api/v1/auth/login", json=payload.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_internal_user_lookup_requires_key_and_returns_limited_profile(
    client, db_session, monkeypatch
):
    user = User(
        username="internaluser",
        email="internal@example.com",
        password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "internal-test-key")

    unauthorized = await client.get(f"/api/v1/internal/users/{user.id}")
    authorized = await client.get(
        f"/api/v1/internal/users/{user.id}",
        headers={"X-Internal-Api-Key": "internal-test-key"},
    )
    authorized_by_email = await client.get(
        f"/api/v1/internal/users/by-email/{user.email}",
        headers={"X-Internal-Api-Key": "internal-test-key"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json() == {"id": user.id, "email": user.email}
    assert authorized_by_email.json() == authorized.json()
