from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Geospatial File Measurement API"
    app_version: str = "1.0.0"
    cors_origins: list[str] = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    metadata_dir: Path = Path("data/metadata")
    measurements_dir: Path = Path("data/measurements")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GEO_API_")

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.measurements_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
