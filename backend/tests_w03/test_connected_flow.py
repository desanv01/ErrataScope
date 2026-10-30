"""W03 connected local flow over the actual API and RQ worker path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest

from erratascope_service import jobs
from erratascope_service.config import load_settings

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class ConnectedFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="connected-flow")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_health_and_openapi_contract(self) -> None:
        ready = self.client.get("/health/ready")
        self.assertEqual(ready.status_code, 200)
        self.assertTrue(ready.json()["database"])
        self.assertTrue(ready.json()["broker"])
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/redoc").status_code, 404)
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        for path in (
            "/api/v1/projects",
            "/api/v1/projects/{project_id}/artifacts",
            "/api/v1/projects/{project_id}/bundles",
            "/api/v1/projects/{project_id}/jobs",
            "/api/v1/projects/{project_id}/review-items",
        ):
            self.assertIn(path, paths)
        self.assertNotIn("/api/v1/projects/{project_id}/secrets", paths)

    def test_connected_upload_digest_download(self) -> None:
        artifact_body = b"connected synthetic flow\n"
        artifact = H.upload_text(self.client, self.project_id, artifact_body)
        self.assertEqual(artifact["sha256"], __import__("hashlib").sha256(artifact_body).hexdigest())

        job = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"kind": "artifact_digest", "artifact_id": artifact["id"]},
        )
        self.assertEqual(job.status_code, 202, job.text)
        job_id = job.json()["id"]
        jobs.dispatch_once(load_settings())

        code = (
            "from rq import Worker;"
            "from rq.serializers import JSONSerializer;"
            "from erratascope_service.config import load_settings;"
            "from erratascope_service.jobs import queue, broker;"
            "s=load_settings();"
            "Worker([queue(s)], connection=broker(s), serializer=JSONSerializer).work(burst=True)"
        )
        subprocess.run(
            [sys.executable, "-c", code],
            cwd="/app",
            env={**os.environ, "PYTHONPATH": "/app"},
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        deadline = time.time() + 90
        state = None
        while time.time() < deadline:
            state = self.client.get(
                f"/api/v1/projects/{self.project_id}/jobs/{job_id}", headers=H.auth("user-a")
            ).json()
            if state["status"] in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.5)
        self.assertIsNotNone(state)
        self.assertEqual(state["status"], "succeeded", state)

        receipt = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{state['result_artifact_id']}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(receipt.status_code, 200)
        body = json.loads(receipt.content)
        self.assertEqual(body["sha256"], artifact["sha256"])
        self.assertEqual(body["byte_length"], len(artifact_body))

        foreign = self.client.get(
            f"/api/v1/projects/{self.project_id}/jobs/{job_id}", headers=H.auth("user-c")
        )
        self.assertEqual(foreign.status_code, 404)


if __name__ == "__main__":
    unittest.main()



