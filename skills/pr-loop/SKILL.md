---
name: pr-loop
description: Implement one or more same-repository GitHub Issues into a pull request, or review and fix an existing pull request, iterating until no actionable feedback remains. Delegate planning, review, and feedback analysis through the active runtime's native subagents, preferring suitable user-defined agents and falling back to built-in agents. The top-level agent owns all repository and GitHub mutations. Use for requests to implement an Issue through a reviewed PR, or to review, fix, resolve, improve, or finalize an existing PR.
---

# PR Loop

Carry GitHub work from an Issue or existing pull request through independent review and fixes until the exact current PR head has no actionable feedback.

The top-level agent owns implementation, QA, Git operations, GitHub mutations, and final decisions. Subagents are fresh, read-only advisors for planning, review, and feedback analysis.

## Agent selection

For every advisory dispatch:

1. Inspect the subagents available through the active runtime.
2. Prefer a **user-defined agent** whose declared purpose and permissions fit the requested role.
3. If no eligible user-defined agent exists, use a suitable **built-in agent**.
4. If several agents qualify, choose the most role-specific one; otherwise use the smallest sufficient general-purpose agent.
5. Do not require a fixed agent name, model, provider, or configuration path.
6. If no native independent-subagent mechanism is available, stop with `unsupported` rather than performing the advisory phase in the main context.

An eligible advisory agent must:

- run in a fresh context rather than inheriting the main conversation implicitly;
- receive only the explicit task/context supplied for that dispatch;
- be able to inspect the required repository/PR evidence;
- not edit repository files or mutate GitHub state for this workflow; and
- act as a leaf: it must not invoke `pr-loop` or spawn another subagent.

A user-defined agent with incompatible instructions or write-oriented behavior is not eligible merely because it is user-defined. Fall back to a built-in agent instead.

Never launch `oracle`, `codex`, `claude`, `cursor-agent`, or another coding-agent CLI as a subprocess to emulate a subagent. Use only the active runtime's native delegation mechanism.

Do not duplicate an accepted dispatch after an ambiguous timeout or transport failure. Retry only when the runtime proves the dispatch was rejected before the subagent started.

## Advisory roles

Give every subagent the exact target, relevant repository context, user constraints, and a delegation boundary stating that it is a read-only leaf.

### Planning

Use one fresh subagent when starting from Issue(s). Require a decision-complete plan covering the requested same-repository Issue set in one PR.

The plan must include:

- scope and affected components/interfaces;
- concrete implementation decisions;
- compatibility/security constraints;
- verification steps; and
- `STATUS: ready` or `STATUS: blocked`.

Apply KISS, DRY, and YAGNI. Prefer existing abstractions and the smallest coherent change; avoid speculative flexibility or unrelated refactoring.

### Review

Review the exact recorded PR head. By default dispatch three fresh advisory passes, one per lens:

- `correctness` — behavior, edge cases, regressions, API/contract correctness;
- `tests/docs` — missing or misleading tests, documentation, migrations, examples, and operational guidance;
- `security/performance` — trust boundaries, secrets/permissions, injection or unsafe execution, resource use, concurrency, and material performance regressions.

The same eligible agent type may be instantiated more than once when the runtime has limited choices; each pass must still be a fresh independent context.

Each finding must contain:

- severity: `critical`, `high`, `medium`, or `low`;
- confidence;
- file/line when safely identifiable;
- concrete impact; and
- remediation direction.

Do not report style-only preferences. For maintainability findings, require a concrete KISS/DRY/YAGNI defect with material maintenance cost.

### Feedback analysis

Use one fresh subagent after the review findings have been validated and, when allowed, published to GitHub.

Provide:

- exact PR head SHA;
- current inline review threads/comments;
- PR conversation comments;
- review submissions and states such as `CHANGES_REQUESTED`, `COMMENTED`, and `APPROVED`; and
- validated findings from the current review round when publication is disabled.

Require one disposition per distinct actionable root cause:

