from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import internal_error_handler, not_found_handler
from app.routers import auth, images

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(images.router, prefix="/images", tags=["Images"])

app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, internal_error_handler)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
