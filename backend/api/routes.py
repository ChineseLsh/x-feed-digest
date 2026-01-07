from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.core.storage import (
    get_job_status,
    list_all_jobs,
    save_output,
    save_summary,
    save_upload,
    set_job_status,
)
from backend.models.schemas import JobListResponse, JobResponse, JobStatus, SummaryResponse
from backend.services.batch_fetcher import fetch_all_tweets
from backend.services.csv_parser import extract_users
from backend.services.summarizer import summarize_csv

router = APIRouter()


def _get_app_cfg(request: Request) -> dict:
    return request.app.state.app_cfg


def _get_providers_cfg(request: Request) -> dict:
    return request.app.state.providers_cfg


def _run_job(job_id: str, upload_path: Path, app_cfg: dict, providers_cfg: dict, batch_size: int, total_users: int) -> None:
    usernames_count = total_users
    total_batches = (usernames_count + batch_size - 1) // batch_size

    status = {
        "job_id": job_id,
        "status": "running",
        "created_at": int(time.time()),
        "batch_size": batch_size,
        "total_users": usernames_count,
        "completed_batches": 0,
        "total_batches": total_batches,
    }
    set_job_status(app_cfg, job_id, status)

    def on_batch_complete(completed: int, total: int):
        status["completed_batches"] = completed
        set_job_status(app_cfg, job_id, status)

    try:
        csv_text = fetch_all_tweets(
            app_cfg, providers_cfg, upload_path, batch_size,
            on_batch_complete=on_batch_complete
        )
        save_output(app_cfg, job_id, csv_text)

        status["status"] = "summarizing"
        set_job_status(app_cfg, job_id, status)

        summary_text = summarize_csv(app_cfg, providers_cfg, csv_text)
        save_summary(app_cfg, job_id, summary_text)

        status["status"] = "done"
        set_job_status(app_cfg, job_id, status)
    except Exception as exc:
        status["status"] = "failed"
        status["error"] = str(exc)
        set_job_status(app_cfg, job_id, status)


@router.post("/jobs", response_model=JobResponse)
def create_job(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_size: Optional[int] = None,
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    app_cfg = _get_app_cfg(request)
    providers_cfg = _get_providers_cfg(request)

    batching_cfg = app_cfg.get("batching", {})
    default_size = int(batching_cfg.get("default_batch_size", 10))
    max_size = int(batching_cfg.get("max_batch_size", 50))

    size = batch_size or default_size
    if size > max_size:
        raise HTTPException(status_code=400, detail=f"batch_size exceeds max_batch_size ({max_size})")

    job_id = str(uuid.uuid4())
    upload_path = save_upload(app_cfg, job_id, file)

    try:
        handles, _ = extract_users(upload_path)
        total_users = len(handles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    status = {
        "job_id": job_id,
        "status": "queued",
        "created_at": int(time.time()),
        "batch_size": size,
        "total_users": total_users,
        "completed_batches": 0,
        "total_batches": (total_users + size - 1) // size,
    }
    set_job_status(app_cfg, job_id, status)

    background_tasks.add_task(_run_job, job_id, upload_path, app_cfg, providers_cfg, size, total_users)

    return JobResponse(job_id=job_id, status="queued")


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(request: Request):
    app_cfg = _get_app_cfg(request)
    jobs = list_all_jobs(app_cfg)
    return JobListResponse(jobs=[JobStatus(**j) for j in jobs])


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, request: Request):
    app_cfg = _get_app_cfg(request)
    status = get_job_status(app_cfg, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**status)


@router.get("/jobs/{job_id}/summary", response_model=SummaryResponse)
def get_summary(job_id: str, request: Request):
    app_cfg = _get_app_cfg(request)
    summaries_dir = Path(app_cfg["storage"]["summaries"])
    path = summaries_dir / f"{job_id}.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Summary not found")
    return SummaryResponse(summary_text=path.read_text(encoding="utf-8"))


@router.get("/jobs/{job_id}/download")
def download_csv(job_id: str, request: Request):
    app_cfg = _get_app_cfg(request)
    outputs_dir = Path(app_cfg["storage"]["outputs"])
    path = outputs_dir / f"{job_id}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output CSV not found")
    return FileResponse(path, media_type="text/csv", filename=f"tweets_{job_id}.csv")