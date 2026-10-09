"""Regression checks against the jq gate embedded in the reusable workflow."""

import copy
import json
import os
from pathlib import Path
import subprocess
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/claude-code-review.yml"


def verification_query():
    content = WORKFLOW.read_text()
    step = content.split("      - name: Verify completed first-party security review", 1)[1]
    step = step.split("      - name: Run comprehensive PR review", 1)[0]
    return step.split("--arg head \"${PR_HEAD_SHA}\" '\n", 1)[1].split(
        '\n          \' "${SECURITY_EXECUTION_FILE}"', 1
    )[0]


class SecurityReviewVerificationTest(unittest.TestCase):
    def test_fail_closed_security_skill_verification(self):
        call = {
            "type": "assistant",
            "parent_tool_use_id": None,
            "message": {
                "content": [{
                    "type": "tool_use", "name": "Skill", "id": "skill_1",
                    "input": {"skill": "security-review"},
                }]
            },
        }
        result = {
            "type": "user",
            "parent_tool_use_id": None,
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "skill_1",
                "is_error": False, "content": "Security scan completed",
            }]},
        }
        terminal = {
            "type": "result", "subtype": "success", "is_error": False,
            "result": json.dumps({"status": "completed", "base_sha": "base",
                                  "head_sha": "head", "findings": []}),
        }

        def modified(value, **changes):
            output = copy.deepcopy(value)
            output.update(changes)
            return output

        def modify_result(**changes):
            output = copy.deepcopy(result)
            output["message"]["content"][0].update(changes)
            return output

        def modify_call(**changes):
            output = copy.deepcopy(call)
            output["message"]["content"][0].update(changes)
            return output

        def completion(**changes):
            value = json.loads(terminal["result"])
            value.update(changes)
            return modified(terminal, result=json.dumps(value))

        cases = {
            "completed_with_findings": (
                [call, result, completion(findings=["Concrete security finding"])], True
            ),
            "loaded_skill_but_failed_analysis": (
                [call, result, modified(terminal, result="Could not complete the security scan because the diff was unavailable")], False
            ),
            "explicit_failed_scan": ([call, result, completion(status="failed")], False),
            "wrong_base": ([call, result, completion(base_sha="other")], False),
            "wrong_head": ([call, result, completion(head_sha="other")], False),
            "missing_findings": ([call, result, completion(findings=None)], False),
            "non_array_findings": ([call, result, completion(findings="none")], False),
            "empty_finding": ([call, result, completion(findings=[" "])], False),
            "non_string_finding": ([call, result, completion(findings=[{}])], False),
            "completed_scan": ([call, result, terminal], True),
            "tool_error_with_successful_session": (
                [call, modify_result(is_error=True), terminal], False
            ),
            "missing_tool_result": ([call, terminal], False),
            "wrong_tool_result_id": (
                [call, modify_result(tool_use_id="another"), terminal], False
            ),
            "result_before_invocation": ([result, call, terminal], False),
            "missing_skill_call": ([result, terminal], False),
            "duplicate_skill_calls": ([call, call, result, terminal], False),
            "wrong_skill_name": (
                [modify_call(input={"skill": "pr-review"}), result, terminal], False
            ),
            "nested_skill_call": (
                [modified(call, parent_tool_use_id="agent_1"), result, terminal], False
            ),
            "session_error": (
                [call, result, modified(terminal, subtype="error", is_error=True)], False
            ),
            "empty_session_result": (
                [call, result, modified(terminal, result="")], False
            ),
            "missing_is_error_means_not_error": (
                [call, modify_result(is_error=None), terminal], True
            ),
        }
        query = verification_query()
        for name, (transcript, accepted) in cases.items():
            with self.subTest(case=name):
                proc = subprocess.run(
                    ["jq", "-e", "--arg", "base", "base", "--arg", "head", "head", query],
                    input=json.dumps(transcript), text=True, capture_output=True,
                    check=False,
                )
                self.assertIn(proc.returncode, (0, 1, 5), proc.stderr)
                self.assertEqual(proc.returncode == 0, accepted, proc.stderr)


