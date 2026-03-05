from fastapi import FastAPI

from app.errors import internal_error_handler, not_found_handler
from app.routers import auth

app = FastAPI(
    title="Road Damage API",
    version="0.1.0",
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])

app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, internal_error_handler)

@app.get("/health")
def health():
    return {"status": "ok"}