from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from conftest import GroupInvitation, GroupMembership, auth_headers, uuid
from app.models.group import MembershipRole


@pytest.mark.asyncio
async def test_create_group_assigns_owner_and_membership(
    client, db_session
):
    response = await client.post(
        "/api/v1/groups",
        json={"name": "  Dinner  ", "description": "  Shared costs "},
        headers=auth_headers(1),
    )

    assert response.status_code == 201
    group = response.json()
    assert group["name"] == "Dinner"
    assert group["description"] == "Shared costs"
    assert group["owner_id"] == 1
    memberships = await db_session.execute(select(GroupMembership))
    owner_membership = memberships.scalar_one()
    assert owner_membership.user_id == 1
    assert owner_membership.role == MembershipRole.OWNER


@pytest.mark.asyncio
async def test_create_group_requires_auth_and_rejects_invalid_name(client):
    unauthenticated = await client.post("/api/v1/groups", json={"name": "Group"})
    invalid = await client.post(
        "/api/v1/groups",
        json={"name": "   "},
        headers=auth_headers(1),
    )

    assert unauthenticated.status_code == 401
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token_cannot_authenticate_to_group_api(client):
    token = jwt.encode(
        {
            "sub": "1",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
        },
        "test-secret-key-with-at-least-32-bytes",
        algorithm="HS256",
    )
    response = await client.get(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_only_owner_can_update_group(client, created_group):
    group_id = created_group["id"]
    denied = await client.patch(
        f"/api/v1/groups/{group_id}",
        json={"name": "Not allowed"},
        headers=auth_headers(2),
    )
    updated = await client.patch(
        f"/api/v1/groups/{group_id}",
        json={"name": "New name", "description": None},
        headers=auth_headers(1),
    )

    assert denied.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["name"] == "New name"
    assert updated.json()["description"] is None


@pytest.mark.asyncio
async def test_list_groups_and_group_details_require_membership(
    client, created_group
):
    group_id = created_group["id"]
    groups = await client.get("/api/v1/groups", headers=auth_headers(1))
    denied = await client.get(
        f"/api/v1/groups/{group_id}", headers=auth_headers(3)
    )
    details = await client.get(
        f"/api/v1/groups/{group_id}", headers=auth_headers(1)
    )

    assert groups.status_code == 200
    assert groups.json()[0]["role"] == "OWNER"
    assert denied.status_code == 403
    assert details.status_code == 200
    assert details.json()["owner"]["email"] == "owner@example.com"
    assert details.json()["member_count"] == 1


@pytest.mark.asyncio
async def test_add_and_remove_member_and_member_can_leave(
    client, created_group
):
    group_id = created_group["id"]
    added = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": 2},
        headers=auth_headers(1),
    )
    duplicate = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": 2},
        headers=auth_headers(1),
    )
    members = await client.get(
        f"/api/v1/groups/{group_id}/members", headers=auth_headers(2)
    )
    left = await client.delete(
        f"/api/v1/groups/{group_id}/members/me", headers=auth_headers(2)
    )

    assert added.status_code == 201
    assert added.json()["role"] == "MEMBER"
    assert duplicate.status_code == 409
    assert members.status_code == 200
    assert len(members.json()) == 2
    assert left.status_code == 204


@pytest.mark.asyncio
async def test_cannot_add_nonexistent_user_or_remove_owner(client, created_group):
    group_id = created_group["id"]
    missing_user = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": 99},
        headers=auth_headers(1),
    )
    await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": 2},
        headers=auth_headers(1),
    )
    remove_owner = await client.delete(
        f"/api/v1/groups/{group_id}/members/1",
        headers=auth_headers(1),
    )
    member_removal = await client.delete(
        f"/api/v1/groups/{group_id}/members/1",
        headers=auth_headers(2),
    )

    assert missing_user.status_code == 404
    assert remove_owner.status_code == 409
    assert member_removal.status_code == 403


@pytest.mark.asyncio
async def test_owner_cannot_leave_and_group_deletion_archives(
    client, created_group, db_session
):
    group_id = created_group["id"]
    invitation = await client.post(
        f"/api/v1/groups/{group_id}/invitation-links",
        json={},
        headers=auth_headers(1),
    )
    owner_leave = await client.delete(
        f"/api/v1/groups/{group_id}/members/me", headers=auth_headers(1)
    )
    deleted = await client.delete(
        f"/api/v1/groups/{group_id}", headers=auth_headers(1)
    )
    membership_rows = await db_session.execute(select(GroupMembership))
    saved_invitation = await db_session.get(
        GroupInvitation, uuid.UUID(invitation.json()["id"])
    )
    hidden = await client.get(
        f"/api/v1/groups/{group_id}", headers=auth_headers(1)
    )

    assert owner_leave.status_code == 409
    assert deleted.status_code == 200
    assert deleted.json()["archived"] is True
    assert len(membership_rows.scalars().all()) == 1
    assert saved_invitation.status.value == "REVOKED"
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_empty_groups_and_missing_group_responses(client):
    groups = await client.get("/api/v1/groups", headers=auth_headers(1))
    missing = await client.get(
        "/api/v1/groups/00000000-0000-0000-0000-000000000001",
        headers=auth_headers(1),
    )

    assert groups.status_code == 200
    assert groups.json() == []
    assert missing.status_code == 404
