from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.models.metadata import RushScanResult
from app.models.templates import ColorManagementProfile, PrepTemplate, TimelineSettings, TreeNode

logger = logging.getLogger(__name__)


@dataclass
class ResolveBridge:
    dry_run: bool = False
    _resolve: Any | None = field(default=None, init=False)
    _project: Any | None = field(default=None, init=False)
    _media_pool: Any | None = field(default=None, init=False)
    _root_folder: Any | None = field(default=None, init=False)

    def connect(self) -> None:
        if self.dry_run:
            return
        resolve = _load_resolve()
        project_manager = resolve.GetProjectManager()
        self._resolve = resolve
        self._project = project_manager.GetCurrentProject()
        if self._project is None:
            raise RuntimeError("No project open in DaVinci Resolve")
        self._media_pool = self._project.GetMediaPool()
        self._root_folder = self._media_pool.GetRootFolder()

    def create_or_load_project(self, project_name: str) -> None:
        if self.dry_run:
            return
        assert self._resolve is not None
        project_manager = self._resolve.GetProjectManager()
        if not project_manager.LoadProject(project_name):
            if not project_manager.CreateProject(project_name):
                raise RuntimeError(f"Unable to create project: {project_name}")
        self._project = project_manager.GetCurrentProject()
        self._media_pool = self._project.GetMediaPool()
        self._root_folder = self._media_pool.GetRootFolder()

    def ensure_bins(self, nodes: list[TreeNode], parent: Any | None = None) -> dict[str, Any]:
        if self.dry_run:
            return {path: None for path in _flatten_bin_paths(nodes)}
        assert self._media_pool is not None
        parent = parent or self._root_folder
        mapping: dict[str, Any] = {}
        for node in nodes:
            mapping.update(self._ensure_bin_node(node, parent, prefix=""))
        return mapping

    def _ensure_bin_node(self, node: TreeNode, parent: Any, prefix: str) -> dict[str, Any]:
        assert self._media_pool is not None
        current_path = f"{prefix}/{node.name}" if prefix else node.name
        folder = _find_subfolder(parent, node.name)
        if folder is None:
            folder = self._media_pool.AddSubFolder(parent, node.name)
        if folder is None:
            raise RuntimeError(f"Unable to create bin: {current_path}")

        mapping = {current_path: folder}
        for child in node.children:
            mapping.update(self._ensure_bin_node(child, folder, current_path))
        return mapping

    def apply_color_management(self, profile: ColorManagementProfile) -> None:
        if self.dry_run:
            return
        project = self._require_project()
        project.SetSetting("colorScienceMode", profile.color_science_mode)
        if profile.separate_color_space_and_gamma:
            project.SetSetting("separateColorSpaceAndGamma", "1")
        settings_map = {
            "colorSpaceInput": profile.color_space_input,
            "colorSpaceTimeline": profile.color_space_timeline,
            "colorSpaceTimelineGamma": profile.color_space_timeline_gamma,
            "colorSpaceOutput": profile.color_space_output,
            "colorSpaceOutputGamma": profile.color_space_output_gamma,
        }
        for key, value in settings_map.items():
            if value:
                project.SetSetting(key, value)

    def import_card_media(
        self,
        scan: RushScanResult,
        bin_mapping: dict[str, Any],
        rushes_bin_name: str = "01_RUSHES",
    ) -> dict[str, list[Any]]:
        imported: dict[str, list[Any]] = {}
        if self.dry_run:
            for card_id, files in scan.cards.items():
                imported[card_id] = [file.path for file in files]
            return imported

        assert self._media_pool is not None
        rushes_folder = bin_mapping.get(rushes_bin_name)
        if rushes_folder is None:
            raise RuntimeError(f"Missing bin: {rushes_bin_name}")

        for card_id, files in scan.cards.items():
            card_folder = _find_subfolder(rushes_folder, card_id)
            if card_folder is None:
                card_folder = self._media_pool.AddSubFolder(rushes_folder, card_id)
            if card_folder is None:
                raise RuntimeError(f"Unable to create card bin: {card_id}")

            self._media_pool.SetCurrentFolder(card_folder)
            clip_paths = [file.path for file in files]
            clips = self._media_pool.ImportMedia(clip_paths) or []
            imported[card_id] = list(clips)
        return imported

    def build_timelines(
        self,
        scan: RushScanResult,
        imported: dict[str, list[Any]],
        timeline_settings: TimelineSettings,
        timelines_bin_name: str = "02_TIMELINES",
        bin_mapping: dict[str, Any] | None = None,
    ) -> list[str]:
        created: list[str] = []
        if self.dry_run:
            for card_id in scan.cards:
                created.append(f"TL_{card_id}")
            return created

        assert self._media_pool is not None
        timelines_folder = None
        if bin_mapping:
            timelines_folder = bin_mapping.get(timelines_bin_name)
        if timelines_folder is not None:
            self._media_pool.SetCurrentFolder(timelines_folder)

        for card_id, clips in imported.items():
            if not clips:
                continue
            timeline_name = f"TL_{card_id}"
            timeline = self._media_pool.CreateEmptyTimeline(timeline_name)
            if timeline is None:
                raise RuntimeError(f"Unable to create timeline: {timeline_name}")

            self._apply_timeline_settings(timeline, timeline_settings)
            self._media_pool.SetCurrentTimeline(timeline)
            self._media_pool.AppendToTimeline(clips)
            created.append(timeline_name)
        return created

    def queue_exports(
        self,
        timeline_names: list[str],
        export_dir: Path,
        template: PrepTemplate,
    ) -> list[str]:
        queued: list[str] = []
        if self.dry_run:
            return timeline_names

        project = self._require_project()
        export_dir.mkdir(parents=True, exist_ok=True)

        for timeline_name in timeline_names:
            timeline = _find_timeline(project, timeline_name)
            if timeline is None:
                raise RuntimeError(f"Timeline not found: {timeline_name}")

            if template.export.use_render_preset and template.export.render_preset_name:
                project.LoadRenderPreset(template.export.render_preset_name)

            project.SetRenderSettings(
                {
                    "TargetDir": str(export_dir),
                    "CustomName": timeline_name,
                    "SelectAllFrames": True,
                }
            )
            job_id = project.AddRenderJob()
            if job_id:
                queued.append(str(job_id))
        return queued

    def start_render(self) -> bool:
        if self.dry_run:
            return True
        project = self._require_project()
        return bool(project.StartRendering())

    def _apply_timeline_settings(self, timeline: Any, settings: TimelineSettings) -> None:
        timeline.SetSetting("timelineFrameRate", settings.frame_rate)
        timeline.SetSetting("timelineResolutionWidth", settings.resolution.split("x")[0])
        timeline.SetSetting("timelineResolutionHeight", settings.resolution.split("x")[1])
        timeline.SetSetting("timelinePixelAspectRatio", settings.pixel_aspect)
        if settings.color_timeline_space:
            timeline.SetSetting("colorSpaceTimeline", settings.color_timeline_space)
        if settings.color_timeline_gamma:
            timeline.SetSetting("colorSpaceTimelineGamma", settings.color_timeline_gamma)

    def _require_project(self) -> Any:
        if self._project is None:
            raise RuntimeError("Resolve project not connected")
        return self._project


