"""Prepare an empty S01 demo project from a user-supplied/downloaded PDF."""

import hashlib
import json
import os
import pathlib
import urllib.request
import uuid
import urllib.error

BASE = "http://api:8000"
PDF = pathlib.Path(os.environ["CLEAN_PDF"])
EXPECTED = "dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd"
STATE = pathlib.Path("/workspace/.local/submission/clean-state.json")
SOURCE_URL = (
    "https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf"
)


def call(method, path, body=None, extra=None, token=None):
    data = body if isinstance(body, (bytes, bytearray)) else (
        json.dumps(body).encode() if body is not None else None
    )
    headers = {"Idempotency-Key": uuid.uuid4().hex}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if isinstance(body, dict):
        headers["Content-Type"] = "application/json"
    if extra:
        headers.update(extra)
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return response.status, json.load(response)


pdf_bytes = PDF.read_bytes()
actual = hashlib.sha256(pdf_bytes).hexdigest()
if actual != EXPECTED:
    raise SystemExit("PDF hash mismatch; provide the pinned ES0620 Rev 5 file or a corrected source version")
session = json.load(urllib.request.urlopen(BASE + "/api/v1/submission/dev-session"))
token = session["token"]
if STATE.exists():
    saved = json.loads(STATE.read_text(encoding="utf-8"))
    try:
        _, existing = call("GET", f"/api/v1/projects/{saved['project_id']}/sources/{saved['source_id']}", token=token)
        if existing["sha256"] != EXPECTED:
            raise SystemExit("Existing demo source differs; refusing to reuse state")
        print("Existing demo source verified; resuming import if needed.")
        raise SystemExit(0)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
status, project = call("POST", "/api/v1/projects", {"name": "S01 recorded live demonstration"}, token=token)
print("project", status)
status, artifact = call(
    "POST",
    f"/api/v1/projects/{project['id']}/artifacts",
    pdf_bytes,
    {"Content-Type": "application/pdf", "X-Filename": "es0620.pdf"},
    token,
)
print("artifact", status)
status, source = call(
    "POST",
    f"/api/v1/projects/{project['id']}/sources",
    {
        "artifact_id": artifact["id"],
        "document_id": "ES0620",
        "revision": "Rev 5",
        "manufacturer": "STMicroelectronics",
        "source_url": SOURCE_URL,
        "published_at": "August 2026",
        "authority": "manufacturer",
        "synthetic": False,
    },
    token=token,
)
print("source", status)
if status != 201:
    raise SystemExit(f"source creation failed: {source}")
STATE.parent.mkdir(parents=True, exist_ok=True)
STATE.write_text(
    json.dumps(
        {
            "project_id": project["id"],
            "artifact_id": artifact["id"],
            "source_id": source["id"],
            "source_sha256": source["sha256"],
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps({"project_id": project["id"], "source_id": source["id"]}))
