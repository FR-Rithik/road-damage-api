from fastapi import FastAPI
from pydantic import BaseModel
from app.config import settings

app = FastAPI(title=settings.app_name)

@app.get("/health")
def health_check():
    return {"status": "ok"}

class EchoRequest(BaseModel):
    message: str

@app.post("/echo")
def echo(request: EchoRequest):
    return {"message": request.message}