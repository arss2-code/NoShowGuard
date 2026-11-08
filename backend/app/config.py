from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = (BASE_DIR / "noshowguard.db").as_posix()

class Settings(BaseSettings):
    BOT_TOKEN: str = "test_bot_token"
    BOT_USERNAME: str = "NoShowGuardBot"
    MINI_APP_URL: str = "https://t.me/NoShowGuardBot/app"

    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_sqlite_url(cls, v: str | None) -> str:
        if not v or "sqlite+aiosqlite:///./" in v:
            return f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}"
        return v

    # YooKassa
    YOOKASSA_SHOP_ID: str | None = None
    YOOKASSA_SECRET_KEY: str | None = None
    YOOKASSA_SANDBOX: bool = True

    # Telegram Mini App & WebApp URLs
    WEBAPP_URL: str = "http://localhost:8000/app"
    MINI_APP_SHORT_NAME: str = "app"
    TELEGRAM_PROXY_URL: str | None = None

    # App & Business Logic
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    DEFAULT_DEPOSIT_AMOUNT: int = 300
    DEPOSIT_LOCK_MINUTES: int = 10

    @property
    def resolved_webapp_url(self) -> str:
        """URL веб-приложения для WebAppInfo (внутри Telegram TMA)."""
        base = ""
        if self.WEBAPP_URL and not self.WEBAPP_URL.startswith("https://t.me"):
            base = self.WEBAPP_URL.rstrip("/")
        elif self.MINI_APP_URL and not self.MINI_APP_URL.startswith("https://t.me"):
            base = self.MINI_APP_URL.rstrip("/")
        else:
            base = f"{self.WEBHOOK_BASE_URL.rstrip('/')}/app"

        if not base.endswith("/app"):
            base = f"{base}/app"
        return base

    def get_tma_direct_link(self, start_param: str = "") -> str:
        """Прямая ссылка на Mini App: https://t.me/bot/app?startapp=param"""
        clean_bot = self.BOT_USERNAME.replace("@", "")
        short_name = self.MINI_APP_SHORT_NAME or "app"
        if start_param:
            return f"https://t.me/{clean_bot}/{short_name}?startapp={start_param}"
        return f"https://t.me/{clean_bot}/{short_name}"

    def get_bot_start_link(self, param: str = "") -> str:
        """Глубокая ссылка на чат с ботом: https://t.me/bot?start=param"""
        clean_bot = self.BOT_USERNAME.replace("@", "")
        if param:
            return f"https://t.me/{clean_bot}?start={param}"
        return f"https://t.me/{clean_bot}"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
