from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx


def _coalesce_env(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1].strip()
        return os.getenv(env_key)
    return value


def _normalize_base_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if base.endswith("/v1"):
        return base + "/"
    return base + "/v1/"


@dataclass
class OpenAICompatibleClient:
    provider_name: str
    base_url: str
    api_key: Optional[str]
    default_headers: Dict[str, str]
    max_retries: int = 2
    timeout_s: float = 60.0

    def __post_init__(self) -> None:
        self.base_url = _normalize_base_url(self.base_url)
        self.api_key = _coalesce_env(self.api_key)
        if not self.api_key:
            raise ValueError(
                f"Provider '{self.provider_name}' missing api_key. "
                "Set it in providers.yaml or use ${ENV_VAR}."
            )

        headers = dict(self.default_headers or {})
        headers.setdefault("Authorization", f"Bearer {self.api_key}")
        headers.setdefault("Content-Type", "application/json")
        self.default_headers = headers

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        temperature: float = 0.2,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_s: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = urljoin(self.base_url, "chat/completions")
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra:
            payload.update(extra)

        timeout = timeout_s if timeout_s is not None else self.timeout_s

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, headers=self.default_headers, json=payload)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_exc = e
                if attempt >= self.max_retries:
                    break
                time.sleep(0.5 * (2**attempt))

        raise RuntimeError(
            f"OpenAI-compatible chat failed for provider={self.provider_name}: {last_exc}"
        )
