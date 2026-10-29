# Security and operations contract — revision 1

Local synthetic development is distinct from public hosted access. No hosted private uploads until authentication, project authorization, and private storage gates pass.

Default roles: owner, reviewer/editor, viewer. Verify hosted JWT signature, issuer, audience, expiry, and allowed algorithms using current provider guidance. Decoding is not verification. Privileged DB/storage credentials do not replace application authorization. Exposed Supabase tables require tested RLS; private tables remain behind the authorized API.

Local identity bypass must be loopback-only; hosted startup fails closed without auth. Public demo is curated and bounded; no unlimited anonymous inference. Secrets remain server-side.

Initially support PDFs and constrained fact input. Bound file size/pages/render dimensions/parser time/concurrency/model calls. Restrict URL import destinations and redirects; reject private/internal addresses. Sanitize rendered content; authorize downloads with safe disposition and expiring links.

Production candidate: container API/worker, managed PostgreSQL/auth/private storage and Redis-compatible broker. Account/region/cost must be verified before provisioning. No paid provisioning or publication is authorized by a worker packet unless explicit in that packet and the human's instructions.

Record dependency versions, health/readiness, usage, retries, parse duration, queue delay, redacted diagnostics, and restore/recovery checks. Tests must include cross-project denial, restart recovery, clean configuration, and actual hosted flow when applicable.

W01 is local feasibility only. It must not inspect unrelated account data or create infrastructure.

