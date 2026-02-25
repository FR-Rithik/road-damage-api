from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "road-damage-api"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()