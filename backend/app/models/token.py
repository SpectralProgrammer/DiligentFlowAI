from datetime import datetime

from pydantic import BaseModel


class ScopedToken(BaseModel):
    agent_id: str
    scopes: list[str]
    expires_at: datetime
    issued_at: datetime
