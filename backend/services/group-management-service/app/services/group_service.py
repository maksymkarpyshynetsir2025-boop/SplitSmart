import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.user_client import auth_user_client
from app.models.group import (
    Group,
    GroupInvitation,
    GroupMembership,
    InvitationStatus,
    MembershipRole,
)


async def require_member(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> tuple[Group, GroupMembership]:
    group = await db.get(Group, group_id)
    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )
    return group, membership


async def require_owner(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> Group:
    group, membership = await require_member(db, group_id, user_id)
    if membership.role != MembershipRole.OWNER or group.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can perform this operation",
        )
    return group


async def create_group(
    db: AsyncSession,
    user_id: int,
    name: str,
    description: str | None,
) -> Group:
    group = Group(name=name, description=description, owner_id=user_id)
    db.add(group)
    await db.flush()
    db.add(
        GroupMembership(
            group_id=group.id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
    )
    await db.commit()
    await db.refresh(group)
    return group


async def list_user_groups(
    db: AsyncSession,
    user_id: int,
    limit: int,
    offset: int,
) -> list[dict]:
    result = await db.execute(
        select(Group, GroupMembership.role)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(
            GroupMembership.user_id == user_id,
            Group.deleted_at.is_(None),
        )
        .order_by(Group.created_at.desc(), Group.id)
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "owner_id": group.owner_id,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
            "role": role,
        }
        for group, role in result.all()
    ]


async def get_group_details(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> dict:
    group, _ = await require_member(db, group_id, user_id)
    owner = await auth_user_client.get_user(group.owner_id)
    count_result = await db.execute(
        select(func.count())
        .select_from(GroupMembership)
        .where(GroupMembership.group_id == group_id)
    )
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "owner_id": group.owner_id,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "owner": {"id": owner["id"], "email": owner["email"]},
        "member_count": count_result.scalar_one(),
    }


async def update_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
    changes: dict,
) -> Group:
    group = await require_owner(db, group_id, user_id)
    for field, value in changes.items():
        setattr(group, field, value)
    group.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(group)
    return group


async def delete_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> None:
    group = await require_owner(db, group_id, user_id)
    now = datetime.now(timezone.utc)
    group.deleted_at = now
    group.updated_at = now
    pending = await db.execute(
        select(GroupInvitation).where(
            GroupInvitation.group_id == group_id,
            GroupInvitation.status == InvitationStatus.PENDING,
        )
    )
    for invitation in pending.scalars():
        invitation.status = InvitationStatus.REVOKED
    await db.commit()


async def list_members(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
    limit: int,
    offset: int,
) -> list[GroupMembership]:
    await require_member(db, group_id, user_id)
    result = await db.execute(
        select(GroupMembership)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.joined_at, GroupMembership.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def add_member(
    db: AsyncSession,
    group_id: uuid.UUID,
    owner_id: int,
    user_id: int,
) -> GroupMembership:
    await require_owner(db, group_id, owner_id)
    await auth_user_client.get_user(user_id)
    existing = await db.execute(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a group member",
        )
    membership = GroupMembership(
        group_id=group_id,
        user_id=user_id,
        role=MembershipRole.MEMBER,
    )
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a group member",
        ) from exc
    await db.refresh(membership)
    return membership


async def remove_member(
    db: AsyncSession,
    group_id: uuid.UUID,
    actor_id: int,
    member_id: int,
) -> None:
    group, actor = await require_member(db, group_id, actor_id)
    if actor.role != MembershipRole.OWNER or group.owner_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can remove other members",
        )
    target_result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == member_id,
        )
    )
    target = target_result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group membership not found",
        )
    if target.role == MembershipRole.OWNER or member_id == group.owner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The group owner cannot be removed",
        )
    await db.delete(target)
    await db.commit()


async def leave_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> None:
    group, membership = await require_member(db, group_id, user_id)
    if membership.role == MembershipRole.OWNER or group.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The owner cannot leave without transferring ownership or deleting the group",
        )
    await db.delete(membership)
    await db.commit()
