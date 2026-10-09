"""Regression checks for the portable pr-review and one-action workflow."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/claude-code-review.yml"
SKILL = ROOT / "skills/pr-review/SKILL.md"


class ReviewContractTest(unittest.TestCase):
    def test_single_claude_action(self):
        workflow = WORKFLOW.read_text()
        self.assertEqual(workflow.count("uses: anthropics/claude-code-action@"), 1)
        self.assertEqual(workflow.count("id: claude-review"), 1)
        self.assertNotIn("id: claude-security", workflow)
        self.assertNotIn("security-review-findings.md", workflow)

    def test_review_publication_is_independently_verified(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("Snapshot existing skill reviews", workflow)
        self.assertIn("Verify pr-review invocation and COMMENT publication", workflow)
        self.assertIn('comm -13 "${REVIEW_BASELINE_PATH}" "${current}"', workflow)
        self.assertIn("pr-review-skill-run: ${PR_HEAD_SHA}-", workflow)
        self.assertIn('"${#new_review_ids[@]}" != 1', workflow)
        self.assertIn("stop_hook_active", workflow)
        self.assertIn('"decision": "block"', workflow)
        self.assertIn("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS", workflow)

    def test_stop_hook_retries_and_accepts_matching_publication(self):
        workflow = WORKFLOW.read_text()
        marker = '<<\'PY\'\n'
        embedded = workflow.split(marker, 1)[1].split('\n          PY', 1)[0]
        script = '\n'.join(line[10:] for line in embedded.splitlines())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook = root / "review-stop-hook.py"
            hook.write_text(script + "\n")
            baseline = root / "baseline"
            baseline.write_text("17\n")
            gh = root / "gh"
            gh.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, subprocess, sys\n"
                "head = os.environ['PR_HEAD_SHA']\n"
                "review = {'id': 18, 'state': 'COMMENTED', 'commit_id': head,\n"
                "  'body': '<!-- pr-review-skill -->\\n<!-- pr-review-skill-run: '"
                " + head + '-nonce -->'}\n"
                "data = [review] if os.environ.get('MOCK_REVIEW') == '1' else []\n"
                "query = sys.argv[sys.argv.index('--jq') + 1]\n"
                "proc = subprocess.run(['jq', '-r', query], input=json.dumps(data),\n"
                "                      text=True, capture_output=True)\n"
                "sys.stdout.write(proc.stdout)\n"
                "sys.stderr.write(proc.stderr)\n"
                "sys.exit(proc.returncode)\n"
            )
            gh.chmod(0o755)
            env = {
                **os.environ,
                "PATH": directory + os.pathsep + os.environ.get("PATH", ""),
                "RUNNER_TEMP": directory,
                "PR_HEAD_SHA": "deadbeef",
                "GITHUB_REPOSITORY": "dceoy/pr-loop",
                "PR_NUMBER": "40",
                "REVIEW_BASELINE_PATH": str(baseline),
            }

            def invoke(mock_review=False, active=False):
                return subprocess.run(
                    [sys.executable, str(hook)],
                    input=json.dumps({"stop_hook_active": active}),
                    capture_output=True, text=True,
                    env={**env, "MOCK_REVIEW": "1" if mock_review else "0"},
                    check=True,
                )

            for i in (1, 2):
                result = json.loads(invoke().stdout)
                self.assertEqual(result["decision"], "block")
                self.assertEqual((root / "review-stop-attempts").read_text(), str(i))
            self.assertEqual(invoke().stdout.strip(), "")
            self.assertEqual(invoke(mock_review=True).stdout.strip(), "")
            self.assertEqual(invoke(active=True).stdout.strip(), "")

    def test_security_skill_is_optional_and_provider_agnostic(self):
        skill = SKILL.read_text()
        section = skill.split("## Optional security-review Skill", 1)[1].split(
            "## Review", 1
        )[0]
        self.assertIn("built-in and third-party Skills", section)
        self.assertIn("run pr-review alone", section)
        self.assertIn("fail closed", section)
        self.assertIn("read-only", section)
        for provider in ("Claude Code:", "OpenAI Codex", "Skill(security-review)"):
            self.assertNotIn(provider, section)

    def test_no_repository_mutation_delegated(self):
        skill = SKILL.read_text()
        self.assertIn("Only the parent `pr-review`", skill)
        self.assertIn("Do not install", skill)


if __name__ == "__main__":
    unittest.main()
