from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.models.metadata import RushScanResult, VideoMetadata


class MetadataScanner:
    def __init__(self, video_extensions: tuple[str, ...] | None = None) -> None:
        self.video_extensions = video_extensions or settings.video_extensions
        self._ffprobe = shutil.which("ffprobe")

    def scan(
        self,
        rushes_root: Path,
        card_grouping: str = "folder",
    ) -> RushScanResult:
        root = rushes_root.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Rushes folder not found: {root}")

        cards: dict[str, list[VideoMetadata]] = {}
        errors: list[str] = []

        if card_grouping == "flat":
            cards["ALL"] = self._scan_directory(root, card_id="ALL", errors=errors)
        else:
            subdirs = sorted(p for p in root.iterdir() if p.is_dir())
            if subdirs:
                for subdir in subdirs:
                    cards[subdir.name] = self._scan_directory(
                        subdir,
                        card_id=subdir.name,
                        errors=errors,
                    )
            else:
                cards[root.name] = self._scan_directory(root, card_id=root.name, errors=errors)

        total = sum(len(files) for files in cards.values())
        return RushScanResult(root=str(root), cards=cards, total_files=total, errors=errors)

    def _scan_directory(
        self,
        directory: Path,
        card_id: str,
        errors: list[str],
    ) -> list[VideoMetadata]:
        files: list[VideoMetadata] = []
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.video_extensions:
                continue
            try:
                files.append(self._probe_file(path, card_id))
            except Exception as exc:  # noqa: BLE001 - collect per-file errors for operator review
                errors.append(f"{path}: {exc}")
        return files

    def _probe_file(self, path: Path, card_id: str) -> VideoMetadata:
        stat = path.stat()
        meta = VideoMetadata(
            path=str(path),
            filename=path.name,
            extension=path.suffix.lower(),
            size_bytes=stat.st_size,
            card_id=card_id,
        )
        if not self._ffprobe:
            return meta

        cmd = [
            self._ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            meta.raw_tags["ffprobe_error"] = result.stderr.strip() or "ffprobe failed"
            return meta

        payload = json.loads(result.stdout or "{}")
        format_tags = payload.get("format", {}).get("tags", {}) or {}
        streams = payload.get("streams", []) or []
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

        duration = payload.get("format", {}).get("duration")
        if duration is not None:
            meta.duration_seconds = float(duration)

        meta.width = _as_int(video_stream.get("width"))
        meta.height = _as_int(video_stream.get("height"))
        meta.codec = video_stream.get("codec_name")
        meta.frame_rate = _parse_frame_rate(video_stream.get("avg_frame_rate"))
        meta.timecode = format_tags.get("timecode") or video_stream.get("tags", {}).get("timecode")
        meta.camera_model = format_tags.get("com.apple.proapps.cameraName") or format_tags.get(
            "camera_model"
        )
        meta.reel_name = format_tags.get("reel_name")

        meta.raw_tags = {
            str(key): str(value)
            for key, value in {**format_tags, **(video_stream.get("tags") or {})}.items()
        }
        return meta


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_frame_rate(value: object) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and "/" in value:
        num, den = value.split("/", 1)
        try:
            denominator = float(den)
            if denominator == 0:
                return None
            return float(num) / denominator
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
