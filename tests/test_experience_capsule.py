from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tools.validate_experience_capsule import CapsuleValidationError, validate_capsule

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "multimodal"


class ExperienceCapsuleTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_all_reference_fixtures_validate(self) -> None:
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(path=path.name):
                validate_capsule(json.loads(path.read_text(encoding="utf-8")))

    def test_generated_reconstruction_requires_label_and_sources(self) -> None:
        capsule = self.load("sparse-video-reconstruction.json")
        generated = next(s for s in capsule["streams"] if s["artifact_class"] == "generated_reconstruction")
        generated["generated"] = False
        with self.assertRaisesRegex(CapsuleValidationError, "generated=true"):
            validate_capsule(capsule)

        capsule = self.load("sparse-video-reconstruction.json")
        generated = next(s for s in capsule["streams"] if s["artifact_class"] == "generated_reconstruction")
        generated["source_stream_refs"] = []
        with self.assertRaisesRegex(CapsuleValidationError, "source_stream_refs"):
            validate_capsule(capsule)

    def test_ephemeral_stream_cannot_have_payload_reference(self) -> None:
        capsule = self.load("transcription-only-voice.json")
        audio = next(s for s in capsule["streams"] if s["modality"] == "audio")
        audio["retention_class"] = "ephemeral"
        audio["payload_ref"] = "vault://forbidden/raw-audio"
        with self.assertRaisesRegex(CapsuleValidationError, "ephemeral stream"):
            validate_capsule(capsule)

    def test_transcription_only_cannot_grant_original_audio_recall(self) -> None:
        capsule = self.load("transcription-only-voice.json")
        audio = next(s for s in capsule["streams"] if s["modality"] == "audio")
        audio["user_recall_available"] = True
        with self.assertRaisesRegex(CapsuleValidationError, "may not be user recallable"):
            validate_capsule(capsule)

        capsule = self.load("transcription-only-voice.json")
        capsule["reconstruction_rights"][0]["may_access_raw"] = True
        with self.assertRaisesRegex(CapsuleValidationError, "raw-audio access"):
            validate_capsule(capsule)

    def test_fidelity_transition_requires_loss_and_reversibility(self) -> None:
        capsule = self.load("sparse-video-reconstruction.json")
        capsule["fidelity_transitions"][0]["information_loss"] = []
        with self.assertRaisesRegex(CapsuleValidationError, "information_loss"):
            validate_capsule(capsule)

        capsule = self.load("transcription-only-voice.json")
        capsule["fidelity_transitions"][0]["reversible"] = True
        with self.assertRaisesRegex(CapsuleValidationError, "cannot be reversible"):
            validate_capsule(capsule)

    def test_material_missing_evidence_cannot_be_complete(self) -> None:
        capsule = self.load("incomplete-experience.json")
        capsule["completeness_status"] = "complete_for_declared_scope"
        with self.assertRaisesRegex(CapsuleValidationError, "material missing evidence"):
            validate_capsule(capsule)

    def test_duplicate_stream_ids_fail(self) -> None:
        capsule = self.load("sparse-video-reconstruction.json")
        duplicate = copy.deepcopy(capsule["streams"][0])
        capsule["streams"].append(duplicate)
        with self.assertRaisesRegex(CapsuleValidationError, "duplicate stream_id"):
            validate_capsule(capsule)


if __name__ == "__main__":
    unittest.main()
