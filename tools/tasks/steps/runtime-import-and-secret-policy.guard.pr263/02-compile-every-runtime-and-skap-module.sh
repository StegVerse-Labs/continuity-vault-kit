python - <<'PY'
import pathlib, sys
bad = []
for d in ("runtime", "skap"):
    for p in sorted(pathlib.Path(d).rglob("*.py")):
        try:
            compile(p.read_bytes(), str(p), "exec")
        except (SyntaxError, ValueError) as exc:
            bad.append(f"{p}: {exc}")
if bad:
    print("\n".join(bad))
    sys.exit(1)
print("all modules compile")
PY
