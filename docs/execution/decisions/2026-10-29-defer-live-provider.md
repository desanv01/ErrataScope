# Decision: independent implementation proceeds while provider credit is unavailable

**Historical/superseded:** [credits are now restored](../decisions/2026-10-29-credits-restored.md). Current dispatch is [W01 live v2](../prompts/W01-LIVE-COMPLETION-V2.md), before W02. Preserve the text below as history; do not execute its old dispatch.

Authority: the user's 29 October 2026 instruction to avoid blocking implementation on delayed credits and support project-local `.env.local` configuration. This supersedes earlier all-or-nothing W01 → W02 sequencing, including the previous live-completion dispatch. No worker lock or attempt-04 handoff existed when the change was made. The prior 111-file baseline passed before Codex edits.

## Acceptance and dependency change

W01 offline findings remain accepted within review-03's limits. W01 G4 and live G5 remain **DEFERRED / NOT RUN**, and P0 is still partial. No real-provider pass is inferred from having an API key, credit application, mock output, or an offline check.

W02 revision 2 is now explicitly authorized from the accepted offline source/anchor findings and the deterministic domain contract frozen by Codex. Its provider-free evaluator has no runtime dependency on W01's live calls. This is a scoped dependency change, not a waived evidence requirement or a declaration that W01 is fully accepted.

After each independent packet is accepted, Codex may bind the next packet's provider-independent scope and perform its Git/GitHub checkpoint. No blanket future dispatch: W03-W10 remain planned until their exact dependencies are bound. One writer at a time still applies. Live resumption must wait for a handoff boundary rather than racing the worker in the shared folder.

| Work | Can be implemented before credits? | Completion limit |
|---|---|---|
| W02 domain/evaluator/replay | Yes; fully offline | Its own gates can pass independently |
| W03 persistence/auth/jobs | Yes, after W02 binding | Hosted-account checks remain separate where needed |
| W04 provider adapter and review workflow | Yes with labeled mocks/fixtures | Actual model extraction remains integration-pending |
| W05-W07 assessment/evidence/change impact | Yes after contract/dependency review | Source fixtures or human-reviewed inputs must be labeled |
| W08 UI/export | Yes after backend binding and explicit UI/imagegen approval | Mock demonstrations cannot establish live model behavior |
| W09 final evaluation/production acceptance | Prepare and execute offline portions | Real model metrics and complete live journey required before acceptance |
| W10 release/submission | Prepare materials | No integration-complete or submission-ready claim without real runtime evidence and all release requirements |

Run the two deferred W01 cases as soon as usable access is available; do not deliberately postpone them until the last submission minutes. Provider incompatibility remains a real rework risk. Preserve adapter boundaries so it affects extraction rather than deterministic domain semantics.

## Hackathon and billing facts

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules), checked 29 October, require a working application using at least one NVIDIA open-source model and running through Token Factory runtime calls or the permitted Nebius compute route. They do not require each development phase to invoke paid inference. This project continues to target its intended NVIDIA-on-Token-Factory runtime; mocks alone do not fulfill it. Deadline shown: 30 October 2026 10:00 PDT = **31 October 2026 01:00 Malaysia time**.

An API key authenticates; it does not add balance or prove account/model permission. [Nebius billing documentation](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) describes an initial US$1 trial credit valid for 30 days; the user's actual balance and eligibility are unverified. Do not assume a paid top-up is necessary or authorize one. The promo redemption problem is handled separately with support. No live calls are dispatched by this decision.

## Project-local credentials

Codex added a small, tested loader for the exact project-root `.env.local` file. It imports only NEBIUS_API_KEY, without shell execution/interpolation; an existing nonempty process variable takes precedence. The CLI now supports `check-key` (presence only, no network/log/ledger write), and loads the same configuration for provider, environment, and self-test commands. Missing/invalid configuration produces value-free errors. The new `.env.example` contains no credential; `.gitignore` already excludes `.env.local`.

Historical advice that `.env.local` is not loaded applied to the old spike. It is superseded for this CLI. DeepSeek itself can continue using its existing coding-model account. Workers must not read/cat `.env.local` or dump environment values; the designated application loader may use it when the human deliberately configures it.

Validation: seven configuration tests pass using fake keys only. Initial test execution hit sandbox temp-directory ACL errors; tests were relocated to isolated project-local directories and rerun successfully. Protected-baseline tooling now supports explicit packet states and W02 manifests instead of assuming every future packet must forever remain planned. A final new baseline protects these changes.

No UI implementation or approval bypass, model call, billing operation, or claim of full W01/P0 completion accompanies this decision.

Final regression evidence: 20/20 independent artifact/CLI/report checks passed; existing worker suite 50 PASS, 0 FAIL, 1 SKIP (no real key used). Observations: `.local/reviews/W01-review-03/run-3449574401ad/observations.json`. Actual provider ledger unchanged, zero live attempts. The added CLI test verifies file loading, presence-only output, and no command-log call; its initial isolated-root baseline-path mismatch was fixed in the test setup before the successful seven-test run.
