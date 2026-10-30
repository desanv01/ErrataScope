# Known limitations and attribution

## Provenance
- The retained real-source draft is a **recorded live** Nemotron/Nebius result from the separately bounded W04 history. Loading it is not a new provider call.
- W04's preserved response artifact is normalized JSON; the recorded response hash binds original wire bytes but cannot be re-derived from the normalized artifact. The UI and export state this limitation rather than displaying a fabricated wire-verified badge.
- W04's second (synthetic omission) live reservation received a complete provider response but failed worker-side draft validation; the response body was not retained. The synthetic case shown here is **offline/mock** and is not a live omission success. W01's exhausted 4/4 history is separate and unchanged.
- No new paid calls, key access, budget reset or live compose override occurred in S01.

## Scope
- Only ES0620 selected entries 2.2.18 and 2.2.5 are processed. 53 entries are detected; 51 are unselected and not assessed. `inventory_complete=false`.
- No facts/applicability form, executable rule acceptance, applicability badge, generic PDF import, team administration or VerifForge capability is included.
- A reviewed interpretation is a human acknowledgement only. It does not create an `AcceptedRule`.
- The source conversion is not represented as a real executable rule: the frozen selector vocabulary cannot faithfully express the NRST reset-mode trigger or DBGMCU register.
- Historical 41 missing artifact IDs remain missing; no replacement bytes are claimed.

## Build/distribution
- The retained local test build and an isolated clean project/fresh-volume installation are both verified from real browser journeys.
- The clean install imports a normalized recorded-live snapshot through the bounded local importer; it does not copy the main database and makes **zero provider calls**. The clean install also prepares the original synthetic/offline missing-information example through the real API/worker. Its excerpts have no physical PDF location.
- Local development auth is generated for loopback localhost only; hosted production authentication/authorization is out of scope (P2 NOT_RUN).
- The approved imagegen direction is implemented as layout guidance; no new design approval is claimed.

## Attribution / licensing
- Original ErrataScope project code: MIT (see root `LICENSE`).
- ST ES0620 document and ST trademarks: STMicroelectronics; vendor document is not redistributed in the repository and is not relicensed. Its public source URL and SHA-256 are recorded.
- NVIDIA Nemotron / Nebius Token Factory: model and provider attribution; outputs are not our original code and remain subject to provider/source terms.
- The approved workspace mockup is an internal design artifact, not a third-party asset.
- React/Vite/TypeScript and Python dependencies retain their own licenses.

Local tokens last two hours. Rerun the launcher to refresh them; reviews and volumes are preserved. The current ST PDF must match the pinned hash; a changed upstream version is refused with instructions to supply the exact PDF.
