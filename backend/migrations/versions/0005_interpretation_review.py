"""S01 interpretation-review schema migration."""

from __future__ import annotations

from alembic import op

revision = "0005_interpretation_review"
down_revision = "0004_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE erratascope.interpretation_reviews (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES erratascope.projects(id),
            draft_id uuid NOT NULL,
            revision integer NOT NULL CHECK (revision >= 1),
            response_hash char(64) NOT NULL CHECK (response_hash ~ '^[0-9a-f]{64}$'),
            decision text NOT NULL CHECK (decision IN ('reviewed', 'rejected')),
            note text NOT NULL CHECK (char_length(btrim(note)) BETWEEN 1 AND 2000),
            actor_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (draft_id, revision),
            FOREIGN KEY (project_id, draft_id)
                REFERENCES erratascope.model_drafts(project_id, id)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER interpretation_reviews_immutable BEFORE UPDATE OR DELETE "
        "ON erratascope.interpretation_reviews FOR EACH ROW "
        "EXECUTE FUNCTION erratascope.reject_mutation()"
    )
    op.execute(
        "GRANT SELECT, INSERT ON erratascope.interpretation_reviews TO erratascope_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON erratascope.interpretation_reviews "
        "TO erratascope_migrator"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS erratascope.interpretation_reviews CASCADE")
