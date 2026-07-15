from __future__ import annotations

import json
from pathlib import Path
import unittest

from multimodal_storage.adapter import plan_experience_access

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "multimodal"


class MultimodalStorageAdapterTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_transcription_recall_does_not_grant_original_audio(self) -> None:
        capsule = self.load("transcription-only-voice.json")
        plan = plan_experience_access(capsule, principal_id="user_001")
        self.assertEqual(plan.permitted_stream_ids, ("stream_text_001",))
        self.assertIn("stream_audio_ephemeral_001", plan.denied_stream_ids)
        self.assertFalse(plan.raw_access_granted)

    def test_raw_request_fails_without_explicit_right(self) -> None:
        capsule = self.load("protected-audio-evidence.json")
        with self.assertRaisesRegex(PermissionError, "raw-evidence access"):
            plan_experience_access(capsule, principal_id="user_001", requested_raw_access=True)

    def test_generated_reconstruction_requires_explicit_request(self) -> None:
        capsule = self.load("sparse-video-reconstruction.json")
        default_plan = plan_experience_access(capsule, principal_id="user_001")
        self.assertIn("stream_video_sparse_001", default_plan.permitted_stream_ids)
        self.assertIn("stream_video_rendered_001", default_plan.denied_stream_ids)

        generated_plan = plan_experience_access(
            capsule,
            principal_id="user_001",
            requested_generation=True,
        )
        self.assertIn("stream_video_rendered_001", generated_plan.permitted_stream_ids)

    def test_unknown_principal_fails_closed(self) -> None:
        capsule = self.load("transcription-only-voice.json")
        with self.assertRaisesRegex(PermissionError, "exactly one"):
            plan_experience_access(capsule, principal_id="unknown")


if __name__ == "__main__":
    unittest.main()
