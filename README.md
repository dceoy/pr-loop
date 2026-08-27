# pr-loop

`pr-loop` is an agent skill for carrying GitHub work through implementation, pull-request review, fixes, and re-review until no actionable feedback remains.

It is a native-subagent rewrite of the former `oracle-pr-loop` workflow. It has no Oracle, browser automation, ChatGPT GitHub-app, fixed-model, or coding-agent CLI dependency.

## Agent routing

For every advisory phase, the top-level agent uses the active runtime's native subagent mechanism:

1. Prefer an eligible user-defined agent whose declared purpose matches the role.
2. If none is available, use a suitable built-in agent.
3. If the runtime exposes no independent subagent capability, stop rather than silently doing the advisory work in the main context.

Subagents are read-only advisors. The top-level agent alone edits files, runs write-mode tools, commits, pushes, opens or updates pull requests, posts review feedback, and resolves threads.

## Workflow

- **Issue-started work:** planning subagent → main-agent implementation/QA → pull request → review loop.
- **Existing pull request:** independent review subagents → feedback-analysis subagent → main-agent fixes/QA → re-review on the new head.
- Finish only when the exact current head has been reviewed and no actionable feedback or unresolved blocking reviewer state remains.

The review phase uses independent lenses for correctness, tests/docs, and security/performance. User-defined agents may satisfy these roles when appropriate; otherwise built-in agents are used.

## Discovery

- Codex-compatible agent runtimes discover the skill at `.agents/skills/pr-loop`.
- Claude Code discovers the skill at `.claude/skills/pr-loop`.
- Both are local symlinks to [`skills/pr-loop`](skills/pr-loop).

## Requirements

- Git and authenticated GitHub access (`gh` or an equivalent integration).
- A coding-agent runtime with a native independent-subagent mechanism.

## Usage

Ask the host agent to implement one or more same-repository Issues through a reviewed pull request, or to review/fix an existing pull request until it is clean.

See [`skills/pr-loop/SKILL.md`](skills/pr-loop/SKILL.md) for the normative workflow.
