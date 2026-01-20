"""Job runner service - extracted from routes for reuse by scheduler."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from backend.core.storage import save_output, save_summary, set_job_status
from backend.services.batch_fetcher import fetch_all_tweets
from backend.services.summarizer import summarize_csv


def run_job(
    job_id: str,
    upload_path: Path,
    app_cfg: dict,
    providers_cfg: dict,
    batch_size: int,
    total_users: int,
    on_status_update: Optional[Callable[[dict], None]] = None,
) -> None:
    """
    Run a fetch + summarize job.
    
    Args:
        job_id: Unique job identifier
        upload_path: Path to the CSV file with usernames
        app_cfg: Application configuration
        providers_cfg: LLM providers configuration
        batch_size: Number of users per batch
        total_users: Total number of users to process
        on_status_update: Optional callback when status changes
    """
    total_batches = (total_users + batch_size - 1) // batch_size

    status = {
        "job_id": job_id,
        "status": "running",
        "created_at": int(time.time()),
        "batch_size": batch_size,
        "total_users": total_users,
        "completed_batches": 0,
        "total_batches": total_batches,
    }
    set_job_status(app_cfg, job_id, status)
    if on_status_update:
        on_status_update(status)

    def on_batch_complete(completed: int, total: int):
        status["completed_batches"] = completed
        set_job_status(app_cfg, job_id, status)
        if on_status_update:
            on_status_update(status)

    try:
        result = fetch_all_tweets(
            app_cfg, providers_cfg, upload_path, batch_size,
            on_batch_complete=on_batch_complete,
            job_id=job_id,
            include_batch_statuses=True,
        )
        csv_text, batch_statuses = result

        failed_batches = sum(1 for b in batch_statuses if b.get("status") == "failed")
        succeeded_batches = sum(1 for b in batch_statuses if b.get("status") == "succeeded")
        status["failed_batches"] = failed_batches
        status["succeeded_batches"] = succeeded_batches

        if failed_batches > 0:
            status["status"] = "failed"
            status["error"] = f"{failed_batches} batch(es) failed"
            set_job_status(app_cfg, job_id, status)
            if on_status_update:
                on_status_update(status)
            return status

        save_output(app_cfg, job_id, csv_text)

        status["status"] = "summarizing"
        set_job_status(app_cfg, job_id, status)
        if on_status_update:
            on_status_update(status)

        summary_text = summarize_csv(app_cfg, providers_cfg, csv_text)
        save_summary(app_cfg, job_id, summary_text)

        status["status"] = "done"
        set_job_status(app_cfg, job_id, status)
        if on_status_update:
            on_status_update(status)

        return status

    except Exception as exc:
        status["status"] = "failed"
        status["error"] = str(exc)
        set_job_status(app_cfg, job_id, status)
        if on_status_update:
            on_status_update(status)
        raise