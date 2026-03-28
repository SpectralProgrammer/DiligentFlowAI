from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str
    name: str
    role: str
