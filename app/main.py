from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from app.config import settings
from app.routers import auth

app = FastAPI(title=settings.app_name)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

class EchoRequest(BaseModel):
    message: str

@app.post("/echo")
def echo(request: EchoRequest):
    return {"message": request.message}

@app.get("/db-ping")
def db_ping():
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}