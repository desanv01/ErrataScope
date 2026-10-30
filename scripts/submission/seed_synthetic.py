"""Prepare the original offline omission example in the clean demo project."""
import json
import pathlib
import time
import urllib.request
import uuid
from erratascope_service.ingestion.fixture import SYNTHETIC_TEXT

BASE = "http://api:8000/api/v1"
state_path = pathlib.Path("/workspace/.local/submission/clean-state.json")
state = json.loads(state_path.read_text())
token = json.load(urllib.request.urlopen(BASE + "/submission/dev-session"))["token"]

def call(method, path, body=None, content_type="application/json"):
    data = body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": content_type,
        "Idempotency-Key": uuid.uuid4().hex, "X-Filename": "original-synthetic-example.txt",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

pid = state["project_id"]
context = call("GET", f"/projects/{pid}/submission-context")
if any(c["kind"] == "synthetic_offline" for c in context["cases"]):
    print("Synthetic offline example already available; no inference.")
    raise SystemExit(0)
if not state.get("synthetic_job_id"):
    artifact = call("POST", f"/projects/{pid}/artifacts", SYNTHETIC_TEXT.encode(), "text/plain")
    source = call("POST", f"/projects/{pid}/sources", {
        "artifact_id": artifact["id"], "document_id": None, "revision": None,
        "manufacturer": None, "authority": "synthetic", "synthetic": True,
    })
    extraction = call("POST", f"/projects/{pid}/sources/{source['id']}/extractions", {
        "selected_entries": ["2.9.99"], "mode": "offline", "case_kind": "synthetic_missing_revision",
    })
    state["synthetic_job_id"] = extraction["job_id"]
    state_path.write_text(json.dumps(state, indent=2) + "\n")
for _ in range(45):
    job = call("GET", f"/projects/{pid}/jobs/{state['synthetic_job_id']}")
    if job["status"] == "succeeded":
        print("Synthetic offline omission example ready; zero provider calls.")
        break
    if job["status"] in ("failed", "cancelled"):
        raise SystemExit("Offline fixture job did not complete; inspect its job status.")
    time.sleep(1)
else:
    raise SystemExit("Offline fixture is still pending; rerun the launcher to resume waiting.")
