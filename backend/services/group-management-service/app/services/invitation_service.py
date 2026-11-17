import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.user_client import auth_user_client
from app.models.group import (
    Group,
    GroupInvitation,
    GroupMembership,
    InvitationStatus,
    MembershipRole,
)
from app.services.group_service import require_owner


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _expire_due_invitations(db: AsyncSession) -> None:
    result = await db.execute(
        update(GroupInvitation)
        .where(
            GroupInvitation.status == InvitationStatus.PENDING,
            GroupInvitation.expires_at <= datetime.now(timezone.utc),
        )
        .values(status=InvitationStatus.EXPIRED)
    )
    if result.rowcount:
        await db.commit()


async def create_invitation(
    db: AsyncSession,
    group_id: uuid.UUID,
    owner_id: int,
    invited_email: str | None,
    expires_in_days: int,
) -> dict:
    await require_owner(db, group_id, owner_id)
    normalized_email = invited_email.lower() if invited_email else None
    if normalized_email:
        invitee = await auth_user_client.get_user_by_email(normalized_email)
        member = await db.execute(
            select(GroupMembership.id).where(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == invitee["id"],
            )
        )
        if member.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a group member",
            )
        pending = await db.execute(
            select(GroupInvitation.id).where(
                GroupInvitation.group_id == group_id,
                func.lower(GroupInvitation.invited_email) == normalized_email,
                GroupInvitation.status == InvitationStatus.PENDING,
            )
        )
        if pending.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this email",
            )

    token = secrets.token_urlsafe(32)
    invitation = GroupInvitation(
        group_id=group_id,
        invited_email=normalized_email,
        token_hash=_token_digest(token),
        created_by=owner_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
    )
    db.add(invitation)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists",
        ) from exc
    await db.refresh(invitation)
    invitation_url = (
        f"{settings.INVITATION_BASE_URL.rstrip('/')}/invitations/"
        f"{invitation.id}#token={token}"
    )
    return {"invitation": invitation, "token": token, "url": invitation_url}


async def list_user_invitations(
    db: AsyncSession,
    user_id: int,
    limit: int,
    offset: int,
) -> dict:
    await _expire_due_invitations(db)
    user = await auth_user_client.get_user(user_id)
    now = datetime.now(timezone.utc)
    filters = (
        func.lower(GroupInvitation.invited_email) == user["email"].lower(),
        GroupInvitation.status == InvitationStatus.PENDING,
        GroupInvitation.expires_at > now,
    )
    total_result = await db.execute(
        select(func.count()).select_from(GroupInvitation).where(*filters)
    )
    items_result = await db.execute(
        select(GroupInvitation)
        .where(*filters)
        .order_by(GroupInvitation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return {
        "items": list(items_result.scalars().all()),
        "total": total_result.scalar_one(),
        "limit": limit,
        "offset": offset,
    }


async def get_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    user_id: int,
) -> dict:
    await _expire_due_invitations(db)
    invitation = await db.get(GroupInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    group = await db.get(Group, invitation.group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    permitted = invitation.created_by == user_id
    if group.owner_id == user_id:
        permitted = True
    if invitation.invited_email:
        user = await auth_user_client.get_user(user_id)
        permitted = permitted or user["email"].lower() == invitation.invited_email.lower()
    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this invitation",
        )
    return {
        "id": invitation.id,
        "group_id": invitation.group_id,
        "invited_email": invitation.invited_email,
        "status": invitation.status,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "created_by": invitation.created_by,
        "invitation_type": "EMAIL" if invitation.invited_email else "LINK",
    }


async def _get_actionable_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    token: str,
) -> GroupInvitation:
    result = await db.execute(
        select(GroupInvitation)
        .where(GroupInvitation.id == invitation_id)
        .with_for_update()
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invitation is already {invitation.status.value.lower()}",
        )
    if not secrets.compare_digest(invitation.token_hash, _token_digest(token)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )
    now = datetime.now(timezone.utc)
    expiry = invitation.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )
    return invitation


async def respond_to_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    user_id: int,
    token: str,
    accept: bool,
) -> GroupInvitation:
    user = await auth_user_client.get_user(user_id)
    invitation = await _get_actionable_invitation(db, invitation_id, token)
    if (
        invitation.invited_email
        and user["email"].lower() != invitation.invited_email.lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation email does not match the authenticated user",
        )
    group, _ = await require_member_or_available_group(
        db, invitation.group_id, user_id
    )
    if not accept:
        invitation.status = InvitationStatus.REJECTED
        await db.commit()
        await db.refresh(invitation)
        return invitation

    existing = await db.execute(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a group member",
        )
    db.add(
        GroupMembership(
            group_id=group.id,
            user_id=user_id,
            role=MembershipRole.MEMBER,
        )
    )
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation could not be accepted because membership already exists",
        ) from exc
    await db.refresh(invitation)
    return invitation


async def require_member_or_available_group(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: int,
) -> tuple[Group, GroupMembership | None]:
    group = await db.get(Group, group_id)
    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    member_result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    return group, member_result.scalar_one_or_none()


async def cancel_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    owner_id: int,
) -> None:
    await _expire_due_invitations(db)
    invitation = await db.get(GroupInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    await require_owner(db, invitation.group_id, owner_id)
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invitations can be canceled",
        )
    invitation.status = InvitationStatus.REVOKED
    await db.commit()
