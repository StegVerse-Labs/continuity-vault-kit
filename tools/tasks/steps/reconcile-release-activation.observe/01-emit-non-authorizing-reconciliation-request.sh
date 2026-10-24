mkdir -p reports/release_reconciliation
cat > reports/release_reconciliation/activation-request.json <<'JSON'
{
  "schema": "stegverse.kv.release-reconciliation-request/v1",
  "state": "TVC_ADMITTED_RELEASE_RECONCILIATION_REQUIRED",
  "workflow_dispatch_performed": false,
  "repository_mutation_performed": false,
  "release_mutation_performed": false,
  "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
  "credential_authority": "TV/TVC",
  "canonical_next_transition": "TVC_ADMITTED_RELEASE_RECONCILIATION",
  "authority_effect": "NONE"
}
JSON
