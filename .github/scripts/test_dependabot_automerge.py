"""Exercise the actual automerge shell with GitHub API calls replaced by fixtures."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).parents[1] / "workflows" / "dependabot-automerge.yml"
HEAD = "a" * 40
BASE = "b" * 40
REQUIRED = ("ci-gate", "workflow-security-gate",
            "security / codeql (rust)", "security / codeql (actions)")


class AutomergeTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "info": {
                "author": {"login": "app/dependabot"},
                "isCrossRepository": False,
                "headRefOid": HEAD,
                "baseRefName": "main",
                "isDraft": False,
                "state": "OPEN",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [
                    {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
                    for name in REQUIRED
                ],
            },
            "base": BASE,
            "appsec": [{"headSha": HEAD, "status": "completed", "conclusion": "success"}],
            "comparison": {"behind_by": 0, "merge_base_commit": {"sha": BASE}},
        }

    def run_workflow(self, case=None, associated_pr=24):
        case = self.case if case is None else case
        script = textwrap.dedent(WORKFLOW.read_text().split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            (directory / "case.json").write_text(json.dumps(case))
            (directory / "event.json").write_text(json.dumps({
                "workflow_run": {"pull_requests": (
                    [{"number": associated_pr}] if associated_pr is not None else []
                )},
            }))
            fake_gh = directory / "gh"
            fake_gh.write_text(f"#!{sys.executable}\n" + textwrap.dedent('''\
                import json
                import os
                from pathlib import Path
                import sys

                root = Path(os.environ["TEST_DIRECTORY"])
                case = json.loads((root / "case.json").read_text())
                args = sys.argv[1:]
                with (root / "calls.jsonl").open("a") as calls:
                    calls.write(json.dumps(args) + "\\n")
                if args[:2] == ["pr", "view"]:
                    print(json.dumps(case["info"]))
                elif args[:2] == ["pr", "merge"]:
                    sys.exit(case.get("merge_exit", 0))
                elif args == ["run", "list", "--repo", "test/repo", "--workflow", "appsec.yml", "--event", "pull_request", "--commit", os.environ["CHECKED_SHA"], "--limit", "1", "--json", "headSha,status,conclusion"]:
                    print(json.dumps(case["appsec"]))
                elif args == ["api", "repos/test/repo/git/ref/heads/main", "--jq", ".object.sha"]:
                    print(case["base"])
                elif args == ["api", "repos/test/repo/compare/" + case["base"] + "..." + os.environ["CHECKED_SHA"]]:
                    if case.get("compare_error"):
                        sys.exit(1)
                    print(json.dumps(case["comparison"]))
                else:
                    raise SystemExit("Unexpected GitHub call: " + repr(args))
            '''))
            fake_gh.chmod(0o700)
            result = subprocess.run(
                ["bash", "-c", script],
                env={**os.environ, "PATH": f"{directory}:{os.environ['PATH']}",
                     "TEST_DIRECTORY": str(directory), "REPO": "test/repo",
                     "CHECKED_SHA": HEAD, "GITHUB_EVENT_PATH": str(directory / "event.json")},
                text=True, capture_output=True, check=False,
            )
            calls_path = directory / "calls.jsonl"
            calls = ([json.loads(line) for line in calls_path.read_text().splitlines()]
                     if calls_path.exists() else [])
        return result, calls

    def assert_waits(self, case=None):
        result, calls = self.run_workflow(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[:2] == ["pr", "merge"] for call in calls), calls)
        return result, calls

    def test_current_base_and_successful_checks_merge_only_checked_head(self):
        result, calls = self.run_workflow()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1], ["pr", "merge", "24", "--repo", "test/repo",
                                    "--squash", "--match-head-commit", HEAD])

    def test_stale_branch_waits_for_signed_dependabot_refresh(self):
        self.case["comparison"]["behind_by"] = 1
        result, _ = self.assert_waits()
        self.assertIn("Dependabot must refresh", result.stdout)

    def test_main_advanced_after_pr_lookup_does_not_merge(self):
        self.case["base"] = "c" * 40
        result, _ = self.assert_waits()
        self.assertIn("Dependabot must refresh", result.stdout)

    def test_unknown_or_blocked_native_merge_state_waits(self):
        for state in ["BEHIND", "BLOCKED", "DIRTY", "DRAFT", "UNKNOWN", "UNSTABLE", None]:
            with self.subTest(state=state):
                self.case["info"]["mergeStateStatus"] = state
                self.assert_waits()

    def test_head_moved_since_trigger_does_not_merge(self):
        self.case["info"]["headRefOid"] = "d" * 40
        _, calls = self.assert_waits()
        self.assertEqual(len(calls), 1)

    def test_each_required_check_must_finish_successfully(self):
        for name in REQUIRED:
            for status, conclusion in [
                ("IN_PROGRESS", None), ("QUEUED", None),
                ("COMPLETED", "FAILURE"), ("COMPLETED", "CANCELLED"),
                ("COMPLETED", "NEUTRAL"), ("COMPLETED", "SKIPPED"),
                ("COMPLETED", "TIMED_OUT"), ("COMPLETED", "ACTION_REQUIRED"),
            ]:
                with self.subTest(name=name, status=status, conclusion=conclusion):
                    case = copy.deepcopy(self.case)
                    check = next(check for check in case["info"]["statusCheckRollup"]
                                 if check["name"] == name)
                    check.update(status=status, conclusion=conclusion)
                    self.assert_waits(case)

    def test_missing_analysis_or_gate_does_not_merge(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                case = copy.deepcopy(self.case)
                case["info"]["statusCheckRollup"] = [
                    check for check in case["info"]["statusCheckRollup"] if check["name"] != name
                ]
                self.assert_waits(case)

    def test_old_successful_checks_do_not_hide_latest_appsec_failure(self):
        for status, conclusion in [("queued", None), ("in_progress", None),
                                   ("completed", "failure"), ("completed", "cancelled"),
                                   ("completed", "neutral"), ("completed", "skipped")]:
            with self.subTest(status=status, conclusion=conclusion):
                self.case["appsec"][0].update(status=status, conclusion=conclusion)
                self.assert_waits()

    def test_appsec_from_a_different_commit_does_not_merge(self):
        self.case["appsec"][0]["headSha"] = "e" * 40
        self.assert_waits()

    def test_missing_appsec_run_does_not_merge(self):
        self.case["appsec"] = []
        self.assert_waits()

    def test_ineligible_pr_does_not_merge(self):
        for key, value in [("author", {"login": "contributor"}), ("isCrossRepository", True),
                           ("baseRefName", "other"), ("isDraft", True), ("state", "CLOSED")]:
            with self.subTest(key=key):
                case = copy.deepcopy(self.case)
                case["info"][key] = value
                self.assert_waits(case)

    def test_no_associated_pr_does_not_call_github(self):
        result, calls = self.run_workflow(associated_pr=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_compare_api_failure_is_not_treated_as_readiness(self):
        self.case["compare_error"] = True
        result, calls = self.run_workflow()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call[:2] == ["pr", "merge"] for call in calls), calls)

    def test_native_merge_rejection_is_not_hidden(self):
        self.case["merge_exit"] = 1
        result, _ = self.run_workflow()
        self.assertNotEqual(result.returncode, 0)

    def test_appsec_completion_triggers_readiness_again(self):
        trigger = WORKFLOW.read_text().split("workflows: [", 1)[1].split("]", 1)[0]
        self.assertIn("AppSec", [name.strip() for name in trigger.split(",")])


if __name__ == "__main__":
    unittest.main()
