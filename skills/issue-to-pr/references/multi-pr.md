# Multi-PR planning and publication

This reference applies when `issue-to-pr` needs more than one PR. Keep the existing single-PR workflow unchanged when one focused PR satisfies the requirements.

## Select the smallest safe PR graph

1. Honor an explicit requirement for multiple PRs, including a requested order or boundaries. If the request names existing PRs, inspect them rather than assuming they are instructions to create duplicates.
2. Prefer one PR for cohesive changes with a single reviewable responsibility. Do not split merely because a diff is long.
3. Use independent PRs when changes are logically separate and neither requires the other's commits. Root them all at the same frozen target base.
4. Use stacked PRs when later changes require earlier commits. A stack is a *linear* chain of same-repository branches, bottom to top: `main <- model <- api <- integration`. A dependent PR's base must be its immediate parent's branch, not `main`. Do not create a single stack with branching/fan-out dependencies; use separate stacks or reorganize the plan.
5. A plan may mix independent PRs and stacks. Use a maximum of five PRs by default, unless the caller provides another finite bound. If the request demands more and the bound cannot accommodate it, return `blocked` rather than discard required parts.

Before editing, retain an ordered, decision-complete plan that includes:

- Frozen Issue identities and material content versions, target branch and exact base SHA.
- Mode (`independent`, `stacked`, or `mixed`), ordered PR IDs, and an acyclic dependency graph.
- Per PR: owning Issues, scoped changes/affected interfaces, expected parent PR, branch name, base ref and expected base commit, implementation/QA/acceptance checks.
- A verification strategy that distinguishes each PR's parent-relative diff from cumulative stack changes.
- A recovery strategy and finite bounds for retries. Confirm that every stage can be built, reviewed, and checked independently of future, unmerged stages.

When an important dependency, acceptance condition, or user-mandated split is ambiguous, use the existing planning `STATUS: blocked` question contract; do not silently choose a materially different scope.

## Build and publish

1. Implement serially in dependency order with one active writer. Every root begins at the frozen target base. Every dependent layer begins at its **verified parent head**; no layer may depend on an unpublished or unexpectedly moved parent.
2. Keep each commit and parent-relative diff within that PR's planned responsibility. Verify the relevant Issue requirements and QA for each layer, including integration with all its ancestors. Avoid duplicating an ancestor's commits as a new unrelated change.
3. Before publication, re-fetch the Issues, target base and expected parent heads. Replan on material Issue changes or unexpected base/parent movement. Never claim a successful QA check from a different commit.
4. Require a fresh, nonexisting remote branch for every generated PR. Create refs using create-if-absent semantics, then read back the exact commit SHA. A preflight absence check **alone** is insufficient: never use a force push or a stack command that may overwrite an unexpected remote branch as a substitute for atomic creation.
5. Open one PR per planned unit and read it back. Verify same repository, intended base branch and current base SHA, intended head ref/SHA, owning Issues, and dependency relationship. Use `Refs #123` or equivalent for partial Issue coverage; do not use `Fixes #123` on a partial stage, because merging that PR alone must not close the Issue.
6. Prefer GitHub-native stack metadata when supported by the repository and available noninteractive tooling. The official `github/gh-stack` CLI supports `gh stack link` for already published branch chains and `gh stack view --json` for verification. Do not install extensions/skills unrequested, assume that a public-preview feature is enabled, or treat a successful command without verified remote state as publication. If only ordinary GitHub branch/PR APIs are available, retain the correctly based dependent PR chain and report that native stack linking was unavailable.
7. Re-fetch every PR after all publication/linking actions. Verify the full ordered set, target base, ancestor relationships, head SHAs, and absence of omitted/duplicate stages. Only then return `STATUS: complete`.

GitHub `gh stack submit --auto --open` is noninteractive, but submission is not an atomic all-branch operation. It may partially push/update branches. Do not invoke it in a way that violates the fresh-ref and expected-SHA invariants above. Prefer create-only remote refs and linking through supported capabilities, or stop if required guarantees cannot be enforced.

## Partial failures and retries

- Track each branch/commit/PR created and its verified base/head. A failure after some PRs exist returns `stopped` with those exact URLs, refs, and the next unfinished stage, not `complete`.
- On retry, discover the prior output and verify ownership, exact expected SHAs, Issue coverage, and base/head relationships before resuming. Never create a duplicate PR, adopt an unrelated branch, or rewrite unexpected remote state.
- Never delete or retarget a partially created PR as implicit cleanup. Require explicit authorization for destructive recovery.
- Do not merge, auto-merge, close Issues, dismiss reviews, or bypass branch protection.

## Examples

- One Issue asks for model, API, and integration PRs with sequential dependencies: create `model -> api -> integration` as one stack.
- Multiple Issues describe unrelated CLI and documentation updates: create two independent PRs targeting the frozen trunk.
- A large Issue cannot be split without breaking compatibility at intermediate layers: keep one PR (or return `blocked` when a user-required split cannot be satisfied safely).
