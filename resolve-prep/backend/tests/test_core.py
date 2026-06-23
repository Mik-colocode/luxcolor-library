from pathlib import Path

from app.services.metadata_scanner import MetadataScanner
from app.services.template_store import TemplateStore


def test_template_store_loads_default() -> None:
    store = TemplateStore(templates_dir=Path(__file__).resolve().parents[2] / "templates")
    template = store.load("default-prep")
    assert template.id == "default-prep"
    assert "01_RUSHES" in template.iter_resolve_bin_paths()


def test_metadata_scanner_flat_mode(tmp_path: Path) -> None:
    media = tmp_path / "clip.mov"
    media.write_bytes(b"fake")
    scanner = MetadataScanner()
    result = scanner.scan(tmp_path, card_grouping="flat")
    assert result.total_files == 1
    assert "ALL" in result.cards
