from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.auth import get_current_client
from app.dataset_service import (
    cleanup_working_directory,
    create_working_directory,
    label_dataset_zip,
    save_uploaded_zip,
)
from app.logger import get_logger
from app.models import ApiClient

logger = get_logger(__name__)

router = APIRouter(
    prefix="/datasets",
)


@router.post("/label")
async def label_dataset(
    file: UploadFile = File(...),
    client: ApiClient = Depends(get_current_client),
):
    """
    Upload a ZIP of images and receive a YOLO-labeled dataset ZIP.
    """
    filename = file.filename or ""

    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=422,
            detail="Please upload a .zip dataset",
        )

    working_directory: Path | None = None

    try:
        working_directory = create_working_directory()

        uploaded_zip = working_directory / "input.zip"

        await run_in_threadpool(
            save_uploaded_zip,
            file.file,
            uploaded_zip,
        )

        output_zip, stats = await run_in_threadpool(
            label_dataset_zip,
            uploaded_zip,
            working_directory,
        )

        logger.info(
            "Dataset labeled by client '%s': %s",
            client.name,
            stats,
        )

        return FileResponse(
            path=output_zip,
            media_type="application/zip",
            filename="annotation-wizard-labeled.zip",
            background=BackgroundTask(
                cleanup_working_directory,
                working_directory,
            ),
        )

    except ValueError as exc:
        if working_directory is not None:
            cleanup_working_directory(working_directory)

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        if working_directory is not None:
            cleanup_working_directory(working_directory)

        logger.exception(
            "Model checkpoint is unavailable during dataset labeling"
        )

        raise HTTPException(
            status_code=503,
            detail="Road-damage model is currently unavailable",
        ) from exc

    except Exception as exc:
        if working_directory is not None:
            cleanup_working_directory(working_directory)

        logger.exception(
            "Dataset labeling failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Dataset labeling failed",
        ) from exc

    finally:
        await file.close()