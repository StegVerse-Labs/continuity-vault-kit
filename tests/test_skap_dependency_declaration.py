"""SKAP-UNDECLARED-CRYPTOGRAPHY-001: every third-party runtime import is declared.

Predicate EVERY_IMPORTED_THIRD_PARTY_PACKAGE_IS_DECLARED, classification
DECLARED_EXISTING_DEPENDENCY (Coordination provisional class C ruling,
StegVerse-org/.github#167 comment 6371963832, C-review PENDING).
"""
import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "requirements-skap.txt"
RUNTIME_DIRS = ("skap", "runtime")
# Distribution name per import root, for the packages that are declared.
DISTRIBUTION_FOR_IMPORT = {"cryptography": "cryptography"}
# cryptography's own requirements, needed for a --require-hashes install.
TRANSITIVE = {"cffi", "pycparser", "typing-extensions"}


def _local_roots():
    return {p.name for p in ROOT.iterdir() if p.is_dir()} | {
        p.stem for p in ROOT.glob("*.py")
    }


def _third_party_imports():
    std = set(sys.stdlib_module_names)
    local = _local_roots()
    found = {}
    for d in RUNTIME_DIRS:
        for path in sorted((ROOT / d).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    root = name.split(".")[0]
                    if root not in std and root not in local:
                        found.setdefault(root, set()).add(path.relative_to(ROOT).as_posix())
    return found


def _declared():
    text = DECLARATION.read_text(encoding="utf-8").replace("\\\n", " ")
    entries = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)==([A-Za-z0-9.]+)\b(.*)$", line)
        if m is None:
            raise AssertionError(f"unpinned or malformed requirement line: {line[:80]}")
        entries[m.group(1).lower()] = (m.group(2), re.findall(r"--hash=sha256:([0-9a-f]{64})", m.group(3)))
    return entries


class SkapDependencyDeclaration(unittest.TestCase):
    def test_every_third_party_runtime_import_is_declared(self):
        declared = _declared()
        imports = _third_party_imports()
        self.assertEqual(set(imports), set(DISTRIBUTION_FOR_IMPORT), imports)
        for root in imports:
            self.assertIn(DISTRIBUTION_FOR_IMPORT[root], declared)

    def test_only_skap_imports_cryptography(self):
        users = _third_party_imports().get("cryptography", set())
        self.assertTrue(users)
        self.assertTrue(all(u.startswith("skap/") for u in users), users)

    def test_every_declared_line_is_exactly_pinned_with_hashes(self):
        declared = _declared()
        self.assertEqual(set(declared), {"cryptography"} | TRANSITIVE)
        self.assertEqual(declared["cryptography"][0], "50.0.2")
        for name, (version, hashes) in declared.items():
            self.assertTrue(hashes, name)
            self.assertEqual(len(hashes), len(set(hashes)), name)

    def test_declaration_names_the_ruling_and_classification(self):
        text = DECLARATION.read_text(encoding="utf-8")
        self.assertIn("DECLARED_EXISTING_DEPENDENCY", text)
        self.assertIn("issues/167#issuecomment-6371963832", text)


if __name__ == "__main__":
    unittest.main()
