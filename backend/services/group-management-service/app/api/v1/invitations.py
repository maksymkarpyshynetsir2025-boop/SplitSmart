import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.invitation import (
    InvitationAction,
    InvitationCreate,
    InvitationCreated,
    InvitationDetail,
    InvitationList,
    InvitationOut,
)
from app.services import invitation_service

router = APIRouter(tags=["invitations"])


@router.post(
    "/groups/{group_id}/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    group_id: uuid.UUID,
    payload: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if payload.invited_email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invited_email is required; use the invitation-links endpoint for links",
        )
    created = await invitation_service.create_invitation(
        db,
        group_id,
        user_id,
        str(payload.invited_email) if payload.invited_email else None,
        payload.expires_in_days,
    )
    invitation = created["invitation"]
    return {
        "id": invitation.id,
        "group_id": invitation.group_id,
        "invited_email": invitation.invited_email,
        "status": invitation.status,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "invitation_token": created["token"],
        "invitation_url": created["url"],
    }


@router.post(
    "/groups/{group_id}/invitation-links",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation_link(
    group_id: uuid.UUID,
    payload: InvitationCreate | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    options = payload or InvitationCreate()
    if options.invited_email is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invitation links cannot specify an email address",
        )
    created = await invitation_service.create_invitation(
        db, group_id, user_id, None, options.expires_in_days
    )
    invitation = created["invitation"]
    return {
        "id": invitation.id,
        "group_id": invitation.group_id,
        "invited_email": invitation.invited_email,
        "status": invitation.status,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "invitation_token": created["token"],
        "invitation_url": created["url"],
    }


@router.get("/invitations", response_model=InvitationList)
async def get_user_invitations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await invitation_service.list_user_invitations(
        db, user_id, limit, offset
    )


@router.get("/invitations/{invitation_id}", response_model=InvitationDetail)
async def get_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await invitation_service.get_invitation(db, invitation_id, user_id)


@router.post("/invitations/{invitation_id}/accept", response_model=InvitationOut)
async def accept_invitation(
    invitation_id: uuid.UUID,
    payload: InvitationAction,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await invitation_service.respond_to_invitation(
        db, invitation_id, user_id, payload.token, accept=True
    )


@router.post("/invitations/{invitation_id}/reject", response_model=InvitationOut)
async def reject_invitation(
    invitation_id: uuid.UUID,
    payload: InvitationAction,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await invitation_service.respond_to_invitation(
        db, invitation_id, user_id, payload.token, accept=False
    )


@router.delete(
    "/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await invitation_service.cancel_invitation(db, invitation_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
