"""W03 foundation schema: projects, artifacts, bundles, reviews, jobs, outbox.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-10-30
"""

from __future__ import annotations

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = [
    # The schema is created by the database init role (owned by the migrator);
    # the migrator role has no CREATE privilege on the database itself.
    """
    CREATE TABLE erratascope.projects (
        id uuid PRIMARY KEY,
        name varchar(120) NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
        created_by uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE erratascope.memberships (
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        actor_id uuid NOT NULL,
        role text NOT NULL CHECK (role IN ('owner', 'editor', 'reviewer', 'viewer')),
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (project_id, actor_id)
    )
    """,
    """
    CREATE TABLE erratascope.artifacts (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        storage_key text NOT NULL UNIQUE,
        sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
        byte_length bigint NOT NULL CHECK (byte_length >= 0 AND byte_length <= 10485760),
        media_type text NOT NULL CHECK (media_type IN ('application/pdf', 'text/plain', 'application/json')),
        original_name text,
        state text NOT NULL CHECK (state IN ('ready')),
        created_by uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.bundles (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        input_hash char(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
        schema_version integer NOT NULL CHECK (schema_version = 1),
        evaluator_version text NOT NULL CHECK (evaluator_version = 'domain-v1'),
        payload jsonb NOT NULL,
        created_by uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, input_hash),
        UNIQUE (project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.domain_versions (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        kind text NOT NULL CHECK (kind IN (
            'snapshot', 'component_instance', 'fact_set', 'fact_version',
            'document_version', 'anchor', 'rule', 'coverage', 'source_baseline'
        )),
        version_id text NOT NULL CHECK (char_length(version_id) BETWEEN 1 AND 200),
        payload jsonb NOT NULL,
        payload_hash char(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, kind, version_id),
        UNIQUE (project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.bundle_members (
        project_id uuid NOT NULL,
        bundle_id uuid NOT NULL,
        kind text NOT NULL,
        version_id text NOT NULL,
        payload_hash char(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
        PRIMARY KEY (bundle_id, kind, version_id),
        FOREIGN KEY (project_id, bundle_id) REFERENCES erratascope.bundles(project_id, id),
        FOREIGN KEY (project_id, kind, version_id)
            REFERENCES erratascope.domain_versions(project_id, kind, version_id)
    )
    """,
    """
    CREATE TABLE erratascope.review_items (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        artifact_id uuid NOT NULL,
        content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
        annotation text NOT NULL CHECK (char_length(annotation) BETWEEN 1 AND 4000),
        current_revision integer NOT NULL DEFAULT 0 CHECK (current_revision >= 0),
        created_by uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, id),
        FOREIGN KEY (project_id, artifact_id) REFERENCES erratascope.artifacts(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.review_events (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL,
        review_item_id uuid NOT NULL,
        revision integer NOT NULL CHECK (revision >= 1),
        actor_id uuid NOT NULL,
        decision text NOT NULL CHECK (decision IN ('accepted', 'rejected')),
        rationale text NOT NULL CHECK (char_length(rationale) BETWEEN 1 AND 4000),
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (review_item_id, revision),
        FOREIGN KEY (project_id, review_item_id) REFERENCES erratascope.review_items(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.idempotency (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL,
        actor_id uuid NOT NULL,
        operation text NOT NULL,
        key varchar(128) NOT NULL CHECK (key ~ '^[ -~]{16,128}$'),
        request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
        response_status integer NOT NULL,
        response_body jsonb NOT NULL,
        resource_id uuid,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, actor_id, operation, key)
    )
    """,
    """
    CREATE TABLE erratascope.jobs (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL REFERENCES erratascope.projects(id),
        actor_id uuid NOT NULL,
        kind text NOT NULL CHECK (kind = 'artifact_digest'),
        artifact_id uuid NOT NULL,
        status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
        attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
        max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 3),
        current_attempt_token uuid,
        lease_until timestamptz,
        next_event_seq integer NOT NULL DEFAULT 0 CHECK (next_event_seq >= 0),
        result_artifact_id uuid,
        result_sha256 char(64),
        error_code text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (project_id, id),
        FOREIGN KEY (project_id, artifact_id) REFERENCES erratascope.artifacts(project_id, id),
        FOREIGN KEY (project_id, result_artifact_id) REFERENCES erratascope.artifacts(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.job_attempts (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL,
        job_id uuid NOT NULL,
        attempt_number integer NOT NULL CHECK (attempt_number >= 1),
        token uuid NOT NULL,
        started_at timestamptz NOT NULL DEFAULT now(),
        ended_at timestamptz,
        outcome text CHECK (outcome IN ('running', 'succeeded', 'failed', 'cancelled')),
        error_code text,
        UNIQUE (job_id, attempt_number),
        UNIQUE (job_id, token),
        FOREIGN KEY (project_id, job_id) REFERENCES erratascope.jobs(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.outbox (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL,
        job_id uuid NOT NULL,
        dispatch_generation integer NOT NULL CHECK (dispatch_generation >= 1),
        available_at timestamptz NOT NULL DEFAULT now(),
        claim_token uuid,
        lease_until timestamptz,
        sent_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (job_id, dispatch_generation),
        FOREIGN KEY (project_id, job_id) REFERENCES erratascope.jobs(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.job_events (
        id uuid PRIMARY KEY,
        project_id uuid NOT NULL,
        job_id uuid NOT NULL,
        seq integer NOT NULL CHECK (seq >= 1),
        event_type text NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 80),
        payload jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (job_id, seq),
        FOREIGN KEY (project_id, job_id) REFERENCES erratascope.jobs(project_id, id)
    )
    """,
    """
    CREATE TABLE erratascope.stage_results (
        project_id uuid NOT NULL,
        job_id uuid NOT NULL,
        stage_key text NOT NULL,
        input_hash char(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
        result_artifact_id uuid NOT NULL,
        result_sha256 char(64) NOT NULL CHECK (result_sha256 ~ '^[0-9a-f]{64}$'),
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (job_id, stage_key),
        FOREIGN KEY (project_id, job_id) REFERENCES erratascope.jobs(project_id, id),
        FOREIGN KEY (project_id, result_artifact_id) REFERENCES erratascope.artifacts(project_id, id)
    )
    """,
    "CREATE INDEX projects_created_at_idx ON erratascope.projects (created_at)",
    "CREATE INDEX artifacts_project_created_idx ON erratascope.artifacts (project_id, created_at)",
    "CREATE INDEX jobs_project_status_idx ON erratascope.jobs (project_id, status)",
    "CREATE INDEX jobs_status_lease_idx ON erratascope.jobs (status, lease_until)",
    "CREATE INDEX outbox_pending_idx ON erratascope.outbox (sent_at, available_at)",
    """
    CREATE OR REPLACE FUNCTION erratascope.reject_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $fn$
    BEGIN
        RAISE EXCEPTION 'IMMUTABLE_TABLE:%', TG_TABLE_NAME USING ERRCODE = '55000';
    END
    $fn$
    """,
    """
    CREATE OR REPLACE FUNCTION erratascope.review_items_guard() RETURNS trigger
    LANGUAGE plpgsql AS $fn$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'IMMUTABLE_TABLE:review_items' USING ERRCODE = '55000';
        END IF;
        IF NEW.project_id IS DISTINCT FROM OLD.project_id
           OR NEW.artifact_id IS DISTINCT FROM OLD.artifact_id
           OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
           OR NEW.annotation IS DISTINCT FROM OLD.annotation
           OR NEW.created_by IS DISTINCT FROM OLD.created_by
           OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'IMMUTABLE_TABLE:review_items_candidate' USING ERRCODE = '55000';
        END IF;
        RETURN NEW;
    END
    $fn$
    """,
]

IMMUTABLE_TABLES = (
    "artifacts",
    "bundles",
    "domain_versions",
    "bundle_members",
    "review_events",
    "job_events",
    "stage_results",
)


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)
    for table in IMMUTABLE_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON erratascope.{table} "
            "FOR EACH ROW EXECUTE FUNCTION erratascope.reject_mutation()"
        )
    op.execute(
        "CREATE TRIGGER review_items_immutable BEFORE UPDATE OR DELETE ON erratascope.review_items "
        "FOR EACH ROW EXECUTE FUNCTION erratascope.review_items_guard()"
    )
    op.execute("REVOKE ALL ON SCHEMA erratascope FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA erratascope TO erratascope_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA erratascope TO erratascope_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE erratascope_migrator IN SCHEMA erratascope "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO erratascope_app"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS erratascope CASCADE")
