from enum import StrEnum


class Permission(StrEnum):
    """Capability a caller needs on a meeting.

    ``MANAGE`` covers deletion and share-link management.
    """

    VIEW = "view"
    EDIT = "edit"
    MANAGE = "manage"


PERMISSION_RANK: dict[Permission, int] = {
    Permission.VIEW: 1,
    Permission.EDIT: 2,
    Permission.MANAGE: 3,
}


class ProjectRole(StrEnum):
    """Role of a user inside a project workspace."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class SharePermission(StrEnum):
    """Access level granted by a meeting share link."""

    VIEWER = "viewer"
    EDITOR = "editor"


class OrderStatus(StrEnum):
    """Lifecycle state of a payment order."""

    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class SubscriptionStatus(StrEnum):
    """Lifecycle state of a subscription row."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REPLACED = "replaced"
    CANCELLED = "cancelled"


class WebhookEventStatus(StrEnum):
    """Processing outcome recorded for each SePay webhook event."""

    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"
    DUPLICATE = "duplicate"
    PARTIAL_AMOUNT = "partial_amount"
    EXPIRED_ORDER = "expired_order"


class SummaryStatus(StrEnum):
    """State of the generated summary for a meeting."""

    NONE = "none"
    PENDING = "pending"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"


class MeetingStatus(StrEnum):
    """Processing state of a meeting."""

    DRAFT = "draft"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
