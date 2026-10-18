from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "RailConnect"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://train:train@localhost:5432/train_management"
    jwt_secret: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
    jwt_expiry_minutes: int = 30
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    allow_waiting_list: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
