python - <<'PY'
import ast, sys
tree = ast.parse(open("runtime/ranged_sha256_measurement.py").read())
names = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        names |= {a.name.split(".")[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom) and n.level == 0:
        names.add(n.module.split(".")[0])
bad = sorted(x for x in names if x != "__future__" and x not in sys.stdlib_module_names)
assert not bad, bad
print("STDLIB_ONLY=PASS", sorted(names))
PY
