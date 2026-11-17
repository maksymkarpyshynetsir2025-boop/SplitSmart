import enum
import uuid

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MembershipRole(str, enum.Enum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_membership"),
        Index("ix_group_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "groups.id",
            ondelete="RESTRICT",
            name="fk_group_memberships_group_id_groups",
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, native_enum=False, length=16), nullable=False
    )
    joined_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GroupInvitation(Base):
    __tablename__ = "group_invitations"
    __table_args__ = (
        Index("ix_group_invitations_group_id", "group_id"),
        Index("ix_group_invitations_created_by", "created_by"),
        Index(
            "uq_pending_group_email_invitation",
            "group_id",
            text("lower(invited_email)"),
            unique=True,
            postgresql_where=text(
                "status = 'PENDING' AND invited_email IS NOT NULL"
            ),
            sqlite_where=text("status = 'PENDING' AND invited_email IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "groups.id",
            ondelete="RESTRICT",
            name="fk_group_invitations_group_id_groups",
        ),
        nullable=False,
    )
    invited_email: Mapped[str | None] = mapped_column(String(320))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False, length=16),
        nullable=False,
        default=InvitationStatus.PENDING,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
