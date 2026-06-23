from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.templates import PrepTemplate
from app.models.workflow import WorkflowRequest, WorkflowResult
from app.services.template_store import TemplateStore
from app.services.workflow_runner import WorkflowRunner

app = FastAPI(
    title="Resolve Prep API",
    version="0.1.0",
    description="Prep, ingest, timeline and transcode workflow for DaVinci Resolve",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

template_store = TemplateStore()
workflow_runner = WorkflowRunner()


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "dry_run_default": settings.dry_run,
    }


@app.get("/templates", response_model=list[PrepTemplate])
def list_templates() -> list[PrepTemplate]:
    return template_store.list_templates()


@app.get("/templates/{template_id}", response_model=PrepTemplate)
def get_template(template_id: str) -> PrepTemplate:
    try:
        return template_store.load(template_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/templates", response_model=PrepTemplate)
def save_template(template: PrepTemplate) -> PrepTemplate:
    return template_store.save(template)


@app.post("/workflow/run", response_model=WorkflowResult)
def run_workflow(request: WorkflowRequest) -> WorkflowResult:
    return workflow_runner.run(request)
