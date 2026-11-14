"""Enforce case-insensitive, trimmed username uniqueness.

Revision ID: a4b7c3d9e201
Revises: d696e8625228
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b7c3d9e201"
down_revision: Union[str, Sequence[str], None] = "d696e8625228"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM users
            GROUP BY lower(trim(username))
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce username uniqueness: existing usernames contain "
            "case-insensitive duplicates after trimming. Resolve them manually "
            "before retrying this migration."
        )

    op.create_index(
        "uq_users_username_lower_trim",
        "users",
        [sa.text("lower(trim(username))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_username_lower_trim", table_name="users")
