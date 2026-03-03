from fastapi import APIRouter, Depends
from app.auth import get_current_client
from app.models import ApiClient

router = APIRouter()

@router.get("/me")
def get_me(client: ApiClient = Depends(get_current_client)):
    return {
        "id": client.id,
        "name": client.name,
        "is_active": client.is_active,
        "created_at": client.created_at,
    }
