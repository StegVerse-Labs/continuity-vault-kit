mkdir -p recovery-evidence
python tools/run_cross_platform_recovery_probe.py > recovery-evidence/kv-cross-platform-recovery.receipt.json
python tools/run_provider_relocation_probe.py > recovery-evidence/kv-provider-relocation.receipt.json
