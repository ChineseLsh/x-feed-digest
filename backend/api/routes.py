from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.core.storage import (
    delete_subscription,
    get_batch_output,
    get_job_status,
    get_subscription,
    get_subscription_csv_path,
    list_all_jobs,
    list_batch_statuses,
    list_subscriptions,
    save_output,
    save_subscription,
    save_subscription_csv,
    save_summary,
    save_upload,
    set_job_status,
)
from backend.models.schemas import (
    JobListResponse,
    JobResponse,
    JobStatus,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionStatus,
    SubscriptionUpdate,
    SummaryResponse,
)
from backend.services.batch_fetcher import fetch_all_tweets, fetch_single_batch_for_job
from backend.services.csv_parser import extract_users
from backend.services.job_runner import run_job
from backend.services.summarizer import summarize_csv

router = APIRouter()


def _get_app_cfg(request: Request) -> dict:
    return request.app.state.app_cfg


def _get_providers_cfg(request: Request) -> dict:
    return request.app.state.providers_cfg


def _get_scheduler(request: Request):
    return getattr(request.app.state, "scheduler", None)


def _run_job(job_id: str, upload_path: Path, app_cfg: dict, providers_cfg: dict, batch_size: int, total_users: int) -> None:
    run_job(job_id, upload_path, app_cfg, providers_cfg, batch_size, total_users)


def _update_job_batch_counts(app_cfg: dict, job_id: str) -> None:
    status = get_job_status(app_cfg, job_id)
    if not status:
        return
    batches = list_batch_statuses(app_cfg, job_id)
    status["failed_batches"] = sum(1 for b in batches if b.get("status") == "failed")
    status["succeeded_batches"] = sum(1 for b in batches if b.get("status") == "succeeded")
    set_job_status(app_cfg, job_id, status)


def _retry_batch(job_id: str, batch_idx: int, app_cfg: dict, providers_cfg: dict) -> None:
    status = get_job_status(app_cfg, job_id)
    if not status:
        return
    batch_size = status.get("batch_size")
    if not batch_size:
        return
    upload_path = Path(app_cfg["storage"]["uploads"]) / f"{job_id}.csv"
    if not upload_path.exists():
        return
    total_users = status.get("total_users")
    if total_users is not None:
        total_batches = (total_users + batch_size - 1) // batch_size
        if batch_idx < 0 or batch_idx >= total_batches:
            return

    status["status"] = "running"
    set_job_status(app_cfg, job_id, status)

    try:
        fetch_single_batch_for_job(
            app_cfg,
            providers_cfg,
            upload_path,
            batch_size,
            batch_idx,
            job_id,
        )
    except Exception as exc:
        status["error"] = f"Batch {batch_idx} retry failed: {exc}"
        status["status"] = "failed"
        set_job_status(app_cfg, job_id, status)
        return

    _update_job_batch_counts(app_cfg, job_id)

    status = get_job_status(app_cfg, job_id)
    if status and status.get("failed_batches", 0) == 0:
        status["status"] = "done"
        status["error"] = None
    else:
        status["status"] = "failed"
    set_job_status(app_cfg, job_id, status)


