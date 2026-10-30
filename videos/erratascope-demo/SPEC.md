# Production specification

GOAL: A judge sees exactly how a cited model interpretation becomes a human-reviewed, exportable record without inventing missing information.

OUTPUT: HyperFrames, 1920 x 1080, 30 fps, H.264 yuv420p MP4; no audio stream. Target 150–165 seconds; hard limit below 180.

LOOK: Actual approved app colors, dark #0d151c, paper #faf7f0, cyan #65d2f4 and amber #edbf65. Inter 700 title 100 px, headings 42 px, chapter labels 24 px, short caption 28–32 px. Real UI without color treatment. Source text and actions remain original browser pixels. No stock media or portrait.

MOTION: Restrained 0.45 second power2.out title reveals, direct cuts between authentic browser clips; a crop may enlarge a real pane without changing its content. Captions sit outside footage. Readable holds at actual user actions, no fake loading/generation.

SHOTS: Intro 8s; workspace/provenance 18s; citation interaction 28s; unknowns/coverage 22s; human review/history 28s; actual export 16s; synthetic omission 24s; close 6s. Adjust trims against captured footage, retain honest labels. Target 150s.

BANNED: Mock product screens, generated UI, fake fresh-inference animations, implied complete coverage, applicability/safety certification, accepted-rule claims, music, voiceover, secrets, private filesystem paths, unapproved portrait reuse.

QA: Inspect midpoint of each scene and cuts; check full HD text, caption contrast, citation switch, real review persistence, downloaded export, synthetic label. ffprobe duration <180s, 1920x1080, 30fps, H.264, no audio; decode full file. Record source footage hashes and final SHA-256.
