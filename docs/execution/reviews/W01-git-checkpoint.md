# W01/P0 Git and GitHub checkpoint

Accepted scope: [W01 review 06](W01-review-06.md), including the source/provider feasibility spike, preserved review history, observed contracts and W02 dispatch preparation. The production domain/evaluator is assigned to W02 and is not claimed implemented here.

Repository: [desanv01/ErrataScope](https://github.com/desanv01/ErrataScope), created and verified **private** under the authenticated `desanv01` account. Local branch: `main`. Checkpoint tag: `w01-accepted`. Initial repository checkpoint uses a direct accepted-baseline commit; there is no pre-existing branch for a meaningful review PR. No merge or public release is implied.

Publication procedure: inspect the exact candidate/staged files; scan for the configured secret and common credential signatures; exclude .env.local, .local, environments, raw provider payloads and vendor PDFs; commit the accepted checkpoint and push main plus the immutable checkpoint tag. Verify remote refs match the local commit. The resulting commit hash and push verification are reported in the Codex handoff and saved locally under `.local/reviews/W01-review-06/`; they cannot be embedded self-referentially in the commit that contains this record.

GitHub CLI initially reported authentication failure under the restricted network. A permitted external-network check confirmed the authenticated account; no credential replacement or user login was needed. The GitHub connector supports account/repository reads but does not expose repository creation, so the authorized creation/publication uses the CLI.

W02's baseline binds the accepted repository files and instructions by content hash. Later W02 work uses its own worker ownership and must not mutate Git. The UI/imagegen approval gate is pending. A private checkpoint is not the public repository/demo release required later for submission.
