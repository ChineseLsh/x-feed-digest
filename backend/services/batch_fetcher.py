from __future__ import annotations

import csv
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from backend.llm.openai_compatible import OpenAICompatibleClient
from backend.core.storage import save_batch_output, set_batch_status
from backend.services.csv_parser import extract_users, format_user_info


GROK_PROMPT_TEMPLATE = """你可以访问X/Twitter的实时数据。请执行以下任务：

任务：获取指定用户列表在过去24小时内的所有发帖记录，并以CSV格式输出。

用户列表（包含用户完整信息）：
{user_list}

输出要求：CSV格式，包含以下字段：username, tweet_id, created_at, text, original_url
筛选条件：过去24小时，包含原创推文、转发、引用推文，排除纯回复
输出格式：直接输出可复制的CSV文本，首行为表头，使用英文逗号分隔，文本字段用双引号包裹
请开始执行
"""


def _chunk(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _parse_csv_response(text: str) -> List[Dict[str, str]]:
    lines = text.strip().split("\n")
    csv_lines = []
    in_csv = False
    for line in lines:
        lower_line = line.lower()
        if "username," in lower_line or '"username"' in lower_line:
            in_csv = True
        if in_csv:
            csv_lines.append(line)
    if not csv_lines:
        csv_lines = lines

    try:
        reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
        rows: List[Dict[str, str]] = []
        for row in reader:
            if not row:
                continue
            rows.append({k: (v or "").strip() for k, v in row.items() if k})
        return rows
    except Exception:
        return []


def _rows_to_csv(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "username,tweet_id,created_at,text,original_url\n"
    fieldnames = ["username", "tweet_id", "created_at", "text", "original_url"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return output.getvalue()


def _fetch_single_batch(
    batch_idx: int,
    batch: List[Dict[str, str]],
    client: OpenAICompatibleClient,
    model: str,
    temperature: float,
    max_retries: int,
    backoff_base: float,
    backoff_max: float,
) -> Tuple[int, List[Dict[str, str]]]:
    user_info_lines = [format_user_info(row) for row in batch]
    prompt = GROK_PROMPT_TEMPLATE.format(user_list="\n".join(user_info_lines))
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries + 1):
        try:
            resp = client.chat(messages, model=model, temperature=temperature)
            content = (
                (resp.get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            rows = _parse_csv_response(content)
            return batch_idx, rows
        except Exception as exc:
            if attempt >= max_retries:
                raise RuntimeError(f"Grok batch {batch_idx} failed: {exc}") from exc
            sleep_s = min(backoff_base * (2**attempt), backoff_max)
            time.sleep(sleep_s)

    return batch_idx, []


def _init_client_and_config(
    app_cfg: Dict[str, Any],
    providers_cfg: Dict[str, Any],
) -> Tuple[OpenAICompatibleClient, str, float, int, int, float, float]:
    retry_cfg = app_cfg.get("retry", {})
    max_retries = int(retry_cfg.get("max_retries", 2))
    batch_max_retries = int(retry_cfg.get("batch_max_retries", 3))
    backoff_base = float(retry_cfg.get("backoff_base_s", 0.5))
    backoff_max = float(retry_cfg.get("backoff_max_s", 8.0))

    grok_cfg = app_cfg.get("grok", {})
    provider_name = grok_cfg.get("provider", "grok")
    provider = providers_cfg["providers"][provider_name]

    client = OpenAICompatibleClient(
        provider_name=provider_name,
        base_url=provider["base_url"],
        api_key=provider.get("api_key"),
        default_headers=provider.get("headers", {}),
        max_retries=max_retries,
        timeout_s=float(grok_cfg.get("timeout_s", 120)),
    )

    model = provider["model"]
    temperature = float(grok_cfg.get("temperature", 0.2))
    return client, model, temperature, max_retries, batch_max_retries, backoff_base, backoff_max


def _write_batch_status(
    app_cfg: Dict[str, Any],
    job_id: Optional[str],
    batch_idx: int,
    payload: Dict[str, Any],
) -> None:
    if not job_id:
        return
    set_batch_status(app_cfg, job_id, batch_idx, payload)


def _fetch_batch_with_retries(
    app_cfg: Dict[str, Any],
    job_id: Optional[str],
    batch_idx: int,
    batch: List[Dict[str, str]],
    client: OpenAICompatibleClient,
    model: str,
    temperature: float,
    max_retries: int,
    batch_max_retries: int,
    backoff_base: float,
    backoff_max: float,
) -> Tuple[int, List[Dict[str, str]], Dict[str, Any]]:
    started_at = int(time.time())
    max_attempts = batch_max_retries + 1
    last_error = None
    final_status: Dict[str, Any] = {
        "index": batch_idx,
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
        "error": None,
        "started_at": started_at,
        "finished_at": None,
        "last_attempt_at": None,
    }

    for attempt in range(max_attempts):
        final_status["attempts"] = attempt + 1
        final_status["status"] = "running"
        final_status["error"] = None
        final_status["last_attempt_at"] = int(time.time())
        _write_batch_status(app_cfg, job_id, batch_idx, dict(final_status))
        try:
            _, rows = _fetch_single_batch(
                batch_idx,
                batch,
                client,
                model,
                temperature,
                max_retries,
                backoff_base,
                backoff_max,
            )
            final_status["status"] = "succeeded"
            final_status["finished_at"] = int(time.time())
            _write_batch_status(app_cfg, job_id, batch_idx, dict(final_status))
            if job_id:
                save_batch_output(app_cfg, job_id, batch_idx, _rows_to_csv(rows))
            return batch_idx, rows, dict(final_status)
        except Exception as exc:
            last_error = str(exc)
            final_status["status"] = "failed"
            final_status["error"] = last_error
            final_status["finished_at"] = int(time.time())
            _write_batch_status(app_cfg, job_id, batch_idx, dict(final_status))
            if attempt < batch_max_retries:
                sleep_s = min(backoff_base * (2**attempt), backoff_max)
                time.sleep(sleep_s)

    return batch_idx, [], dict(final_status)


def fetch_single_batch_for_job(
    app_cfg: Dict[str, Any],
    providers_cfg: Dict[str, Any],
    upload_path,
    batch_size: int,
    batch_idx: int,
    job_id: Optional[str],
) -> Tuple[bool, Optional[str]]:
    _, user_rows = extract_users(upload_path)
    batches = _chunk(user_rows, batch_size)
    if batch_idx < 0 or batch_idx >= len(batches):
        raise ValueError("batch_idx out of range")

    client, model, temperature, max_retries, batch_max_retries, backoff_base, backoff_max = _init_client_and_config(
        app_cfg, providers_cfg
    )
    _, rows, status_payload = _fetch_batch_with_retries(
        app_cfg,
        job_id,
        batch_idx,
        batches[batch_idx],
        client,
        model,
        temperature,
        max_retries,
        batch_max_retries,
        backoff_base,
        backoff_max,
    )
    if status_payload.get("status") != "succeeded":
        return False, status_payload.get("error")
    return True, None


def fetch_all_tweets(
    app_cfg: Dict[str, Any],
    providers_cfg: Dict[str, Any],
    upload_path,
    batch_size: int,
    on_batch_complete: Optional[Callable[[int, int], None]] = None,
    job_id: Optional[str] = None,
    include_batch_statuses: bool = False,
) -> Union[str, Tuple[str, List[Dict[str, Any]]]]:
    handles, user_rows = extract_users(upload_path)
    batches = _chunk(user_rows, batch_size)
    total_batches = len(batches)

    batching_cfg = app_cfg.get("batching", {})
    max_workers = int(batching_cfg.get("max_workers", 5))

    client, model, temperature, max_retries, batch_max_retries, backoff_base, backoff_max = _init_client_and_config(
        app_cfg, providers_cfg
    )

    all_rows: List[Dict[str, str]] = []
    completed_count = 0
    lock = threading.Lock()
    batch_statuses: Dict[int, Dict[str, Any]] = {}

    if job_id:
        max_attempts = batch_max_retries + 1
        for batch_idx in range(total_batches):
            _write_batch_status(
                app_cfg,
                job_id,
                batch_idx,
                {
                    "index": batch_idx,
                    "status": "pending",
                    "attempts": 0,
                    "max_attempts": max_attempts,
                    "error": None,
                    "started_at": None,
                    "finished_at": None,
                    "last_attempt_at": None,
                },
            )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _fetch_batch_with_retries,
                app_cfg,
                job_id,
                batch_idx,
                batch,
                client,
                model,
                temperature,
                max_retries,
                batch_max_retries,
                backoff_base,
                backoff_max,
            ): batch_idx
            for batch_idx, batch in enumerate(batches)
        }

        results: Dict[int, List[Dict[str, str]]] = {}
        for future in as_completed(futures):
            try:
                batch_idx, rows, status_payload = future.result()
            except Exception as exc:
                batch_idx = futures[future]
                status_payload = {
                    "index": batch_idx,
                    "status": "failed",
                    "attempts": 0,
                    "max_attempts": batch_max_retries + 1,
                    "error": str(exc),
                    "started_at": None,
                    "finished_at": int(time.time()),
                    "last_attempt_at": None,
                }
                rows = []
                if job_id:
                    _write_batch_status(app_cfg, job_id, batch_idx, dict(status_payload))

            batch_statuses[batch_idx] = status_payload
            if status_payload.get("status") == "succeeded":
                results[batch_idx] = rows

            with lock:
                completed_count += 1
                if on_batch_complete:
                    on_batch_complete(completed_count, total_batches)

    for i in range(total_batches):
        all_rows.extend(results.get(i, []))

    csv_text = _rows_to_csv(all_rows)
    if include_batch_statuses:
        ordered_statuses = [batch_statuses[i] for i in sorted(batch_statuses)]
        return csv_text, ordered_statuses
    return csv_text