import json
import os
from pathlib import Path
import shlex

root = Path(os.environ["RUNNER_TEMP"])
hook = "python3 " + shlex.quote(str(root / "security-tool-policy.py"))
hook_config = [{"matcher": ".*", "hooks": [{"type": "command", "command": hook}]}]
settings = {"hooks": {"PreToolUse": hook_config, "SubagentStart": hook_config}}
(root / "security-subagents.jsonl").write_text("")
reader = {"security-review-reader": {
    "description": "Read-only security analysis and false-positive filtering",
    "prompt": "Analyze the supplied security task using only Read, Glob, and Grep. "
              "Return complete findings and confidence or an explicit no-findings report. "
              "Do not modify files, execute commands, or delegate further.",
    "tools": ["Read", "Glob", "Grep"],
    "permissionMode": "dontAsk",
}}
(root / "security-settings.json").write_text(json.dumps(settings))
(root / "security-agents.json").write_text(json.dumps(reader))
