python3 scripts/validate_skap_intr_review_candidate.py specs/skap-intr-review-candidate.v1.json --self-test
python3 scripts/validate_intr_packet_review_candidate.py specs/intr-packet-review-candidate.v1.json --self-test
python3 scripts/validate_skap_endpoint_contracts.py --self-test
python3 scripts/intr_hop_receipt.py verify-chain examples/intr-hop-receipt-chain.example.json
python3 scripts/intr_hop_receipt.py verify-chain examples/intr-hop-return-receipt-chain.example.json
