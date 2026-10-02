"""Calls a local Ollama server as an alternative to the Claude Code CLI --
fully offline, no subscription usage, but lower quality for this kind of
nuanced rewriting than Claude. Requires Ollama installed and running
(https://ollama.com) with the configured model already pulled
(`ollama pull <model>`).
"""
from __future__ import annotations

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT_SECONDS = 180


def call_ollama(prompt: str, model: str) -> str:
    try:
        resp = httpx.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
    except httpx.ConnectError as e:
        raise RuntimeError(
            "Couldn't reach Ollama at localhost:11434 -- is it installed and running?"
        ) from e
    except httpx.TimeoutException as e:
        raise RuntimeError("Ollama took too long to respond (timed out).") from e

    if resp.status_code != 200:
        detail = resp.json().get("error", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        if "not found" in detail.lower():
            detail += f" -- run `ollama pull {model}` first."
        raise RuntimeError(f"Ollama request failed: {detail}")

    return resp.json().get("response", "")
