from datetime import datetime, timedelta, timezone

import pytest

from conftest import GroupInvitation, auth_headers
from app.models.group import InvitationStatus


@pytest.mark.asyncio
async def test_email_invitation_acceptance_adds_member(client, created_group):
    group_id = created_group["id"]
    created = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "member@example.com"},
        headers=auth_headers(1),
    )
    invite = created.json()
    accepted = await client.post(
        f"/api/v1/invitations/{invite['id']}/accept",
        json={"token": invite["invitation_token"]},
        headers=auth_headers(2),
    )

    assert created.status_code == 201
    assert len(invite["invitation_token"]) >= 32
    assert invite["invitation_token"] in invite["invitation_url"]
    stored_invitation = await client.get(
        f"/api/v1/invitations/{invite['id']}", headers=auth_headers(1)
    )
    assert stored_invitation.status_code == 200
    assert "token_hash" not in stored_invitation.json()
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_email_invitation_wrong_user_and_single_use(
    client, created_group
):
    group_id = created_group["id"]
    created = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "member@example.com"},
        headers=auth_headers(1),
    )
    invitation = created.json()
    invalid_token = await client.post(
        f"/api/v1/invitations/{invitation['id']}/accept",
        json={"token": "x" * 40},
        headers=auth_headers(2),
    )
    wrong_user = await client.post(
        f"/api/v1/invitations/{invitation['id']}/accept",
        json={"token": invitation["invitation_token"]},
        headers=auth_headers(3),
    )
    accepted = await client.post(
        f"/api/v1/invitations/{invitation['id']}/accept",
        json={"token": invitation["invitation_token"]},
        headers=auth_headers(2),
    )
    reused = await client.post(
        f"/api/v1/invitations/{invitation['id']}/accept",
        json={"token": invitation["invitation_token"]},
        headers=auth_headers(2),
    )

    assert invalid_token.status_code == 404
    assert wrong_user.status_code == 403
    assert accepted.status_code == 200
    assert reused.status_code == 409


@pytest.mark.asyncio
async def test_link_invitation_reject_and_duplicate_email(
    client, created_group
):
    group_id = created_group["id"]
    link = await client.post(
        f"/api/v1/groups/{group_id}/invitation-links",
        json={"expires_in_days": 3},
        headers=auth_headers(1),
    )
    rejected = await client.post(
        f"/api/v1/invitations/{link.json()['id']}/reject",
        json={"token": link.json()["invitation_token"]},
        headers=auth_headers(3),
    )
    email_invite = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "member@example.com"},
        headers=auth_headers(1),
    )
    duplicate = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "MEMBER@example.com"},
        headers=auth_headers(1),
    )

    assert link.status_code == 201
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert email_invite.status_code == 201
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_expired_invitation_is_marked_and_cannot_be_accepted(
    client, created_group, db_session
):
    group_id = created_group["id"]
    created = await client.post(
        f"/api/v1/groups/{group_id}/invitation-links",
        json={},
        headers=auth_headers(1),
    )
    invitation_id = created.json()["id"]
    from uuid import UUID

    invitation = await db_session.get(GroupInvitation, UUID(invitation_id))
    invitation.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/invitations/{invitation_id}/accept",
        json={"token": created.json()["invitation_token"]},
        headers=auth_headers(2),
    )

    assert response.status_code == 410
    assert invitation.status == InvitationStatus.EXPIRED


@pytest.mark.asyncio
async def test_owner_can_cancel_and_non_owner_cannot_create_invitation(
    client, created_group
):
    group_id = created_group["id"]
    denied = await client.post(
        f"/api/v1/groups/{group_id}/invitation-links",
        json={},
        headers=auth_headers(2),
    )
    created = await client.post(
        f"/api/v1/groups/{group_id}/invitation-links",
        json={},
        headers=auth_headers(1),
    )
    canceled = await client.delete(
        f"/api/v1/invitations/{created.json()['id']}",
        headers=auth_headers(1),
    )

    assert denied.status_code == 403
    assert canceled.status_code == 204


@pytest.mark.asyncio
async def test_invite_existing_member_and_list_invite_for_recipient(
    client, created_group
):
    group_id = created_group["id"]
    added = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": 2},
        headers=auth_headers(1),
    )
    existing_member_invite = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "member@example.com"},
        headers=auth_headers(1),
    )
    invite = await client.post(
        f"/api/v1/groups/{group_id}/invitations",
        json={"invited_email": "other@example.com"},
        headers=auth_headers(1),
    )
    recipient_invitations = await client.get(
        "/api/v1/invitations", headers=auth_headers(3)
    )

    assert added.status_code == 201
    assert existing_member_invite.status_code == 409
    assert invite.status_code == 201
    assert recipient_invitations.status_code == 200
    assert recipient_invitations.json()["total"] == 1
    assert recipient_invitations.json()["items"][0]["id"] == invite.json()["id"]
