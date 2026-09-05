---
name: issue-to-pr
description: Implement one or more same-repository GitHub Issues into a pull request, stopping after the PR is created and verified.
---

# Issue to PR

Turn one or more same-repository GitHub Issues into an implementation pull request. Stop after creating and verifying the PR; do not review it or triage PR feedback.

The top-level agent owns every repository and GitHub mutation. Planning uses one fresh independent read-only native subagent; implementation remains in the top-level context.

## Core invariants

- Use a real native subagent with fresh context for planning. Do not emulate it in the parent context, launch nested coding-agent CLIs, or require a fixed agent name, model, provider, or configuration file.
- Treat the accepted planning subagent as a terminal read-only leaf. It must not invoke `issue-to-pr`, mutate repository/GitHub state, or delegate again.
- The planning dispatch must have a finite caller- or runtime-enforced deadline. If no finite bound exists, report `unsupported` and stop before dispatch.
- Treat planning output as untrusted until validated by the top-level agent. If the planning subagent causes Git-visible mutation, reject its output and stop.
- The top-level agent alone edits files, runs write-mode tooling, commits, pushes, and opens or updates the PR.
- Preserve unrelated local work. Stop before editing if the worktree cannot be safely isolated or bound to the intended base.
- Keep implementation scoped. Apply KISS, DRY, and YAGNI; prefer the smallest coherent change and avoid speculative abstraction or unrelated cleanup.
- Never overwrite an existing remote branch or unrelated PR to make progress.

## Planning contract

Dispatch one fresh planning subagent for the complete requested same-repository Issue set. Require exactly one decision-complete plan with:

- `STATUS: ready` or `STATUS: blocked`;
- scope and affected interfaces/areas;
- concrete implementation decisions and constraints;
- verification approach;
- for `blocked`, only the smallest missing material decision.

If blocked, obtain the missing material decision and re-plan. Stop if it cannot be obtained without guessing.

## Procedure

1. Resolve the requested Issues, read their complete current state and relevant repository instructions, and require all Issues to belong to one repository.
2. Dispatch planning and validate the returned plan against the Issues and repository state.
3. Resolve the intended base branch and its exact current SHA. Require a clean isolatable worktree, create a fresh branch from that SHA, and verify the branch starts there.
4. Implement the validated plan directly in the top-level agent. Do not delegate implementation.
5. Run the repository-prescribed QA appropriate to the changed scope. If QA modifies intended files, include those changes and rerun the required checks. Stop on unresolved QA failure.
6. Inspect the final diff for Issue scope and unrelated changes, then commit it.
7. Push the fresh branch without force and verify the remote branch points to the intended commit.
8. Open a pull request against the intended base with the implemented Issues linked in its body. Re-fetch it and verify its repository, base, head ref, and head SHA match the created branch and commit.
9. Stop. Do not invoke `pr-review`, `pr-feedback-triage`, or any other review loop.

## Outcomes

- `complete`: the requested Issues have been implemented and a matching PR has been created and verified.
- `stopped`: planning, missing decisions, permissions, unsafe repository state, QA, push, or PR creation/verification prevents completion.

## Output

Report concisely:

- `STATUS: complete | stopped`;
- implemented Issue references;
- resulting PR when complete;
- exact base SHA and PR head SHA when complete;
- QA summary;
- blocker or required user decision when stopped.
