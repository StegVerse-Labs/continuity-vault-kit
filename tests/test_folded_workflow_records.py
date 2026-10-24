"""G17 check preservation: every folded workflow's run blocks still run.

tools/tasks/folded/<file>.yml is the verbatim record (non-executing; outside
.github/workflows) of each workflow folded by the G17 consolidation. For every
record classified CONSOLIDATE_INTO_STABLE_DISPATCHER in
control/workflow-surface-registry.json, the run blocks in the record are exactly the
step bodies of its catalog groups, except steps a carried pull request replaced or
moved (recorded with source_pr in the catalog). Contracts that read the records
(tools/test_automation_contracts.py, the *_retirement tests) therefore read what
the dispatcher runs. Stdlib only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDED = ROOT / "tools/tasks/folded"
REGISTRY = ROOT / "control/workflow-surface-registry.json"
CATALOG = ROOT / "tools/tasks/task_catalog.json"
RUN = re.compile(r"^(?P<lead>\s*)(?:- )?(?P<key>run):(?P<rest>.*)$")


def run_blocks(text):
    """The run: values of a workflow file (literal blocks and plain one-liners)."""
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        m = RUN.match(lines[i])
        if not m:
            i += 1
            continue
        key_indent = len(lines[i]) - len(lines[i].lstrip(" ")) + (2 if lines[i].lstrip().startswith("- ") else 0)
        rest = m.group("rest").strip()
        if rest in ("|", "|-", "|+"):
            body, j, indent = [], i + 1, None
            while j < len(lines):
                line = lines[j]
                if line.strip():
                    lead = len(line) - len(line.lstrip(" "))
                    if lead <= key_indent:
                        break
                    indent = lead if indent is None else indent
                body.append(line[indent:] if indent is not None and line.strip() else "")
                j += 1
            while body and not body[-1]:
                body.pop()
            out.append("\n".join(body) + ("" if rest == "|-" else "\n"))
            i = j
        else:
            out.append(rest)
            i += 1
    return out


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FoldedWorkflowRecordTests(unittest.TestCase):
    def setUp(self):
        self.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.rows = {row["workflow"].split("/")[-1]: row for row in self.reg["folded"]}

    def test_every_record_is_a_registered_folded_workflow_pinned_by_sha256(self):
        records = sorted(p.name for p in FOLDED.glob("*.yml"))
        self.assertEqual(records, sorted(self.rows))
        for name in records:
            self.assertEqual(hashlib.sha256((FOLDED / name).read_bytes()).hexdigest(),
                             self.rows[name]["record_sha256"], name)

    def test_consolidated_run_blocks_are_the_catalog_step_bodies(self):
        by_workflow = collections.defaultdict(list)
        for group in self.catalog["groups"]:
            if group["source"].get("source_pr") or "workflow" not in group["source"]:
                continue
            by_workflow[group["source"]["workflow"].split("/")[-1]].append(group)
        for name, row in self.rows.items():
            if row["classification"] != "CONSOLIDATE_INTO_STABLE_DISPATCHER":
                continue
            expected = collections.Counter()
            for group in by_workflow[name]:
                self.assertIn(group["id"], row["catalog_groups"])
                for step in group["steps"]:
                    expected[step.get("replaces_run_sha256") or step["run_sha256"]] += 1
                for removed in group["source"].get("removed_steps", []):
                    expected[removed["run_sha256"]] += 1
            found = collections.Counter(sha(b) for b in run_blocks((FOLDED / name).read_text(encoding="utf-8")))
            self.assertEqual(found, expected, name)

    def test_carried_pull_request_copies_are_pinned_and_are_the_catalog_step_bodies(self):
        """A carried PR's workflow copy (tools/tasks/carried/) is pinned by sha256 in the
        registry, and its run blocks are exactly the step bodies of the group carrying it."""
        groups = {g["id"]: g for g in self.catalog["groups"]}
        carried = [c for c in self.reg["carried_pull_requests"] if c.get("source_copy")]
        self.assertTrue(carried)
        for entry in carried:
            copy = ROOT / entry["source_copy"]
            self.assertEqual(hashlib.sha256(copy.read_bytes()).hexdigest(), entry["source_copy_sha256"], entry["source_copy"])
            group = groups[entry["catalog_group"]]
            self.assertEqual(group["source"].get("source_pr"), entry["pr"])
            found = collections.Counter(sha(b) for b in run_blocks(copy.read_text(encoding="utf-8")))
            self.assertEqual(found, collections.Counter(s["run_sha256"] for s in group["steps"]), entry["catalog_group"])

    def test_pr263_carried_copies_cover_storage_interlock_and_guard(self):
        """#263 @48e8a2b4 (same workflow bytes as #258 @4fdab7af): each carried copy is
        registered, and each carrying group selects on the finish-point test file."""
        entries = {c["catalog_group"]: c for c in self.reg["carried_pull_requests"]
                   if c["pr"].endswith("#263")}
        self.assertEqual(sorted(entries), [
            "kv-storage-endpoint-v2.validate.pr263",
            "runtime-import-and-secret-policy.guard.pr263",
            "validate-kv-interlock-contract.validate.pr263",
        ])
        groups = {g["id"]: g for g in self.catalog["groups"]}
        for gid, entry in entries.items():
            self.assertEqual(entry["source_copy"], "tools/tasks/carried/pr263/" + entry["source_workflow"].split("/")[-1])
            self.assertIn("tests/test_kv_skap_vault_finish_point.py", groups[gid]["select_when"]["paths_present"])
            base = groups[gid.rsplit(".", 1)[0]]
            self.assertIn("tests/test_kv_skap_vault_finish_point.py", base["select_when"]["paths_absent"])
        self.assertEqual(len(groups["runtime-import-and-secret-policy.guard.pr263"]["steps"]), 7)


if __name__ == "__main__":
    unittest.main()
