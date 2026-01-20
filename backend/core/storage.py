from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def init_storage(app_cfg: Dict[str, Any]) -> None:
    storage = app_cfg.get("storage", {})
    for key in ("root", "uploads", "outputs", "summaries", "jobs", "subscriptions"):
        value = storage.get(key)
        if value:
            _ensure_dir(Path(value))


def _storage_paths(app_cfg: Dict[str, Any]) -> Dict[str, Path]:
    storage = app_cfg.get("storage", {})
    return {
        "uploads": Path(storage["uploads"]),
        "outputs": Path(storage["outputs"]),
        "summaries": Path(storage["summaries"]),
        "jobs": Path(storage["jobs"]),
        "subscriptions": Path(storage.get("subscriptions", "data/subscriptions")),
    }


def _batch_dir(paths: Dict[str, Path], job_id: str) -> Path:
    path = paths["jobs"] / job_id / "batches"
    _ensure_dir(path)
    return path


def save_upload(app_cfg: Dict[str, Any], job_id: str, upload: UploadFile) -> Path:
    paths = _storage_paths(app_cfg)
    path = paths["uploads"] / f"{job_id}.csv"
    with path.open("wb") as f:
        f.write(upload.file.read())
    return path


def save_output(app_cfg: Dict[str, Any], job_id: str, csv_text: str) -> Path:
    paths = _storage_paths(app_cfg)
    path = paths["outputs"] / f"{job_id}.csv"
    path.write_text(csv_text, encoding="utf-8")
    return path


def save_summary(app_cfg: Dict[str, Any], job_id: str, summary_text: str) -> Path:
    paths = _storage_paths(app_cfg)
    path = paths["summaries"] / f"{job_id}.txt"
    path.write_text(summary_text, encoding="utf-8")
    return path


def save_batch_output(app_cfg: Dict[str, Any], job_id: str, batch_idx: int, csv_text: str) -> Path:
    paths = _storage_paths(app_cfg)
    batch_dir = _batch_dir(paths, job_id)
    path = batch_dir / f"{batch_idx}.csv"
    path.write_text(csv_text, encoding="utf-8")
    return path


def get_batch_output(app_cfg: Dict[str, Any], job_id: str, batch_idx: int) -> Optional[str]:
    paths = _storage_paths(app_cfg)
    batch_dir = _batch_dir(paths, job_id)
    path = batch_dir / f"{batch_idx}.csv"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def set_batch_status(app_cfg: Dict[str, Any], job_id: str, batch_idx: int, payload: Dict[str, Any]) -> Path:
    paths = _storage_paths(app_cfg)
    batch_dir = _batch_dir(paths, job_id)
    path = batch_dir / f"{batch_idx}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_batch_status(app_cfg: Dict[str, Any], job_id: str, batch_idx: int) -> Optional[Dict[str, Any]]:
    paths = _storage_paths(app_cfg)
    batch_dir = _batch_dir(paths, job_id)
    path = batch_dir / f"{batch_idx}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_batch_statuses(app_cfg: Dict[str, Any], job_id: str) -> List[Dict[str, Any]]:
    paths = _storage_paths(app_cfg)
    batch_dir = paths["jobs"] / job_id / "batches"
    if not batch_dir.exists():
        return []
    batches = []
    for path in batch_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            batches.append(data)
        except Exception:
            continue
    batches.sort(key=lambda x: x.get("index", 0))
    return batches


def set_job_status(app_cfg: Dict[str, Any], job_id: str, payload: Dict[str, Any]) -> Path:
    paths = _storage_paths(app_cfg)
    path = paths["jobs"] / f"{job_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_job_status(app_cfg: Dict[str, Any], job_id: str) -> Optional[Dict[str, Any]]:
    paths = _storage_paths(app_cfg)
    path = paths["jobs"] / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_all_jobs(app_cfg: Dict[str, Any]) -> list[Dict[str, Any]]:
    """List all jobs sorted by creation time (newest first)."""
    paths = _storage_paths(app_cfg)
    jobs_dir = paths["jobs"]
    jobs = []
    for path in jobs_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            jobs.append(data)
        except Exception:
            continue
    jobs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return jobs


def save_subscription_csv(app_cfg: Dict[str, Any], sub_id: str, upload: UploadFile) -> Path:
    """Save uploaded CSV for a subscription."""
    paths = _storage_paths(app_cfg)
    path = paths["subscriptions"] / f"{sub_id}.csv"
    with path.open("wb") as f:
        f.write(upload.file.read())
    return path


def save_subscription(app_cfg: Dict[str, Any], sub_id: str, payload: Dict[str, Any]) -> Path:
    """Save subscription metadata as JSON."""
    paths = _storage_paths(app_cfg)
    path = paths["subscriptions"] / f"{sub_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_subscription(app_cfg: Dict[str, Any], sub_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription metadata by ID."""
    paths = _storage_paths(app_cfg)
    path = paths["subscriptions"] / f"{sub_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_subscriptions(app_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all subscriptions sorted by creation time (newest first)."""
    paths = _storage_paths(app_cfg)
    subs_dir = paths["subscriptions"]
    subs = []
    for path in subs_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            subs.append(data)
        except Exception:
            continue
    subs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return subs


def delete_subscription(app_cfg: Dict[str, Any], sub_id: str) -> None:
    """Delete subscription and its CSV file."""
    paths = _storage_paths(app_cfg)
    json_path = paths["subscriptions"] / f"{sub_id}.json"
    csv_path = paths["subscriptions"] / f"{sub_id}.csv"
    if json_path.exists():
        json_path.unlink()
    if csv_path.exists():
        csv_path.unlink()


def get_subscription_csv_path(app_cfg: Dict[str, Any], sub_id: str) -> Optional[Path]:
    """Get the CSV file path for a subscription."""
    paths = _storage_paths(app_cfg)
    csv_path = paths["subscriptions"] / f"{sub_id}.csv"
    if csv_path.exists():
        return csv_path
    return None