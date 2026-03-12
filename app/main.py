from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.config import settings
from app.errors import internal_error_handler, not_found_handler
from app.routers import auth

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])

app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, internal_error_handler)

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}

@app.post("/echo")
def echo(data: dict):
    return {"message": data.get("message")}

# @app.get("/db-ping")
# def db_ping(db: Session = Depends(get_db)):
#     db.execute(text("SELECT 1"))
#     return {"status": "ok", "database": "connected"}