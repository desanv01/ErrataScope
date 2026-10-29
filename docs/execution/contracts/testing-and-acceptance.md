# Testing and acceptance contract — revision 1

Worker implements checks, runs them, and fixes in-scope failures. Codex independently accepts based on actual files/runtime evidence. A report alone is not proof.

Every packet lists required behavior/checks. Record actual command, working directory, exit code, result path, and known limits. Missing dependency, skipped test, timeout, mock, cached model call, or synthetic fixture must be explicit. Do not delete failing tests, loosen expectations, or exclude failures from denominators.

Codex review is proportional:
- contracts/evaluator: semantic edge cases and invariant checks;
- persistence/jobs: migrations, idempotency, isolation, restart;
- model/parser: real artifact inspection, grounding, error paths;
- UI: connected user journey against actual API;
- change impact: new entries, missing-selector arrival, preserved history;
- release: hosted journey, reproduction, access links.

Evaluation separates pre-review model output from human-corrected workflow outcomes. Split related source-condition variants together. Report coverage and unknown rate alongside accuracy; no invented percentages. Ground truth is independently source-reviewed, not solely model self-grading.

A packet is accepted only when Codex records accepted baseline, checks, known limitations, and next eligible work. Never waive evidence integrity to gain a green status. Partial acceptance explicitly lists unresolved gates and does not make dependent work automatically dispatchable.

