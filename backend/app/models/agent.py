from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    action: str
    resource: str
    description: str


class AgentDefinition(BaseModel):
    id: str
    name: str
    summary: str
    provider_status: str = Field(
        default="mocked",
        description="Whether this agent is backed by a real integration or demo logic.",
    )
    capabilities: list[AgentCapability]
