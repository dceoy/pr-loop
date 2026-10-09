"""Regression checks for the portable pr-review and one-action workflow."""

from pathlib import Path
import re
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
