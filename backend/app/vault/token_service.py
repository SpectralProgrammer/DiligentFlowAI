from datetime import datetime, timedelta, timezone

from app.models.token import ScopedToken


def issue_token(agent_id: str, scopes: list[str]) -> ScopedToken:
    issued_at = datetime.now(timezone.utc)
    return ScopedToken(
        agent_id=agent_id,
        scopes=scopes,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=30),
    )