def _load_resolve() -> Any:
    if sys.platform == "darwin":
        modules = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
        lib = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    elif sys.platform == "win32":
        modules = os.path.join(
            os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
            "Blackmagic Design",
            "DaVinci Resolve",
            "Support",
            "Developer",
            "Scripting",
            "Modules",
        )
        lib = "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll"
    else:
        modules = "/opt/resolve/Developer/Scripting/Modules"
        lib = "/opt/resolve/libs/Fusion/fusionscript.so"

    if modules not in sys.path:
        sys.path.append(modules)
    os.environ.setdefault("RESOLVE_SCRIPT_API", str(Path(modules).parent))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)

    import DaVinciResolveScript as dvr  # type: ignore[import-not-found]

    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError(
            "Unable to connect to DaVinci Resolve. "
            "Ensure Studio is running and external scripting is set to Local."
        )
    return resolve


def _find_subfolder(parent: Any, name: str) -> Any | None:
    for subfolder in parent.GetSubFolderList() or []:
        if subfolder.GetName() == name:
            return subfolder
    return None


def _find_timeline(project: Any, name: str) -> Any | None:
    count = int(project.GetTimelineCount())
    for index in range(1, count + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline and timeline.GetName() == name:
            return timeline
    return None


def _flatten_bin_paths(nodes: list[TreeNode], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for node in nodes:
        current = f"{prefix}/{node.name}" if prefix else node.name
        paths.append(current)
        paths.extend(_flatten_bin_paths(node.children, current))
    return paths
