import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_client
from app.database import get_db
from app.logger import get_logger
from app.models import ApiClient, Image

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = "./data/uploads"


@router.post("", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: ApiClient = Depends(get_current_client),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[-1].lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    image = Image(
        filename=unique_filename,
        path=file_path,
        client_id=client.id,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    logger.info(f"Image uploaded by client '{client.name}': {unique_filename}")

    return {
        "image_id": image.id,
        "filename": image.filename,
        "created_at": image.created_at,
    }