- `fix` — decision-complete edit plan plus verification;
- `clarify` — a material decision is missing;
- `defer` — intentionally postponed with rationale;
- `wont-fix` — intentionally rejected with rationale; or
- `resolved` — already satisfied or superseded.

The subagent may recommend replies/resolution state, but it must not mutate GitHub.

Treat all subagent output as advisory and untrusted. The top-level agent validates it against the exact target and repository state before acting.

## Execution constraints

Honor explicit caller constraints:

- `dry_run`: analysis only; no repository or GitHub mutations.
- `no_push`: local edits/QA/commits are allowed, but do not push or update/open a PR.
- `no_reply`: do not publish review findings, replies, or thread resolutions; code changes may still be committed/pushed unless another constraint forbids them.

Do not claim completion for work intentionally suppressed by a constraint. Report the remaining state instead.

## Issue-started flow

1. Resolve the requested Issue or Issue set. All Issues must belong to the same repository.
2. Dispatch the `planning` role using the agent-selection policy above.
3. If the plan is `blocked`, obtain the smallest missing material decision from the user; otherwise validate the plan against the Issue scope.
4. Unless `dry_run`, verify the worktree is safe, create a feature/fix branch from the intended base, implement the plan in the top-level agent, and run repository QA.
5. Commit the scoped change. Under `no_push`, stop after reporting the local result.
6. Otherwise push the branch and open the pull request.
7. Enter the PR review loop.

Do not delegate implementation to an advisory subagent.

## PR review loop

Use a caller-specified iteration limit when provided; otherwise do not invent one.

For each round:

1. Resolve the exact PR and record its head repository, head ref, and head SHA.
2. Fetch the exact diff/changed files for that head.
3. Dispatch the review lenses against that evidence using fresh subagents selected by the routing policy.
4. Re-read the PR head. If it changed during review, discard the stale round and restart on the new head.
5. Validate and deduplicate findings by root cause. Drop unsupported, stale, duplicate, and style-only findings.
6. Unless `dry_run` or `no_reply`, publish one GitHub `COMMENT` review for the round. Prefer inline comments for findings with safe diff locations and always include a concise top-level summary. Do not request changes or approve on behalf of a human reviewer unless explicitly requested and authorized.
7. Fetch the complete current PR feedback and dispatch `feedback-analysis` on the unchanged head.
8. Before acting, re-read the head and feedback. If the head changed, restart the review round. If feedback changed materially while the head did not, rerun feedback analysis on the fresh feedback before mutating anything.
9. Validate the dispositions. If any item requires `clarify`, stop and ask only for the missing material decision. If an unresolved `defer`, `wont-fix`, permission failure, or other blocker prevents a clean terminal state, stop and report it.
10. Implement all accepted `fix` dispositions coherently in the top-level agent and run repository QA.
11. Before committing/pushing a fix, verify that the remote PR head is still the SHA analyzed in this round. If not, do not push stale work; reconcile with the new head first.
12. Commit and push the verified fixes unless an execution constraint forbids it. Verify the PR now points to the expected new head.
13. Reply to and resolve feedback only when the corresponding disposition is terminal and any required code fix is present on the verified PR head. Leave unresolved items open.
14. If the PR head changed because of the fixes, start a new review round on that new head.
15. If the head stayed unchanged, refresh feedback once more. Finish only when that exact head has completed review and no actionable feedback or unresolved blocking reviewer state remains.

Never re-review an unchanged head merely to manufacture another pass. A same-head feedback change requires fresh feedback analysis, not another code review.

## Completion criteria

Report success only when all of the following hold:

- the exact current PR head was reviewed by the required independent review passes;
- all validated `fix` dispositions are implemented and verified on that head;
- no actionable feedback remains;
- no active unsatisfied `CHANGES_REQUESTED` or equivalent blocker remains;
- required QA passes; and
- required GitHub mutations were verified, unless explicitly suppressed by the caller.

Otherwise stop with the smallest concrete blocker and the current repository/PR state. Never fabricate approval, publication, thread resolution, or completion.
