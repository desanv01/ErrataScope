# ErrataScope

ErrataScope investigates manufacturer errata and advisory evidence: what a document says, which product configuration it may apply to, what remains unknown, and what needs human review.

**Current status:** W01/P0 feasibility accepted. Two bounded live NVIDIA Nemotron calls on Nebius produced a cited real-source draft and a passing synthetic missing-information case. The production application has not been implemented. W02 is the next offline domain-model and deterministic-evaluator packet.

- [Execution entry point](docs/execution/START_HERE.md)
- [Current status](docs/execution/STATUS.md)
- [W01 acceptance review](docs/execution/reviews/W01-review-06.md)
- [Observed contracts](docs/execution/bindings/W01-observed-contracts.md)
- [W02 implementation assignment](docs/execution/packets/W02-domain-core.md)

The repository contains planning, the feasibility spike, original synthetic fixtures and public-safe evidence metadata. Credentials, local environments, manufacturer PDFs, raw model responses and private artifacts are excluded. Some historical review scripts require those private local artifacts and are not standalone CI tests. Baseline checks verify protected repository bytes, not provider accuracy.

Model outputs remain drafts. Missing information stays unknown; no safety, certification or whole-device coverage claim is made. The project does not run firmware, simulate hardware or generate repairs. Application UI awaits explicit human approval of imagegen mockups.
