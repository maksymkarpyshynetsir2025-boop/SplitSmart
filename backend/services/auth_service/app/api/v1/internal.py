import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import InternalUserOut

router = APIRouter(prefix="/internal", tags=["internal"])


async def verify_internal_api_key(
    x_internal_api_key: str | None = Header(default=None),
) -> None:
    if not settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal user lookup is not configured",
        )
    if not x_internal_api_key or not hmac.compare_digest(
        x_internal_api_key, settings.INTERNAL_API_KEY
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )


@router.get(
    "/users/{user_id}",
    response_model=InternalUserOut,
    dependencies=[Depends(verify_internal_api_key)],
)
async def get_internal_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get(
    "/users/by-email/{email}",
    response_model=InternalUserOut,
    dependencies=[Depends(verify_internal_api_key)],
)
async def get_internal_user_by_email(
    email: EmailStr,
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(User).where(func.lower(User.email) == str(email).lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
