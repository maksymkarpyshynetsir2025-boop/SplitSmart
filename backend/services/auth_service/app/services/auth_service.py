from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.auth import User
from app.core.security import verify_password, hash_password
from app.core.jwt import create_access_token, create_refresh_token


async def _raise_if_registration_conflict(
    db: AsyncSession,
    username: str,
    email: str,
) -> None:
    email_result = await db.execute(select(User.id).where(User.email == email))
    if email_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    username_result = await db.execute(
        select(User.id).where(
            func.lower(func.trim(User.username)) == username.lower()
        )
    )
    if username_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken",
        )


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


async def register_user(db: AsyncSession, username: str, email: str, password: str,) -> dict:
    username = username.strip()
    await _raise_if_registration_conflict(db, username, email)

    user = User(
        username=username,
        email=email,
        password=hash_password(password),
    )

    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await _raise_if_registration_conflict(db, username, email)
        raise
    await db.refresh(user)

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
