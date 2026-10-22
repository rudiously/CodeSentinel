from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=()
    )
    model_artifact_dir: Path = Path("models/codesentinel-codebert/v1")
    max_code_chars: int = Field(default=100000, ge=1, le=100000)
    max_batch_size: int = Field(default=32, ge=1, le=32)
    max_request_bytes: int = Field(default=1000000, ge=1, le=10000000)
    explain_steps: int = Field(default=8, ge=0, le=64)
