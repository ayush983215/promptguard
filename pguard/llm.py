"""Tiny OpenAI-compatible chat client (works with OpenAI, Ollama, etc.).

Configured by environment variables so no key is ever written to disk:
  PG_LLM_URL   base URL, default https://api.openai.com/v1
  PG_LLM_KEY   API key (omit for a local server such as Ollama)
  PG_LLM_MODEL model name
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    url: str
    key: str
    model: str

    @classmethod
    def from_env(cls) -> "LLMConfig | None":
        model = os.environ.get("PG_LLM_MODEL")
        if not model:
            return None
        return cls(os.environ.get("PG_LLM_URL", "https://api.openai.com/v1").rstrip("/"),
                   os.environ.get("PG_LLM_KEY", ""), model)


def chat(cfg: LLMConfig, messages: list[dict], timeout: float = 20.0) -> str:
    body = json.dumps({"model": cfg.model, "messages": messages, "temperature": 0}).encode()
    headers = {"Content-Type": "application/json"}
    if cfg.key:
        headers["Authorization"] = f"Bearer {cfg.key}"
    req = urllib.request.Request(f"{cfg.url}/chat/completions", body, headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]
