from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, ValidationError

from app.core.config import settings


class AuthUser(BaseModel):
    id: int
    email: EmailStr


class AuthUserClient:
    async def get_user(self, user_id: int) -> dict:
        return await self._request(f"/api/v1/internal/users/{user_id}")

    async def get_user_by_email(self, email: EmailStr | str) -> dict:
        return await self._request(
            f"/api/v1/internal/users/by-email/{quote(str(email), safe='')}"
        )

    async def _request(self, path: str) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=settings.AUTH_SERVICE_URL.rstrip("/"),
                timeout=5.0,
            ) as client:
                response = await client.get(
                    path,
                    headers={"X-Internal-Api-Key": settings.AUTH_SERVICE_API_KEY},
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is unavailable",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service user lookup failed",
            )
        try:
            return AuthUser.model_validate(response.json()).model_dump()
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service returned an invalid user profile",
            ) from exc


auth_user_client = AuthUserClient()
