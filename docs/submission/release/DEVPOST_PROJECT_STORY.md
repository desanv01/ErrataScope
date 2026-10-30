# Devpost project story

Project: ErrataScope
Project URL: https://devpost.com/software/erratascope
Submission ID: 1272641

The story below was entered and saved in Project details. Final submission confirmation is recorded separately.

## Inspiration

Manufacturer errata can change the meaning of a reset sequence, register value, or workaround. A fluent AI summary is not enough when a missed revision or an invented exception can send an engineer in the wrong direction. I wanted a workspace where the source, the interpretation, and the reviewer's uncertainty remain visible together.

ErrataScope's central idea is simple: trace the claim, keep the unknowns, and preserve the human decision.

## What it does

ErrataScope is a working desktop-browser application for cited manufacturer-errata interpretation and human review. The included real case uses STMicroelectronics ES0620 Rev 5 and two selected entries: 2.2.18, concerning NRST reset behavior, and 2.2.5, concerning DBGMCU_IDCODE.

- Read located manufacturer excerpts beside the model's structured interpretation.
- Click a citation to switch to its source entry, reveal supporting context, and highlight the actual excerpt.
- Inspect source identity, revision, request provenance, token usage, and hashes.
- Preserve unresolved fields and explicit selected coverage: 2 supported entries out of 53 detected; the inventory is incomplete.
- Add a required review note, acknowledge or reject the interpretation, and retain an append-only history.
- Export the source, claims, citations, unknowns, coverage, and review history as JSON or Markdown.
- Switch to a separately labeled synthetic/offline example with deliberately missing identity and revision.

A human review is an observation recorded against a draft. It does not establish device applicability or create an accepted executable engineering rule.

## How I built it

The interface uses React 19, TypeScript and Vite. FastAPI and Python provide the application API and processing. PostgreSQL stores project and review authority; Valkey and RQ support durable background work. Manufacturer parsing uses bounded pdfplumber processing, with located anchors and source hashes. Private local artifact storage and Docker Compose support the verified local test build.

The workflow is: selected source evidence → located citation anchors → NVIDIA model interpretation → strict draft validation → human review → portable evidence export. Reviews are bound to the draft response hash and revision, with current-role authorization and conflict handling. The application preserves earlier decisions instead of overwriting their history.

## NVIDIA Nemotron and Nebius Token Factory

The backend makes actual runtime requests to nvidia/Nemotron-3.5-Super-VL through the Nebius Token Factory inference API. Nemotron interprets selected manufacturer excerpts into a structured, cited draft. Token Factory provides hosted NVIDIA-model inference, allowing the application to use the model through an API without preparing a local GPU inference server.

The demonstrated manufacturer result came from an actual successful live request. Its provider request ID, token usage, prompt version and saved response hash are retained. The free judging build replays that recorded result; opening the page does not make a fresh model call or spend credits. Provider credentials are never shipped to the browser or public repository.

## Challenges I ran into

The first challenge was distinguishing valid JSON from a faithful interpretation. Workarounds, exceptions, revision mappings and optional example details need different meanings. Unknown information must remain unknown, rather than becoming a guessed fact or a false value.

Live integration also exposed a reasoning/output-budget mismatch: an early request spent its completion budget on reasoning without producing a final draft. Disabling thinking for this bounded extraction path allowed a usable final structured response. Strict validation then helped expose citation and unresolved-field contract mismatches. Failed attempts were retained rather than relabeled as successes.

Citation navigation needed to preserve physical and printed page references, switch between selected entries, and open the identity/legend context when necessary. Storage and review behavior also needed real integration checks so a successful interface action corresponded to a retained record.

## Accomplishments I'm proud of

The local review workflow was checked through real PostgreSQL, worker, API, filesystem and browser behavior. A clean isolated installation imported the recorded case without copying the development database or making provider calls. Actual review/export behavior survived an API restart. The silent demonstration shows genuine source navigation, a newly saved review note, its history, downloaded exports, and the separate synthetic case.

The public repository includes source, an MIT license, setup instructions, a pinned manufacturer-PDF prerequisite, actual demo frames and documented limitations.

## What I learned

A trustworthy AI workflow needs three distinct checks: what the provider actually returned, what the source supports, and what a human has decided. Structural validation helps, but it cannot replace source-grounded semantic review. Missing data, incomplete coverage, and a reviewer's acknowledgment must remain explicit in both the interface and exported evidence.

## What's next

Expand reviewed manufacturer/source adapters and coverage, improve ingestion and source selection, and qualify hosted deployment. Device-fact applicability and executable-rule acceptance need their own faithful conversion and independent validation before being exposed as product capabilities.

## Try the working test build

Code: https://github.com/desanv01/ErrataScope

Setup and testing: https://github.com/desanv01/ErrataScope/blob/main/docs/submission/release/TESTING.md

Download source: https://github.com/desanv01/ErrataScope/archive/refs/heads/main.zip

The supported judging route is the local Windows/Docker recorded demo. It requires no Nebius key or paid credits. Follow the setup guide and supply the exact pinned ES0620 Rev 5 PDF if the manufacturer's automatic download is unavailable or changed.

## Scope and attribution

This build covers selected-source interpretation and review, not arbitrary PDF import, whole-document coverage, hardware simulation, automated repair, or a hosted production service. The original provider wire-byte hash cannot be re-derived from the normalized saved response; this limitation is disclosed in the application and exports. The synthetic fixture is not manufacturer evidence or proof of a successful live omission test.

Original project code is MIT licensed. STMicroelectronics manufacturer excerpts retain their own rights and are used with permission. Model outputs and dependencies retain their applicable terms.
