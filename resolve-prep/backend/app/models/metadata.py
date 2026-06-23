from __future__ import annotations

from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    path: str
    filename: str
    extension: str
    size_bytes: int
    card_id: str
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    frame_rate: float | None = None
    codec: str | None = None
    timecode: str | None = None
    camera_model: str | None = None
    reel_name: str | None = None
    raw_tags: dict[str, str] = Field(default_factory=dict)


class RushScanResult(BaseModel):
    root: str
    cards: dict[str, list[VideoMetadata]]
    total_files: int
    errors: list[str] = Field(default_factory=list)
