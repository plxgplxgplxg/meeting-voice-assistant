import secrets
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select

from app.api.deps import BearerCredentials, DbSession
from app.core.config import settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_agent_token
from app.domain.actor import Actor
from app.models.agent import AgentConversationModel
from app.models.user import UserModel


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Who the AI service is acting for in this request.

    Attributes:
        user: The user whose rights bound everything the agent does.
        actor: Authorization identity (``via="agent"``, never usable with share tokens).
        meeting_id: The one meeting the delegated token is scoped to.
        conversation_id: Conversation the turn belongs to.
    """

    user: UserModel
    actor: Actor
    meeting_id: uuid.UUID
    conversation_id: uuid.UUID


async def get_agent_context(
    auth: BearerCredentials,
    db: DbSession,
    service_token: Annotated[str | None, Header(alias="X-Service-Token")] = None,
) -> AgentContext:
    """Authenticate a tool call: service token plus the delegated user token.

    The service token proves the caller is the AI service. The delegated token
    (``aud="agent"``, five minutes, scoped to one meeting) proves which user and
    meeting the call is for, so a compromised or prompt-injected agent can never
    exceed that user's rights on that meeting.

    Args:
        auth: Parsed Authorization header carrying the delegated token.
        db: Active database session.
        service_token: Value of the ``X-Service-Token`` header.

    Returns:
        The validated agent context.

    Raises:
        AuthenticationError: If either credential is missing, invalid, or stale.
        PermissionDeniedError: If the user is deactivated.
    """
    expected = settings.ai_service_token.encode()
    if not service_token or not secrets.compare_digest(service_token.encode(), expected):
        raise AuthenticationError("Missing or invalid service token.", code="INVALID_SERVICE_TOKEN")
    if not auth or not auth.credentials:
        raise AuthenticationError("Authentication required.")

    claims = decode_agent_token(auth.credentials)
    invalid = AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN")
    try:
        user_id = uuid.UUID(str(claims["sub"]))
        conversation_id = uuid.UUID(str(claims["conv"]))
        scope = str(claims["scope"])
        meeting_id = uuid.UUID(scope.removeprefix("meeting:"))
    except (KeyError, ValueError) as exc:
        raise invalid from exc
    if not scope.startswith("meeting:"):
        raise invalid

    user = await db.scalar(select(UserModel).where(UserModel.id == user_id))
    if user is None or claims.get("tv") != user.token_version:
        raise invalid
    if not user.is_active:
        raise PermissionDeniedError("User account is deactivated.", code="ACCOUNT_DISABLED")

    conversation = await db.scalar(
        select(AgentConversationModel).where(
            AgentConversationModel.id == conversation_id,
            AgentConversationModel.user_id == user_id,
            AgentConversationModel.meeting_id == meeting_id,
        )
    )
    if conversation is None:
        raise invalid
    return AgentContext(user, Actor(user_id=user.id, via="agent"), meeting_id, conversation_id)


AgentCtx = Annotated[AgentContext, Depends(get_agent_context)]


async def agent_scope(meeting_id: uuid.UUID, ctx: AgentCtx) -> AgentContext:
    """Require the path meeting to equal the meeting the delegated token is scoped to.

    Args:
        meeting_id: Meeting from the route path.
        ctx: Validated agent context.

    Returns:
        The same context.

    Raises:
        PermissionDeniedError: With code ``AGENT_SCOPE_MISMATCH`` for any other meeting.
    """
    if ctx.meeting_id != meeting_id:
        raise PermissionDeniedError(
            "The delegated token does not cover this meeting.", code="AGENT_SCOPE_MISMATCH"
        )
    return ctx


ScopedAgent = Annotated[AgentContext, Depends(agent_scope)]
