# Dispatch and return prompts

Current assignment: [W02 revision 2](W02-START.md), attempt 01, READY_TO_DISPATCH after W01/P0 acceptance. W01 live prompts are historical; its lifetime budget is exhausted. Follow [STATUS](../STATUS.md).

Future packet prompts are issued by Codex after acceptance of their dependencies and baseline binding. A generic prompt is not authorization to skip those gates.

## Codex review return template

```text
Review ErrataScope packet <ID> revision <REV>.
The worker has stopped editing.
Read docs/execution/handoffs/<ID>-attempt-<NN>.md.
Inspect actual changes against the packet and accepted baseline.
Run focused independent checks. Record acceptance, partial findings,
or one consolidated repair assignment. Update phase/status only for
gates supported by evidence. Bind the next eligible packet before
issuing its start prompt.
```

## Worker repair dispatch template — Codex fills exact values

```text
Work in C:\Users\Dv\Desktop\ErrataScope.
Repair packet <ID> using docs/execution/reviews/<REVIEW_FILE>.
Read the original packet, current contracts, and the repair's exact
baseline, writable paths, and acceptance checks.
Do not reopen accepted architecture or work outside the repair scope.
Run the specified checks and write a new attempt-numbered handoff.
Stop editing and return the Codex review prompt.
```

Never overwrite a previous handoff/review. Codex may perform a tiny isolated correction after the worker stops when that is faster; it records the change and reruns the affected check instead of implying it reviewed unchanged worker output.

