from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=()
    )
    model_service_url: str = "http://127.0.0.1:8001"
    model_timeout_seconds: float = Field(default=10, gt=0, le=120)
    max_request_bytes: int = Field(default=1000000, ge=1, le=10000000)
    max_code_chars: int = Field(default=100000, ge=1, le=100000)
    max_files: int = Field(default=50, ge=1, le=200)
    max_functions: int = Field(default=200, ge=1, le=1000)
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    cors_origins: list[str] = ["http://localhost:3002"]
    environment: str = "development"
    dev_login_enabled: bool = False
    github_webhook_secret: str = ""
    allow_python_ast: bool = False
    static_analysis_mode: Literal["external", "builtin-python"] = "external"
    risk_model_weight: float = Field(default=0.5, ge=0, le=1)
    risk_static_weight: float = Field(default=0.5, ge=0, le=1)
    risk_agreement_bonus: float = Field(default=0.1, ge=0, le=1)
    risk_warn_threshold: float = Field(default=0.35, gt=0, le=1)
    risk_block_threshold: float = Field(default=0.65, gt=0, le=1)
    database_url: str = "sqlite:///codesentinel.db"
    auth_required: bool = True
    jwt_secret: str = ""
    jwt_expiry_minutes: int = Field(default=60, ge=1, le=1440)
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_callback_url: str = "http://localhost:8000/auth/github/callback"
    github_allowed_user_ids: list[str] = []
    frontend_url: str = "http://localhost:3002"
    github_token: str = ""
    github_app_id: str = ""
    github_app_installation_id: int = Field(default=0, ge=0)
    github_app_private_key: str = ""

    @model_validator(mode="after")
    def production_controls(self) -> "Settings":
        if abs(self.risk_model_weight + self.risk_static_weight - 1.0) > 1e-9:
            raise ValueError("Risk weights must sum to one")
        if self.risk_warn_threshold >= self.risk_block_threshold:
            raise ValueError("Risk thresholds must be ordered")
        if self.environment == "production":
            if (
                self.dev_login_enabled
                or not self.auth_required
                or len(self.jwt_secret) < 32
            ):
                raise ValueError(
                    "Production requires auth, strong JWT secret, and disabled dev login"
                )
        return self

    scan_timeout_seconds: float = Field(default=60, gt=0, le=300)
    github_oidc_enabled: bool = False
    github_allowed_repositories: list[str] = []
    github_oidc_audience: str = "codesentinel"
