import uuid
from dataclasses import dataclass
from typing import Literal

ActorVia = Literal["user", "share", "agent"]


@dataclass(frozen=True, slots=True)
class Actor:
    """Identity on whose behalf a command runs.

    The same actor flows from REST endpoints, Celery tasks, and the agent into
    every application-service method so authorization is enforced in one place.

    Attributes:
        user_id: Authenticated user, or None for share-link guests.
        share_token: Share token presented by the caller, if any.
        via: Channel the request arrived through.
    """

    user_id: uuid.UUID | None = None
    share_token: str | None = None
    via: ActorVia = "user"

    @property
    def is_authenticated(self) -> bool:
        """Whether the actor is a real user rather than a guest."""
        return self.user_id is not None
