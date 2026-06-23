from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.models.workflow import StepResult, WorkflowRequest, WorkflowResult, WorkflowStep
from app.services.filesystem import FilesystemService
from app.services.metadata_scanner import MetadataScanner
from app.services.resolve_bridge import ResolveBridge
from app.services.template_store import TemplateStore


class WorkflowRunner:
    def __init__(self) -> None:
        self.templates = TemplateStore()
        self.filesystem = FilesystemService()
        self.scanner = MetadataScanner()

    def run(self, request: WorkflowRequest) -> WorkflowResult:
        template = self.templates.load(request.template_id)
        dry_run = request.dry_run if request.dry_run is not None else settings.dry_run
        production_root = Path(request.production_root).expanduser().resolve()
        rushes_root = Path(request.rushes_root).expanduser().resolve()

        result = WorkflowResult(
            project_name=request.project_name,
            template=template,
            dry_run=dry_run,
        )

        resolve = ResolveBridge(dry_run=dry_run)

        # Step 1 — prep project structure
        try:
            if not dry_run:
                resolve.connect()
                resolve.create_or_load_project(request.project_name)
            fs_created = self.filesystem.ensure_tree(
                production_root,
                template.filesystem,
                dry_run=dry_run,
            )
            if not dry_run:
                bin_mapping = resolve.ensure_bins(template.resolve_bins)
                resolve.apply_color_management(template.color_management)
            else:
                bin_mapping = {path: None for path in template.iter_resolve_bin_paths()}

            result.steps.append(
                StepResult(
                    step=WorkflowStep.PREP_PROJECT,
                    success=True,
                    message="Project and folder structure prepared",
                    details={
                        "production_root": str(production_root),
                        "filesystem_created": fs_created,
                        "resolve_bins": list(bin_mapping.keys()),
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            result.steps.append(
                StepResult(
                    step=WorkflowStep.PREP_PROJECT,
                    success=False,
                    message=str(exc),
                )
            )
            return result

        # Step 2 — scan rushes
        try:
            scan = self.scanner.scan(rushes_root, card_grouping=request.card_grouping)
            result.scan = scan
            result.steps.append(
                StepResult(
                    step=WorkflowStep.SCAN_RUSHES,
                    success=True,
                    message=f"Scanned {scan.total_files} files across {len(scan.cards)} cards",
                    details={
                        "cards": {card: len(files) for card, files in scan.cards.items()},
                        "errors": scan.errors,
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            result.steps.append(
                StepResult(
                    step=WorkflowStep.SCAN_RUSHES,
                    success=False,
                    message=str(exc),
                )
            )
            return result

        # Step 3 — import media
        try:
            imported = resolve.import_card_media(scan, bin_mapping)
            result.steps.append(
                StepResult(
                    step=WorkflowStep.IMPORT_MEDIA,
                    success=True,
                    message="Media imported into card bins",
                    details={
                        card: len(clips) for card, clips in imported.items()
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            result.steps.append(
                StepResult(
                    step=WorkflowStep.IMPORT_MEDIA,
                    success=False,
                    message=str(exc),
                )
            )
            return result

        timeline_names: list[str] = []

        # Step 4 — build timelines
        if request.create_timelines:
            try:
                timeline_names = resolve.build_timelines(
                    scan,
                    imported,
                    template.timeline,
                    bin_mapping=bin_mapping,
                )
                result.steps.append(
                    StepResult(
                        step=WorkflowStep.BUILD_TIMELINES,
                        success=True,
                        message=f"Created {len(timeline_names)} timelines",
                        details={"timelines": timeline_names},
                    )
                )
            except Exception as exc:  # noqa: BLE001
                result.steps.append(
                    StepResult(
                        step=WorkflowStep.BUILD_TIMELINES,
                        success=False,
                        message=str(exc),
                    )
                )
                return result

        # Step 5 — queue exports
        if request.queue_exports and timeline_names:
            try:
                export_dir = self.filesystem.resolve_path(
                    production_root,
                    template.export.target_dir_relative,
                )
                jobs = resolve.queue_exports(timeline_names, export_dir, template)
                if not dry_run:
                    resolve.start_render()
                result.steps.append(
                    StepResult(
                        step=WorkflowStep.QUEUE_EXPORTS,
                        success=True,
                        message=f"Queued {len(jobs)} render jobs",
                        details={
                            "export_dir": str(export_dir),
                            "jobs": jobs,
                        },
                    )
                )
            except Exception as exc:  # noqa: BLE001
                result.steps.append(
                    StepResult(
                        step=WorkflowStep.QUEUE_EXPORTS,
                        success=False,
                        message=str(exc),
                    )
                )

        return result
