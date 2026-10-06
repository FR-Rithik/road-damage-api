from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.auth import get_current_client
from app.logger import get_logger
from app.model_service import predict_image
from app.models import ApiClient
from app.uploads import read_upload_with_limit

router = APIRouter()
logger = get_logger(__name__)


@router.post("/predict", status_code=200)
async def predict(
    file: UploadFile = File(...),
    client: ApiClient = Depends(get_current_client),
):
    image_bytes = await read_upload_with_limit(file)

    try:
        return await run_in_threadpool(
            predict_image,
            image_bytes,
            file.filename or "uploaded-image",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except FileNotFoundError:
        logger.exception("Road-damage model checkpoint is unavailable")
        raise HTTPException(
            status_code=503,
            detail="Road-damage model is currently unavailable",
        )

    except Exception:
        logger.exception("Road-damage prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed",
        )