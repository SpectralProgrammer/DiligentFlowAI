from fastapi import APIRouter

from app.permissions.openfga_client import list_permissions

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("")
def get_permissions() -> dict[str, list[str]]:
    return list_permissions()
