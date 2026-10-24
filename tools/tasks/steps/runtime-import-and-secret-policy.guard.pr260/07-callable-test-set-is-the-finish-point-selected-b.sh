set +e
LABS="$RUNNER_TEMP/labs-tool"
selector=""
if [ "$EVENT" = pull_request ]; then
  pin=.stegverse/labs-tool-pin.json
  if python3 - "$pin" "$LABS" <<'PY'
import hashlib, json, os, subprocess, sys
pin, dest = json.load(open(sys.argv[1])), sys.argv[2]
env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
git = lambda *a: subprocess.run(["git", "-C", dest, *a], check=True, env=env, capture_output=True, text=True)
subprocess.run(["git", "init", "-q", dest], check=True, env=env)
git("-c", "http.https://github.com/.extraheader=", "fetch", "--no-tags", "--quiet", "--depth=1", pin["url"], pin["commit"])
git("checkout", "-q", "FETCH_HEAD")
assert git("rev-parse", "HEAD").stdout.strip() == pin["commit"], "fetched commit is not the pinned commit"
for path, want in sorted(pin["files"].items()):
    got = hashlib.sha256(open(os.path.join(dest, path), "rb").read()).hexdigest()
    print(path, got)
    assert got == want, f"{path}: sha256 {got} is not the pinned {want}"
PY
  then
    selector="$LABS/scripts/test_set_selection.py"
    python3 "$selector" select --root . \
      --manifest .stegverse/test-sets.json --spec .stegverse/test-set-spec.json \
      --base HEAD^1 --head HEAD --pr-head "$PR_HEAD" \
      --retry-entrypoint "Runtime Import + Secret Field Policy / guard" \
      --out "$RUNNER_TEMP/selection.json" || echo "::warning::selection is FAIL_CLOSED (see the record); the verdict decides"
  else
    echo "::warning::PINNED_LABS_TOOL_UNAVAILABLE: the pinned selector could not be fetched or verified; the finish point runs"
  fi
fi
out=$(python3 .stegverse/finish_point_verdict.py decide --event "$EVENT" \
  --spec .stegverse/test-set-spec.json --selection "$RUNNER_TEMP/selection.json" \
  --selector "$selector" --head "$(git rev-parse HEAD)" --pr-head "$PR_HEAD" \
  --out "$RUNNER_TEMP/finish-point-verdict.json")
if [ "$out" = run=false ]; then run=false; else run=true; fi
echo "run=$run" >> "$GITHUB_OUTPUT"
echo "FINISH_POINT_SET verdict run=$run (event $EVENT); record finish-point-verdict.json" | tee -a "$GITHUB_STEP_SUMMARY"
exit 0
