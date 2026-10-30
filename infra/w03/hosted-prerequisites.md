# W03 hosted prerequisites (NOT_RUN)

W03 is a **local foundation only**. No hosted account, project, bucket, database or
deployment was created or validated. The items below must be bound and reviewed before any
hosted P2 acceptance; this document is a checklist, not evidence of hosted operation.

## Required hosted decisions before implementation

- Provider/account/region selection and an approved cost ceiling (Supabase/Render/Neon or
  equivalent), including database compute, storage and egress.
- Managed PostgreSQL with a private connection string; application and migration roles
  separated (migrator owns schema, app role DML only). TLS required.
- Managed Redis-compatible broker reachable only from API/worker services.
- Private object storage with server-side encryption, private buckets and short-lived
  authorized downloads; no public bucket/URL. Artifact size/type limits must match local
  (10 MiB; PDF/text/JSON).
- Supabase-style asymmetric JWT signing keys published via HTTPS JWKS; backend pins
  issuer, audience, allowed algorithms, expiry and clock skew. No client-supplied identity
  headers and no symmetric fallback in this packet.
- Secret management (not committed files); local dev passwords/tokens are not reused.
- Startup fail-closed mode: hosted requires valid JWT/storage/broker configuration and
  must reject `HOSTED_STORAGE_NOT_READY` states instead of silently using local storage.

## Hosted adapter work still outstanding

- Replace `LocalArtifactStore` with a private object-store adapter preserving atomic
  staging, SHA-256/size verification and private delivery semantics.
- Replace local JWKS file with bounded HTTPS JWKS fetch (already coded but unverified
  against a real hosted issuer), cache/rotation tests and hosted-mode startup tests.
- Managed service health/readiness, metrics, log redaction, backup/restore and retention.
- RLS or equivalent authorization checks for any exposed storage/database surface;
  application authorization remains authoritative.
- Load/concurrency/soak and provider-outage recovery tests with real hosted resources.
- Hosted network restriction, egress policy and secret rotation runbooks.

## Explicitly not performed in W03 attempt 01

- No hosted provisioning, Supabase/Render/Neon API calls, account inspection, bucket
  creation or deployment.
- No UI/imagegen work; UI approval remains PENDING.
- No W04 conversion/automation work.
- No promise of exactly-once provider billing; retries may repeat external calls.

Hosted execution status: **NOT_RUN**. P2 overall hosted/UI deliverables remain pending.
