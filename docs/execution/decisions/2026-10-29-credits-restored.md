# Credits restored — complete live W01 before W02

Latest user instruction, 29 October 2026: the account now shows US$25 and live steps should no longer be deferred. This supersedes the [earlier temporary sequencing decision](2026-10-29-defer-live-provider.md). No worker lock, W01-attempt-04 handoff or W02-attempt-01 handoff existed when checked. No W02 implementation was started. W02's detailed domain binding is preserved for prompt dispatch after W01 acceptance.

Current assignment: [W01 live completion v2](../continuations/W01-live-completion-v2.md), [prompt](../prompts/W01-LIVE-COMPLETION-V2.md). W01 remains partial until actual G4/live G5 results pass independent structural and semantic review. W02 is prepared but not dispatchable until that review. Codex then performs the Git/GitHub checkpoint and rebinds/dispatches W02 immediately. UI/imagegen approval remains pending.

The screenshot establishes a displayed $25 balance, not API-key or model-access validation. The project's new presence-only CLI currently reports NEBIUS_API_KEY MISSING. The human should configure root `.env.local` as described in [local credentials](../../LOCAL_CREDENTIALS.md). The loader and tests are retained; no Windows-wide variable is required. No secret value was requested, displayed or copied by Codex.

## Cost decision

Keep the already validated adapter's model `nvidia/Nemotron-3.5-Super-VL` for the two bounded W01 text calls. [Nebius's official announcement](https://nebius.com/blog/posts/three-new-open-weight-models-from-us-companies-give-builders-more-choice), rechecked 29 October, publishes $0.30/M input and $0.90/M output. At 16,000 input and 8,192 output tokens, estimated token cost is $0.0121728 per request, $0.0243456 for two, $0.0365184 for three. These are calculations from published token rates, not an account-specific billing guarantee; image billing and taxes are not included.

The actual existing guards remain stricter than the whole account balance: <=3 total W01 reserved attempts, <=16,000 bounded input tokens and <=8,192 output tokens per request, <=$0.25 aggregate estimate, no automatic retries. The v2 continuation authorizes only two new cases; preserve all ledger history. Having $25 does not authorize bulk model evaluation or provisioning.

[Nebius's model overview](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference) lists Nemotron 3.5 Lightning and Nemotron 3 Nano at $0.06/M input and $0.24/M output. These are good later low-cost candidates, not proven replacements for this document-interpretation workload. After the baseline succeeds, a separately bounded comparison may establish quality before routing routine extraction to a smaller model. Do not change the protected model or its prices silently. The savings for the two W01 calls are about two cents; preserving the reviewed adapter avoids an unnecessary compatibility change now.

Coding remains in DeepSeek/Codex on their existing accounts; the Nebius balance is for designated runtime inference, not every development/test turn. Local deterministic checks remain free of provider calls.

Validation inherited from this turn: seven fake-key configuration tests pass; 20 independent artifact/CLI/report cases pass; worker suite 50 PASS and one SKIP; actual provider ledger unchanged with zero requests. The 119-file W02 draft baseline passed before this latest scheduling update. Historical manifests remain unchanged; use the new live-v2 baseline for current dispatch.
