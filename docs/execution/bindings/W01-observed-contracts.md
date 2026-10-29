# W01 observed contracts — accepted feasibility freeze

Accepted by [review 06](../reviews/W01-review-06.md), 29 October 2026. Machine-readable hashes and evidence: [ACCEPTANCE.json](../../evidence/W01/ACCEPTANCE.json). This freeze is the input boundary for W02; it does not make experimental spike models the production domain schema.

## Source and anchors

Pinned source: ST ES0620 Rev 5, August 2026, 38 pages. SHA-256 `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`. Selected entries 2.2.18 and 2.2.5 only. Document revision is distinct from silicon revision. Interpretation uses the sealed identity anchor, section/body/code anchors, table rows, governing column headers and status legends. Derived matrix is navigation, not independent authority.

Anchor schema version 1: top-left origin, x right/y down, normalized boxes relative to rendered page bounds; physical zero-based page_index distinct from printed page label. Anchor IDs are page-scoped parser ordinals, not stable identifiers across reparses. Preserve document hash and parser/geometry provenance. Real located geometry is distinct from synthetic_not_located placeholders. Production identity/versioning follows the W02 binding.

## Runtime and request

Observed Python 3.11.15 / Pydantic 2.14.1. Actual text-only requests used `nvidia/Nemotron-3.5-Super-VL` at the configured Nebius Token Factory chat-completions endpoint; prompt mode `draft-v4-grounded-no-thinking`; top-level chat_template_kwargs.enable_thinking=false; temperature=0; stream=false; max_tokens=8192. Both successful calls reported zero reasoning tokens and a complete final answer. This is observed compatibility, not a general availability/SLA claim.

The CLI deliberately loads NEBIUS_API_KEY from the project-designated environment or root .env.local; process environment takes precedence. W02 must not read that file or initialize this adapter. No W01 inference reservations remain.

## Draft boundary

DraftInterpretation schema version 1 has nullable document identity/revision, cited claims, unresolved_fields and limitations. Every emitted claim has at least one relevant supplied anchor; absence may be represented only in unresolved_fields. Null/unknown is not false. Exact source identity and citation checks run before a draft is eligible for semantic review. Model output is data, never executable code or an automatically active rule.

The successful draft's workaround-category clarification is accepted as faithful source text, not a directly executable restriction. Unknown trigger/exception fields must not become implicit true/empty accepted predicates. W04 will require explicit human-reviewed conversion with immutable versions, preserving source scope and all qualifications.

## Evidence and gate semantics

Provider evidence uses artifact wrapper schema 2: exact case, attempt, endpoint/model, prompt version, request/response/validation hashes and preserved raw content in private local artifacts. A success requires actual complete response content, case-bound hashes, recomputed validation and (for omission) the separate expectation check. A mocked response, empty file, HTTP success alone, edited draft or ledger summary is insufficient. CLI and report use the shared evidence validator; semantic acceptance is a separate Codex review decision.

W01 budget is exhausted at four reservations, including both failed attempts. No implicit reset when another packet starts. W02 is wholly offline and requires no provider calls, credits or secrets. Later inference work needs a separately bounded assignment.

## W02 production boundary

[W02 domain-v1](W02-domain-v1.md) specifies strict immutable entities, review states, accepted fact/rule versions, exact scope, three-valued logic, complete dependency traces, coverage and deterministic hashes/replay. Use original labeled synthetic fixtures. Do not import the spike or mechanically translate free-text claims into the AST. No simulator, firmware runner, repair generator or other VerifForge planned capability is introduced.
