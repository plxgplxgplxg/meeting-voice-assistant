import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProjectCreateRequest(BaseModel):
    """Schema for creating a new workspace project."""
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdateRequest(BaseModel):
    """Schema for updating an existing workspace project."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectMemberResponse(BaseModel):
    """Schema representing a project member and their role."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str  # owner, editor, viewer
    created_at: datetime


class ProjectResponse(BaseModel):
    """Schema for workspace project summary."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    owner_id: uuid.UUID
    my_role: str | None = None
    members_count: int = 1
    meetings_count: int = 0
    created_at: datetime


class AddProjectMemberRequest(BaseModel):
    """Schema for inviting a member to a project via email."""
    email: EmailStr
    role: str = Field(default="viewer", pattern="^(editor|viewer)$")


class UpdateProjectMemberRoleRequest(BaseModel):
    """Schema for updating a member's project access role."""
    role: str = Field(pattern="^(editor|viewer)$")
