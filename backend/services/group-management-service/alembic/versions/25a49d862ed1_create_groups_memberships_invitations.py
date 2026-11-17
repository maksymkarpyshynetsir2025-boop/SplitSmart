"""Create groups, memberships, and invitations.

Revision ID: 25a49d862ed1
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "25a49d862ed1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"])

    op.create_table(
        "group_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name="fk_group_memberships_group_id_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_membership"),
    )
    op.create_index(
        "ix_group_memberships_user_id", "group_memberships", ["user_id"]
    )

    op.create_table(
        "group_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name="fk_group_invitations_group_id_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_group_invitations_group_id", "group_invitations", ["group_id"]
    )
    op.create_index(
        "ix_group_invitations_created_by", "group_invitations", ["created_by"]
    )
    op.create_index(
        "uq_pending_group_email_invitation",
        "group_invitations",
        ["group_id", sa.text("lower(invited_email)")],
        unique=True,
        postgresql_where=sa.text(
            "status = 'PENDING' AND invited_email IS NOT NULL"
        ),
        sqlite_where=sa.text("status = 'PENDING' AND invited_email IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_pending_group_email_invitation", table_name="group_invitations"
    )
    op.drop_index("ix_group_invitations_created_by", table_name="group_invitations")
    op.drop_index("ix_group_invitations_group_id", table_name="group_invitations")
    op.drop_table("group_invitations")
    op.drop_index("ix_group_memberships_user_id", table_name="group_memberships")
    op.drop_table("group_memberships")
    op.drop_index("ix_groups_owner_id", table_name="groups")
    op.drop_table("groups")
