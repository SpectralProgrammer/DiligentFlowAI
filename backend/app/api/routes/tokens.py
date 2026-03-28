from fastapi import APIRouter

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/about")
def about_tokens() -> dict[str, str | int]:
    return {
        "kind": "scoped-demo-token",
        "ttl_minutes": 30,
        "issuer": "local-demo-vault",
        "note": "Replace this with Auth0 or your preferred token broker when ready.",
    }
