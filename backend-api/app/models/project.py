import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.domain.enums import ProjectRole
from app.models.constraints import enum_check


class ProjectModel(Base):
    """Database model representing a workspace project."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    owner = relationship("UserModel", back_populates="projects_owned")
    members = relationship(
        "ProjectMemberModel", back_populates="project", cascade="all, delete-orphan"
    )
    meetings = relationship(
        "ProjectMeetingModel", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMemberModel(Base):
    """Database model representing a user's membership and role in a project."""
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id"),
        enum_check("role", ProjectRole, "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50), default="viewer", nullable=False
    )  # owner, editor, viewer
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    project = relationship("ProjectModel", back_populates="members")
    user = relationship("UserModel", back_populates="project_memberships")


class ProjectMeetingModel(Base):
    """Database model associating a meeting to a project."""
    __tablename__ = "project_meetings"
    __table_args__ = (UniqueConstraint("project_id", "meeting_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    project = relationship("ProjectModel", back_populates="meetings")
    meeting = relationship("MeetingModel", back_populates="project_links")
