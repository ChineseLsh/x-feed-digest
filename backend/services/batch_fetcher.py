from __future__ import annotations

import csv
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.llm.openai_compatible import OpenAICompatibleClient
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


def fetch_all_tweets(
    app_cfg: Dict[str, Any],
    providers_cfg: Dict[str, Any],
    upload_path,
    batch_size: int,
    on_batch_complete: Optional[Callable[[int, int], None]] = None,
) -> str:
    handles, user_rows = extract_users(upload_path)
    batches = _chunk(user_rows, batch_size)
    total_batches = len(batches)

    retry_cfg = app_cfg.get("retry", {})
    max_retries = int(retry_cfg.get("max_retries", 2))
    backoff_base = float(retry_cfg.get("backoff_base_s", 0.5))
    backoff_max = float(retry_cfg.get("backoff_max_s", 8.0))

    batching_cfg = app_cfg.get("batching", {})
    max_workers = int(batching_cfg.get("max_workers", 5))

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

    all_rows: List[Dict[str, str]] = []
    completed_count = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _fetch_single_batch,
                batch_idx,
                batch,
                client,
                model,
                temperature,
                max_retries,
                backoff_base,
                backoff_max,
            ): batch_idx
            for batch_idx, batch in enumerate(batches)
        }

        results: Dict[int, List[Dict[str, str]]] = {}
        for future in as_completed(futures):
            batch_idx, rows = future.result()
            results[batch_idx] = rows

            with lock:
                completed_count += 1
                if on_batch_complete:
                    on_batch_complete(completed_count, total_batches)

    for i in range(total_batches):
        all_rows.extend(results.get(i, []))

    return _rows_to_csv(all_rows)