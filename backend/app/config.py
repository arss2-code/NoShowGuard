from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    BOT_TOKEN: str = "test_bot_token"
    BOT_USERNAME: str = "NoShowGuardBot"
    MINI_APP_URL: str = "https://t.me/NoShowGuardBot/app"

    DATABASE_URL: str = "sqlite+aiosqlite:///./noshowguard.db"

    # YooKassa
    YOOKASSA_SHOP_ID: str | None = None
    YOOKASSA_SECRET_KEY: str | None = None
    YOOKASSA_SANDBOX: bool = True

    # App & Business Logic
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    DEFAULT_DEPOSIT_AMOUNT: int = 300
    DEPOSIT_LOCK_MINUTES: int = 10

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
