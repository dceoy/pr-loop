# Multi-PR planning and publication

Use this reference only when `issue-to-pr` needs more than one PR. Keep the single-PR procedure unchanged when one cohesive PR satisfies the Issues.

## Plan the smallest safe graph

- Honor requested PR boundaries/order; inspect named existing PRs rather than creating duplicates. Do not split solely because a diff is large.
- Use **independent** PRs for unrelated responsibilities at the same frozen trunk SHA. Use **stacked** PRs for changes dependent on earlier commits: linear same-repository chains such as `main <- model <- API <- integration`, with each PR targeting its immediate predecessor's branch. No fan-out inside a stack; use separate stacks or revise the plan. Mixed graphs are permitted.
- Default to **at most five PRs**, unless the caller sets another finite limit. If a required split cannot be represented safely, return `blocked` rather than silently combine it.
- Before edits, freeze Issue identities/material versions, target branch and SHA; record mode, topological order, edges, and per-PR owning Issues, responsibility/interfaces, branch, parent, exact expected base, acceptance/QA checks, and recovery/retry bounds. Each layer must build and be reviewable without unmerged successors. Distinguish parent-relative diffs from cumulative stack changes.
- If an essential dependency, required split, or acceptance condition remains ambiguous, use the main skill's `STATUS: blocked` question contract.

## Implement and publish

1. Implement **serially** with one writer in topological order: each root starts at the frozen target SHA and each layer at its **verified parent head**. Confirm its scoped parent-relative diff, Issue requirements, integration with ancestors, and QA.
2. Before publication, refresh material Issue content, target base, and expected parent heads; replan on material changes. Do not attribute tests from a different commit to the candidate.
3. Publish every commit through a **new, absent remote ref**, with atomic create-if-absent semantics. Verify exact remote SHA. A preflight absence check is not atomic; never substitute force-push or an implicit stack-command push.
4. Create and re-fetch each PR, verifying same repository, exact base ref/SHA and head ref/SHA, Issue coverage, and parent relation. Use `Refs #123` for partial Issue coverage, not `Fixes #123` unless that one merged PR closes the Issue.
5. Prefer GitHub-native stack metadata when **supported and safely available**, but only after refreshing and verifying every planned base/head pair. The stack REST endpoint `POST /repos/{owner}/{repo}/stacks` accepts verified PR numbers in bottom-to-top order; read back membership via `GET /repos/{owner}/{repo}/stacks?pull_request=<number>` or `GET /repos/{owner}/{repo}/stacks/<stack-number>`, asserting exact order and head SHAs. Do **not** use `gh stack link`: it may push branches or retarget PRs. Do not install unrequested extensions or claim native linkage from base/head checks alone. When native API support/verification is absent, retain and label a normal branch-based dependent PR chain.
6. Re-fetch **all** PRs and verify graph edges, target base, ancestor relations, head SHAs, and complete intended coverage. Return `STATUS: complete` only for the fully verified set.

`gh stack submit --auto --open` is noninteractive but can partially push/update branches. Do not use it when it would violate create-only ref and expected-SHA guarantees.

## Partial failures

Preserve every verified created PR, branch, commit, and its base/head on partial failure. Return `stopped` with URLs, exact unfinished stage, and safe recovery state. For retries, verify prior output, ownership, SHAs, Issue coverage, and graph edges before resuming. Never create duplicate PRs, adopt unrelated branches, silently retarget, delete partially published state, overwrite unexpected refs, merge, auto-merge, close Issues, dismiss reviews, or bypass branch protection.

Examples: dependent model/API/integration stages form one stack; unrelated CLI and documentation changes form independent PRs. An indivisible change stays in one PR unless the caller requires splitting, in which case an unsafe split blocks publication.
