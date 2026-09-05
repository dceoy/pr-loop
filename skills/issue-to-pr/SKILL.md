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
- Bind planning and implementation to the same exact repository base SHA. Repository evidence supplied to planning must come from that frozen revision rather than a mutable working tree or moving branch tip.
- Treat planning output as untrusted until validated by the top-level agent. If the planning subagent causes Git-visible mutation, reject its output and stop.
- The top-level agent alone edits files, runs write-mode tooling, commits, pushes, and opens or updates the PR.
- Preserve unrelated local work. Stop before editing if the worktree cannot be safely isolated or bound to the intended base.
- Keep implementation scoped. Apply KISS, DRY, and YAGNI; prefer the smallest coherent change and avoid speculative abstraction or unrelated cleanup.
- Publish the fresh remote branch with an atomic create-only guard that requires the destination ref to be absent (for Git, an explicit empty-expected-value `--force-with-lease=<ref>:` or equivalent API semantics). Never update an existing remote branch or unrelated PR; stop if the ref exists or is created concurrently, and verify the created ref points to the intended commit.

## Planning contract

Snapshot the complete requested same-repository Issue set, applicable repository instructions, intended base branch, and its exact current SHA before planning. Dispatch one fresh planning subagent against that frozen repository revision and Issue snapshot. Require exactly one decision-complete plan with:

- `STATUS: ready` or `STATUS: blocked`;
- scope and affected interfaces/areas;
- concrete implementation decisions and constraints;
- verification approach;
- for `blocked`, only the smallest missing material decision.

If a blocked plan receives the missing decision, or the Issue requirements materially change before implementation, refresh the Issue/base snapshot and plan again rather than mixing evidence from different snapshots.

## Flow

```mermaid
flowchart TD
  A[Resolve Issues, instructions, base branch + exact SHA] --> B{All Issues in one repository?}
  B -->|no| X[Stopped]
  B -->|yes| C[Dispatch planner on frozen repository + Issue snapshot]
  C --> D{Planning output valid?}
  D -->|no| X
  D -->|yes| E{Plan status}
  E -->|blocked| F{Missing material decision obtained?}
  F -->|yes, refresh snapshot| C
  F -->|no| X
  E -->|ready| G[Create verified isolated fresh branch from planned base SHA]
  G --> H[Implement validated plan in the top-level agent]
  H --> I[Run prescribed scoped QA; include intended QA changes and rerun]
  I --> J{QA passes?}
  J -->|no| Q{Failure fixable within validated scope?}
  Q -->|yes| H
  Q -->|no| X
  J -->|yes| K[Inspect final scoped diff and commit]
  K --> L[Atomically create remote branch and verify its commit]
  L --> M{Published safely?}
  M -->|no| X
  M -->|yes| N[Open PR linking implemented Issues and re-fetch it]
  N --> O{Repository, base, head ref, and head SHA match?}
  O -->|no| X
  O -->|yes| P[Complete]
```

## Outcomes

- `complete`: the requested Issues have been implemented from the exact planned base and a matching PR has been created and verified.
- `stopped`: planning, missing decisions, permissions, unsafe repository state, unresolved QA, push, or PR creation/verification prevents completion.

## Output

Report concisely:

- `STATUS: complete | stopped`;
- implemented Issue references;
- resulting PR when complete;
- exact planned base SHA and PR head SHA when complete;
- QA summary;
- blocker or required user decision when stopped.
