"""Calls the Claude Code CLI (`claude -p`) as a subprocess to propose resume
edits. When Claude Code is logged in via a Claude.ai subscription rather than
a raw ANTHROPIC_API_KEY, `-p` (print/non-interactive) mode uses that
subscription's usage allowance -- Anthropic's own documented scripting
pattern -- rather than separate metered API billing.
"""
from __future__ import annotations

import subprocess

CLAUDE_TIMEOUT_SECONDS = 120


def call_claude(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "The `claude` CLI isn't on PATH -- resume tailoring needs Claude Code installed and logged in."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Claude took too long to respond (timed out).") from e

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout
