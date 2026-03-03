from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ApiClient
import hashlib

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def get_current_client(
    api_key: str = Security(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> ApiClient:
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header missing")

    key_hash = hash_key(api_key)
    client = db.query(ApiClient).filter(ApiClient.key_hash == key_hash).first()

    if not client:
        raise HTTPException(status_code=403, detail="Invalid API key")

    if not client.is_active:
        raise HTTPException(status_code=403, detail="API key is inactive")

    return client

