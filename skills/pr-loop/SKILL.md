---
name: pr-loop
description: Implement same-repository GitHub Issues into a reviewed pull request, or review and fix an existing PR until the final head is reviewed and unblocked.
---

# PR Loop

Compose [`issue-to-pr`](../issue-to-pr/SKILL.md), [`pr-review`](../pr-review/SKILL.md), and [`pr-feedback-triage`](../pr-feedback-triage/SKILL.md) until the stable final PR head is reviewed, triaged, and unblocked.

Each sibling owns its standalone mechanics and safety contract. Resolve bundled sibling/support files through normal skill or file access; a missing registry entry alone is not a failure.

## Procedure

1. For an Issue start, run `issue-to-pr` for the complete requested Issue set and continue only after `STATUS: complete` with a verified PR.
2. Freeze the current PR head as `reviewed_target`.
3. Run `pr-review` for that exact SHA with publication enabled. Continue only after `STATUS: reviewed` and `REVIEWED_HEAD == reviewed_target`.
4. Run `pr-feedback-triage` against the latest live PR state and retain its exact final head and feedback snapshot. Continue only after `STATUS: complete`.
5. Re-fetch the live head and complete feedback:
   - if feedback changed while the head stayed the same, triage again;
   - if the head changed, start another review round;
   - if state matches the retained triage snapshot and the head equals the latest reviewed head, continue.
6. Stop if any active reviewer/merge blocker remains; otherwise succeed.

Do not clear reviewer state merely to satisfy the loop.

## Bounds

Keep review-round and triage-restart limits separate. Caller/runtime values override defaults.

- review rounds: default maximum 3;
- triage restarts: use `pr-feedback-triage`'s default maximum 9.

If an applicable bound is exhausted, stop. If a required finite bound or mandatory operation cannot be provided, return `unsupported`.

## Result

- `success`: live head/feedback equal the latest triage-complete snapshot, live head equals the latest reviewed head, and no reviewer/merge blocker remains.
- `stopped`: a phase, state check, permission, exhausted bound, or reviewer/merge blocker prevents success.
- `unsupported`: a required capability/resource or finite bound is unavailable.

Report the outcome, resulting PR/Issues when applicable, review rounds and final reviewed head, triage final head/restarts, and any remaining action or blocker.
