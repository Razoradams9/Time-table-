"""Application configuration loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "College Timetable & Smart Substitution System"
    database_url: str = "sqlite:///./timetable.db"

    # Branding / institution labels shown in the UI
    institution_name: str = "JGI JAIN"
    institution_subtitle: str = "Deemed-to-be University"
    department_name: str = "Department of Computer Applications"
    product_name: str = "Timetable Management System"
    semester_label: str = "Even semester | 2026"

    # Auth
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 12  # 12 hours
    algorithm: str = "HS256"

    # Substitution engine tunables
    max_substitutions_per_week: int = 3
    same_department_preferred: bool = True

    # Notifications (email). If smtp_host is empty, emails are logged to console.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@college.edu"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
