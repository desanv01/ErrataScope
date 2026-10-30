# Silent video release handoff

Production project: `videos/erratascope-demo/`. **Verified final master:** `videos/erratascope-demo/renders/ErrataScope_Demo_Desan_Vasu.mp4` — **2:32**, 1920×1080, 30fps, H.264, no audio stream, 21,395,190 bytes. Full decode and actual exported-review checks passed. SHA-256: `f7658c4ac6a664d6c86567ea40d8650354efb0aeca9481e25d94183e17a716ce`. Detailed evidence: `videos/erratascope-demo/VERIFICATION.json` and `REVIEW.md`.

The verified video is now **published publicly on YouTube**: https://youtu.be/oD1uhOq6UHk. YouTube confirmed “Video published,” 2:32 duration and no copyright issues on 30 October 2026. The full saved title, description, chapter timestamps and settings are in YOUTUBE_METADATA.md. Devpost submission confirmation is recorded separately.

## YouTube

1. Open YouTube Studio in the intended account, choose Create → Upload videos, and select the verified final MP4.
2. Title: **ErrataScope — Cited Errata Review | NVIDIA × Nebius Hackathon | Desan Vasu**.
3. Use the description below, choose the truthful audience setting, continue through checks, and set visibility to **Public**. The supplied official rules explicitly require public visibility.
4. Wait for processing, open the public watch URL while signed out and confirm playback, under-three-minute duration, readable source/action footage and correct labels.
5. Copy the actual watch URL into Devpost's video field. A local file path or HyperFrames preview URL is not the public video URL.

Suggested description:

```text
ErrataScope by Desan Vasu — NVIDIA × Nebius Global AI Hackathon.

ErrataScope helps a reviewer inspect an AI interpretation of manufacturer errata against its source citations, preserve unknown information, record a human review, and export the evidence.

NVIDIA Nemotron (nvidia/Nemotron-3.5-Super-VL) runs through the Nebius Token Factory inference API to interpret selected manufacturer excerpts. This video demonstrates the working local application using a recorded result from an actual earlier live request. Loading the demo does not make a fresh inference call. The separate synthetic/offline example is explicitly labeled.

The demonstrated scope is two selected ES0620 entries, not whole-document coverage or a device-applicability decision. Human review does not create an accepted executable rule.

Code: https://github.com/desanv01/ErrataScope
Setup and testing: https://github.com/desanv01/ErrataScope/blob/main/docs/submission/release/TESTING.md
Manufacturer source: STMicroelectronics ES0620, Rev 5. Manufacturer material remains subject to its own rights.

Track: Best Apps and Agents Track.
```

## Devpost

- Public code repository: https://github.com/desanv01/ErrataScope
- Source and test-build setup: https://github.com/desanv01/ErrataScope/blob/main/docs/submission/release/TESTING.md
- Downloadable source checkout: https://github.com/desanv01/ErrataScope/archive/refs/heads/main.zip
- Public YouTube video: https://youtu.be/oD1uhOq6UHk.
- Project description and NVIDIA/Nebius feedback: copy and finalize `SUBMISSION_COPY.md`.
- Track: **Best Apps and Agents Track**.
- Test access: local Docker test build with recorded live result and synthetic fixture; no Nebius key required for judging that workflow. Follow the pinned manufacturer-PDF prerequisite. Do not present the local URL as hosted public availability.
- Source license: standard MIT with separate third-party NOTICE; detected in GitHub's prior accepted checkpoint.

Save/submit the actual form, then verify the submission confirmation and that code, test instructions and video links open publicly. The official deadline recorded in RELEASE_NEXT.md is 31 October 2026 at 01:00 MYT; target 00:15 MYT for upload/form contingency.
