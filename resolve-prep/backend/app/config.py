from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESOLVE_PREP_")

    templates_dir: Path = Path(__file__).resolve().parents[2] / "templates"
    dry_run: bool = False
    video_extensions: tuple[str, ...] = (
        ".mov",
        ".mp4",
        ".mxf",
        ".r3d",
        ".braw",
        ".ari",
        ".dng",
        ".mts",
        ".m2ts",
        ".avi",
        ".mkv",
    )


settings = Settings()
