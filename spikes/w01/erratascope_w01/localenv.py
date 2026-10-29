"""Load only the project-designated Nebius key; never search or log secrets."""
from __future__ import annotations

import os
from pathlib import Path

from . import config


class LocalEnvError(ValueError):
    """Deliberately value-free error safe for CLI output."""


def load_nebius_key(path: Path | None = None) -> str:
    """Process environment wins; otherwise use root .env.local, without expansion.

    Supported subset: a single NEBIUS_API_KEY=value line, optionally wrapped
    in matching quotes. Other variables/comments are ignored. This is not a
    shell or general dotenv parser. Never call with untrusted arbitrary paths.
    The path parameter is for isolated tests; the CLI always uses the default.
    """
    name = config.PROVIDER["api_key_env"]
    if os.environ.get(name, "").strip():
        return "process_environment"
    target = path if path is not None else config.PROJECT_ROOT / ".env.local"
    if not target.exists():
        return "missing"
    try:
        lines = target.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        raise LocalEnvError("Cannot read project .env.local; no value displayed") from None
    values = []
    for line in lines:
        key, separator, raw = line.partition("=")
        if not separator or key.strip() != name:
            continue
        value = raw.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise LocalEnvError("Invalid NEBIUS_API_KEY quoting in .env.local")
            value = value[1:-1]
        if any(ord(char) <= 32 or ord(char) >= 127 for char in value):
            raise LocalEnvError("NEBIUS_API_KEY must be one ASCII token without whitespace")
        values.append(value)
    if len(values) > 1:
        raise LocalEnvError("Duplicate NEBIUS_API_KEY entries in .env.local")
    if not values or not values[0]:
        return "missing"
    os.environ[name] = values[0]
    return "project_env_local"
