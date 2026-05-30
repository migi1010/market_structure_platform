from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _env_list(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _cors_origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS") or os.getenv(
        "CORS_WHITELIST",
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "capacitor://localhost,"
        "ionic://localhost,"
        "https://frontend-kuan-s-projects1.vercel.app,"
        "https://miji-quant.com,"
        "https://api.miji-quant.com",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _runtime_mode() -> str:
    raw = os.getenv("MIJI_RUNTIME_MODE", "render_safe").strip().lower()
    return raw if raw in {"render_safe", "local_full"} else "render_safe"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Miji Quant Institutional API")
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    cors_whitelist: List[str] = None  # type: ignore[assignment]
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", ".cache"))
    sqlite_cache_path: Path = Path(os.getenv("SQLITE_CACHE_PATH", ".cache/market_cache.sqlite3"))
    quote_ttl_seconds: int = int(os.getenv("QUOTE_TTL_SECONDS", "300"))
    history_ttl_seconds: int = int(os.getenv("HISTORY_TTL_SECONDS", "3600"))
    statement_ttl_seconds: int = int(os.getenv("STATEMENT_TTL_SECONDS", "21600"))
    news_ttl_seconds: int = int(os.getenv("NEWS_TTL_SECONDS", "1800"))
    alpha_ranking_ttl_seconds: int = int(os.getenv("ALPHA_RANKING_TTL_SECONDS", "1800"))
    fundamentals_ttl_seconds: int = int(os.getenv("FUNDAMENTALS_TTL_SECONDS", "21600"))
    sector_rotation_ttl_seconds: int = int(os.getenv("SECTOR_ROTATION_TTL_SECONDS", "900"))
    theme_ttl_seconds: int = int(os.getenv("THEME_TTL_SECONDS", "900"))
    market_regime_ttl_seconds: int = int(os.getenv("MARKET_REGIME_TTL_SECONDS", "900"))
    market_overview_ttl_seconds: int = int(os.getenv("MARKET_OVERVIEW_TTL_SECONDS", "300"))
    miji_runtime_mode: str = _runtime_mode()
    miji_lightweight_mode: bool = _env_bool("MIJI_LIGHTWEIGHT_MODE", True)
    miji_enable_heavy_alpha: bool = _env_bool("MIJI_ENABLE_HEAVY_ALPHA", False)
    miji_enable_heavy_regime: bool = _env_bool("MIJI_ENABLE_HEAVY_REGIME", False)
    miji_enable_theme_forecast: bool = _env_bool("MIJI_ENABLE_THEME_FORECAST", False)
    miji_enable_lean: bool = _env_bool("MIJI_ENABLE_LEAN", False)
    miji_enable_background_jobs: bool = _env_bool("MIJI_ENABLE_BACKGROUND_JOBS", False)
    miji_enable_feature_store: bool = _env_bool("MIJI_ENABLE_FEATURE_STORE", False)
    miji_feature_store_dir: Path = Path(os.getenv("MIJI_FEATURE_STORE_DIR", ".cache/research_store"))
    alpha_regime_circuit_cooldown_seconds: int = int(os.getenv("ALPHA_REGIME_CIRCUIT_COOLDOWN_SECONDS", "120"))
    provider_timeout_seconds: float = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "8"))
    provider_retry_count: int = int(os.getenv("PROVIDER_RETRY_COUNT", "2"))
    provider_retry_backoff_seconds: float = float(os.getenv("PROVIDER_RETRY_BACKOFF_SECONDS", "1.25"))
    enable_scheduler: bool = _env_bool("ENABLE_SCHEDULER", False)
    fmp_api_key: str = os.getenv("FMP_API_KEY", "")
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "")
    alpha_vantage_api_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    firebase_server_key: str = os.getenv("FIREBASE_SERVER_KEY", "")
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_whitelist",
            _cors_origins(),
        )
        if self.miji_runtime_mode == "local_full":
            object.__setattr__(self, "miji_lightweight_mode", _env_bool("MIJI_LIGHTWEIGHT_MODE", False))
            object.__setattr__(self, "miji_enable_theme_forecast", _env_bool("MIJI_ENABLE_THEME_FORECAST", True))
            object.__setattr__(self, "miji_enable_feature_store", _env_bool("MIJI_ENABLE_FEATURE_STORE", True))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_cache_path.parent.mkdir(parents=True, exist_ok=True)
    settings.miji_feature_store_dir.mkdir(parents=True, exist_ok=True)
    return settings
