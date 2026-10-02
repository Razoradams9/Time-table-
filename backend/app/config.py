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

    # Semester time windows. S1 & S5 BCA run in the morning block; S3 BCA runs
    # in the afternoon block. Values are the LAST morning period index. With 8
    # periods (0..7) a value of 3 means morning = periods 0-3 (08:30-12:30) and
    # afternoon = periods 4-7 (12:30 onward).
    morning_last_period_index: int = 3

    # Fatigue / rest tunables. These shape how the engine spreads load so
    # teachers get as much rest as possible. All are soft (scoring) weights so
    # coverage is never blocked -- a tired teacher is still assigned if they are
    # the only free option.
    fatigue_adjacency_penalty: int = 18   # penalty per period touching an existing one (back-to-back)
    fatigue_gap_bonus: int = 10           # bonus when the assignment leaves a free-period buffer
    fatigue_run_penalty: int = 14         # extra penalty per period beyond the preferred consecutive run
    fatigue_max_consecutive: int = 2      # preferred max periods in a row before a rest is wanted
    fatigue_daily_load_penalty: int = 4   # penalty per period already taught that day

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
