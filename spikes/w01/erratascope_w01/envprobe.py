"""Read-only environment and capability probing. Never prints secret values."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import config
from .util import rel, utc_now_iso, write_json

PROBE_PACKAGES = (
    "pydantic",
    "httpx",
    "pdfplumber",
    "pymupdf",
    "docling",
    "pypdfium2",
    "pillow",
)

SECRET_VARIABLE_NAMES = (
    "NEBIUS_API_KEY",
    "OPENAI_API_KEY",
    "HF_TOKEN",
)


def _version_of(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def _run_read_only(command: list[str], timeout: int = 20) -> dict:
    """Run an inspection command; never starts services."""
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "reason": f"{command[0]} not on PATH"}
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
            shell=False,
        )
        first_line = (completed.stdout or completed.stderr or "").strip().splitlines()
        text = first_line[0][:200] if first_line else ""
        # Some Windows tools emit UTF-16 on a pipe; keep the recorded text readable.
        text = text.replace("\x00", "").strip()
        return {
            "available": True,
            "exit_code": completed.returncode,
            "first_line": text,
        }
    except subprocess.TimeoutExpired:
        return {"available": True, "exit_code": None, "reason": "timeout"}
    except Exception as exc:  # noqa: BLE001 - capability probe, reported verbatim
        return {"available": True, "exit_code": None, "reason": f"{type(exc).__name__}: {exc}"}


def _package_versions() -> dict:
    packages = {}
    for name in PROBE_PACKAGES:
        version = _version_of(name)
        packages[name] = {"installed": version is not None, "version": version}
    return packages


def _docling_runtime() -> dict:
    """Record whether the Docling pipeline executes on this machine.

    The W01 run measured this separately; the flag here is a cheap import
    check plus a recorded environment note, not a fresh model conversion.
    """
    try:
        import docling

        version = getattr(docling, "__version__", None) or _version_of("docling")
        return {"importable": True, "version": version}
    except Exception as exc:  # noqa: BLE001
        return {"importable": False, "reason": f"{type(exc).__name__}: {exc}"}


def _project_relative(path: str | Path) -> str:
    try:
        return rel(Path(path))
    except Exception:
        return Path(path).name


def inspect_environment(persist: bool = True) -> dict:
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "scope": "W01 feasibility spike environment; not application acceptance",
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "executable": _project_relative(sys.executable),
            "venv_prefix": _project_relative(sys.prefix),
            "in_virtualenv": sys.prefix != sys.base_prefix,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "packages": _package_versions(),
        "docling_runtime": _docling_runtime(),
        "capabilities": {
            "docker_client": _run_read_only(["docker", "--version"]),
            "docker_daemon": _run_read_only(["docker", "version", "--format", "{{.Server.Version}}"]),
            "wsl": _run_read_only(["wsl", "--status"]),
            "git": _run_read_only(["git", "--version"]),
        },
        "configured_secret_variables": {
            name: {"configured": bool(os.environ.get(name))} for name in SECRET_VARIABLE_NAMES
        },
        "path_environment": {
            "project_root_name": config.PROJECT_ROOT.name,
            "note": "Absolute user paths are omitted from public evidence.",
        },
        "known_environment_quirks": [
            (
                "Windows sandbox denies access to directories created with POSIX mode 0700 "
                "(tempfile.mkdtemp default); the spike therefore creates its own directories "
                "with 0777 and sets HF_HUB_DISABLE_XET=1 so that Docling/Hugging Face model "
                "downloads do not use 0700 temporary directories."
            ),
            (
                "Docker client is present; the daemon availability recorded above was probed "
                "read-only. No container was started for W01."
            ),
        ],
    }
    if persist:
        write_json(config.ENVIRONMENT_PATH, payload)
    return payload
