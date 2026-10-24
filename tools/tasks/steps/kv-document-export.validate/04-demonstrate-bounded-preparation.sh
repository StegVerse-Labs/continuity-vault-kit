python tools/prepare_document_export.py \
  fixtures/document-export/admitted.json \
  --bundle-out /tmp/publisher-bundle.json \
  --receipt-out /tmp/kv-export-receipt.json
test -s /tmp/publisher-bundle.json
test -s /tmp/kv-export-receipt.json
