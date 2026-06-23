from __future__ import annotations

from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    """Recursive folder/bin node used for Resolve and filesystem trees."""

    name: str = Field(..., min_length=1, description="Folder or bin name")
    children: list[TreeNode] = Field(default_factory=list)


class TimelineSettings(BaseModel):
    frame_rate: str = "25"
    resolution: str = "1920x1080"
    pixel_aspect: str = "square"
    color_timeline_space: str | None = None
    color_timeline_gamma: str | None = None


class ColorManagementProfile(BaseModel):
    color_science_mode: str = "davinciYRGBColorManagedv2"
    separate_color_space_and_gamma: bool = True
    color_space_input: str | None = None
    color_space_timeline: str | None = None
    color_space_timeline_gamma: str | None = None
    color_space_output: str | None = None
    color_space_output_gamma: str | None = None


class ExportProfile(BaseModel):
    name: str = "default_transcode"
    use_render_preset: bool = True
    render_preset_name: str | None = "H.264_Proxy"
    target_dir_relative: str = "03_EXPORTS/TRANSCODES"
    custom: dict[str, str | int | float | bool] = Field(default_factory=dict)


class PrepTemplate(BaseModel):
    id: str
    name: str
    version: int = 1
    description: str = ""
    resolve_bins: list[TreeNode] = Field(default_factory=list)
    filesystem: list[TreeNode] = Field(default_factory=list)
    timeline: TimelineSettings = Field(default_factory=TimelineSettings)
    color_management: ColorManagementProfile = Field(default_factory=ColorManagementProfile)
    export: ExportProfile = Field(default_factory=ExportProfile)

    def iter_resolve_bin_paths(self) -> list[str]:
        return _flatten_paths(self.resolve_bins)

    def iter_filesystem_paths(self) -> list[str]:
        return _flatten_paths(self.filesystem)


def _flatten_paths(nodes: list[TreeNode], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for node in nodes:
        current = f"{prefix}/{node.name}" if prefix else node.name
        paths.append(current)
        paths.extend(_flatten_paths(node.children, current))
    return paths