def _aggregate_job(job_id: str, app_cfg: dict, providers_cfg: dict, summarize: bool) -> None:
    status = get_job_status(app_cfg, job_id)
    if not status:
        return
    batches = list_batch_statuses(app_cfg, job_id)
    successful_batches = [b for b in batches if b.get("status") == "succeeded"]
    if not successful_batches:
        status["status"] = "failed"
        status["error"] = "No successful batches to aggregate"
        set_job_status(app_cfg, job_id, status)
        return

    status["status"] = "summarizing"
    set_job_status(app_cfg, job_id, status)

    combined_lines = []
    missing_outputs = []
    for batch in sorted(successful_batches, key=lambda x: x.get("index", 0)):
        batch_idx = batch.get("index")
        if batch_idx is None:
            continue
        csv_text = get_batch_output(app_cfg, job_id, batch_idx)
        if not csv_text:
            missing_outputs.append(batch_idx)
            continue
        lines = [line for line in csv_text.splitlines() if line]
        if not lines:
            continue
        if not combined_lines:
            combined_lines.extend(lines)
        else:
            combined_lines.extend(lines[1:])

    if missing_outputs:
        status["status"] = "failed"
        status["error"] = f"Missing output files for batches: {missing_outputs}"
        set_job_status(app_cfg, job_id, status)
        return

    if not combined_lines:
        combined_lines = ["username,tweet_id,created_at,text,original_url"]
    csv_text = "\n".join(combined_lines) + "\n"
    save_output(app_cfg, job_id, csv_text)

    if summarize:
        try:
            summary_text = summarize_csv(app_cfg, providers_cfg, csv_text)
            save_summary(app_cfg, job_id, summary_text)
        except Exception as exc:
            status["status"] = "failed"
            status["error"] = f"Summarization failed: {exc}"
            set_job_status(app_cfg, job_id, status)
            return

    status["status"] = "done"
    status["error"] = None
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
    status["batches"] = list_batch_statuses(app_cfg, job_id)
    return JobStatus(**status)


