from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import UploadFile


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def init_storage(app_cfg: Dict[str, Any]) -> None:
    storage = app_cfg.get("storage", {})
    for key in ("root", "uploads", "outputs", "summaries", "jobs"):
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
    }


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