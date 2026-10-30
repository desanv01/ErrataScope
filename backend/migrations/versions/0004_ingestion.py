"""W04 ingestion, draft, conversion and provider-accounting schema."""

from __future__ import annotations

from alembic import op

revision = "0004_ingestion"
down_revision = "0003_staging_fencing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE erratascope.source_versions (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES erratascope.projects(id),
            artifact_id uuid NOT NULL,
            document_id text,
            revision text,
            manufacturer text,
            source_url text,
            published_at text,
            predecessor_id uuid,
            authority text NOT NULL CHECK (authority IN ('manufacturer', 'forum', 'synthetic')),
            synthetic boolean NOT NULL,
            sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            byte_length bigint NOT NULL CHECK (byte_length >= 0),
            schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version = 1),
            content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
            created_by uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            retrieval_utc timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, id),
            FOREIGN KEY (project_id, artifact_id)
                REFERENCES erratascope.artifacts(project_id, id),
            FOREIGN KEY (project_id, predecessor_id)
                REFERENCES erratascope.source_versions(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.extractions (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES erratascope.projects(id),
            source_id uuid NOT NULL,
            job_id uuid NOT NULL,
            mode text NOT NULL CHECK (mode IN ('offline', 'live')),
            case_kind text CHECK (case_kind IN ('real_source', 'synthetic_missing_revision')),
            selected_entries jsonb NOT NULL,
            status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
            diagnostics jsonb NOT NULL DEFAULT '[]'::jsonb,
            current_stage text,
            error_code text,
            created_by uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, id),
            UNIQUE (job_id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id),
            FOREIGN KEY (project_id, job_id)
                REFERENCES erratascope.jobs(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.extraction_outputs (
            extraction_id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            source_id uuid NOT NULL,
            output_hash char(64) NOT NULL CHECK (output_hash ~ '^[0-9a-f]{64}$'),
            manifest jsonb NOT NULL,
            parser jsonb NOT NULL,
            selected_scope jsonb NOT NULL,
            coverage_summary jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, extraction_id),
            FOREIGN KEY (project_id, extraction_id)
                REFERENCES erratascope.extractions(project_id, id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.source_anchors (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            extraction_id uuid NOT NULL,
            anchor_key text NOT NULL,
            source_id uuid NOT NULL,
            page_index integer NOT NULL CHECK (page_index >= 0),
            printed_page_label text,
            section text,
            section_title text,
            block_role text NOT NULL,
            context_kind text,
            geometry_kind text NOT NULL CHECK (geometry_kind IN ('located', 'synthetic_not_located')),
            anchor_text text NOT NULL,
            bbox jsonb NOT NULL,
            bbox_original jsonb NOT NULL,
            page_width_pt double precision NOT NULL CHECK (page_width_pt > 0),
            page_height_pt double precision NOT NULL CHECK (page_height_pt > 0),
            page_rotation integer NOT NULL CHECK (page_rotation >= 0 AND page_rotation <= 359),
            parser jsonb NOT NULL,
            document_sha256 char(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (extraction_id, anchor_key),
            FOREIGN KEY (project_id, extraction_id)
                REFERENCES erratascope.extraction_outputs(project_id, extraction_id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.coverage_entries (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            extraction_id uuid NOT NULL,
            section text NOT NULL,
            title text,
            status text NOT NULL CHECK (status IN (
                'discovered', 'selected', 'supported', 'reviewed', 'failed', 'unsupported', 'ambiguous', 'missing'
            )),
            page_indexes jsonb NOT NULL,
            anchor_keys jsonb NOT NULL,
            reason text,
            notes jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (extraction_id, section),
            FOREIGN KEY (project_id, extraction_id)
                REFERENCES erratascope.extraction_outputs(project_id, extraction_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.model_drafts (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            extraction_id uuid NOT NULL,
            source_id uuid NOT NULL,
            case_kind text NOT NULL CHECK (case_kind IN ('real_source', 'synthetic_missing_revision')),
            provenance text NOT NULL CHECK (provenance IN ('live', 'cached', 'mock', 'offline')),
            prompt_version text NOT NULL,
            request_hash char(64) NOT NULL,
            response_hash char(64) NOT NULL,
            draft jsonb NOT NULL,
            validation jsonb NOT NULL,
            status text NOT NULL CHECK (status IN ('validated', 'rejected')),
            provider_request_id text,
            usage jsonb,
            request_artifact_id uuid,
            response_artifact_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, id),
            UNIQUE (extraction_id, response_hash),
            FOREIGN KEY (project_id, extraction_id)
                REFERENCES erratascope.extraction_outputs(project_id, extraction_id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.conversion_proposals (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            draft_id uuid NOT NULL,
            source_id uuid NOT NULL,
            extraction_id uuid NOT NULL,
            entry_id text NOT NULL,
            payload jsonb NOT NULL,
            content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
            ineligible_reason text,
            reviewer_rationale text,
            current_revision integer NOT NULL DEFAULT 0 CHECK (current_revision >= 0),
            created_by uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, id),
            FOREIGN KEY (project_id, draft_id)
                REFERENCES erratascope.model_drafts(project_id, id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id),
            FOREIGN KEY (project_id, extraction_id)
                REFERENCES erratascope.extraction_outputs(project_id, extraction_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.proposal_reviews (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            proposal_id uuid NOT NULL,
            revision integer NOT NULL CHECK (revision >= 1),
            actor_id uuid NOT NULL,
            decision text NOT NULL CHECK (decision IN ('accepted', 'rejected')),
            rationale text NOT NULL CHECK (char_length(rationale) BETWEEN 1 AND 4000),
            expected_content_hash char(64) NOT NULL,
            accepted_rule_version_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (proposal_id, revision),
            FOREIGN KEY (project_id, proposal_id)
                REFERENCES erratascope.conversion_proposals(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.accepted_rules (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL,
            proposal_id uuid NOT NULL,
            review_id uuid NOT NULL,
            source_id uuid NOT NULL,
            entry_id text NOT NULL,
            payload jsonb NOT NULL,
            content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
            reviewer_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, proposal_id),
            FOREIGN KEY (project_id, proposal_id)
                REFERENCES erratascope.conversion_proposals(project_id, id),
            FOREIGN KEY (project_id, source_id)
                REFERENCES erratascope.source_versions(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.provider_reservations (
            id uuid PRIMARY KEY,
            budget_id text NOT NULL,
            attempt integer NOT NULL CHECK (attempt >= 1),
            project_id uuid NOT NULL,
            job_id uuid NOT NULL,
            case_kind text NOT NULL CHECK (case_kind IN ('real_source', 'synthetic_missing_revision')),
            source_sha256 char(64) NOT NULL,
            extraction_id uuid,
            context_hash char(64) NOT NULL,
            request_hash char(64) NOT NULL,
            prompt_version text NOT NULL,
            endpoint text NOT NULL,
            model text NOT NULL,
            input_token_bound integer NOT NULL CHECK (input_token_bound >= 0),
            output_token_bound integer NOT NULL CHECK (output_token_bound >= 0),
            input_price_usd_per_million numeric(12, 6) NOT NULL,
            output_price_usd_per_million numeric(12, 6) NOT NULL,
            max_estimated_cost_usd numeric(12, 8) NOT NULL CHECK (max_estimated_cost_usd >= 0),
            status text NOT NULL CHECK (status IN (
                'reserved', 'dispatched', 'succeeded', 'failed', 'uncertain'
            )),
            reserved_utc timestamptz NOT NULL DEFAULT now(),
            dispatch_utc timestamptz,
            finalized_utc timestamptz,
            provider_request_id text,
            response_hash char(64),
            usage jsonb,
            error_code text,
            UNIQUE (budget_id, attempt),
            FOREIGN KEY (project_id, job_id)
                REFERENCES erratascope.jobs(project_id, id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.provider_attempt_events (
            id uuid PRIMARY KEY,
            reservation_id uuid NOT NULL REFERENCES erratascope.provider_reservations(id),
            event text NOT NULL,
            detail jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE erratascope.provider_budgets (
            budget_id text PRIMARY KEY,
            requests_reserved integer NOT NULL DEFAULT 0 CHECK (requests_reserved >= 0),
            spend_reserved_usd numeric(12, 8) NOT NULL DEFAULT 0 CHECK (spend_reserved_usd >= 0),
            caps jsonb NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        INSERT INTO erratascope.provider_budgets (budget_id, requests_reserved, spend_reserved_usd, caps)
        VALUES (
            'W04-backend-v1', 0, 0,
            '{"max_requests": 2, "max_estimated_spend_usd": 0.25, "max_input_tokens_per_request": 16000,
              "max_output_tokens_per_request": 8192, "input_usd_per_million": 0.30,
              "output_usd_per_million": 0.90}'::jsonb
        )
        ON CONFLICT (budget_id) DO NOTHING
        """
    )
    # Allow the additive job kind without changing existing artifact_digest rows.
    op.execute("ALTER TABLE erratascope.jobs DROP CONSTRAINT jobs_kind_check")
    op.execute(
        "ALTER TABLE erratascope.jobs ADD CONSTRAINT jobs_kind_check "
        "CHECK (kind IN ('artifact_digest', 'source_extract'))"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION erratascope.conversion_proposal_guard() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'IMMUTABLE_TABLE:conversion_proposals' USING ERRCODE = '55000';
            END IF;
            IF NEW.project_id IS DISTINCT FROM OLD.project_id
               OR NEW.draft_id IS DISTINCT FROM OLD.draft_id
               OR NEW.source_id IS DISTINCT FROM OLD.source_id
               OR NEW.extraction_id IS DISTINCT FROM OLD.extraction_id
               OR NEW.entry_id IS DISTINCT FROM OLD.entry_id
               OR NEW.payload IS DISTINCT FROM OLD.payload
               OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
               OR NEW.ineligible_reason IS DISTINCT FROM OLD.ineligible_reason
               OR NEW.reviewer_rationale IS DISTINCT FROM OLD.reviewer_rationale
               OR NEW.created_by IS DISTINCT FROM OLD.created_by
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'IMMUTABLE_TABLE:conversion_proposals_candidate' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $fn$
        """
    )
    for table in (
        "source_versions",
        "extraction_outputs",
        "source_anchors",
        "coverage_entries",
        "model_drafts",
        "proposal_reviews",
        "accepted_rules",
        "provider_attempt_events",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON erratascope.{table} "
            "FOR EACH ROW EXECUTE FUNCTION erratascope.reject_mutation()"
        )
    op.execute(
        "CREATE TRIGGER conversion_proposals_immutable BEFORE UPDATE OR DELETE "
        "ON erratascope.conversion_proposals FOR EACH ROW "
        "EXECUTE FUNCTION erratascope.conversion_proposal_guard()"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA erratascope "
        "TO erratascope_app"
    )


def downgrade() -> None:
    for table in (
        "provider_attempt_events",
        "provider_reservations",
        "provider_budgets",
        "accepted_rules",
        "proposal_reviews",
        "conversion_proposals",
        "model_drafts",
        "coverage_entries",
        "source_anchors",
        "extraction_outputs",
        "extractions",
        "source_versions",
    ):
        op.execute(f"DROP TABLE IF EXISTS erratascope.{table} CASCADE")
    op.execute("ALTER TABLE erratascope.jobs DROP CONSTRAINT jobs_kind_check")
    op.execute(
        "ALTER TABLE erratascope.jobs ADD CONSTRAINT jobs_kind_check CHECK (kind = 'artifact_digest')"
    )
