import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth import get_current_client
from app.database import get_db
from app.logger import get_logger
from app.model_service import predict_image
from app.models import ApiClient, Image
from app.uploads import read_upload_with_limit

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = "./data/uploads"


@router.post("", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: ApiClient = Depends(get_current_client),
):
    contents = await read_upload_with_limit(file)
    try:
        prediction = await run_in_threadpool(
            predict_image, contents, file.filename or "uploaded-image"
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        logger.exception("Road-damage model checkpoint is unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - model/runtime dependent
        logger.exception("Road-damage prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed") from exc

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    original_filename = file.filename or "uploaded-image"
    ext = os.path.splitext(original_filename)[-1].lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

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
        "prediction": prediction,
        "report": prediction["report"],
    }
