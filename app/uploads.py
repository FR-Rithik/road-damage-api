from fastapi import HTTPException, UploadFile

from app.config import settings


async def read_upload_with_limit(file: UploadFile) -> bytes:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    limit = settings.max_upload_bytes
    data = await file.read(limit + 1)  # never read more than limit + 1 bytes

    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {limit // (1024 * 1024)} MB",
        )
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    return data