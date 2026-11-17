import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.group import InvitationStatus


class InvitationCreate(BaseModel):
    invited_email: EmailStr | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationAction(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class InvitationOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    invited_email: EmailStr | None
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class InvitationCreated(InvitationOut):
    invitation_token: str
    invitation_url: str


class InvitationDetail(InvitationOut):
    created_by: int
    invitation_type: str


class InvitationList(BaseModel):
    items: list[InvitationOut]
    total: int
    limit: int
    offset: int
