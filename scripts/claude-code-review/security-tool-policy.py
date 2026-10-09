import glob
import json
import os
from pathlib import Path
import sys

# Exact commands used by the published and bundled security-review prompts.
COMMANDS = {
    "git status": "git status",
    "git diff --name-only origin/HEAD...":
        "git diff --no-ext-diff --no-textconv --name-only origin/HEAD...",
    "git log --no-decorate origin/HEAD...":
        "git log --no-decorate origin/HEAD...",
    "git diff --merge-base origin/HEAD":
        "git diff --no-ext-diff --no-textconv --merge-base origin/HEAD",
    "git diff origin/HEAD...":
        "git diff --no-ext-diff --no-textconv origin/HEAD...",
}
COMMANDS.update({value: value for value in tuple(COMMANDS.values())})


def decision(event):
    tool = event.get("tool_name")
    data = event.get("tool_input")
    if not isinstance(data, dict):
        return {"permissionDecision": "deny"}
    if tool in {"Read", "Glob", "Grep"}:
        root = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
        value = data.get("file_path") if tool == "Read" else data.get("path", ".")
        if not isinstance(value, str):
            return {"permissionDecision": "deny"}
        path = Path(value).expanduser()
        cwd = Path(event.get("cwd", str(root))).resolve()
        target = (path if path.is_absolute() else cwd / path).resolve()
        diff = Path(os.environ["SECURITY_DIFF_FILE"]).resolve()
        listing = diff.with_name("security-review-files.txt")
        if tool == "Read" and target in {diff, listing}:
            return {"permissionDecision": "allow"}
        if not target.is_relative_to(root) or ".git" in target.relative_to(root).parts:
            return {"permissionDecision": "deny"}
        # Search tools may follow descendant links; refuse unsafe search trees.
        if tool in {"Glob", "Grep"} and target.is_dir():
            for directory, dirs, files in os.walk(target, followlinks=False):
                for name in dirs + files:
                    entry = Path(directory) / name
                    if entry.is_symlink():
                        resolved = entry.resolve()
                        if (not resolved.is_relative_to(root)
                                or ".git" in resolved.relative_to(root).parts):
                            return {"permissionDecision": "deny"}
        if tool == "Glob":
            pattern = data.get("pattern")
            if (not isinstance(pattern, str) or Path(pattern).is_absolute()
                    or ".." in pattern or ".git" in Path(pattern).parts
                    or any(char in pattern for char in "~\\{}")):
                return {"permissionDecision": "deny"}
            # Hidden metadata can also be selected by wildcard patterns.
            for match in glob.iglob(pattern, root_dir=target, recursive=True,
                                    include_hidden=True):
                matched = target / match
                resolved = matched.resolve()
                if (".git" in matched.relative_to(root).parts
                        or not resolved.is_relative_to(root)
                        or ".git" in resolved.relative_to(root).parts):
                    return {"permissionDecision": "deny"}
        return {"permissionDecision": "allow"}
    if tool == "Skill" and data.get("skill") == "security-review" and not data.get("args"):
        return {"permissionDecision": "allow"}
    if tool == "Bash":
        if (set(data) <= {"command", "description", "timeout", "run_in_background"}
                and data.get("command") in COMMANDS
                and data.get("run_in_background", False) is False):
            return {"permissionDecision": "allow", "updatedInput": {
                **data, "command": COMMANDS[data["command"]], "run_in_background": False,
            }}
    if tool in {"Agent", "Task"}:
        if (set(data) <= {"description", "prompt", "subagent_type", "model",
                         "run_in_background", "max_turns", "effort"}
                and data.get("subagent_type") == "security-review-reader"
                and data.get("run_in_background", False) is False):
            return {"permissionDecision": "allow"}
    return {"permissionDecision": "deny"}


try:
    event = json.load(sys.stdin)
    if event.get("hook_event_name") == "SubagentStart":
        with open(os.environ["SECURITY_AGENT_AUDIT_FILE"], "a") as audit:
            audit.write(json.dumps({"id": event.get("agent_id"),
                                    "type": event.get("agent_type")}) + "\n")
        sys.exit(0)
    result = decision(event)
except Exception:
    print("Malformed security tool request", file=sys.stderr)
    sys.exit(2)
result["permissionDecisionReason"] = "Security review permits only bounded read-only tools"
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **result}}))