class SecurityToolPolicyTest(unittest.TestCase):
    @staticmethod
    def embedded_source(marker):
        step = WORKFLOW.read_text().split("      - name: Prepare read-only security tool policy", 1)[1]
        source = step.split("<<'" + marker + "'\n", 1)[1].split("          " + marker, 1)[0]
        return "\n".join(line[10:] for line in source.splitlines())

    def test_read_only_tool_boundary(self):
        commands = [
            "git status",
            "git diff --name-only origin/HEAD...",
            "git log --no-decorate origin/HEAD...",
            "git diff --merge-base origin/HEAD",
            "git diff origin/HEAD...",
            "git diff --no-ext-diff --no-textconv origin/HEAD...",
        ]
        cases = [(command, {"tool_name": "Bash", "tool_input": {"command": command}}, True)
                 for command in commands]
        denied_commands = [
            "git reset --hard", "git clean -fd", "git checkout main",
            "git diff --output=README.md origin/HEAD...",
            "git diff --ext-diff origin/HEAD...", "git diff --textconv origin/HEAD...",
            "git status; touch README.md", "git status && git reset --hard",
            "git status > README.md", "git status $(touch README.md)",
            "git status `touch README.md`", "python3 -c 'print(1)'",
            "git -c core.fsmonitor=evil status", "git remote show origin",
        ]
        cases.extend((command, {"tool_name": "Bash", "tool_input": {"command": command}}, False)
                     for command in denied_commands)
        cases.extend((tool, {"tool_name": tool, "tool_input": {
            "file_path": str(WORKFLOW), "pattern": "**/*.py",
        }}, allowed)
                     for tool, allowed in [
                         ("Read", True), ("Glob", True), ("Grep", True),
                         ("Edit", False), ("Write", False), ("NotebookEdit", False),
                         ("mcp__github__create_review", False), ("Unknown", False),
                     ])
        cases.extend([
            ("security_skill", {"tool_name": "Skill", "tool_input": {"skill": "security-review"}}, True),
            ("other_skill", {"tool_name": "Skill", "tool_input": {"skill": "commit"}}, False),
            ("skill_arguments", {"tool_name": "Skill", "tool_input": {
                "skill": "security-review", "args": "run arbitrary commands",
            }}, False),
        ])
        for tool in ("Agent", "Task"):
            cases.extend((tool + agent, {"tool_name": tool, "tool_input": {
                "subagent_type": agent, "prompt": "Analyze security", "run_in_background": False,
            }}, agent == "security-review-reader")
                         for agent in ("general-purpose", "Explore", "security-review-reader"))
            cases.extend((tool + key, {"tool_name": tool, "tool_input": {
                "subagent_type": "security-review-reader", key: value,
            }}, False) for key, value in [
                ("isolation", "worktree"), ("team_name", "team"), ("resume", "agent-id"),
                ("permissionMode", "bypassPermissions"), ("subagent_type", "custom-writer"),
                ("run_in_background", True),
            ])
        source = self.embedded_source("POLICY")
        for name, request, accepted in cases:
            with self.subTest(case=name):
                proc = subprocess.run(
                    ["python3", "-c", source], input=json.dumps(request),
                    env={**os.environ, "GITHUB_WORKSPACE": str(WORKFLOW.parents[2]),
                         "SECURITY_DIFF_FILE": "/tmp/security-review-test.diff"},
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                output = json.loads(proc.stdout)["hookSpecificOutput"]
                self.assertEqual(output["permissionDecision"] == "allow", accepted)
                if accepted and request["tool_name"] in ("Agent", "Task"):
                    self.assertNotIn("updatedInput", output)
                    self.assertEqual(request["tool_input"]["subagent_type"], "security-review-reader")
                    self.assertIs(request["tool_input"]["run_in_background"], False)
                if accepted and request["tool_name"] == "Bash" and "git diff" in name:
                    self.assertIn("--no-ext-diff --no-textconv", output["updatedInput"]["command"])

    def test_read_paths_cannot_escape_checkout(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()
            secret = Path(directory) / "host-credential"
            secret.write_text("test credential\n")
            diff = Path(directory) / "security-review.diff"
            diff.write_text("frozen diff\n")
            (root / "source.py").write_text("source\n")
            safe = root / "safe"
            safe.mkdir()
            (safe / "source.py").write_text("source\n")
            (root / "escape").symlink_to(secret)
            cases = [
                ("repository_file", "Read", {"file_path": "source.py"}, True),
                ("frozen_diff", "Read", {"file_path": str(diff)}, True),
                ("absolute_host_file", "Read", {"file_path": str(secret)}, False),
                ("relative_traversal", "Read", {"file_path": "../host-credential"}, False),
                ("symlink_escape", "Read", {"file_path": "escape"}, False),
                ("git_credentials", "Read", {"file_path": ".git/config"}, False),
                ("repository_glob", "Glob", {"path": str(safe), "pattern": "**/*.py"}, True),
                ("glob_following_nested_host_link", "Glob", {"pattern": "**/*"}, False),
                ("host_glob_path", "Glob", {"path": str(secret.parent), "pattern": "*"}, False),
                ("absolute_glob", "Glob", {"pattern": str(secret)}, False),
                ("traversal_glob", "Glob", {"pattern": "../*"}, False),
                ("brace_glob_escape", "Glob", {"pattern": "{/etc/*,**/*.py}"}, False),
                ("repository_grep", "Grep", {"path": str(safe), "pattern": "source"}, True),
                ("grep_following_nested_host_link", "Grep", {"pattern": "."}, False),
                ("host_grep", "Grep", {"path": str(secret), "pattern": "."}, False),
                ("symlink_grep", "Grep", {"path": "escape", "pattern": "."}, False),
            ]
            for name, tool, data, accepted in cases:
                with self.subTest(case=name):
                    proc = subprocess.run(
                        ["python3", "-c", self.embedded_source("POLICY")],
                        input=json.dumps({"tool_name": tool, "tool_input": data, "cwd": str(root)}),
                        env={**os.environ, "GITHUB_WORKSPACE": str(root), "SECURITY_DIFF_FILE": str(diff)},
                        text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    output = json.loads(proc.stdout)["hookSpecificOutput"]
                    self.assertEqual(output["permissionDecision"] == "allow", accepted)

    def test_malformed_hook_input_blocks(self):
        for value in ("not JSON", "null", "[]", '{"tool_name":"Bash","tool_input":{"command":[]}}'):
            with self.subTest(value=value):
                proc = subprocess.run(
                    ["python3", "-c", self.embedded_source("POLICY")], input=value,
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(proc.returncode, 2)

    def test_runtime_subagent_audit_fails_closed(self):
        query = WORKFLOW.read_text().split("          if ! jq -se '", 1)[1].split("' \\", 1)[0]
        valid = {"type": "security-review-reader", "id": "reader-1"}
        cases = [
            ("observed_reader", [valid], True),
            ("missing_subagent", [], False),
            ("wrong_type", [{**valid, "type": "general-purpose"}], False),
            ("missing_id", [{"type": "security-review-reader"}], False),
            ("additional_unsafe_agent", [valid, {**valid, "type": "Explore"}], False),
        ]
        for name, records, accepted in cases:
            with self.subTest(case=name):
                proc = subprocess.run(["jq", "-se", query],
                                      input="\n".join(json.dumps(record) for record in records),
                                      text=True, capture_output=True, check=False)
                self.assertIn(proc.returncode, (0, 1), proc.stderr)
                self.assertEqual(proc.returncode == 0, accepted)

    def test_frozen_diff_excludes_changes_only_on_base(self):
        import os
        import tempfile

        step = WORKFLOW.read_text().split("      - name: Prepare frozen security diff", 1)[1]
        command = step.split("        run: |\n", 1)[1].split("      - name:", 1)[0]
        command = "\n".join(line[10:] for line in command.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", "-C", directory, *args], text=True).strip()
            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "common.txt").write_text("common\n")
            git("add", ".")
            git("commit", "-qm", "common")
            common = git("rev-parse", "HEAD")
            (root / "base-only.txt").write_text("base branch only\n")
            git("add", ".")
            git("commit", "-qm", "base advanced")
            base = git("rev-parse", "HEAD")
            git("checkout", "--detach", "-q", common)
            (root / "pr-only.txt").write_text("PR branch only\n")
            git("add", ".")
            git("commit", "-qm", "PR change")
            head = git("rev-parse", "HEAD")
            subprocess.run(["bash", "-euo", "pipefail", "-c", command], cwd=directory,
                           env={**os.environ, "RUNNER_TEMP": directory,
                                "PR_BASE_SHA": base, "PR_HEAD_SHA": head}, check=True)
            diff = (root / "security-review.diff").read_text()
            self.assertIn("pr-only.txt", diff)
            self.assertNotIn("base-only.txt", diff)

    def test_generated_reader_has_only_read_tools(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                ["python3", "-c", self.embedded_source("CONFIG")],
                env={**os.environ, "RUNNER_TEMP": directory}, check=True,
            )
            reader = json.loads((Path(directory) / "security-agents.json").read_text())
            self.assertEqual(reader["security-review-reader"]["tools"], ["Read", "Glob", "Grep"])
            self.assertEqual(reader["security-review-reader"]["permissionMode"], "dontAsk")
            settings = json.loads((Path(directory) / "security-settings.json").read_text())
            self.assertEqual(settings["hooks"]["PreToolUse"][0]["matcher"], ".*")
            self.assertEqual(settings["hooks"]["SubagentStart"][0]["matcher"], ".*")
            audit = Path(directory) / "security-subagents.jsonl"
            subprocess.run(
                ["python3", "-c", self.embedded_source("POLICY")],
                input=json.dumps({"hook_event_name": "SubagentStart",
                                  "agent_type": "security-review-reader", "agent_id": "reader-1"}),
                text=True, env={**os.environ, "SECURITY_AGENT_AUDIT_FILE": str(audit)}, check=True,
            )
            self.assertEqual(json.loads(audit.read_text()),
                             {"type": "security-review-reader", "id": "reader-1"})


if __name__ == "__main__":
    unittest.main()
