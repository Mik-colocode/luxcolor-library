from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.metadata import RushScanResult
from app.models.templates import PrepTemplate


class WorkflowStep(str, Enum):
    PREP_PROJECT = "prep_project"
    SCAN_RUSHES = "scan_rushes"
    IMPORT_MEDIA = "import_media"
    BUILD_TIMELINES = "build_timelines"
    QUEUE_EXPORTS = "queue_exports"


class WorkflowRequest(BaseModel):
    project_name: str = Field(..., min_length=1)
    production_root: str = Field(..., description="Root folder on disk for the production")
    rushes_root: str = Field(..., description="Folder containing camera cards or day folders")
    template_id: str = "default-prep"
    card_grouping: str = Field(
        default="folder",
        description="folder = first subfolder under rushes_root, flat = single card",
    )
    create_timelines: bool = True
    queue_exports: bool = False
    dry_run: bool | None = None


class StepResult(BaseModel):
    step: WorkflowStep
    success: bool
    message: str
    details: dict = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    project_name: str
    template: PrepTemplate
    scan: RushScanResult | None = None
    steps: list[StepResult] = Field(default_factory=list)
    dry_run: bool = False