@router.post("/jobs/{job_id}/batches/{batch_idx}/retry", response_model=JobResponse)
def retry_job_batch(
    job_id: str,
    batch_idx: int,
    request: Request,
    background_tasks: BackgroundTasks,
):
    app_cfg = _get_app_cfg(request)
    providers_cfg = _get_providers_cfg(request)
    status = get_job_status(app_cfg, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    total_users = status.get("total_users")
    batch_size = status.get("batch_size")
    if total_users is not None and batch_size:
        total_batches = (total_users + batch_size - 1) // batch_size
        if batch_idx < 0 or batch_idx >= total_batches:
            raise HTTPException(status_code=400, detail="batch_idx out of range")
    background_tasks.add_task(_retry_batch, job_id, batch_idx, app_cfg, providers_cfg)
    return JobResponse(job_id=job_id, status="retrying")


@router.post("/jobs/{job_id}/aggregate", response_model=JobResponse)
def aggregate_job_endpoint(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    summarize: bool = True,
):
    app_cfg = _get_app_cfg(request)
    providers_cfg = _get_providers_cfg(request)
    status = get_job_status(app_cfg, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    background_tasks.add_task(_aggregate_job, job_id, app_cfg, providers_cfg, summarize)
    return JobResponse(job_id=job_id, status="aggregating")


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


# ─── Subscription Endpoints ───


@router.post("/subscriptions", response_model=SubscriptionResponse)
def create_subscription(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    schedule_hour: int = Form(8),
    schedule_minute: int = Form(0),
    enabled: bool = Form(True),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    app_cfg = _get_app_cfg(request)

    sub_id = str(uuid.uuid4())
    csv_path = save_subscription_csv(app_cfg, sub_id, file)

    try:
        handles, _ = extract_users(csv_path)
        total_users = len(handles)
    except ValueError as e:
        csv_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    now = int(time.time())
    sub = {
        "id": sub_id,
        "name": name or file.filename,
        "csv_filename": file.filename,
        "schedule_hour": schedule_hour,
        "schedule_minute": schedule_minute,
        "enabled": enabled,
        "created_at": now,
        "updated_at": now,
        "last_run": None,
        "next_run": None,
        "last_job_id": None,
        "last_status": None,
        "last_error": None,
        "total_users": total_users,
    }
    save_subscription(app_cfg, sub_id, sub)

    scheduler = _get_scheduler(request)
    if scheduler and enabled:
        scheduler.schedule_subscription(sub_id)

    return SubscriptionResponse(id=sub_id, status="created")


@router.get("/subscriptions", response_model=SubscriptionListResponse)
def list_subs(request: Request):
    app_cfg = _get_app_cfg(request)
    scheduler = _get_scheduler(request)
    
    subs = list_subscriptions(app_cfg)
    
    # Update next_run from scheduler
    for sub in subs:
        if scheduler:
            next_run = scheduler.get_next_run(sub["id"])
            if next_run:
                sub["next_run"] = next_run
    
    return SubscriptionListResponse(subscriptions=[SubscriptionStatus(**s) for s in subs])


@router.get("/subscriptions/{sub_id}", response_model=SubscriptionStatus)
def get_sub(sub_id: str, request: Request):
    app_cfg = _get_app_cfg(request)
    sub = get_subscription(app_cfg, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    scheduler = _get_scheduler(request)
    if scheduler:
        next_run = scheduler.get_next_run(sub_id)
        if next_run:
            sub["next_run"] = next_run
    
    return SubscriptionStatus(**sub)


@router.patch("/subscriptions/{sub_id}", response_model=SubscriptionStatus)
def update_sub(sub_id: str, update: SubscriptionUpdate, request: Request):
    app_cfg = _get_app_cfg(request)
    sub = get_subscription(app_cfg, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if update.name is not None:
        sub["name"] = update.name
    if update.schedule_hour is not None:
        sub["schedule_hour"] = update.schedule_hour
    if update.schedule_minute is not None:
        sub["schedule_minute"] = update.schedule_minute
    if update.enabled is not None:
        sub["enabled"] = update.enabled
    
    sub["updated_at"] = int(time.time())
    save_subscription(app_cfg, sub_id, sub)

    scheduler = _get_scheduler(request)
    if scheduler:
        scheduler.schedule_subscription(sub_id)

    return SubscriptionStatus(**sub)


@router.delete("/subscriptions/{sub_id}")
def delete_sub(sub_id: str, request: Request):
    app_cfg = _get_app_cfg(request)
    sub = get_subscription(app_cfg, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    scheduler = _get_scheduler(request)
    if scheduler:
        scheduler._unschedule_subscription(sub_id)

    delete_subscription(app_cfg, sub_id)
    return {"status": "deleted", "id": sub_id}


@router.post("/subscriptions/{sub_id}/run", response_model=JobResponse)
def run_sub_now(sub_id: str, request: Request, background_tasks: BackgroundTasks):
    app_cfg = _get_app_cfg(request)
    providers_cfg = _get_providers_cfg(request)
    
    sub = get_subscription(app_cfg, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    csv_path = get_subscription_csv_path(app_cfg, sub_id)
    if not csv_path:
        raise HTTPException(status_code=400, detail="CSV file not found")

    try:
        handles, _ = extract_users(csv_path)
        total_users = len(handles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batching_cfg = app_cfg.get("batching", {})
    batch_size = int(batching_cfg.get("default_batch_size", 10))

    job_id = str(uuid.uuid4())
    
    now = int(time.time())
    sub["last_run"] = now
    sub["last_job_id"] = job_id
    sub["last_status"] = "queued"
    sub["last_error"] = None
    sub["updated_at"] = now
    save_subscription(app_cfg, sub_id, sub)

    status = {
        "job_id": job_id,
        "status": "queued",
        "created_at": now,
        "batch_size": batch_size,
        "total_users": total_users,
        "completed_batches": 0,
        "total_batches": (total_users + batch_size - 1) // batch_size,
    }
    set_job_status(app_cfg, job_id, status)

    def update_sub_status(job_status: dict):
        sub["last_status"] = job_status.get("status")
        if job_status.get("error"):
            sub["last_error"] = job_status["error"]
        save_subscription(app_cfg, sub_id, sub)

    def run_with_callback():
        from backend.services.job_runner import run_job as do_run_job
        try:
            do_run_job(job_id, csv_path, app_cfg, providers_cfg, batch_size, total_users, update_sub_status)
        except Exception:
            pass

    background_tasks.add_task(run_with_callback)

    return JobResponse(job_id=job_id, status="queued")