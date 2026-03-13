import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_client, hash_key, require_admin
from app.database import get_db
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


@router.post("/keys", status_code=201)
def create_key(
    name: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    raw_key = secrets.token_hex(32)
    client = ApiClient(name=name, key_hash=hash_key(raw_key))
    db.add(client)
    db.commit()
    db.refresh(client)
    return {
        "id": client.id,
        "name": client.name,
        "key": raw_key,
        "note": "Store this key safely. It will not be shown again.",
    }


@router.delete("/keys/{client_id}", status_code=200)
def revoke_key(
    client_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    client = db.query(ApiClient).filter(ApiClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.is_active = False
    db.commit()
    return {"detail": f"Key for '{client.name}' has been revoked"}