"""
OpenCode CLI subprocess wrapper for the AI Answer Agent fallback.

Runs: opencode run --model <model> <prompt>
Returns OpenCodeResult dataclass (never raises).
"""
import re
import subprocess
from dataclasses import dataclass
from loguru import logger

# Strip ANSI escape codes from OpenCode's terminal output
_ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


@dataclass
class OpenCodeResult:
    """Result of an OpenCode CLI invocation."""
    ok: bool
    text: str = ''
    error: str = ''


def run_opencode(prompt: str, model: str, timeout: float) -> OpenCodeResult:
    """
    Run opencode CLI and capture stdout as the answer.

    Args:
        prompt:  the full prompt string
        model:   model identifier, e.g. 'opencode/deepseek-v4.1-flash-free'
        timeout: maximum seconds to wait

    Returns:
        OpenCodeResult with ok=True and text on success,
        or ok=False and error on any failure
    """
    cmd = ['opencode', 'run', '--model', model, prompt]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return OpenCodeResult(False, error='opencode CLI not found on PATH')
    except subprocess.TimeoutExpired:
        return OpenCodeResult(False, error=f'opencode timed out after {timeout}s')

    if proc.returncode != 0:
        err = _ANSI.sub('', proc.stderr).strip()[:300]
        logger.warning(f'opencode exit {proc.returncode}: {err}')
        return OpenCodeResult(False, error=f'exit {proc.returncode}: {err}')

    text = _ANSI.sub('', proc.stdout).strip()
    if not text:
        return OpenCodeResult(False, error='empty output')

    return OpenCodeResult(True, text=text)
