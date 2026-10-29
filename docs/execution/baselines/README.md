# Protected starting baseline

W01 begins from a documentation-only workspace, with no application implementation claimed.

`W01-baseline.json` contains SHA-256 hashes of the planning/execution files and preserved proposal assets present when Codex issued W01. The baseline does not include itself, transient locks, later handoffs, private downloads, or future worker outputs. It protects prior files, not an entire future filesystem.

Run from the project root:

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json
```

The verifier also checks execution-framework links/structure. It is a standard-library-only documentation tool, not an application test. If Python is unavailable, report that and use an equivalent hash check only with the exact manifest contents; do not skip the baseline silently.

A protected mismatch means stop before writing and ask Codex to resolve the baseline. Missing expected directories for future artifacts are normal. New files outside assigned paths are not automatically authorized just because they are absent from the manifest.

After worker execution, repeat verification and list every changed/new path in the handoff. Codex reviews the actual outputs, then binds later packets to new accepted baselines.

