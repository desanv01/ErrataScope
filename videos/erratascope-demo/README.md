# ErrataScope silent demo production

Local HyperFrames composition: **152 seconds / 2:32**, 1920×1080, 30fps, silent. Creator: Desan Vasu. The production follows the inspected MajuPilot workflow; see BRIEF.md and RULES_AND_RIGHTS.md.

The captured application is the actual accepted S01 test build at `http://127.0.0.1:18081/`. It shows a stored result from an earlier real Nemotron request, genuine source navigation, a new human review and actual downloaded summaries. The separate synthetic case is explicitly identified. No provider calls occur during recording.

## Files

- `EDIT.json`: actual timed edit, source trims and labels.
- `scripts/capture-*.js`: reproducible Playwright interaction sequences.
- `scripts/build-composition.mjs`: builds the editable HTML scenes.
- `scripts/verify-video.mjs`: probes and fully decodes the MP4; checks the actual downloaded review summary and hashes source clips.
- `REVIEW.md` and `VERIFICATION.json`: final review and measured output evidence, once completed.
- `renders/ErrataScope_Demo_Desan_Vasu.mp4`: final local deliverable, excluded from Git.

Raw recordings, browser downloads, review sheets and rendered video stay local. The public source checkpoint contains the edit and production source, not the source footage. Rendering from a fresh checkout requires these local captures; this does not affect the application setup documented at the repository root.

## Local render

With Node 22+, FFmpeg, and the existing local captures:

```powershell
node scripts/build-composition.mjs
npm run check -- --json
npx --yes hyperframes@0.8.221 preview --background --port 3017
npm run render -- --quality delivery --fps 30 --output renders/ErrataScope_Demo_Desan_Vasu.mp4
node scripts/verify-video.mjs
```

Review the editable timeline at `http://localhost:3017/#project/erratascope-demo`. The film is intentionally silent; the silence warning and title-card holds are accepted. All explanatory overlay text is at least 28px. Product interface text remains authentic; full workspace context is supported by enlarged evidence panes.

## Publication

The local file is ready only after VERIFICATION.json reports `ok: true` and decoded frames have been reviewed. Upload that file to public YouTube, then put its actual public URL in Devpost. No upload or submission is performed by producing this local file.
