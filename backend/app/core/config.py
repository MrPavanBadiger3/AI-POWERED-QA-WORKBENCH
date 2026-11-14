"""Application settings. All secrets come from backend/.env or real environment variables."""
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    APP_NAME: str = "AI-Powered QA Workbench"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = False

    # AI provider (Groq). The key is never returned by any API.
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_TEMPERATURE: float = 0.2

    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'qa_workbench.db').as_posix()}"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # Automation
    SAUCEDEMO_URL: str = "https://www.saucedemo.com"
    EXECUTION_TIMEOUT_SECONDS: int = 600
    HEADLESS: bool = True

    # Folders
    REPORTS_DIR: Path = BACKEND_DIR / "reports"
    SCREENSHOTS_DIR: Path = BACKEND_DIR / "screenshots"
    TEST_DATA_DIR: Path = BACKEND_DIR / "automation" / "test_data"
    GENERATED_DIR: Path = BACKEND_DIR / "automation" / "generated"
    ARTIFACTS_DIR: Path = PROJECT_DIR / "artifacts"


settings = Settings()
for _d in (settings.REPORTS_DIR, settings.SCREENSHOTS_DIR, settings.TEST_DATA_DIR / "uploads",
           settings.GENERATED_DIR, settings.ARTIFACTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
