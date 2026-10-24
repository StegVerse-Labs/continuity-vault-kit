if [ "$JOB_STATUS" != "failure" ]; then
  echo "KV guardrails job status: $JOB_STATUS; no repair guidance needed."
  exit 0
fi
echo ""
echo "KV guardrails failed."
echo "Layer/footer repair path: push a format/<name> branch so KV Format Branch can auto-label Markdown files."
echo "Emoji repair path: replace obscure arrow glyphs with canonical relationship emoji or ASCII arrows."
echo "InTr/SKAP repair path: preserve authenticated cryptographic sealing, browser public-key ingress, callback-only browser-to-canonical SKAP admission, TVC/SKAP private-key confinement, transient owner-authorized ingress, lifecycle/grant-bound resolution, rotation/revocation invalidation, canonical adjacency, sealed transit, non-transfer of authority, endpoint-session gating, bidirectional receipt-chain integrity, KV metadata/ciphertext-only persistence, complete reconstruction evidence, synthetic transport I/O, non-secret external endpoint verification, and verified-session-before-resolution ordering."
echo "No workflow may move, delete, or inspect user-authored personal vault content."
echo ""
exit 0
