mkdir -p probe-evidence
python tools/run_endpoint_fanout_probe.py \
  --value "stegverse-endpoint-fanout-probe" \
  --probe-id "ci-endpoint-fanout-001" \
  --e0-standin-healthy-node \
  --output probe-evidence/endpoint-fanout-probe.result.json
