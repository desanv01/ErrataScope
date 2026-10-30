# Submission copy (draft for the user/Codex to finalize)

**Title:** ErrataScope — cited errata interpretation and human review

**Short description:** ErrataScope turns a real manufacturer errata document into a source-grounded interpretation that a reviewer can inspect, acknowledge or reject. It shows exact citations, selected coverage, unresolved information and a downloadable review summary — without pretending a model draft is an approved rule.

**What is real in this build:**
- ST ES0620 Rev 5, 38-page PDF, selected entries 2.2.18 and 2.2.5.
- A **recorded live NVIDIA Nemotron result via Nebius** (one real request from the earlier W04 bounded budget) with its request ID, usage, model, prompt version and hashes.
- Real located source excerpts/geometry, 53 coverage entries, unresolved fields and append-only interpretation reviews.
- A separate, clearly labeled synthetic/offline missing-information example.

**What is not claimed:** new live calls, whole-document coverage, applicability/facts assessment, an accepted executable rule, hosted production acceptance, UI imagegen re-approval, or VerifForge functionality.

**Tech:** Python 3.11 / FastAPI / PostgreSQL 17 / Valkey / RQ / React 19 / Vite / TypeScript; local Docker Compose test build.

**Video guidance:** silent, under-three-minute demonstration with the user’s name and brief project introduction; follow VIDEO_PREFERENCES.md and inspect the MajuPilot Desktop HyperFrames workflow before producing it; keep it under three minutes; show the actual workspace and export. Do not show secrets, raw provider envelopes, private tokens or unrelated project data.

**Track:** Best Apps and Agents Track. This is an engineering evidence-review application, not a coding agent or physical robot. Official rules: https://nebiusglobalaihackathon.devpost.com/rules.

**Nebius/NVIDIA feedback:** The real backend successfully called NVIDIA Nemotron through Token Factory. Disabling thinking for this bounded extraction request allowed a final structured draft within the output cap. Strict validation exposed a missing-field allowlist issue on the synthetic case; we retain that failure and distinguish model output from reviewer acceptance. Loading the free test build replays the recorded result; it does not charge inference.
