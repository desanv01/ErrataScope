# ErrataScope

ErrataScope helps engineers inspect manufacturer errata alongside an AI interpretation, see what remains unknown, and record an explicit review or rejection. Every displayed claim has source citations; human review does not turn a draft into an executable engineering rule.

The local submission build includes ST ES0620 Rev 5, two selected entries, a **recorded real NVIDIA Nemotron result from Nebius Token Factory**, and an original synthetic missing-information example. Loading the demonstration makes no paid calls.

## Run the free local test build

Requirements: Windows PowerShell, Git (or download this repository as a ZIP), and Docker Desktop running Linux containers with current Docker Compose. Tested with Compose 5.5.1. No host Python, Node, private development environment, Nebius key or paid credits are needed for this recorded demonstration.

```powershell
git clone https://github.com/desanv01/ErrataScope.git
cd ErrataScope
powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1
```

Open **http://127.0.0.1:18081/**. The launcher builds the app, creates an isolated database/store, downloads and verifies the pinned manufacturer PDF, imports the recorded interpretation, and prepares the original offline example. It does not copy the developer's database. Local sign-in is prepared automatically.

If ST's source is unavailable or has changed, obtain the exact ES0620 Rev 5 PDF and supply it explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1 -PdfPath "C:\path\to\es0620.pdf"
```

Expected SHA256: `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`. Changed documents are refused rather than silently relabeled.

Local sessions expire after two hours. Rerun the launcher with `-NoBuild` to refresh them; reviews and volumes remain. Stop with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/submission/stop-clean.ps1
```

## Try the journey

1. Inspect the **Recorded live Nemotron result** and its source version/provenance.
2. Click a citation: the source pane switches to the relevant entry and opens context when needed.
3. Inspect unresolved fields and selected coverage: two supported entries out of 53 detected; the inventory is incomplete.
4. Add a note, review or reject the interpretation, then export JSON or Markdown.
5. Select **Synthetic / offline example** to see unknown identity/revision and explicitly unlocated synthetic excerpts.

The free demo reuses a recorded provider result. The backend's actual Nebius integration produced that result with `nvidia/Nemotron-3.5-Super-VL`; its request ID, usage and provenance are preserved. Fresh inference is disabled in this launcher and requires separately configured, authorized provider access. No provider key is shipped to the browser or repository.

## Status and scope

S01's reduced local cited-review workflow is independently reviewed; see [review](docs/submission/S01-review-01.md). Public video and final Devpost submission are separate release steps. Full W04/P3 and hosted P2 are not accepted.

No applicability assessment, executable-rule acceptance, arbitrary PDF import, hardware simulation or automated repair is claimed. The original provider wire-byte hash cannot be re-derived from its normalized saved response; the UI/export disclose that limitation. The synthetic example is not a successful live omission test.

[Testing and setup](docs/submission/release/TESTING.md) · [Known limitations](docs/submission/release/KNOWN_LIMITATIONS.md) · [Silent demo brief](docs/submission/release/VIDEO_PREFERENCES.md) · [Release steps](docs/submission/RELEASE_NEXT.md)

Original code is [MIT licensed](LICENSE). ST documents, trademarks, model outputs and dependencies retain their respective rights/licenses. The full vendor PDF, credentials and raw provider responses are not redistributed. Historical development evidence includes 41 explicit legacy missing artifacts; the independent clean demo does not depend on those artifacts.
