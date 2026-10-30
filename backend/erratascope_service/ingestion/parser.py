"""Parent-side bounded parser invocation and output validation."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from .schemas import ParseResult

MAX_PDF_BYTES = 10 * 1024 * 1024


class ParseError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _limits(memory_mb: int) -> Callable[[], None]:
    def apply() -> None:
        import resource

        limit = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

    return apply


def parse_pdf(
    data: bytes,
    *,
    source_key: str,
    document_sha256: str,
    selected_entries: list[str],
    timeout_seconds: int,
    memory_mb: int,
    cancel_check: Callable[[], bool] | None = None,
) -> dict:
    if not data.startswith(b"%PDF-"):
        raise ParseError("PDF_INVALID", "artifact does not start with a PDF header")
    if len(data) > MAX_PDF_BYTES:
        raise ParseError("PDF_TOO_LARGE", "source PDF exceeds the bounded parser size")
    tempdir = Path(tempfile.mkdtemp(prefix="w04-parse-"))
    input_path = tempdir / "source.pdf"
    output_path = tempdir / "parsed.json"
    stdout_path = tempdir / "stdout.log"
    stderr_path = tempdir / "stderr.log"
    input_path.write_bytes(data)
    backend_root = Path(__file__).resolve().parents[2]
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONPATH": str(backend_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    command = [
        sys.executable,
        "-m",
        "erratascope_service.ingestion.parser_worker",
        str(input_path),
        str(output_path),
        source_key,
        document_sha256,
        json.dumps(selected_entries),
    ]
    process = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                cwd=str(backend_root),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                preexec_fn=_limits(memory_mb),
            )
            deadline = time.monotonic() + timeout_seconds
            while True:
                try:
                    process.wait(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if cancel_check is not None and cancel_check():
                    _terminate(process)
                    raise ParseError("PARSE_CANCELLED", "extraction was cancelled")
                if time.monotonic() >= deadline:
                    _terminate(process)
                    raise ParseError("PARSE_TIMEOUT", "PDF parser exceeded its bounded deadline")
        if process.returncode != 0:
            detail = _tail(stderr_path)
            try:
                error = json.loads(detail.splitlines()[-1])
                code = str(error.get("error", "PARSE_FAILED"))
                message = str(error.get("message", "parser failed"))
            except (json.JSONDecodeError, IndexError, KeyError):
                code, message = "PARSE_FAILED", "PDF parser failed without a structured diagnostic"
            raise ParseError(code, message)
        if not output_path.exists():
            raise ParseError("PARSE_FAILED", "parser produced no output")
        raw = json.loads(output_path.read_text(encoding="utf-8"))
        try:
            parsed = ParseResult.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise ParseError(
                "PARSE_OUTPUT_INVALID", f"parser output failed schema validation: {str(exc)[:1500]}"
            ) from exc
        if parsed.document_sha256 != document_sha256:
            raise ParseError("PARSE_IDENTITY_MISMATCH", "parser output is bound to different bytes")
        if parsed.coverage_summary.selected_entries != selected_entries:
            raise ParseError("PARSE_OUTPUT_INVALID", "parser selected scope differs from request")
        return parsed.model_dump(mode="json")
    finally:
        if process is not None and process.poll() is None:
            _terminate(process)
        shutil.rmtree(tempdir, ignore_errors=True)


def _terminate(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _tail(path: Path, limit: int = 2000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""
