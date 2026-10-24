python tools/conversation_continuity.py build examples/conversation_continuity/sample_session.jsonl continuity-evidence
python tools/conversation_continuity.py verify continuity-evidence
python tools/conversation_continuity.py reconstruct continuity-evidence "bundle retention" > continuity-evidence/reconstruction.json
