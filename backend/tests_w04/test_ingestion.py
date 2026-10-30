"""W04 backend integration and negative tests on real PostgreSQL/storage."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest import mock

from sqlalchemy import delete, text
from sqlalchemy.exc import DBAPIError

from erratascope_service import jobs, services
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.ingestion import provider
from erratascope_service.ingestion.draft import validate_draft
from erratascope_service.ingestion.models import (
    AcceptedRule,
    CoverageEntry,
    Extraction,
    ExtractionOutput,
    ModelDraft,
    ProviderAttemptEvent,
    ProviderBudget,
    ProviderReservation,
    SourceAnchor,
    SourceVersion,
)
from erratascope_service.ingestion.parser import ParseError, parse_pdf
from erratascope_service.models import Job

from tests_w03 import helpers as H

PDF_PATH = Path("/w04/st-es0620.pdf")
PDF_SHA = "dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd"


def setUpModule() -> None:
    H.reset_database()


def session():
    return get_session_factory()()


class W04Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name=f"w04-{uuid.uuid4().hex[:8]}")
        cls.pdf = PDF_PATH.read_bytes()
        response = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/artifacts",
            headers={
                **H.auth("user-a"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "application/pdf",
                "X-Filename": "st-es0620.pdf",
            },
            content=cls.pdf,
        )
        assert response.status_code == 201, response.text
        cls.artifact = response.json()
        cls.source = cls._create_source()

    @classmethod
    def _create_source(cls) -> dict:
        response = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/sources",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": cls.artifact["id"],
                "document_id": "ES0620",
                "revision": "Rev 5",
                "manufacturer": "STMicroelectronics",
                "authority": "manufacturer",
                "synthetic": False,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    def _extraction(self, selected=None, mode="offline", case_kind=None):
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/sources/{self.source['id']}/extractions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "selected_entries": selected or ["2.2.18", "2.2.5"],
                "mode": mode,
                "case_kind": case_kind,
            },
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def _run_extraction(self):
        extraction = self._extraction()
        jobs.execute(extraction["job_id"])
        detail = self.client.get(
            f"/api/v1/extractions/{extraction['id']}", headers=H.auth("user-a")
        ).json()
        return extraction, detail

    def _draft_and_proposal(self):
        extraction, detail = self._run_extraction()
        drafts = self.client.get(
            f"/api/v1/extractions/{extraction['id']}/drafts", headers=H.auth("user-a")
        ).json()["items"]
        draft = drafts[0]
        anchors = self.client.get(
            f"/api/v1/extractions/{extraction['id']}/anchors", headers=H.auth("user-a")
        ).json()["items"]
        identity = next(a["anchor_key"] for a in anchors if a["context_kind"] == "source_identity")
        body = next(
            a["anchor_key"]
            for a in anchors
            if a["section"] == "2.2.5" and a["block_role"] == "body"
        )
        return extraction, draft, identity, body


class SourceAndParseTests(W04Base):
    def test_real_pdf_anchors_coverage_and_mock_draft(self) -> None:
        extraction, detail = self._run_extraction()
        self.assertEqual(detail["status"], "succeeded")
        self.assertEqual(detail["coverage_summary"]["inventory_complete"], False)
        self.assertGreaterEqual(detail["coverage_summary"]["detected_entries"], 40)
        anchors = self.client.get(
            f"/api/v1/extractions/{extraction['id']}/anchors", headers=H.auth("user-a")
        ).json()["items"]
        self.assertTrue(any(a["context_kind"] == "source_identity" for a in anchors))
        self.assertTrue(any(a["context_kind"] == "revision_header" for a in anchors))
        self.assertTrue(any(a["context_kind"] == "status_legend" for a in anchors))
        sections = {a["section"] for a in anchors}
        self.assertIn("2.2.18", sections)
        self.assertIn("2.2.5", sections)
        row = next(a for a in anchors if a["section"] == "2.2.5" and a["block_role"] == "table_row")
        self.assertIn("Rev. Z=N", row["text"])
        for anchor in anchors:
            self.assertLessEqual(anchor["bbox"]["left"], anchor["bbox"]["right"])
            self.assertEqual(anchor["document_sha256"], PDF_SHA)
        coverage = self.client.get(
            f"/api/v1/extractions/{extraction['id']}/coverage", headers=H.auth("user-a")
        ).json()["items"]
        selected = [entry for entry in coverage if entry["section"] in ("2.2.18", "2.2.5")]
        self.assertTrue(all(entry["status"] == "supported" for entry in selected))
        self.assertTrue(any(entry["status"] == "discovered" and entry["reason"] == "not_selected" for entry in coverage))
        drafts = self.client.get(
            f"/api/v1/extractions/{extraction['id']}/drafts", headers=H.auth("user-a")
        ).json()["items"]
        self.assertEqual(drafts[0]["provenance"], "mock")
        self.assertEqual(drafts[0]["status"], "validated")
        self.assertEqual(drafts[0]["draft"]["source_document_id"], "ES0620")
        database = session()
        try:
            self.assertEqual(
                database.query(ProviderReservation)
                .filter(ProviderReservation.project_id == uuid.UUID(self.project_id))
                .count(),
                0,
            )
        finally:
            database.close()

    def test_source_immutability_and_cross_project_reference(self) -> None:
        database = session()
        try:
            with self.assertRaises(DBAPIError):
                database.execute(
                    text("UPDATE erratascope.source_versions SET revision='forged' WHERE id=:id"),
                    {"id": self.source["id"]},
                )
                database.commit()
            database.rollback()
            with self.assertRaises(DBAPIError):
                database.execute(
                    text("DELETE FROM erratascope.source_versions WHERE id=:id"),
                    {"id": self.source["id"]},
                )
                database.commit()
        finally:
            database.rollback()
            database.close()
        other = H.create_project(self.client, name="w04-other")
        response = self.client.post(
            f"/api/v1/projects/{other}/sources",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": self.artifact["id"],
                "authority": "manufacturer",
                "synthetic": False,
                "predecessor_id": self.source["id"],
            },
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_malformed_pdf_fails_visibly(self) -> None:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-a"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "application/pdf",
                "X-Filename": "broken.pdf",
            },
            content=b"%PDF-1.4 not a real pdf",
        )
        self.assertEqual(response.status_code, 201)
        broken = response.json()
        source = self.client.post(
            f"/api/v1/projects/{self.project_id}/sources",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"artifact_id": broken["id"], "authority": "manufacturer", "synthetic": False},
        ).json()
        extraction = self.client.post(
            f"/api/v1/projects/{self.project_id}/sources/{source['id']}/extractions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"selected_entries": ["2.2.18"], "mode": "offline"},
        ).json()
        jobs.execute(extraction["job_id"])
        detail = self.client.get(
            f"/api/v1/extractions/{extraction['id']}", headers=H.auth("user-a")
        ).json()
        self.assertEqual(detail["status"], "failed")
        self.assertTrue(detail["diagnostics"])
        self.assertEqual(
            self.client.get(
                f"/api/v1/extractions/{extraction['id']}/anchors", headers=H.auth("user-a")
            ).json()["items"],
            [],
        )

    def test_parser_bounds_and_scanned_coverage_disclosure(self) -> None:
        with self.assertRaises(ParseError) as oversized:
            parse_pdf(
                b"%PDF-" + b"0" * (10 * 1024 * 1024 + 1),
                source_key="st-es0620",
                document_sha256="0" * 64,
                selected_entries=["2.2.18"],
                timeout_seconds=10,
                memory_mb=128,
            )
        self.assertEqual(oversized.exception.code, "PDF_TOO_LARGE")

    def test_synthetic_missing_revision_offline_mechanism(self) -> None:
        from erratascope_service.ingestion.fixture import SYNTHETIC_TEXT

        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-a"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "text/plain",
                "X-Filename": "synthetic-missing-revision.txt",
            },
            content=SYNTHETIC_TEXT.encode("utf-8"),
        )
        self.assertEqual(response.status_code, 201, response.text)
        synthetic_artifact = response.json()
        source = self.client.post(
            f"/api/v1/projects/{self.project_id}/sources",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": synthetic_artifact["id"],
                "authority": "synthetic",
                "synthetic": True,
            },
        )
        self.assertEqual(source.status_code, 201, source.text)
        source_id = source.json()["id"]
        extraction = self.client.post(
            f"/api/v1/projects/{self.project_id}/sources/{source_id}/extractions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"selected_entries": ["2.9.99"], "mode": "offline"},
        )
        self.assertEqual(extraction.status_code, 202, extraction.text)
        body = extraction.json()
        jobs.execute(body["job_id"])
        detail = self.client.get(
            f"/api/v1/extractions/{body['id']}", headers=H.auth("user-a")
        ).json()
        self.assertEqual(detail["status"], "succeeded", detail)
        draft = self.client.get(
            f"/api/v1/extractions/{body['id']}/drafts", headers=H.auth("user-a")
        ).json()["items"][0]
        self.assertIsNone(draft["draft"]["source_document_id"])
        self.assertIsNone(draft["draft"]["source_revision"])
        self.assertIn("source_document_id", draft["draft"]["unresolved_fields"])
        self.assertIn("source_revision", draft["draft"]["unresolved_fields"])
        self.assertEqual(draft["validation"]["status"], "validated")


class ProviderTests(unittest.TestCase):
    def _clear_provider_ledger(self) -> None:
        H.reset_database()

    def _job(self) -> tuple[uuid.UUID, uuid.UUID]:
        project_id = H.create_project(H.client(), name=f"w04-provider-{uuid.uuid4().hex[:8]}")
        database = session()
        try:
            artifact = services.create_artifact_record(
                database,
                project_id=project_id,
                actor_id=H.subject_for("user-a"),
                artifact_id=uuid.uuid4(),
                storage_key=f"unused/{uuid.uuid4().hex}",
                sha256="a" * 64,
                byte_length=1,
                media_type="text/plain",
                original_name="x.txt",
            )
            database.commit()
            job = services.create_job(
                database,
                project_id=uuid.UUID(project_id),
                actor_id=H.subject_for("user-a"),
                artifact_id=artifact.id,
                kind="source_extract",
                max_attempts=1,
            )
            database.commit()
            return uuid.UUID(project_id), job.id
        finally:
            database.close()

    def test_reservation_cap_and_ledger_mirror(self) -> None:
        self._clear_provider_ledger()
        project_id, job_id = self._job()
        settings = load_settings()
        with tempfile.TemporaryDirectory(prefix="w04-ledger-") as directory:
            live = settings.__class__(**{**settings.__dict__, "w04_live_enabled": True, "w04_ledger_path": Path(directory) / "ledger.jsonl"})
            database = session()
            try:
                budget = database.get(ProviderBudget, provider.BUDGET_ID)
                budget.requests_reserved = 1
                budget.spend_reserved_usd = 0
                database.commit()
            finally:
                database.close()
            base = dict(
                project_id=project_id,
                job_id=job_id,
                case_kind="real_source",
                source_sha256="a" * 64,
                extraction_id=None,
                context_hash="b" * 64,
                request_hash="c" * 64,
                prompt_version="test",
                endpoint=settings.w04_provider_endpoint,
                model=settings.w04_provider_model,
                input_bound=100,
                output_bound=100,
            )
            first = provider._reserve(live, **base)
            self.assertEqual(first.attempt, 2)
            entries = [
                json.loads(line)
                for line in live.w04_ledger_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(entries[0]["event"], "reserved")
            self.assertEqual(entries[0]["reservation_id"], str(first.id))
            with self.assertRaises(provider.ProviderBlocked) as exhausted:
                provider._reserve(live, **base)
            self.assertEqual(exhausted.exception.code, "BUDGET_EXHAUSTED")

    def test_mock_transport_rejections_are_settled_and_ledgered(self) -> None:
        self._clear_provider_ledger()
        project_id, job_id = self._job()
        settings = load_settings()
        with tempfile.TemporaryDirectory(prefix="w04-provider-") as directory:
            live = settings.__class__(**{**settings.__dict__, "w04_live_enabled": True, "w04_ledger_path": Path(directory) / "ledger.jsonl"})
            os.environ["NEBIUS_API_KEY"] = "fake-offline-test-key"
            try:
                for body, code in (
                    (
                        {
                            "model": live.w04_provider_model,
                            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
                        },
                        "PROVIDER_INCOMPLETE",
                    ),
                    (
                        {
                            "model": "wrong/model",
                            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                        },
                        "PROVIDER_MODEL",
                    ),
                ):
                    fake = _FakeResponse(body)
                    with mock.patch.object(
                        provider.httpx, "Client", lambda *a, **k: _FakeClient(fake)
                    ):
                        with self.assertRaises(provider.ProviderBlocked) as blocked:
                            provider.run_case(
                                live,
                                project_id=project_id,
                                job_id=job_id,
                                extraction_id=None,
                                source_id=uuid.uuid4(),
                                source_sha256="a" * 64,
                                case_kind="real_source",
                                messages=[{"role": "user", "content": "x"}],
                                declared_identity=None,
                                context={"context_hash": "b" * 64},
                            )
                        self.assertEqual(blocked.exception.code, code)
            finally:
                os.environ.pop("NEBIUS_API_KEY", None)
            database = session()
            try:
                reservations = database.query(ProviderReservation).all()
                self.assertEqual(len(reservations), 2)
                self.assertTrue(all(row.status == "failed" for row in reservations))
            finally:
                database.close()


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self.status_code = 200
        self.headers = {"content-type": "application/json", "x-request-id": "fake-request"}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_bytes(self):
        yield json.dumps(self._body).encode("utf-8")


class _FakeClient:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def stream(self, *args, **kwargs):
        return self.response


class ReviewTests(W04Base):
    def _proposal(self, extraction, draft, identity, body):
        payload = {
            "draft_id": draft["id"],
            "entry_id": "2.2.5",
            "target": {
                "op": "eq",
                "selector": "component.family",
                "value": {"kind": "text", "value": "STM32N6"},
                "anchor_ids": [identity],
            },
            "trigger": {
                "op": "constant",
                "value": True,
                "anchor_ids": [body],
                "review_rationale": "Synthetic mechanism test only; not semantic acceptance.",
            },
            "exceptions": [],
            "consequence": "Synthetic candidate for mechanism testing.",
            "evidence": [
                {"path": "target", "anchor_keys": [identity]},
                {"path": "trigger", "anchor_keys": [body]},
                {"path": "consequence", "anchor_keys": [body]},
            ],
            "reviewer_rationale": "Synthetic mechanism test; not semantic acceptance.",
        }
        response = self.client.post(
            f"/api/v1/drafts/{draft['id']}/proposals",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_accept_stale_conflict_and_immutability(self) -> None:
        extraction, draft, identity, body = self._draft_and_proposal()
        proposal = self._proposal(extraction, draft, identity, body)
        response = self.client.post(
            f"/api/v1/proposals/{proposal['id']}/reviews",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "decision": "accepted",
                "rationale": "Synthetic mechanism acceptance only.",
                "expected_revision": 0,
                "expected_content_hash": proposal["content_hash"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        rule_id = response.json()["accepted_rule"]["id"]
        stale = self.client.post(
            f"/api/v1/proposals/{proposal['id']}/reviews",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "decision": "rejected",
                "rationale": "stale",
                "expected_revision": 0,
                "expected_content_hash": proposal["content_hash"],
            },
        )
        self.assertEqual(stale.status_code, 409)
        database = session()
        try:
            with self.assertRaises(DBAPIError):
                database.execute(
                    text("UPDATE erratascope.accepted_rules SET entry_id='mutated' WHERE id=:id"),
                    {"id": rule_id},
                )
                database.commit()
        finally:
            database.rollback()
            database.close()

    def test_foreign_anchor_and_ineligible_review(self) -> None:
        extraction, draft, identity, body = self._draft_and_proposal()
        payload = {
            "draft_id": draft["id"],
            "entry_id": "2.2.5",
            "target": {"op": "constant", "value": True, "anchor_ids": ["foreign:anchor"], "review_rationale": "x"},
            "trigger": {"op": "constant", "value": True, "anchor_ids": [body], "review_rationale": "x"},
            "exceptions": [],
            "consequence": "x",
            "evidence": [{"path": "target", "anchor_keys": ["foreign:anchor"]}],
            "reviewer_rationale": "Synthetic",
        }
        response = self.client.post(
            f"/api/v1/drafts/{draft['id']}/proposals",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        proposal = response.json()
        self.assertTrue(proposal["ineligible_reason"])
        review = self.client.post(
            f"/api/v1/proposals/{proposal['id']}/reviews",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "decision": "accepted",
                "rationale": "should fail",
                "expected_revision": 0,
                "expected_content_hash": proposal["content_hash"],
            },
        )
        self.assertEqual(review.status_code, 409)
        self.assertEqual(H.error_code(review), "PROPOSAL_INELIGIBLE")


class CancellationTests(W04Base):
    def test_duplicate_delivery_reuses_sealed_output(self) -> None:
        extraction, detail = self._run_extraction()
        self.assertEqual(detail["status"], "succeeded")
        database = session()
        try:
            anchors_before = (
                database.query(SourceAnchor)
                .filter(SourceAnchor.extraction_id == uuid.UUID(extraction["id"]))
                .count()
            )
            outputs_before = (
                database.query(ExtractionOutput)
                .filter(ExtractionOutput.extraction_id == uuid.UUID(extraction["id"]))
                .count()
            )
            drafts_before = (
                database.query(ModelDraft)
                .filter(ModelDraft.extraction_id == uuid.UUID(extraction["id"]))
                .count()
            )
        finally:
            database.close()
        jobs.execute(extraction["job_id"])
        database = session()
        try:
            self.assertEqual(
                database.query(SourceAnchor)
                .filter(SourceAnchor.extraction_id == uuid.UUID(extraction["id"]))
                .count(),
                anchors_before,
            )
            self.assertEqual(
                database.query(ExtractionOutput)
                .filter(ExtractionOutput.extraction_id == uuid.UUID(extraction["id"]))
                .count(),
                outputs_before,
            )
            self.assertEqual(
                database.query(ModelDraft)
                .filter(ModelDraft.extraction_id == uuid.UUID(extraction["id"]))
                .count(),
                drafts_before,
            )
        finally:
            database.close()

    def test_cancelled_job_publishes_nothing(self) -> None:
        extraction = self._extraction()
        canceled = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs/{extraction['job_id']}/cancel",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
        )
        self.assertEqual(canceled.status_code, 200, canceled.text)
        jobs.execute(extraction["job_id"])
        self.assertEqual(
            self.client.get(
                f"/api/v1/extractions/{extraction['id']}/anchors", headers=H.auth("user-a")
            ).json()["items"],
            [],
        )
        database = session()
        try:
            self.assertIsNone(database.get(ExtractionOutput, uuid.UUID(extraction["id"])))
        finally:
            database.close()
