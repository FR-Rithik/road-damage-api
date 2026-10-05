from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import database_error_handler, internal_error_handler, not_found_handler
from app.logger import get_logger
from app.model_service import get_model, is_model_ready
from app.routers import auth, images, predict

logger = get_logger(__name__)
PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the checkpoint before this process accepts requests."""
    try:
        await run_in_threadpool(get_model)
    except Exception as exc:  # pragma: no cover - depends on deployment assets
        # Keep the service available for diagnostics; /health will advertise
        # that prediction is unavailable rather than claiming the app is ready.
        app.state.model_load_error = str(exc)
        logger.exception("Road-damage model failed to load during startup")
    else:
        app.state.model_load_error = None

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(images.router, prefix="/images", tags=["Images"])
app.include_router(predict.router, prefix="", tags=["Prediction"])

app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, internal_error_handler)
app.add_exception_handler(SQLAlchemyError, database_error_handler)


@app.get("/", include_in_schema=False)
def frontend():
    """Serve the browser client alongside the API."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/reference-image", include_in_schema=False)
def reference_image():
    return FileResponse(PROJECT_DIR / "image.png")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    if not is_model_ready():
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "connected",
                "model": "unavailable",
            },
        )

    return {"status": "ok", "db": "connected", "model": "ready"}
