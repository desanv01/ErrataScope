"""W03 repair: staging journal for bounded artifact writes.

Revision ID: 0002_staging
Revises: 0001_foundation
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op

revision = "0002_staging"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE erratascope.upload_staging (
            artifact_id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES erratascope.projects(id),
            actor_id uuid NOT NULL,
            staging_key text NOT NULL UNIQUE,
            state text NOT NULL CHECK (state IN ('active', 'finalized', 'abandoned')),
            lease_until timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX upload_staging_state_lease_idx "
        "ON erratascope.upload_staging (state, lease_until)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON erratascope.upload_staging TO erratascope_app"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS erratascope.upload_staging")
