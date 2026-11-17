import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.group import (
    GroupCreate,
    GroupDetailsOut,
    GroupOut,
    GroupUpdate,
    MemberCreate,
    MemberOut,
    UserGroupOut,
)
from app.services import group_service

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.create_group(
        db, user_id, payload.name, payload.description
    )


@router.get("", response_model=list[UserGroupOut])
async def get_user_groups(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.list_user_groups(db, user_id, limit, offset)


@router.get("/{group_id}", response_model=GroupDetailsOut)
async def get_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.get_group_details(db, group_id, user_id)


@router.patch("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.update_group(
        db, group_id, user_id, payload.model_dump(exclude_unset=True)
    )


@router.delete("/{group_id}")
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await group_service.delete_group(db, group_id, user_id)
    return {
        "detail": "Group archived; membership and related records were preserved",
        "group_id": str(group_id),
        "archived": True,
    }


@router.get("/{group_id}/members", response_model=list[MemberOut])
async def get_group_members(
    group_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.list_members(
        db, group_id, user_id, limit, offset
    )


@router.post(
    "/{group_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_group_member(
    group_id: uuid.UUID,
    payload: MemberCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await group_service.add_member(db, group_id, user_id, payload.user_id)


@router.delete("/{group_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await group_service.leave_group(db, group_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_group_member(
    group_id: uuid.UUID,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await group_service.remove_member(db, group_id, user_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
