"""Regression checks against the jq gate embedded in the reusable workflow."""

import copy
import json
from pathlib import Path
import subprocess
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/claude-code-review.yml"


def verification_query():
    content = WORKFLOW.read_text()
    step = content.split("      - name: Verify completed first-party security review", 1)[1]
    step = step.split("      - name: Run comprehensive PR review", 1)[0]
    return step.split("          if ! jq -e '\n", 1)[1].split(
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
            "result": "Security Review: no findings",
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

        cases = {
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
                    ["jq", "-e", query],
                    input=json.dumps(transcript), text=True, capture_output=True,
                    check=False,
                )
                self.assertIn(proc.returncode, (0, 1), proc.stderr)
                self.assertEqual(proc.returncode == 0, accepted, proc.stderr)


if __name__ == "__main__":
    unittest.main()
