from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth import get_current_client
from app.database import get_db
from app.model_service import predict_image
from app.models import ApiClient
from app.uploads import read_upload_with_limit

router = APIRouter()


@router.post("/predict", status_code=200)
async def predict(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: ApiClient = Depends(get_current_client),
):
    del db
    image_bytes = await read_upload_with_limit(file)

    try:
        return await run_in_threadpool(
            predict_image, image_bytes, file.filename or "uploaded-image"
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc
