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


if __name__ == "__main__":
    unittest.main()
