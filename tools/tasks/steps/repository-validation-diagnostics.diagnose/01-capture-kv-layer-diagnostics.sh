set +e
python3 tools/kv_layer_check.py --mode validate > kv-layer-diagnostics.txt 2>&1
echo "exit_code=$?" >> kv-layer-diagnostics.txt
exit 0
