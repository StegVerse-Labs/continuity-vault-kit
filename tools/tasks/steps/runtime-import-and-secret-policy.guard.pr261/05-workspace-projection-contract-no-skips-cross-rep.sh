set -o pipefail
parity=$(python3 .stegverse/cross_repo_inputs.py tests .stegverse/workspace-parity-pin.json)
n=$(printf '%s\n' "$parity" | grep -c .)
deselect=$(printf -- '--deselect=%s ' $parity)
python -m pytest -q -rs $deselect tests/test_workspace_projection.py tests/test_workspace_continuity_checkpoint.py tests/test_workspace_assistant_binding.py tests/test_workspace_session_authentication.py tests/test_workspace_tasks_projection.py tests/test_workspace_family_projections.py tests/test_workspace_continuity_checkpoint_projection.py tests/test_workspace_decision_reasons.py 2>&1 | tee /tmp/workspace.txt
if grep -Eq "[0-9]+ skipped|^SKIPPED" /tmp/workspace.txt; then
  echo "::error::a Workspace projection test was skipped; skips are never accepted"; exit 1
fi
if ! grep -Eq "[0-9]+ passed, $n deselected" /tmp/workspace.txt; then
  echo "::error::expected exactly the $n pinned parity tests deselected"; exit 1
fi
