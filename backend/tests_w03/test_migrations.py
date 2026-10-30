"""W03 repair R?: upgrading an existing 0001 database without reset."""

from __future__ import annotations

import unittest
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from erratascope_service import services
from erratascope_service.db import get_session_factory

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database("0001_foundation")


class MigrationUpgradeTests(unittest.TestCase):
    def test_0001_upgrades_to_head_preserving_data(self) -> None:
        sessions = get_session_factory()()
        project_id = uuid.uuid4()
        actor = H.subject_for("user-a")
        try:
            services.create_project(sessions, actor_id=actor, name="pre-0002", project_id=project_id)
            sessions.commit()
            exists = sessions.execute(
                text("SELECT to_regclass('erratascope.upload_staging') IS NOT NULL")
            ).scalar()
            self.assertFalse(exists)
        finally:
            sessions.close()

        command.upgrade(Config("/app/alembic.ini"), "head")
        command.upgrade(Config("/app/alembic.ini"), "head")  # idempotent

        sessions = get_session_factory()()
        try:
            project = sessions.get(services.Project, project_id)
            self.assertIsNotNone(project)
            self.assertEqual(project.name, "pre-0002")
            staging = sessions.execute(
                text("SELECT to_regclass('erratascope.upload_staging') IS NOT NULL")
            ).scalar()
            self.assertTrue(staging)
            columns = {
                row[0]
                for row in sessions.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='erratascope' AND table_name='upload_staging'"
                    )
                )
            }
            self.assertTrue({"owner_kind", "owner_job_id", "owner_attempt_token"}.issubset(columns))
            version = sessions.execute(
                text("SELECT version_num FROM erratascope.alembic_version")
            ).scalar()
            self.assertEqual(version, "0004_ingestion")
        finally:
            sessions.close()


if __name__ == "__main__":
    unittest.main()

