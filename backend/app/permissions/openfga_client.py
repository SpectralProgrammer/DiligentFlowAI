POLICY_MATRIX: dict[str, set[str]] = {
    "email-agent": {"send:gmail-api", "draft:gmail-api"},
    "calendar-agent": {"schedule:google-calendar", "read:google-calendar"},
    "finance-agent": {"analyze:market-data", "summarize:market-data"},
}


def check_permission(agent_id: str, action: str, resource: str) -> bool:
    allowed_scopes = POLICY_MATRIX.get(agent_id, set())
    return f"{action}:{resource}" in allowed_scopes


def list_permissions() -> dict[str, list[str]]:
    return {
        agent_id: sorted(scopes)
        for agent_id, scopes in POLICY_MATRIX.items()
    }
