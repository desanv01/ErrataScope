"""W03 repair-02: staging ownership/lease fencing for upload and receipt writers.

Revision ID: 0003_staging_fencing
Revises: 0002_staging
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op

revision = "0003_staging_fencing"
down_revision = "0002_staging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE erratascope.upload_staging "
        "ADD COLUMN owner_kind text NOT NULL DEFAULT 'upload'"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging ADD COLUMN owner_job_id uuid"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging ADD COLUMN owner_attempt_token uuid"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging "
        "ADD CONSTRAINT staging_owner_kind_check CHECK (owner_kind IN ('upload', 'result'))"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging DROP CONSTRAINT IF EXISTS upload_staging_state_check"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging DROP CONSTRAINT IF EXISTS staging_state_check"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging "
        "ADD CONSTRAINT staging_state_check "
        "CHECK (state IN ('active', 'finalized', 'abandoned', 'ambiguous'))"
    )
    op.execute(
        "CREATE INDEX upload_staging_owner_job_idx "
        "ON erratascope.upload_staging (owner_job_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS erratascope.upload_staging_owner_job_idx")
    op.execute("DELETE FROM erratascope.upload_staging WHERE owner_kind = 'result'")
    op.execute(
        "ALTER TABLE erratascope.upload_staging DROP CONSTRAINT staging_owner_kind_check"
    )
    op.execute("ALTER TABLE erratascope.upload_staging DROP COLUMN owner_attempt_token")
    op.execute("ALTER TABLE erratascope.upload_staging DROP COLUMN owner_job_id")
    op.execute("ALTER TABLE erratascope.upload_staging DROP COLUMN owner_kind")
    op.execute(
        "ALTER TABLE erratascope.upload_staging DROP CONSTRAINT IF EXISTS staging_state_check"
    )
    op.execute(
        "ALTER TABLE erratascope.upload_staging "
        "ADD CONSTRAINT staging_state_check "
        "CHECK (state IN ('active', 'finalized', 'abandoned'))"
    )
