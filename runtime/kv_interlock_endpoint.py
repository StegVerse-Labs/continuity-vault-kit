from __future__ import annotations

import ast
import copy
import hashlib
import json
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from runtime.kv_receipt_ledgers import KV_LEDGER, read_receipt_ledger, receipt_ledger_binding
from runtime.secret_field_policy import field_name_is_forbidden


REQUEST_SCHEMA = "kv.interlock.request.v1"
RESPONSE_SCHEMA = "kv.interlock.response.v1"
ENVELOPE_SCHEMA = "stegverse.kv-interlock.intr-envelope/v1"
ALLOWED_OPERATIONS = {"DISCOVER", "REQUEST", "COMMIT_CANDIDATE"}
ALLOWED_DECISIONS = {"ALLOW_BOUNDED_CONTEXT", "REVIEW_REQUIRED", "DENY", "FAIL_CLOSED"}
REQUEST_REQUIRED = {
    "schema_version", "operation", "request_id", "requester", "purpose",
    "record_class", "requested_scope", "minimum_necessary_justification",
    "authority_ref", "disclosure_mode",
}
REQUEST_ALLOWED = REQUEST_REQUIRED | {"time_scope", "candidate_writeback", "selector"}
ENVELOPE_REQUIRED = {
    "schema", "protocol", "packet_id", "direction", "source_role", "next_role",
    "request_id", "operation", "payload_schema_version", "payload_hash",
    "sealed_material_ref", "authority", "boundary_proof", "receipt_policy",
}
ENVELOPE_ALLOWED = ENVELOPE_REQUIRED | {
    "prior_receipt_hash", "issued_at", "expires_at", "nonce",
}
FORBIDDEN_FIELD_TOKENS = {
    "password", "secret", "credential", "credential_value", "token",
    "private_key", "private_key_material", "raw_secret", "seed", "mnemonic",
}


class KVInterlockRuntimeError(ValueError):
    pass


# --- Layer 1 of the two credential layers (StegVerse-Labs/.github#3330 rev 1, LC-KV-07/08/10/11) -------------------
# KV is reachable only through InTr from a currently admitted healthy node. handle() is the DEVICE->KV InTr entry
# (INTR_DEVICE_KV). It first requires REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE, decided by the code InTr owns
# (LC-KV-13/14, Lane B): StegVerse-org/LLM-adapter#432's evaluate_anchored, which runs Lane B's anchored-root check and
# then llm_adapter/healthy_node_evaluator.py (unchanged, fdaa2005) over the anchored root. Both are vendored
# byte-identical in runtime/intr_pinned/ and verified by sha256 before every resolution. This runtime never decides
# health or anchoring itself.
# * It calls evaluate_anchored with require_admission=True over the org ledger and node endpoint bound to this
#   runtime. Neither is ever supplied by the requester.
# * It accepts only the evaluator's exact ALLOW shape for the InTr source identity.
# * Anything else is the six-field FAIL_CLOSED KV_ACCESS_LAYER1_REFUSED, carrying the evaluator's six fields as
#   health_evaluation.
# An admitted request mints one KV-access receipt into this runtime's own layer-1 receipt store. The separate layer-2
# gate (runtime/kv_skap_layer2.py) verifies against that store.
GOAL_REF = "KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
LAYER1_REFUSAL_CODE = "KV_ACCESS_LAYER1_REFUSED"
LAYER1_BOUNDARY = "INTR_DEVICE_KV"
LAYER1_PREDICATE = "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE"
LAYER1_RETRY = "runtime.kv_interlock_endpoint.KVInterlockRuntime.handle (StegVerse-Labs/continuity-vault-kit)"
KV_ACCESS_RECEIPT_SCHEMA = "stegverse.kv-access-receipt/v1"
HEALTHY_NODE_PREDICATE = "REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE"
HEALTHY_NODE_REFUSAL_CODE = "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY"
HEALTHY_NODE_RECEIPT_SCHEMA = "stegverse.healthy-node-evaluation/v1"  # the pinned evaluator's RESULT_SCHEMA
HEALTHY_NODE_GATE = "CURRENT_NODE_HEALTH"
#: The pinned InTr-owned evaluator (LC-KV-13/14). The interface is documented in docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md.
#: The evaluator bytes (fdaa2005...1f58) are unchanged from #428 @0b37fe3b through #429, #430 and #432 @c2c57505 and
#: @1cbad77e, @a2ee67e6, @73316297, @74509fec, @c4cfc145 and @eecf4843 (vendored head; previously c4cfc145; after a2ee67e6 only #432's test fixtures and the
#: GENESIS_NOT_PINNED next_attempt text, now naming REPOSITORY_LEDGER_GENESIS_PIN, changed).
#: Layer 1 never calls evaluate() bare any more: it calls #432's evaluate_anchored (PINNED_ANCHORED_EVALUATOR), which
#: runs Lane B's anchored-root check and then this evaluate(), unchanged, over the anchored root only.
#:   evaluate(node_id, *, ledger_root, transport_state, report_receipt_sha256, require_admission, repository) -> dict
PINNED_HEALTHY_NODE_EVALUATOR = {
    "repository": "StegVerse-org/LLM-adapter",
    "commit": "eecf4843e4ec2ec05ea5dbf6582e7d92080e8f9e",
    "pull_request": "StegVerse-org/LLM-adapter#432 (draft; evaluator bytes unchanged since #428)",
    "module": "llm_adapter.healthy_node_evaluator",
    "callable": "evaluate",
    "source_path": "llm_adapter/healthy_node_evaluator.py",
    "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
    "interface_doc": "docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md",
    "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
    "vendored_path": "runtime/intr_pinned/llm_adapter/healthy_node_evaluator.py",
    "owning_task": "LC-KV-13/LC-KV-14 (InTr and Mesh Destinations lane, StegVerse-org/.github#162)",
    "provenance": [
        {"pull_request": "StegVerse-org/LLM-adapter#428 (draft)", "commit": "0b37fe3b786a2de687235f5d9d146af49ffee9cd",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d"},
        {"pull_request": "StegVerse-org/LLM-adapter#429 (draft, NODE_HEALTH_REPORTED producer, contains #428)",
         "commit": "5f5f7bbeea96d5f313effaa02f86b01196465247",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:a363ff9bb498aa816adf9cc9d64559a389dec6acd3d02144056ee9c2540b91f0"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (draft, LC-KV-13 class B inputs: existence read-back, "
                         "NODE_IDENTITY_BINDING, NODE_HEALTH_CHECK_OBSERVED; carries #429 and #428)",
         "commit": "4e1499ab88144e8eae341058f7360b0d2a805b56",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:6b523e3949d89a4cb85904559d5bb458b9796ec910fde2c26296096f0d3f8b62"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (draft; head moved from 4e1499ab, evaluator bytes unchanged)",
         "commit": "3c106de4d9b87da498e620e5db33f8b922773c26",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft, anchored-root check evaluate_anchored; evaluator bytes "
                         "unchanged; pinned-code-digests file .stegverse/node-ledger/pinned-code-digests.v1.json)",
         "commit": "c2c57505535fb89ee88477eda1378c5fc610e0f7",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; head moved from c2c57505: schemas published, LC-KV-16 "
                         "in the wrapper; evaluator bytes unchanged)",
         "commit": "1cbad77eaff3254ea30fb9d3377d40abcf6728df",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; head moved from 1cbad77e: failure precedence location, "
                         "anchor, identity, health/admission, transport, carrier; repository passed through; org genesis "
                         "pinned by the org-ledger contract and head authenticated by the append route; ingress counts only "
                         "with its InTr carrier; evaluator bytes unchanged)",
         "commit": "a2ee67e65c3d1da83dd2d750d48ea8b282d7604e",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; code unchanged since a2ee67e6, only the org-ledger contract "
                         "fixtures changed)",
         "commit": "733162978292fbc7be3a562a4fa9f5bed4ada91e",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; evaluator unchanged; endpoint_ledger_anchor d47cd0a4: "
                         "GENESIS_NOT_PINNED next_attempt names REPOSITORY_LEDGER_GENESIS_PIN)",
         "commit": "74509feca062d5f17dbefe5730cbb1304ab6b318",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},

        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; evaluator unchanged; re-pinned to "
                         "continuity-vault-kit#263 @bf684aad via the designation module's source commit 2494d75a: endpoint_ledger_anchor 2d80e443, "
                         "endpoint_ledger_designation 35217d33, intr_transport_carrier 81ad9d3b, supplied_epoch be91daad)",
         "commit": "c4cfc14566786e9da43d7a6d45d569745a582a3d",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},

        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; evaluator unchanged; re-pinned to "
                         "continuity-vault-kit#263 @9bc54d05 via the designation module's source commit 64121f4d (StegVerse-org/.github#162 comment "
                         "6374660708): endpoint_ledger_anchor 153cf121, endpoint_ledger_designation d69dbb22, "
                         "intr_transport_carrier 9d3e69c8, endpoint-kind.v1 592bb3e5; PERMANENT is a "
                         "NODE_STORAGE_ENDPOINT designation, NODE_STORAGE_ENDPOINT_READER_NOT_DOCUMENTED)",
         "commit": "eecf4843e4ec2ec05ea5dbf6582e7d92080e8f9e",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
         "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
         "pinned_code_digests_file_sha256":
             "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8"},
    ],
    "admission_order": "StegVerse-org/LLM-adapter#429 lands with or before #428; #432 builds on #430",
    "re_vendor": "a final re-vendor follows once Lane B's stack (#429, #430, #432) settles",
}
#: Lane B's anchored-root check (StegVerse-org/LLM-adapter#432 @eecf4843, draft; was @c4cfc145, @74509fec). It is authoritative for whether a
#: caller-supplied node root is anchored on the org ledger; KV does not re-implement it. It needs the pinned producer
#: modules at their upstream-relative paths (it hashes ROOT/<path> for every entry of the pinned-code-digests file, with
#: ROOT = runtime/intr_pinned), so every file below is vendored byte-identical at that layout and re-hashed before every
#: resolution. node_ingress_boundary.py is vendored and pin-hashed but never executed: it imports the StegVerse SDK
#: (node_standing -> stegverse.manifest_contract), which is not a cvk dependency. endpoint_ledger_anchor reads only its
#: four string constants, which KV reads from the pinned bytes by AST (constants_only). org_ledger_location.py is
#: executed: it is evaluate_anchored's one I/O boundary (a local `git archive` of the contract-designated ref and
#: namespace, protocol.allow=never), reading the designation and pinned genesis from the vendored contract.json and the
#: append route's published head attesters from org-ledger-head-signers.v1.json (empty: MERGE_APPEND_PATH_NOT_ADMITTED).
#: intr_transport_carrier.py (stdlib only) is executed: evaluate_anchored counts a NODE_INGRESS_ADMITTED record only
#: when its signal was carried by an InTr path pair on the authenticated org chain.
PINNED_ANCHORED_EVALUATOR = {
    "repository": "StegVerse-org/LLM-adapter",
    "pull_request": "StegVerse-org/LLM-adapter#432 (draft, Lane B anchored-root check)",
    "commit": "eecf4843e4ec2ec05ea5dbf6582e7d92080e8f9e",
    "module": "llm_adapter.endpoint_ledger_anchor",
    "callable": "evaluate_anchored",
    "source_path": "llm_adapter/endpoint_ledger_anchor.py",
    "source_sha256": "sha256:153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09",
    "result_schema": "stegverse.endpoint-ledger-anchor-result/v1",
    "pinned_code_digests_path": ".stegverse/node-ledger/pinned-code-digests.v1.json",
    "pinned_code_digests_file_sha256": "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8",
    #: sha256 of the canonical digests map; the anchored genesis binds this value.
    "pinned_code_digests_sha256": "sha256:86f8b5d008a5e70e7843238388fbddf6975ec994f9fcc1b115d56dd3f40a3360",
    "vendored_root": "runtime/intr_pinned",
    "vendored_files": {
        "llm_adapter/endpoint_ledger_anchor.py":
            "sha256:153cf121a51199da8432735d4b2fb34b396f7eaa24da80f1bf9c77040013ac09",
        # #432 @c4cfc145: the designation module (byte copy of its source @2494d75a) and the supplied-epoch helper, both executed
        "llm_adapter/endpoint_ledger_designation.py":
            "sha256:d69dbb22a1446a22e84b86532f93d9698ac6dc3c82e6aa6ee20882c6764049d8",
        "llm_adapter/supplied_epoch.py": "sha256:be91daad3d5557f810872731c3ea8cc36e1f13af569e1b7634f487fd36f44534",
        "llm_adapter/org_ledger_location.py":
            "sha256:b51e6a8bd39ba6fd83044222a3858a2cb0c437020e3e9abbe97c4494d41f2681",
        "llm_adapter/intr_transport_carrier.py":
            "sha256:9d3e69c838d7e20533f0c5a06401b018948cb12a4201889f6b41d4b497df720f",
        "llm_adapter/healthy_node_evaluator.py":
            "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
        "llm_adapter/ed25519_verify.py": "sha256:ab05e39a3e40b99f02ff199b178554e0ba435c3ff387dca3f896619770770232",
        "llm_adapter/node_existence_readback.py":
            "sha256:cbed113d7fe59fc0919953bad5a0a08cdaeba3ad70a4e728e572c360f6fb2fb7",
        "llm_adapter/node_health_check_projection.py":
            "sha256:97cb7043c3f43d9aab2f0a591e1eefb94d3b127efc542d75be8d7574ce561ae8",
        "llm_adapter/node_health_report_producer.py":
            "sha256:21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361",
        "llm_adapter/node_identity_binding_producer.py":
            "sha256:ab578c921c6de5f50b9ecca50a71645e10582a051d2dd3417faa62d0dfdec01a",
        "llm_adapter/node_ingress_boundary.py":
            "sha256:86bae0426956581b862dd085c4ac64bf0a4f7dc37b0309ca9d223a3306754339",
        "llm_adapter/node_receipt_common.py":
            "sha256:7e73b65b649c7238aa6ae47409282b2fb729157de083c093fe595611966e43c7",
        ".stegverse/node-ledger/pinned-code-digests.v1.json":
            "sha256:9ed1e817f6faa983ffbc4facc9be15409fa23e6bb133dbb8a57fe24dbd3230f8",
        ".stegverse/transition-ledger/emit.py": "sha256:9579726de7ef915ac8cd61be1ba1c5ef6e34de4ca996504374b0dce7f7c2c9c3",
        # supporting data read by the pinned modules (not in the pin set; byte-identical at c4cfc145 and eecf4843)
        ".stegverse/transition-ledger/contract.json":
            "sha256:a59040e8cabe6dc618af0ba340cb5563ce726f645a76248ccb354961d29144e7",
        ".stegverse/heartbeat-awareness.json": "sha256:87b1c4006d3829ea70626d481012791c557e97bcd580a6c3d5ccc61389a6951b",
        # published NODE_LEDGER_OPENED signer references (TV/TVC custody); empty at eecf4843, so EPHEMERAL fails closed
        ".stegverse/node-ledger/node-ledger-opened-signers.v1.json":
            "sha256:478174cb89dc173e9bf7e8deb1db8b3881161e5a2fd10d6435298f74b6d3c63d",
        # published org-ledger append-route head attesters (TV/TVC custody); empty at eecf4843, so every org-ledger read
        # is FAIL_CLOSED MERGE_APPEND_PATH_NOT_ADMITTED until the append route is admitted
        ".stegverse/node-ledger/org-ledger-head-signers.v1.json":
            "sha256:3be27ff079433995d5eba111a5bb8cbe058e492938fb2b7ca299fe7bf6b69297",
        # Lane B's published v1 schemas (#432 @1cbad77e, unchanged at a2ee67e6); KV takes the endpoint_kind enum from endpoint-kind.v1.json
        "schemas/endpoint-kind.v1.json": "sha256:592bb3e5d67685912426a331769c44f60e75ff914138e0b0afc279c0c177b7a7",
        # KV/SKAP head signers read by endpoint_ledger_designation (byte copy of cvk#263's; signers [] at eecf4843)
        ".stegverse/node-ledger/kv-ledger-head-signers.v1.json":
            "sha256:758d798388599171c145e3d19ca4eb155ad3d3762a3721804da65c08ebc1fe72",
        "schemas/node-ledger-opened.v1.json":
            "sha256:2ef662f3cbe5da67aeae3732e526b86e71010c51a95887686d24d65ce919a352",
        "schemas/node-ledger-opened-signed.v1.json":
            "sha256:74cdc7e520d55f1bc1f964485ecada2a3953e331b1a87cca6dc9d36f74c5efa1",
        "schemas/node-ledger-opened-generation.v1.json":
            "sha256:7012ff4993213ce2ecbfa17ec01eeb149d2c0b999152a37e65f6205e6f48f0d4",
    },
    "constants_only": {"llm_adapter/node_ingress_boundary.py": ("ADMITTED_CLASS", "REFUSED_CLASS", "RECORD_SCHEMA",
                                                               "INTERLOCK_INTR")},
    "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
}
#: Where the evaluator's chain lives. It is bound by contract location: the existing org-ledger contract location
#: (generate_ledger_contracts.py repository_ledger_location), with no new ref and no new ledger root. KV derives the
#: evaluator's ledger_root as <checkout of the ref>/<namespace>. A requester never names it.
HEALTHY_NODE_LEDGER_LOCATION = {
    "repository": "StegVerse-org/.github",
    "ref": "refs/stegverse/organization-ledger",
    "namespace": "repository-ledger/StegVerse-org/LLM-adapter",
    "chain_repository": "StegVerse-org/LLM-adapter",
    "locator_form": "git+<checkout>#refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter",
    "new_ref": False,
    "new_ledger_root": False,
    "designation_source": "Coordination ruling on #3330 rev 1 (Oct 23), relayed to Lane D",
}
HEALTHY_NODE_LEDGER_PREDICATE = "HEALTHY_NODE_LEDGER_CHAIN_ONBOARDED_WITH_GENESIS"
HEALTHY_NODE_LEDGER_REFUSAL_CAUSE = "HEALTHY_NODE_LEDGER_NOT_ONBOARDED"
HEALTHY_NODE_LEDGER_ONBOARDING = (
    "the StegVerse-org/LLM-adapter organization-ledger onboarding route (closed unmerged by the owner; edge removed by "
    "StegVerse-org/.github#249). It would bind repository_ledger_location in "
    ".stegverse/transition-ledger/contract.json to StegVerse-org/.github refs/stegverse/organization-ledger:"
    "repository-ledger/StegVerse-org/LLM-adapter. It stays FAIL_CLOSED until that chain's genesis and an admitted append "
    "route exist")
HEALTHY_NODE_LEDGER_OWNER = ("KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324) via LC-KV-13 "
                             "(Lane B, InTr and Mesh Destinations, StegVerse-org/.github#162)")


def healthy_node_ledger_root(checkout: Any) -> str | None:
    """The evaluator ledger_root under a checkout (materialized tree) of the org-ledger ref, or None if not bound."""
    if not isinstance(checkout, (str, os.PathLike)) or not str(checkout):
        return None
    return os.path.join(str(checkout), *HEALTHY_NODE_LEDGER_LOCATION["namespace"].split("/"))
PINNED_HEALTHY_NODE_EVALUATOR_ID = (PINNED_HEALTHY_NODE_EVALUATOR["module"] + "."
                                    + PINNED_HEALTHY_NODE_EVALUATOR["callable"])
PINNED_ANCHORED_EVALUATOR_ID = PINNED_ANCHORED_EVALUATOR["module"] + "." + PINNED_ANCHORED_EVALUATOR["callable"]
#: The exact fields of the pinned evaluator's ALLOW result when called with require_admission=True.
_HEALTHY_RECEIPT_EXACT = {
    "schema": HEALTHY_NODE_RECEIPT_SCHEMA,
    "disposition": "ALLOW",
    "predicate": HEALTHY_NODE_PREDICATE,
    "gate": HEALTHY_NODE_GATE,
    "healthy_node_established": True,
    "health_status": "HEALTHY",
    "admission_required": True,
    "authority_effect": "NONE_EVALUATION_ONLY",
}


def _file_sha256(path: Any) -> str | None:
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except Exception:
        return None


def _code_sha256(fn: Any) -> str | None:
    """sha256 of a deterministic view of fn's compiled code object, observed from the object itself, never from what it reports
    about itself (__module__, __qualname__, co_filename). None for anything that is not a plain Python function."""
    code = getattr(fn, "__code__", None)
    if not isinstance(fn, types.FunctionType) or not isinstance(code, types.CodeType):
        return None
    try:
        return "sha256:" + hashlib.sha256(repr(_code_shape(code)).encode("utf-8")).hexdigest()
    except Exception:
        return None


def _code_shape(value: Any) -> Any:
    """A deterministic, recursive view of a code object (bytecode, constants, names, signature counts, flags).
    marshal.dumps is not used: its output depends on reference counts (FLAG_REF), so the same unchanged code object
    can marshal differently after it has run."""
    if isinstance(value, types.CodeType):
        return ("code", value.co_code, tuple(_code_shape(c) for c in value.co_consts), value.co_names,
                value.co_varnames, value.co_freevars, value.co_cellvars, value.co_argcount, value.co_posonlyargcount,
                value.co_kwonlyargcount, value.co_flags, value.co_name)
    if isinstance(value, (tuple, frozenset)):
        items = tuple(_code_shape(v) for v in value)
        return (type(value).__name__, tuple(sorted(items, key=repr)) if isinstance(value, frozenset) else items)
    return (type(value).__name__, repr(value))


_INTR_PINNED_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intr_pinned")
_PINNED_PACKAGE = "llm_adapter"
#: Load order of the executed pinned modules (each imports only earlier ones, the stdlib and, lazily, emit.py).
_PINNED_LOAD_ORDER = ("healthy_node_evaluator", "ed25519_verify", "node_receipt_common", "node_existence_readback",
                      "node_health_check_projection", "node_health_report_producer", "node_identity_binding_producer",
                      "org_ledger_location", "supplied_epoch", "endpoint_ledger_designation", "intr_transport_carrier",
                      "endpoint_ledger_anchor")
#: The executed vendored modules, in load order, as static paths (so a closure checker resolves every load target).
_PINNED_EXEC_SOURCES = (
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "healthy_node_evaluator.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "ed25519_verify.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "node_receipt_common.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "node_existence_readback.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "node_health_check_projection.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "node_health_report_producer.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "node_identity_binding_producer.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "org_ledger_location.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "supplied_epoch.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "endpoint_ledger_designation.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "intr_transport_carrier.py"),
    os.path.join(_INTR_PINNED_ROOT, "llm_adapter", "endpoint_ledger_anchor.py"),
)
_PINNED_LOCK = threading.Lock()
_PINNED_MODULES: dict[str, Any] = {}
#: LC-KV-10 (P1 rev 4, class A): what the pinned callables ARE, recorded at load time. Each executed module is compiled
#: from the exact bytes whose sha256 was just checked against its pin (never re-read from disk), and the resulting
#: function objects and their code-object digests are recorded here. A decider is pinned only if it `is` one of these
#: objects and its code object still hashes to the digest recorded at load. Names, qualnames and source filenames a
#: callable reports about itself are never consulted.
_PINNED_LOADED: dict[str, dict[str, Any]] = {}


def _pinned_bytes() -> tuple[dict[str, bytes] | None, str]:
    """({relative path: bytes}, "") with every vendored file read once and checked against its pin, else (None, why)."""
    found: dict[str, bytes] = {}
    for rel, want in PINNED_ANCHORED_EVALUATOR["vendored_files"].items():
        try:
            with open(os.path.join(_INTR_PINNED_ROOT, *rel.split("/")), "rb") as handle:
                data = handle.read()
        except Exception as exc:
            return None, f"runtime/intr_pinned/{rel} is unreadable ({type(exc).__name__})"
        observed = "sha256:" + hashlib.sha256(data).hexdigest()
        if observed != want:
            return None, f"runtime/intr_pinned/{rel} hashes to {observed}, not the pinned {want}"
        found[rel] = data
    return found, ""


def _pinned_bytes_failure() -> str | None:
    """None when every vendored file re-derives its pinned sha256, else why not."""
    return _pinned_bytes()[1] or None


def _constants_from_pinned_bytes(data: bytes, names: tuple[str, ...]) -> dict[str, str] | None:
    """Module-level string constants read by AST from the (already digest-checked) bytes of a file never executed."""
    try:
        tree = ast.parse(data)
    except Exception:
        return None
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in names and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            found[node.targets[0].id] = node.value.value
    return found if set(found) == set(names) else None


def load_pinned_intr() -> tuple[dict[str, Any] | None, str]:
    """({module name: module} for the pinned InTr code, "") or (None, why not).

    The vendored bytes are re-hashed on every call. The modules are loaded once under their upstream names
    (llm_adapter.*) from runtime/intr_pinned only, with the package's search path empty so nothing else can be imported
    under that name, and are removed from sys.modules again afterwards. A process that already imported another
    llm_adapter is refused rather than mixed.
    """
    blobs, failure = _pinned_bytes()
    if blobs is None:
        return None, failure
    with _PINNED_LOCK:
        if _PINNED_MODULES:
            return dict(_PINNED_MODULES), ""
        if any(name == _PINNED_PACKAGE or name.startswith(_PINNED_PACKAGE + ".") for name in sys.modules):
            return None, ("another llm_adapter is already imported in this process; the pinned InTr code is loaded "
                          "only from runtime/intr_pinned")
        (boundary_rel, names), = PINNED_ANCHORED_EVALUATOR["constants_only"].items()
        constants = _constants_from_pinned_bytes(blobs[boundary_rel], names)
        if constants is None:
            return None, f"{boundary_rel} does not declare {list(names)} as string constants"
        package = types.ModuleType(_PINNED_PACKAGE, "pinned InTr code (runtime/intr_pinned), loaded by KV")
        package.__path__ = []  # nothing is importable under llm_adapter except what is staged below
        boundary = types.ModuleType(_PINNED_PACKAGE + ".node_ingress_boundary",
                                    "constants only, read from the pinned bytes; the module itself is not executed")
        boundary.__dict__.update(constants)
        package.node_ingress_boundary = boundary
        staged = {package.__name__: package, boundary.__name__: boundary}
        try:
            sys.modules.update(staged)
            for source_path in _PINNED_EXEC_SOURCES:
                name = os.path.basename(source_path)[:-len(".py")]
                rel = f"{_PINNED_PACKAGE}/{name}.py"
                pinned_source = Path(source_path).read_bytes()
                # what runs is exactly what was hashed: these bytes are checked against the pin, then compiled
                if "sha256:" + hashlib.sha256(pinned_source).hexdigest() != \
                        PINNED_ANCHORED_EVALUATOR["vendored_files"][rel] or pinned_source != blobs[rel]:
                    raise ValueError(f"runtime/intr_pinned/{rel} changed while loading; not the pinned bytes")
                module = types.ModuleType(f"{_PINNED_PACKAGE}.{name}")
                module.__file__ = source_path
                module.__package__ = _PINNED_PACKAGE
                staged[module.__name__] = sys.modules[module.__name__] = module
                exec(compile(pinned_source, source_path, "exec", dont_inherit=True), module.__dict__)  # noqa: S102
                setattr(package, name, module)
        except Exception as exc:
            return None, f"the pinned InTr code does not load ({type(exc).__name__}: {exc})"
        finally:
            for name in staged:
                sys.modules.pop(name, None)
        anchor = package.endpoint_ledger_anchor
        if tuple(getattr(anchor, "ENDPOINT_KINDS", ())) != ENDPOINT_KINDS \
                or getattr(anchor, "RESULT_SCHEMA", None) != PINNED_ANCHORED_EVALUATOR["result_schema"] \
                or getattr(anchor, "EVALUATOR_SHA256", None) != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
            return None, "the pinned anchored-root check does not declare the endpoint kinds, schema and evaluator KV pins"
        if (getattr(anchor, "ENDPOINT_KIND_SCHEMA", None), getattr(anchor, "GENESIS_SCHEMA", None),
                getattr(anchor, "ANCHOR_BODY_SCHEMA", None), getattr(anchor, "OPENED_ANCHOR_SCHEMA", None),
                getattr(anchor, "SIGNED_OPENED_SCHEMA", None), getattr(anchor, "GENERATION_SCHEMA", None),
                getattr(anchor, "TRANSPORT_FAILURE_CODE", None), getattr(anchor, "FAILURE_CODE", None),
                getattr(anchor, "ENDPOINT_FAILURE_CODE", None)) != (
                ENDPOINT_KIND_SCHEMA, ENDPOINT_GENESIS_SCHEMA, ENDPOINT_ANCHOR_SCHEMA,
                EPHEMERAL_NODE_LEDGER_OPENED_SCHEMA, EPHEMERAL_NODE_LEDGER_OPENED_SIGNED_SCHEMA,
                EPHEMERAL_NODE_LEDGER_OPENED_GENERATION_SCHEMA, "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED",
                ANCHOR_REFUSAL_CODE, ENDPOINT_ANCHOR_REFUSAL_CODE):
            return None, "the pinned anchored-root check does not declare the v1 schemas and failure codes KV pins"
        for pin, module_name, rel in (
                (PINNED_ANCHORED_EVALUATOR, "endpoint_ledger_anchor", PINNED_ANCHORED_EVALUATOR["source_path"]),
                (PINNED_HEALTHY_NODE_EVALUATOR, "healthy_node_evaluator", PINNED_HEALTHY_NODE_EVALUATOR["source_path"])):
            fn = getattr(getattr(package, module_name), pin["callable"], None)
            code = _code_sha256(fn)
            if code is None:
                return None, f"{rel} defines no plain function {pin['callable']}"
            _PINNED_LOADED[pin["module"] + "." + pin["callable"]] = {
                "object": fn, "code_sha256": code, "source_sha256": pin["source_sha256"],
                "loaded_bytes_sha256": "sha256:" + hashlib.sha256(blobs[rel]).hexdigest()}
        if anchor.hne.evaluate is not _PINNED_LOADED[PINNED_HEALTHY_NODE_EVALUATOR_ID]["object"]:
            return None, "the pinned anchored-root check does not call the pinned evaluate()"
        _PINNED_MODULES.update({name: getattr(package, name) for name in _PINNED_LOAD_ORDER})
        return dict(_PINNED_MODULES), ""


def resolve_pinned_healthy_node_evaluator() -> tuple[Callable[..., Any] | None, str]:
    """(#432's evaluate_anchored, "") when every vendored byte re-derives its pin, else (None, why not).

    Layer 1's health decision is evaluate_anchored: Lane B's anchored-root check followed by the unchanged pinned
    evaluate() over the anchored root. Bare evaluate() is never used by layer 1 (it accepts a foreign producer)."""
    modules, why = load_pinned_intr()
    if modules is None:
        return None, why
    candidate = getattr(modules["endpoint_ledger_anchor"], PINNED_ANCHORED_EVALUATOR["callable"], None)
    return (candidate, "") if callable(candidate) else (None, "the vendored anchor module has no evaluate_anchored")


NOT_PINNED_DECIDER = "NOT_THE_PINNED_OBJECT"


def pinned_decider_identity(decider: Any, pin_id: str = PINNED_ANCHORED_EVALUATOR_ID) -> str | None:
    """pin_id when decider IS the function loaded from the digest-checked vendored bytes and its code object still
    hashes to the digest recorded at load (and the vendored bytes still re-derive their pins); else None."""
    if load_pinned_intr()[0] is None:
        return None
    loaded = _PINNED_LOADED.get(pin_id)
    if loaded is None or decider is not loaded["object"] or _code_sha256(decider) != loaded["code_sha256"]:
        return None
    return pin_id


def evaluator_identity(evaluator: Any) -> str:
    """The pin id for the pinned object itself, else NOT_THE_PINNED_OBJECT (never a self-reported name)."""
    for pin_id in (PINNED_ANCHORED_EVALUATOR_ID, PINNED_HEALTHY_NODE_EVALUATOR_ID):
        if pinned_decider_identity(evaluator, pin_id):
            return pin_id
    return NOT_PINNED_DECIDER


def _layer1_decider_record(decider: Any) -> dict[str, Any]:
    """What a KV-access receipt records for the layer-1 health decision (LC-KV-10, pinned by identity).

    Only when decider IS the loaded evaluate_anchored (identity plus load-time code digest) are the pins recorded: the
    anchored-root check and the unchanged evaluate() it calls, with the source digests checked on the bytes that were
    compiled and the code-object digests observed at load. Anything else, however it names itself, is recorded as
    NOT_THE_PINNED_OBJECT with its code digest and no source digest, which layer 2 and the finish point refuse."""
    if pinned_decider_identity(decider) is not None:
        outer = _PINNED_LOADED[PINNED_ANCHORED_EVALUATOR_ID]
        inner = _PINNED_LOADED[PINNED_HEALTHY_NODE_EVALUATOR_ID]
        return {"healthy_node_evaluator": PINNED_HEALTHY_NODE_EVALUATOR_ID,
                "healthy_node_evaluator_source_sha256": inner["loaded_bytes_sha256"],
                "healthy_node_evaluator_code_sha256": inner["code_sha256"],
                "healthy_node_anchor_check": PINNED_ANCHORED_EVALUATOR_ID,
                "healthy_node_anchor_check_source_sha256": outer["loaded_bytes_sha256"],
                "healthy_node_anchor_check_code_sha256": outer["code_sha256"]}
    code = _code_sha256(decider)
    return {"healthy_node_evaluator": NOT_PINNED_DECIDER, "healthy_node_evaluator_source_sha256": None,
            "healthy_node_evaluator_code_sha256": code, "healthy_node_anchor_check": NOT_PINNED_DECIDER,
            "healthy_node_anchor_check_source_sha256": None, "healthy_node_anchor_check_code_sha256": code}


# --- LC-KV-15: the trust anchors layer 1 binds to (StegVerse-Labs/.github#3330, P1 DENY on cvk#258 @61104a57) -------
# Layer 1 trusts nothing its constructor or a requester hands it for the inputs P1 found bypassable:
# * the org ledger, which is bound only by contract location at an exactly observed org-ledger head with a pinned
#   genesis; the head pin handed to evaluate_anchored is that tree's HEAD.json;
# * the node's root, which is the deployment's endpoint binding {endpoint_kind, ledger_root} and is admitted only by
#   Lane B's anchored-root check (#432 evaluate_anchored); KV no longer verifies anchors itself;
# * the requester identity, which is derived from the installed InTr transport's verification of the envelope and never
#   read from a caller field, and whose node_identity_key must be the anchored genesis key;
# * the transport state, which is the observed transport's state, else UNKNOWN_NOT_AUTHENTICALLY_OBSERVED.
# TRUST_ANCHORS holds what KV pins for those. Production code never mutates it. Every value is None today, because none
# of it is authentically observed yet, so the real path is a six-field FAIL_CLOSED until StegVerse-Labs/.github#3255
# (org-ledger genesis), the org-ledger location designation and #429 (producer) are admitted and the InTr
# transport is installed. The tests' E0 harness (tests/kv_two_layer_e0.py) swaps in labelled E0 anchors inside an
# explicit scope and restores these afterwards. Every receipt records the anchors' label, and layer 2 and the finish
# point refuse a receipt minted under different anchors than the ones in force.
UNKNOWN = "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED"
PRODUCTION_TRUST_ANCHORS_LABEL = "PRODUCTION"
TRUST_ANCHORS: dict[str, Any] = {
    "label": PRODUCTION_TRUST_ANCHORS_LABEL,
    # The installed InTr transport: an object with transport_id, state and authenticate(envelope) ->
    # {"node_id", "node_identity_key"} | None. No installed transport is observed (Lane B / InTr).
    "intr_transport": None,
}
#: The NODE_HEALTH_REPORTED producer (LC-KV-13/#429), one of the pinned producers evaluate_anchored admits.
PINNED_NODE_HEALTH_REPORT_PRODUCER = {
    "repository": "StegVerse-org/LLM-adapter",
    "source_path": "llm_adapter/node_health_report_producer.py",
    "source_sha256": "sha256:21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361",
    "observed_at": [
        {"pull_request": "StegVerse-org/LLM-adapter#429 (draft)", "commit": "5f5f7bbeea96d5f313effaa02f86b01196465247"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (draft)", "commit": "3c106de4d9b87da498e620e5db33f8b922773c26"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft)", "commit": "c2c57505535fb89ee88477eda1378c5fc610e0f7"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft)", "commit": "1cbad77eaff3254ea30fb9d3377d40abcf6728df"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft)", "commit": "a2ee67e65c3d1da83dd2d750d48ea8b282d7604e"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; code byte-identical to a2ee67e6, only the org-ledger "
                         "contract fixtures changed)",
         "commit": "733162978292fbc7be3a562a4fa9f5bed4ada91e"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; producer unchanged)",
         "commit": "74509feca062d5f17dbefe5730cbb1304ab6b318"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; producer unchanged; re-pinned to "
                         "cvk#263 @bf684aad, StegVerse-org/.github#162 6373907403)",
         "commit": "c4cfc14566786e9da43d7a6d45d569745a582a3d"},
        {"pull_request": "StegVerse-org/LLM-adapter#432 (draft; vendored head; producer unchanged; re-pinned to "
                         "cvk#263 @9bc54d05, StegVerse-org/.github#162 6374660708)",
         "commit": "eecf4843e4ec2ec05ea5dbf6582e7d92080e8f9e"},
    ],
}
# Org InTr endpoint model, aligned to #432 @a2ee67e6 and its published v1 schemas (runtime/intr_pinned/schemas/):
# EPHEMERAL (a temporary StegOS-generated StegApp/StegBrowser/StegNode node, own ledger bounded until dissolution,
# anchored by StegOS's NODE_LEDGER_OPENED generation record inside a signed envelope), PERMANENT, KV and SKAP_VAULT (own
# unbounded ledgers anchored by an InTr path receipt pair), GATEWAY (no own ledger: its root derives from the org root,
# node-ledger/StegVerse-org/<node_id>) and ORG (the .github ledger; it issues anchors and is never a node health root).
# KV's layer-1 receipts are endpoint_kind KV and the SKAP Vault's layer-2 receipts SKAP_VAULT. The finish point expects
# a PERMANENT node (LC-KV-13 completes with one; EPHEMERAL generation is a separate task and does not block it).
# The endpoint-kind schema is no longer pending: Lane B published schemas/endpoint-kind.v1.json, and KV takes the
# endpoint_kind enum from that file's bytes (digest-pinned above), never from a hand-written list. If the vendored
# schema does not re-derive its pin, the enum is empty and every endpoint is refused.
ENDPOINT_KIND_SCHEMA_PATH = "schemas/endpoint-kind.v1.json"


def _endpoint_kinds_from_schema() -> tuple[str, ...]:
    """The endpoint_kind enum ($defs.endpoint_kind.enum) of the digest-checked vendored endpoint-kind.v1.json."""
    want = PINNED_ANCHORED_EVALUATOR["vendored_files"][ENDPOINT_KIND_SCHEMA_PATH]
    try:
        data = Path(os.path.join(_INTR_PINNED_ROOT, "schemas", "endpoint-kind.v1.json")).read_bytes()
        if "sha256:" + hashlib.sha256(data).hexdigest() != want:
            return ()
        enum = json.loads(data.decode("utf-8"))["$defs"]["endpoint_kind"]["enum"]
    except Exception:
        return ()
    return tuple(enum) if isinstance(enum, list) and all(isinstance(k, str) and k for k in enum) else ()


ENDPOINT_KINDS = _endpoint_kinds_from_schema()
#: ORG issues anchors and is never a node health root (endpoint-kind.v1.json "anchor": NONE_IS_THE_ISSUER).
NODE_ROOT_ENDPOINT_KINDS = tuple(k for k in ENDPOINT_KINDS if k != "ORG")
FINISH_POINT_NODE_ENDPOINT_KIND = "PERMANENT"
ENDPOINT_KIND_SCHEMA = "stegverse.endpoint-kind/v1"  # schemas/endpoint-kind.v1.json ($id endpoint-kind.v1.json)
ENDPOINT_GENESIS_SCHEMA = "stegverse.endpoint-ledger-genesis/v1"  # #432 GENESIS_SCHEMA, carries endpoint_kind
ENDPOINT_ANCHOR_SCHEMA = "stegverse.endpoint-ledger-anchor/v1"  # #432 ANCHOR_BODY_SCHEMA (PERMANENT/KV/SKAP_VAULT)
#: the issued EPHEMERAL anchor (schemas/node-ledger-opened.v1.json); issuer and issuer_receipt_ref exist only here
EPHEMERAL_NODE_LEDGER_OPENED_SCHEMA = "stegverse.node-ledger-opened/v1"
EPHEMERAL_NODE_LEDGER_OPENED_SIGNED_SCHEMA = "stegverse.node-ledger-opened-signed/v1"  # the signed InTr body
EPHEMERAL_NODE_LEDGER_OPENED_GENERATION_SCHEMA = "stegverse.node-ledger-opened-generation/v1"  # StegOS's record
#: evaluate_anchored refusals that wait on TV/TVC publishing a NODE_LEDGER_OPENED signer (signers file empty).
EPHEMERAL_SIGNER_REASONS = ("NODE_LEDGER_OPENED_SIGNER_NOT_PUBLISHED",)
EPHEMERAL_SIGNER_OWNER = ("TV/TVC (publishes the NODE_LEDGER_OPENED signer reference in "
                          ".stegverse/node-ledger/node-ledger-opened-signers.v1.json; LC-KV-16, StegVerse-org/LLM-adapter"
                          "#432); EPHEMERAL generation does not block the finish point, which expects PERMANENT")
EPHEMERAL_SIGNER_NEXT = ("when TV/TVC publishes a NODE_LEDGER_OPENED signer reference (with its publication receipt) in "
                         "the vendored signers file and KV re-vendors it; event-driven, never on a timer")
LEDGER_SOURCE_ANCHORED = "ANCHORED_ENDPOINT_LEDGER"
#: evaluate_anchored's own failure codes for transport (read from receipts) and identity (proven by signature), #432
INTR_TRANSPORT_REFUSAL_CODE = "INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED"
IDENTITY_REFUSAL_CODE = "NODE_IDENTITY_NOT_PROVEN"
IDENTITY_ESTABLISHED_BY = "NODE_IDENTITY_KEY_ED25519_PROOF"
#: The pins the anchored genesis binds, as evaluate_anchored's ALLOW returns them (anchor.pinned_digests, in KV's key
#: names). Health receipts carry no per-receipt evidence.pinned_digests (adding them would change producer 21249f25);
#: KV checks these on the ALLOW instead.
PINNED_DIGESTS_FROM_GENESIS = {
    "evaluator_source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
    "producer_source_sha256": "sha256:21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361",
}
#: Fallback six-field failure_code when Lane B's anchored-root check refuses the node root without one of its own
#: (evaluate_anchored's own six fields are carried verbatim as health_evaluation). Since #432 @c4cfc145 its per-kind
#: failure_code is carried: EPHEMERAL_NODE_LEDGER_NOT_ANCHORED for EPHEMERAL only; for PERMANENT the org-ledger reason
#: itself, else ENDPOINT_LEDGER_NOT_ANCHORED; rule (1) reasons are their own code.
ANCHOR_REFUSAL_CODE = "EPHEMERAL_NODE_LEDGER_NOT_ANCHORED"
#: #432 @c4cfc145 ENDPOINT_FAILURE_CODE: a non-EPHEMERAL (PERMANENT) anchor refusal that is not an org-ledger reason
ENDPOINT_ANCHOR_REFUSAL_CODE = "ENDPOINT_LEDGER_NOT_ANCHORED"
ANCHOR_PREDICATE = "NODE_ROOT_ANCHORED_ON_ORG_LEDGER_BY_EVALUATE_ANCHORED"
#: evaluate_anchored reasons that wait on an upstream event (class B); every other anchor refusal is class C.
#: #432 @a2ee67e6 adds ORG_LEDGER_GENESIS_NOT_PINNED (waits on the contract's expected_genesis_receipt_sha256) and
#: MERGE_APPEND_PATH_NOT_ADMITTED (waits on the admitted append route and its TV/TVC-published head attester); a store
#: whose genesis or head does not match (ORG_LEDGER_GENESIS_MISMATCH, ORG_LEDGER_HEAD_NOT_AUTHENTICATED) is class C.
ANCHOR_CLASS_B_REASONS = ("UNANCHORED", "ENDPOINT_LEDGER_UNREADABLE", "ORG_LEDGER_UNREADABLE",
                          "ORG_LEDGER_LOCATION_NOT_DESIGNATED", "ORG_LEDGER_LOCATION_UNREADABLE",
                          "ORG_LEDGER_GENESIS_NOT_PINNED", "MERGE_APPEND_PATH_NOT_ADMITTED",
                          # #432 @eecf4843 (class B there): PERMANENT's own storage endpoint has no documented reader,
                          # and the Org-side crossing readback is not observed
                          "NODE_STORAGE_ENDPOINT_READER_NOT_DOCUMENTED", "KV_CROSSING_RECORD_NOT_OBSERVED")
INTR_TRANSPORT_PREDICATE = "REQUESTER_IDENTITY_AUTHENTICATED_BY_INSTALLED_INTR_TRANSPORT"
INTR_TRANSPORT_RETRY = ("the installed InTr DEVICE->KV transport (Lane B, InTr and Mesh Destinations, "
                        "StegVerse-org/.github#162), then runtime.kv_interlock_endpoint.KVInterlockRuntime.handle")
GENESIS_RETRY = ("StegVerse-Labs/.github#3255 (organization-ledger genesis) and the org-ledger location designation "
                 "(the LLM-adapter onboarding route is retired, StegVerse-org/.github#249); KV derives the genesis from the receipt it then observes at the contract location")


class LedgerBindingRefused(Exception):
    """Raised inside bind_healthy_node_ledger; layer 1 turns it into a six-field FAIL_CLOSED."""

    def __init__(self, cause: str, detail: str, *, failure_class: str = "B", predicate: str = HEALTHY_NODE_LEDGER_PREDICATE,
                 retry: str = HEALTHY_NODE_LEDGER_ONBOARDING, owner: str = HEALTHY_NODE_LEDGER_OWNER,
                 next_attempt: str = "when the LLM-adapter chain is onboarded and its genesis exists at the contract "
                                     "location", failure_code: str | None = None, evaluation: Any = None) -> None:
        super().__init__(f"{cause}: {detail}")
        self.cause, self.detail, self.failure_class, self.predicate = cause, detail, failure_class, predicate
        self.retry, self.owner, self.next_attempt, self.failure_code = retry, owner, next_attempt, failure_code
        self.evaluation = evaluation


def _read_chain(ledger_root: str) -> tuple[list[dict[str, Any]], str | None, str]:
    modules, why = load_pinned_intr()
    if modules is None:
        return [], "EVALUATOR_NOT_PINNED", why
    return modules["healthy_node_evaluator"].read_chain(ledger_root, HEALTHY_NODE_LEDGER_LOCATION["chain_repository"])


#: LC-KV-15: no genesis constant is pinned in KV. Since #432 @a2ee67e6 the org genesis is pinned by the org-ledger contract
#: (repository_ledger_location.expected_genesis_receipt_sha256) and checked inside evaluate_anchored's org-ledger read
#: (ORG_LEDGER_GENESIS_NOT_PINNED / ORG_LEDGER_GENESIS_MISMATCH), so KV's own derivation of the genesis from its receipt
#: (the former _org_genesis_failure / HEALTHY_NODE_LEDGER_GENESIS_NOT_DERIVABLE) is dropped as a duplicate. KV records
#: the genesis it read; an ALLOW proves it is the contract's pinned genesis.
GENESIS_DERIVATION = "ORG_LEDGER_GENESIS_PINNED_BY_CONTRACT_CHECKED_BY_EVALUATE_ANCHORED"


#: LC-KV-18 and the org-ledger legs: what the vendored #432 org-ledger read needs before any PERMANENT anchor can ALLOW.
#: Read from the pinned org_ledger_location only (contract designation, pinned genesis, published append-route head
#: attesters); never a ledger read, never a write. Each unmet leg is a six-field FAIL_CLOSED row.
ORG_LEDGER_PREREQUISITES = (
    ("ORG_LEDGER_LOCATION_NOT_DESIGNATED", "ORG_LEDGER_LOCATION_FROM_CONTRACT",
     "the repository_ledger_location designation in .stegverse/transition-ledger/contract.json; its onboarding route was closed "
     "unmerged by the owner and its edge removed by StegVerse-org/.github#249, so Lane B must reconcile it",
     "the repository_ledger_location (repository, ref, namespace) in the vendored contract.json, then re-vendor",
     "when Lane B reconciles the designation into the contract; event-driven, never on a timer"),
    ("ORG_LEDGER_GENESIS_NOT_PINNED", "ORG_LEDGER_GENESIS_PINNED_BY_CONTRACT",
     "the contract's expected_genesis_receipt_sha256 (null on purpose until the genesis is observed; its onboarding route is "
     "retired, StegVerse-org/.github#249), Lane B",
     "repository_ledger_location.expected_genesis_receipt_sha256 written by the REPOSITORY_LEDGER_GENESIS_PIN "
     "transition from the observed REPOSITORY_LEDGER_INITIALIZATION genesis "
     "receipt_sha256 on refs/stegverse/organization-ledger, never by hand and never invented, then re-vendor",
     "when the REPOSITORY_LEDGER_GENESIS_PIN transition runs on the receipted genesis record and its contract write "
     "is admitted; event-triggered by that record, no cron, no polling, no person"),
    ("MERGE_APPEND_PATH_NOT_ADMITTED", "ORG_LEDGER_HEAD_AUTHENTICATED_BY_APPEND_ROUTE",
     "TV/TVC (publishes the ORG_LEDGER_HEAD attester via GitHub Product) + Lane C (admits the org-ledger append route)",
     "a TV/TVC-custodied Ed25519 ORG_LEDGER_HEAD key published in .stegverse/node-ledger/org-ledger-head-signers.v1.json "
     "(empty at #432 @eecf4843) and the admitted append route attesting each org-ledger head; a TV/TVC transition, "
     "not a blocker",
     "when TV/TVC publishes the head attester and the append route is admitted; event-driven, never on a timer"),
)


def org_ledger_prerequisites() -> list[dict[str, Any]]:
    """LC-KV-18: one row per leg of the pinned #432 org-ledger read; FAIL_CLOSED class B rows for unmet legs."""
    modules, why = load_pinned_intr()
    rows = []
    location = modules["org_ledger_location"] if modules else None
    designated = location.org_ledger_location() if location else None
    met = {"ORG_LEDGER_LOCATION_NOT_DESIGNATED": designated is not None,
           "ORG_LEDGER_GENESIS_NOT_PINNED": bool(designated and designated.get("expected_genesis_receipt_sha256")),
           "MERGE_APPEND_PATH_NOT_ADMITTED": bool(location and location.load_head_signers())}
    for code, predicate, owner, repair, next_attempt in ORG_LEDGER_PREREQUISITES:
        row = {"prerequisite": predicate, "tracked_by": "LC-KV-18" if code == "MERGE_APPEND_PATH_NOT_ADMITTED"
               else "LC-KV-13 / LC-KV-15"}
        if met[code]:
            row["disposition"] = "ALLOW"
        else:
            row.update(disposition="FAIL_CLOSED", failure_code=code, failure_class="B", failed_predicate=predicate,
                       required_evidence_or_repair=f"{code}: {repair}" + (f" ({why})" if why else ""),
                       retry_entrypoint=("python -m runtime.kv_skap_vault finish-point "
                                         "(StegVerse-Labs/continuity-vault-kit), after re-vendoring #432"),
                       owning_existing_goal=f"{GOAL_REF}; dependency owner {owner}", next_attempt=next_attempt,
                       dependency_owner=owner, gates="every PERMANENT anchor (evaluate_anchored), so the finish point")
        rows.append(row)
    return rows


def _git(git_dir: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--git-dir", git_dir, *args], capture_output=True, timeout=60, check=False,
                          env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})


def _resolve_git_dir(path: str) -> str | None:
    """The repository at exactly path (a worktree's .git or a bare repository), never an enclosing one."""
    dot_git = os.path.join(path, ".git")
    if os.path.isdir(dot_git):
        return dot_git
    if os.path.isfile(dot_git):  # a linked worktree
        probe = subprocess.run(["git", "-C", path, "rev-parse", "--absolute-git-dir"], capture_output=True,
                               timeout=60, check=False, env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"})
        return probe.stdout.decode().strip() or None if probe.returncode == 0 else None
    if os.path.isfile(os.path.join(path, "HEAD")) and os.path.isdir(os.path.join(path, "objects")):
        return path
    return None


def _bind_organization_ledger(git_path: Any) -> tuple[dict[str, Any], str, str]:
    """Materialize the contract-location namespace from the exactly observed org-ledger head.

    Returns (binding, scratch workdir, git dir). The git dir is what evaluate_anchored reads the designated ref and
    namespace from itself (org_ledger_git_dir); KV's own materialization derives the genesis and the head pin."""
    loc = HEALTHY_NODE_LEDGER_LOCATION
    git_dir = _resolve_git_dir(str(git_path)) if isinstance(git_path, (str, os.PathLike)) and str(git_path) else None
    if git_dir is None:
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, (
            f"no git repository of {loc['repository']} is bound to KV; the healthy-node chain is read only from "
            f"{loc['ref']}:{loc['namespace']} at an observed head (a bare directory or scratch ledger root is refused)"))
    head = _git(git_dir, "rev-parse", "--verify", "--quiet", loc["ref"] + "^{commit}")
    if head.returncode != 0 or not head.stdout.strip():
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, (
            f"{loc['repository']} {loc['ref']} is not observed in the bound repository (the organization-ledger "
            "genesis is StegVerse-Labs/.github#3255)"), retry=GENESIS_RETRY)
    observed_head = head.stdout.decode().strip()
    archive = _git(git_dir, "archive", "--format=tar", observed_head, loc["namespace"])
    if archive.returncode != 0:
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, (
            f"{loc['ref']}@{observed_head[:12]} has no {loc['namespace']} (the org-ledger route has not onboarded it)"))
    workdir = tempfile.mkdtemp(prefix="kv-org-ledger-")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            members = [m for m in tar.getmembers() if m.isfile() or m.isdir()]
            if any(m.name.startswith("/") or ".." in m.name.split("/") for m in members):
                raise LedgerBindingRefused("HEALTHY_NODE_LEDGER_TREE_MALFORMED", "the namespace tree has unsafe paths",
                                           failure_class="C")
            if hasattr(tarfile, "data_filter"):
                tar.extractall(workdir, members=members, filter="data")
            else:  # pragma: no cover - interpreters before the extraction filters
                tar.extractall(workdir, members=members)  # noqa: S202 - members filtered above
        root = os.path.join(workdir, *loc["namespace"].split("/"))
        chain, reason, detail = _read_chain(root)
        if reason == "LEDGER_HEAD_UNREADABLE":
            raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, (
                f"{loc['namespace']}/HEAD.json is unreadable at {loc['ref']}@{observed_head[:12]}"))
        if reason is not None or not chain:
            raise LedgerBindingRefused("HEALTHY_NODE_LEDGER_CHAIN_UNREADABLE", (
                f"{loc['ref']}@{observed_head[:12]}:{loc['namespace']} does not read back as a chain ({reason}: "
                f"{detail})"), failure_class="C", evaluation={"disposition": "FAIL_CLOSED", "reason": reason, "detail": detail})
        genesis = chain[-1].get("receipt_sha256")
    except BaseException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    return {"kind": LEDGER_SOURCE_ANCHORED, "repository": loc["repository"], "ref": loc["ref"],
            "namespace": loc["namespace"], "observed_head": observed_head, "genesis_receipt_sha256": genesis,
            "genesis_derived_from": GENESIS_DERIVATION, "chain_head_receipt_sha256": chain[0].get("receipt_sha256")}, \
        workdir, git_dir


def bind_healthy_node_ledger(source: Any) -> tuple[dict[str, Any], str, str | None, Any, str, Any]:
    """The single ledger binding. Returns (org binding, org ledger root, scratch dir to remove or None, endpoint, org
    ledger git dir, org-ledger head attestation or None) or raises LedgerBindingRefused.

    source is the deployment's binding, never a requester's:
    * {"kind": LEDGER_SOURCE_ANCHORED, "org_ledger_git_dir": path, "endpoint": {"endpoint_kind", "ledger_root"}} plus
      optionally "org_ledger_head_attestation" (the admitted append route's stegverse.org-ledger-head-attestation/v1
      for that store's head, as the deployment received it): the org ledger is read from
      refs/stegverse/organization-ledger at the head observed now, and the endpoint and attestation are handed to
      evaluate_anchored, which alone decides whether the store is the org ledger (contract-pinned genesis, head attested
      by a published append-route key) and whether that node root is anchored. KV never trusts the store or the
      attestation itself, and a requester can supply neither;
    * a git repository path alone: the org ledger is bound but no node endpoint is declared, which evaluate_anchored
      refuses (ENDPOINT_INVALID). The org chain itself is never a node health root (#432: ORG is refused).
    Anything else is unbound and refused.
    """
    if source is None:
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, "no ledger source is bound to KV")
    endpoint = None
    if isinstance(source, dict):
        if source.get("kind") != LEDGER_SOURCE_ANCHORED or not {"kind", "org_ledger_git_dir", "endpoint"} <= set(source) \
                or not set(source) <= {"kind", "org_ledger_git_dir", "endpoint", "org_ledger_head_attestation"}:
            raise LedgerBindingRefused("LEDGER_SOURCE_NOT_BOUND_BY_CONTRACT", (
                f"a ledger is bound only as {{kind: {LEDGER_SOURCE_ANCHORED}, org_ledger_git_dir, endpoint}} (the org "
                "ledger by contract location, the node root by Lane B's anchored-root check) or as an org-ledger git "
                "repository; any other caller-shaped source is refused"), failure_class="C",
                predicate=ANCHOR_PREDICATE, failure_code=ANCHOR_REFUSAL_CODE)
        endpoint = copy.deepcopy(source["endpoint"])
        attestation = copy.deepcopy(source.get("org_ledger_head_attestation"))
        source = source["org_ledger_git_dir"]
    else:
        attestation = None
    binding, workdir, git_dir = _bind_organization_ledger(source)
    return (binding, os.path.join(workdir, *HEALTHY_NODE_LEDGER_LOCATION["namespace"].split("/")), workdir, endpoint,
            git_dir, attestation)


def observe_intr_transport() -> tuple[Any, str, str | None]:
    """(transport, state, transport_id). state is UNKNOWN_NOT_AUTHENTICALLY_OBSERVED when none is installed."""
    transport = TRUST_ANCHORS.get("intr_transport")
    if transport is None:
        return None, UNKNOWN, None
    state = getattr(transport, "state", None)
    transport_id = getattr(transport, "transport_id", None)
    if not isinstance(state, str) or not isinstance(transport_id, str) or not callable(
            getattr(transport, "authenticate", None)):
        return None, UNKNOWN, None
    return transport, state, transport_id


def layer1_receipt_conformance(receipt: Any) -> str | None:
    """None when a KV-access receipt was minted under the pinned evaluate_anchored and the trust anchors in force; else
    why. Layer 2 (LC-KV-10) and the finish point both use this; neither trusts the receipt's own say-so."""
    if not isinstance(receipt, dict):
        return "LAYER1_RECEIPT_ABSENT"
    if receipt.get("healthy_node_evaluator") != PINNED_HEALTHY_NODE_EVALUATOR_ID \
            or receipt.get("healthy_node_evaluator_source_sha256") != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"
    if receipt.get("healthy_node_anchor_check") != PINNED_ANCHORED_EVALUATOR_ID \
            or receipt.get("healthy_node_anchor_check_source_sha256") != PINNED_ANCHORED_EVALUATOR["source_sha256"]:
        return "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED"
    if load_pinned_intr()[0] is None or any(
            receipt.get(field) != (_PINNED_LOADED.get(pin_id) or {}).get("code_sha256") for field, pin_id in (
                ("healthy_node_anchor_check_code_sha256", PINNED_ANCHORED_EVALUATOR_ID),
                ("healthy_node_evaluator_code_sha256", PINNED_HEALTHY_NODE_EVALUATOR_ID))):
        return "LAYER1_DECIDER_CODE_NOT_THE_PINNED_CODE"
    if receipt.get("trust_anchors_label") != TRUST_ANCHORS.get("label"):
        return "LAYER1_RECEIPT_MINTED_UNDER_OTHER_TRUST_ANCHORS"
    if receipt.get("endpoint_kind") != "KV":
        return "LAYER1_RECEIPT_NOT_FROM_A_KV_ENDPOINT"
    transport, state, transport_id = observe_intr_transport()
    if transport is None or state != "INSTALLED" or receipt.get("intr_transport_state") != "INSTALLED" \
            or receipt.get("intr_transport_id") != transport_id:
        return "LAYER1_TRANSPORT_NOT_THE_INSTALLED_ONE"
    identity = receipt.get("requester_identity")
    if not isinstance(identity, dict) or identity.get("node_id") != receipt.get("requester_node_ref") \
            or identity.get("authenticated_by") != transport_id or not identity.get("node_identity_key"):
        return "LAYER1_REQUESTER_IDENTITY_NOT_TRANSPORT_AUTHENTICATED"
    binding = receipt.get("healthy_node_ledger_binding")
    if not isinstance(binding, dict):
        return "LAYER1_LEDGER_BINDING_ABSENT"
    loc = HEALTHY_NODE_LEDGER_LOCATION
    if binding.get("kind") != LEDGER_SOURCE_ANCHORED or binding.get("genesis_derived_from") != GENESIS_DERIVATION \
            or not _is_sha256_uri(binding.get("genesis_receipt_sha256")) \
            or (binding.get("repository"), binding.get("ref"), binding.get("namespace")) != (
                loc["repository"], loc["ref"], loc["namespace"]) or not binding.get("observed_head") \
            or not _is_sha256_uri(binding.get("chain_head_receipt_sha256")):
        return "LAYER1_LEDGER_NOT_BOUND_BY_CONTRACT_LOCATION"
    healthy = receipt.get("healthy_node_receipt")
    anchored = healthy.get("anchor") if isinstance(healthy, dict) else None
    if binding.get("endpoint_kind") not in NODE_ROOT_ENDPOINT_KINDS or not isinstance(anchored, dict) \
            or anchored.get("schema") != PINNED_ANCHORED_EVALUATOR["result_schema"] \
            or anchored.get("disposition") != "ALLOW" or anchored.get("node_id") != identity.get("node_id") \
            or anchored.get("endpoint_kind") != binding.get("endpoint_kind") \
            or anchored.get("genesis_receipt_sha256") != binding.get("endpoint_genesis_receipt_sha256") \
            or anchored.get("pinned_digests") != PINNED_DIGESTS_FROM_GENESIS \
            or anchored.get("org_ledger_head_receipt_sha256") != binding.get("chain_head_receipt_sha256") \
            or anchored.get("evaluator_sha256") != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"] \
            or anchored.get("pinned_code_digests_sha256") != PINNED_ANCHORED_EVALUATOR["pinned_code_digests_sha256"] \
            or binding.get("node_identity_key") != identity.get("node_identity_key"):
        return ANCHOR_REFUSAL_CODE
    return None


def layer1_refusal(request: Any, cause: str, detail: str, *, predicate: str = LAYER1_PREDICATE,
                   failure_class: str = "B", next_attempt: str | None = None,
                   health_evaluation: Any = None, retry_entrypoint: str = LAYER1_RETRY,
                   owning_existing_goal: str = GOAL_REF, failure_code: str | None = None) -> dict[str, Any]:
    """Six-field FAIL_CLOSED for layer 1, returned (never raised) by handle()."""
    request_id = request.get("request_id") if isinstance(request, dict) else None
    return {
        "schema_version": RESPONSE_SCHEMA,
        "request_id": request_id,
        "decision": "FAIL_CLOSED",
        "disposition": "FAIL_CLOSED",
        "layer": LAYER1_BOUNDARY,
        "failure_code": failure_code or LAYER1_REFUSAL_CODE,
        "failed_predicate": predicate,
        "required_evidence_or_repair": f"{cause}: {detail}",
        "retry_entrypoint": retry_entrypoint,
        "owning_existing_goal": owning_existing_goal,
        "next_attempt": next_attempt or "on the next DEVICE->KV InTr transition that carries the repair",
        "failure_class": failure_class,
        "refusal_cause": cause,
        "granted_scope": [],
        "context": {},
        "kv_access_receipt": None,
        "health_evaluation": health_evaluation,
        "authority_effect": "NONE",
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_uri(value: Any) -> str:
    return "sha256:" + sha256_hex(value)


def _is_sha256_uri(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        ch in "0123456789abcdef" for ch in value[7:]
    )


def _unique_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and all(isinstance(item, str) and item for item in value)
    )


def _contains_forbidden_name(name: str, value: Any = None) -> bool:
    return field_name_is_forbidden(name, value, FORBIDDEN_FIELD_TOKENS)


def _context_is_safe(value: Any) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and not _contains_forbidden_name(key, child)
            and _context_is_safe(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return all(_context_is_safe(child) for child in value)
    return isinstance(value, (str, int, float, bool)) or value is None


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KVInterlockRuntimeError("invalid time value") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def response_hash(response: dict[str, Any]) -> str:
    projection = {
        "schema_version": response.get("schema_version"),
        "request_id": response.get("request_id"),
        "decision": response.get("decision"),
        "granted_scope": response.get("granted_scope"),
        "context": response.get("context"),
        "source_refs": response.get("source_refs"),
    }
    return sha256_hex(projection)


class KVInterlockRuntime:
    """Fail-closed KV-INTERLOCK-v1 runtime core.

    The runtime does not establish transport identity itself. The caller must
    provide the exact already-verified DEVICE->KV InTr envelope and an opaque
    durable InTr receipt reference. Authority, policy, candidate persistence,
    and receipt persistence are injected boundaries.
    """

    def __init__(
        self,
        *,
        authority_validator: Callable[[str, dict[str, Any], dict[str, Any]], bool],
        policy_evaluator: Callable[[dict[str, Any]], dict[str, Any]],
        receipt_store: Callable[[dict[str, Any]], str],
        candidate_store: Callable[[dict[str, Any]], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        healthy_node_evaluator: Callable[..., Any] | None = None,
        healthy_node_ledger_checkout: Any = None,
    ) -> None:
        self.authority_validator = authority_validator
        self.policy_evaluator = policy_evaluator
        self.receipt_store = receipt_store
        self.candidate_store = candidate_store
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        # Layer 1 consumes the InTr-owned evaluate_anchored; it never supplies one of its own. An injected decider is
        # refused at handle() unless it IS the loaded pinned object (LC-KV-10); only the exercise-only subclass in
        # runtime/kv_skap_vault.py runs one, and its receipts are recorded NOT_THE_PINNED_OBJECT and refused downstream.
        if healthy_node_evaluator is None:
            healthy_node_evaluator, self._evaluator_unavailable = resolve_pinned_healthy_node_evaluator()
        else:
            self._evaluator_unavailable = ""
        self.healthy_node_evaluator = healthy_node_evaluator
        # The deployment's ledger binding (bind_healthy_node_ledger): the org-ledger repository read at the observed
        # head of HEALTHY_NODE_LEDGER_LOCATION's ref, plus the node endpoint. Never supplied by a requester.
        self.healthy_node_ledger_checkout = healthy_node_ledger_checkout
        self._kv_access_receipts: dict[str, dict[str, Any]] = {}

    _EXERCISE_ONLY_UNPINNED_DECIDER = False

    @staticmethod
    def receipt_ledger(storage_endpoint: Any = None, readback_root: Any = None, head_attestation: Any = None,
                       recorded_head: Any = None) -> dict[str, Any]:
        """Layer 1's recorded receipt chain, read back from KV's own location (STEGVERSE_KV _StegVerse/Receipts,
        through the documented storage endpoint v2 of the KV #2 lineage; KV-SKAP-LEDGER-LOCATION-001). Six-field
        FAIL_CLOSED KV2_STORAGE_ENDPOINT_PENDING_INTERLOCK_INTR while KV #2 is PENDING_INTERLOCK_INTR, then
        KV_RECEIPT_CHAIN_GENESIS_NOT_PINNED until the genesis pin. The rollback watermark is read back from KV's own
        head record and the Org's crossing records are compared only to refuse (ruling .github#167 6374130335);
        ``recorded_head`` is optional and only a claim (Org-sourced -> FAIL_CLOSED
        KV_ROLLBACK_WATERMARK_ORG_LEDGER_SOURCED; not the read-back head -> DENY KV_LEDGER_HEAD_ROLLBACK_DETECTED)."""
        return read_receipt_ledger(KV_LEDGER, storage_endpoint, readback_root, head_attestation, recorded_head)

    def verify_kv_access_receipt(self, receipt_hash: Any) -> dict[str, Any] | None:
        """The layer-1 receipt this runtime minted under receipt_hash, re-derived, or None. Layer 2 calls this."""
        receipt = self._kv_access_receipts.get(receipt_hash) if isinstance(receipt_hash, str) else None
        if receipt is None:
            return None
        if sha256_uri({k: v for k, v in receipt.items() if k != "receipt_hash"}) != receipt_hash:
            return None
        return copy.deepcopy(receipt)

    def _refused(self, request: Any, exc: LedgerBindingRefused) -> dict[str, Any]:
        loc = HEALTHY_NODE_LEDGER_LOCATION
        detail = exc.detail
        if exc.cause == HEALTHY_NODE_LEDGER_REFUSAL_CAUSE:
            detail += (f". The healthy-node chain is bound by contract location to {loc['repository']} {loc['ref']}:"
                       f"{loc['namespace']}; that chain must be onboarded with a genesis before any health report is "
                       "readable")
        return layer1_refusal(request, exc.cause, detail, predicate=exc.predicate, failure_class=exc.failure_class,
                              health_evaluation=exc.evaluation, retry_entrypoint=exc.retry,
                              owning_existing_goal=exc.owner, next_attempt=exc.next_attempt,
                              failure_code=exc.failure_code)

    def _access_context(self, request: dict[str, Any],
                        envelope: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """LC-KV-15: bind the org ledger and the node endpoint, observe the transport and derive the requester identity
        from it.

        Returns (context, None) or (None, six-field refusal). Nothing here is read from a caller field: the envelope's
        boundary_proof.source_identity_ref is only compared with the identity the installed transport authenticated.
        """
        claimed = envelope["boundary_proof"]["source_identity_ref"]
        scratch = None
        try:
            binding, org_root, scratch, endpoint, git_dir, attestation = bind_healthy_node_ledger(
                self.healthy_node_ledger_checkout)
            transport, state, transport_id = observe_intr_transport()
            if transport is None or state != "INSTALLED":
                raise LedgerBindingRefused("INTR_TRANSPORT_NOT_AUTHENTICALLY_OBSERVED", (
                    f"transport_state is {state}; KV derives the requester identity only from the installed InTr "
                    f"transport's verification of the envelope, and boundary_proof.source_identity_ref ({claimed!r}) "
                    "is a caller field that is never trusted"), predicate=INTR_TRANSPORT_PREDICATE,
                    retry=INTR_TRANSPORT_RETRY, owner=GOAL_REF,
                    next_attempt="when an installed InTr DEVICE->KV transport is authentically observed")
            try:
                identity = transport.authenticate(copy.deepcopy(envelope))
            except Exception:
                identity = None
            if not isinstance(identity, dict) or not isinstance(identity.get("node_id"), str) \
                    or not identity["node_id"] or not identity.get("node_identity_key"):
                raise LedgerBindingRefused("REQUESTER_IDENTITY_NOT_TRANSPORT_AUTHENTICATED", (
                    f"the installed transport {transport_id} did not authenticate this envelope's source; a "
                    f"caller-asserted identity ({claimed!r}) is refused"), failure_class="C",
                    predicate=INTR_TRANSPORT_PREDICATE, retry=INTR_TRANSPORT_RETRY, owner=GOAL_REF,
                    next_attempt="on a DEVICE->KV InTr transition the installed transport authenticates")
            if identity["node_id"] != claimed:
                raise LedgerBindingRefused("REQUESTER_IDENTITY_MISMATCH", (
                    f"the transport authenticated {identity['node_id']!r}, but the envelope claims {claimed!r}"),
                    failure_class="C", predicate=INTR_TRANSPORT_PREDICATE, retry=INTR_TRANSPORT_RETRY, owner=GOAL_REF,
                    next_attempt="on a DEVICE->KV InTr transition whose source is the authenticated node")
        except LedgerBindingRefused as exc:
            if scratch:
                shutil.rmtree(scratch, ignore_errors=True)
            return None, self._refused(request, exc)
        return {"org_ledger_root": org_root, "org_ledger_head_receipt_sha256": binding["chain_head_receipt_sha256"],
                "org_ledger_git_dir": git_dir, "org_ledger_head_attestation": attestation,
                "identity_proof": copy.deepcopy(identity.get("identity_proof")),
                "endpoint": endpoint, "binding": binding, "scratch": scratch, "transport_state": state,
                "transport_id": transport_id, "trust_anchors_label": TRUST_ANCHORS.get("label"),
                "identity": {"node_id": identity["node_id"],
                             "node_identity_key": copy.deepcopy(identity["node_identity_key"]),
                             "authenticated_by": transport_id}}, None

    def _healthy_node(self, request: dict[str, Any], envelope: dict[str, Any], evidence: Any
                      ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """(the pinned evaluator's verified ALLOW, access context, None) or (None, None, six-field refusal).

        ``evidence`` is what the requester may cite: None, or {"health_report_receipt_sha256": <sha256>}. Health is
        decided only by the evaluator over the bound ledger, for the transport-authenticated node, at the observed
        transport state.
        """
        pin = PINNED_HEALTHY_NODE_EVALUATOR
        if self.healthy_node_evaluator is None:
            return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"no {HEALTHY_NODE_PREDICATE} evaluator is available ({self._evaluator_unavailable}); the pinned "
                f"InTr evaluator is {pin['repository']}@{pin['commit'][:8]}:{pin['source_path']} "
                f"({pin['source_sha256']}), and KV never asserts a node's health itself"),
                predicate=HEALTHY_NODE_PREDICATE,
                next_attempt="when runtime/intr_pinned/ is re-vendored at a pinned LLM-adapter commit (LC-KV-13/14)")
        if not self._EXERCISE_ONLY_UNPINNED_DECIDER and pinned_decider_identity(self.healthy_node_evaluator) is None:
            # LC-KV-10 (P1 rev 4, class A): pinned by identity, never by what a callable says about itself
            return None, None, layer1_refusal(request, "LAYER1_NOT_EVALUATED_THROUGH_EVALUATE_ANCHORED", (
                "the layer-1 health decider is not the evaluate_anchored object loaded from the digest-checked "
                f"vendored bytes ({PINNED_ANCHORED_EVALUATOR['source_sha256']}, evaluator {pin['source_sha256']}); "
                "a callable's __module__, __qualname__ or source filename is never accepted as its identity"),
                predicate=HEALTHY_NODE_PREDICATE, failure_class="C",
                next_attempt="when KVInterlockRuntime is constructed without an injected decider")
        cite = None
        if evidence is not None:
            cite = evidence.get("health_report_receipt_sha256") if isinstance(evidence, dict) else evidence
            if not (isinstance(evidence, dict) and set(evidence) <= {"health_report_receipt_sha256"}
                    and (cite is None or _is_sha256_uri(cite))):
                return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                    "healthy_node_evidence may only cite health_report_receipt_sha256 (a sha256 receipt address); "
                    "health itself is never caller-asserted"), predicate=HEALTHY_NODE_PREDICATE, failure_class="C")
        ctx, refusal = self._access_context(request, envelope)
        if refusal is not None:
            return None, None, refusal
        try:
            return self._evaluate_health(request, ctx, cite)
        finally:
            if ctx.get("scratch"):
                shutil.rmtree(ctx["scratch"], ignore_errors=True)

    def _evaluate_health(self, request: dict[str, Any], ctx: dict[str, Any], cite: Any
                         ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """Layer 1's health decision: #432 evaluate_anchored (Lane B's anchored-root check, authoritative, then the
        unchanged pinned evaluate over the anchored root). KV passes only what it observed: the org ledger at the
        observed head and its HEAD.json pin, the deployment's endpoint, the observed transport state, the
        transport-authenticated node and require_admission=True. KV then keeps its stricter checks: the exact ALLOW
        shape, the anchor block, and the authenticated node_identity_key equal to the anchored genesis key."""
        node_ref = ctx["identity"]["node_id"]
        try:
            # #432 @a2ee67e6 (LC-KV-16 inside the wrapper): the node_id is what the identity proof establishes (the
            # transport-authenticated node is passed as claimed_node_id, which must agree); the org ledger is read from
            # the contract designation in the object store KV bound, accepted only at the contract-pinned genesis and
            # with the append route's head attestation; transport is read from the node's receipts and counts only
            # with its InTr carrier on that authenticated chain (the observed state is passed, recorded, and decides
            # nothing there); admission is always required; the chain repository is passed through.
            out = self.healthy_node_evaluator(
                node_ref, endpoint=copy.deepcopy(ctx["endpoint"]), org_ledger_git_dir=ctx["org_ledger_git_dir"],
                org_ledger_head_receipt_sha256=ctx["org_ledger_head_receipt_sha256"],
                org_ledger_head_attestation=copy.deepcopy(ctx["org_ledger_head_attestation"]),
                identity_proof=copy.deepcopy(ctx["identity_proof"]), transport_state=ctx["transport_state"],
                report_receipt_sha256=cite, repository=HEALTHY_NODE_LEDGER_LOCATION["chain_repository"])
        except Exception as exc:  # an evaluator fault is a refusal, never an admission
            out = {"disposition": "FAIL_CLOSED", "failure_code": HEALTHY_NODE_REFUSAL_CODE, "reason": "EVALUATOR_FAULT",
                   "required_evidence_or_repair": f"the evaluator raised {type(exc).__name__}"}
        if not isinstance(out, dict) or out.get("disposition") != "ALLOW":
            evaluation = copy.deepcopy(out) if isinstance(out, dict) else None
            reason = (evaluation or {}).get("reason")
            failure_code = (evaluation or {}).get("failure_code")
            if failure_code in (INTR_TRANSPORT_REFUSAL_CODE, IDENTITY_REFUSAL_CODE):
                # evaluate_anchored enforces transport (from receipts) and identity (from the proof); authoritative
                return None, None, layer1_refusal(request, str(reason), (
                    f"evaluate_anchored refused {node_ref!r} ({reason}: {evaluation.get('required_evidence_or_repair')}; "
                    f"{evaluation.get('detail')})"), predicate=evaluation.get("failed_predicate") or HEALTHY_NODE_PREDICATE,
                    failure_class="C" if reason == "NODE_IDENTITY_PROOF_INVALID" else "B",
                    health_evaluation=evaluation, retry_entrypoint=evaluation.get("retry_entrypoint") or LAYER1_RETRY,
                    owning_existing_goal=evaluation.get("owning_existing_goal") or GOAL_REF,
                    next_attempt=evaluation.get("next_attempt"), failure_code=failure_code)
            if (evaluation or {}).get("schema") == PINNED_ANCHORED_EVALUATOR["result_schema"]:
                # Lane B's anchored-root check refused the node root; its six fields are authoritative and carried.
                return None, None, layer1_refusal(request, f"NODE_ROOT_NOT_ANCHORED_{reason}", (
                    f"evaluate_anchored refused the {(ctx.get('endpoint') or {}).get('endpoint_kind')!r} root of "
                    f"{node_ref!r} ({reason}: {evaluation.get('required_evidence_or_repair')}; {evaluation.get('detail')})"),
                    predicate=evaluation.get("failed_predicate") or ANCHOR_PREDICATE,
                    failure_class="B" if reason in ANCHOR_CLASS_B_REASONS + EPHEMERAL_SIGNER_REASONS else "C",
                    health_evaluation=evaluation,
                    retry_entrypoint=evaluation.get("retry_entrypoint") or LAYER1_RETRY,
                    owning_existing_goal=EPHEMERAL_SIGNER_OWNER if reason in EPHEMERAL_SIGNER_REASONS
                    else evaluation.get("owning_existing_goal") or GOAL_REF,
                    next_attempt=EPHEMERAL_SIGNER_NEXT if reason in EPHEMERAL_SIGNER_REASONS
                    else evaluation.get("next_attempt"),
                    # #432 @c4cfc145 (Lane D finding 3): evaluate_anchored's own per-kind failure_code is carried
                    failure_code=evaluation.get("failure_code") or ANCHOR_REFUSAL_CODE)
            # No receipted report yet (the #429 producer is not admitted): class B.
            failure_class = "B" if reason == "HEALTH_REPORT_MISSING" else "C"
            return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"the pinned healthy-node evaluator did not ALLOW {node_ref!r}"
                + (f" ({(evaluation or {}).get('disposition')} {reason}: "
                   f"{(evaluation or {}).get('required_evidence_or_repair')})" if evaluation else "")),
                predicate=HEALTHY_NODE_PREDICATE, failure_class=failure_class, health_evaluation=evaluation,
                next_attempt=(evaluation or {}).get("next_attempt") or "on the node's next receipted HEALTHY report")
        anchored = out.get("anchor") if isinstance(out.get("anchor"), dict) else {}
        endpoint_kind = (ctx.get("endpoint") or {}).get("endpoint_kind")
        problem, cause = None, HEALTHY_NODE_REFUSAL_CODE
        if any(out.get(k) != v for k, v in _HEALTHY_RECEIPT_EXACT.items()):
            problem = "the evaluator's ALLOW does not carry the pinned interface fields (require_admission=True)"
        elif out.get("node_id") != node_ref:
            problem = "the evaluator's ALLOW names another node than the transport-authenticated identity"
        elif not _is_sha256_uri(out.get("health_report_receipt_sha256")) \
                or not _is_sha256_uri(out.get("chain_head_receipt_sha256")):
            problem = "the evaluator's ALLOW binds no receipted health report on a ledger chain"
        elif cite is not None and out.get("health_report_receipt_sha256") != cite:
            problem = "the evaluator's ALLOW is for another health report than the one cited"
        elif anchored.get("schema") != PINNED_ANCHORED_EVALUATOR["result_schema"] \
                or anchored.get("disposition") != "ALLOW" or anchored.get("node_id") != node_ref \
                or anchored.get("endpoint_kind") != endpoint_kind or endpoint_kind not in NODE_ROOT_ENDPOINT_KINDS \
                or anchored.get("org_ledger_head_receipt_sha256") != ctx["org_ledger_head_receipt_sha256"] \
                or anchored.get("evaluator_sha256") != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"] \
                or anchored.get("pinned_code_digests_sha256") != PINNED_ANCHORED_EVALUATOR["pinned_code_digests_sha256"] \
                or anchored.get("pinned_digests") != PINNED_DIGESTS_FROM_GENESIS \
                or not _is_sha256_uri(anchored.get("genesis_receipt_sha256")):
            problem = ("the ALLOW is not evaluate_anchored's over the bound endpoint at the observed org-ledger head "
                       "(anchor block absent or for another node, kind, head, evaluator, pin set or pinned digests)")
        elif (out.get("identity") or {}).get("node_id") != node_ref \
                or (out.get("identity") or {}).get("established_by") != IDENTITY_ESTABLISHED_BY:
            # #432 @a2ee67e6 returns ALLOW only after its transport-record and InTr-carrier stages pass, so KV's former
            # re-check of observed_transport INTERLOCK_INTR/INSTALLED on the ALLOW is dropped as a duplicate.
            problem = "the ALLOW does not carry evaluate_anchored's proven identity for the transport-authenticated node"
        else:
            chain, reason, _ = _read_chain(str(anchored.get("ledger_root") or ""))
            genesis = chain[-1] if chain and reason is None else {}
            genesis_key = (genesis.get("evidence") or {}).get("node_identity_key") \
                if isinstance(genesis.get("evidence"), dict) else None
            if genesis.get("receipt_sha256") != anchored.get("genesis_receipt_sha256") or genesis_key is None \
                    or genesis_key != ctx["identity"]["node_identity_key"]:
                cause = "REQUESTER_KEY_NOT_THE_ANCHORED_NODE_IDENTITY_KEY"
                problem = ("the transport-authenticated node_identity_key is not the key the anchored genesis binds; "
                           "a node is admitted only under the key its anchored ledger was opened with")
        if problem:
            return None, None, layer1_refusal(request, cause, problem, predicate=HEALTHY_NODE_PREDICATE,
                                              failure_class="C", health_evaluation=copy.deepcopy(out))
        ctx["binding"] = {**ctx["binding"], "endpoint_kind": endpoint_kind,
                          "endpoint_genesis_receipt_sha256": anchored["genesis_receipt_sha256"],
                          "node_identity_key": copy.deepcopy(genesis_key),
                          "anchor": {k: copy.deepcopy(anchored.get(k)) for k in (
                              "anchor", "anchor_source_receipt_sha256", "anchor_destination_receipt_sha256",
                              "node_ledger_opened", "location", "ledger_lifetime", "node_kind", "org_ledger_location")
                              if k in anchored},
                          "anchored_by": PINNED_ANCHORED_EVALUATOR_ID}
        recorded = copy.deepcopy(out)
        # the node root's local filesystem path is a deployment detail, not evidence: the receipt binds the endpoint
        # by its anchored genesis (genesis_receipt_sha256) instead, so receipts are reproducible across machines
        recorded["anchor"].pop("ledger_root", None)
        return recorded, ctx, None

    def _mint_kv_access_receipt(self, request: dict[str, Any], envelope: dict[str, Any], intr_receipt_ref: str,
                                healthy: dict[str, Any], response: dict[str, Any],
                                ctx: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schema": KV_ACCESS_RECEIPT_SCHEMA,
            "boundary": LAYER1_BOUNDARY,
            "layer": 1,
            "hop_index": 0,
            "from_role": "DEVICE",
            "to_role": "KV",
            "minted_by": "KVInterlockRuntime.handle",
            "endpoint_kind": "KV",
            "endpoint_kind_schema": ENDPOINT_KIND_SCHEMA,
            "request_id": request["request_id"],
            "operation": request["operation"],
            "packet_id": envelope["packet_id"],
            "intr_receipt_ref": intr_receipt_ref,
            "requester_node_ref": ctx["identity"]["node_id"],
            "requester_identity": copy.deepcopy(ctx["identity"]),
            "intr_transport_state": ctx["transport_state"],
            "intr_transport_id": ctx["transport_id"],
            "healthy_node_ledger_binding": copy.deepcopy(ctx["binding"]),
            "trust_anchors_label": ctx["trust_anchors_label"],
            "kv_boundary_ref": envelope["boundary_proof"]["next_boundary_identity_ref"],
            "healthy_node_predicate": HEALTHY_NODE_PREDICATE,
            "healthy_node_receipt": healthy,
            **_layer1_decider_record(self.healthy_node_evaluator),
            "granted_scope": list(response["granted_scope"]),
            "response_hash": response["receipt"]["response_hash"],
            "prior_receipt_hash": None,
            # KV-SKAP-LEDGER-LOCATION-001: the receipt belongs on KV's own receipt chain (_StegVerse/Receipts)
            "receipt_ledger": receipt_ledger_binding(KV_LEDGER),
            "authority_effect": "NONE",
        }
        receipt = {**body, "receipt_hash": sha256_uri(body)}
        self._kv_access_receipts[receipt["receipt_hash"]] = copy.deepcopy(receipt)
        return receipt

    def handle(
        self,
        request: dict[str, Any],
        *,
        intr_envelope: dict[str, Any],
        intr_receipt_ref: str,
        healthy_node_evidence: Any = None,
    ) -> dict[str, Any]:
        """Layer 1 (INTR_DEVICE_KV). Every refusal is returned as a six-field FAIL_CLOSED, never raised."""
        try:
            self._validate_request(request)
            self._validate_intr_admission(request, intr_envelope, intr_receipt_ref)
        except KVInterlockRuntimeError as exc:
            return layer1_refusal(request, "INTR_DEVICE_KV_TRANSITION_NOT_ADMITTED", str(exc), failure_class="C")
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return layer1_refusal(request, "INTR_DEVICE_KV_TRANSITION_MALFORMED", f"{type(exc).__name__}: {exc}",
                                  failure_class="C")
        healthy, ctx, refusal = self._healthy_node(request, intr_envelope, healthy_node_evidence)
        if refusal is not None:
            return refusal
        try:
            response = self._decide(request, intr_envelope, intr_receipt_ref)
        except KVInterlockRuntimeError as exc:
            return layer1_refusal(request, "KV_INTERLOCK_RECEIPT_NOT_PERSISTED", str(exc), failure_class="A")
        if response["decision"] == "ALLOW_BOUNDED_CONTEXT":
            response["kv_access_receipt"] = self._mint_kv_access_receipt(
                request, intr_envelope, intr_receipt_ref, healthy, response, ctx)
        return response

    def _decide(self, request: dict[str, Any], intr_envelope: dict[str, Any],
                intr_receipt_ref: str) -> dict[str, Any]:
        try:
            authority_ok = self.authority_validator(
                request["authority_ref"], request, intr_envelope
            )
        except Exception:
            authority_ok = False
        if authority_ok is not True:
            return self._fail_closed(
                request, intr_receipt_ref, "AUTHORITY_NOT_ADMITTED"
            )

        try:
            decision = self.policy_evaluator(copy.deepcopy(request))
        except Exception:
            return self._fail_closed(
                request, intr_receipt_ref, "POLICY_EVALUATION_FAILED"
            )

        try:
            return self._apply_policy_decision(request, intr_receipt_ref, decision)
        except KVInterlockRuntimeError:
            return self._fail_closed(
                request, intr_receipt_ref, "POLICY_RESULT_REJECTED"
            )

    def _validate_request(self, request: dict[str, Any]) -> None:
        if not isinstance(request, dict):
            raise KVInterlockRuntimeError("request must be an object")
        if not REQUEST_REQUIRED.issubset(request):
            raise KVInterlockRuntimeError("request missing required fields")
        if not set(request).issubset(REQUEST_ALLOWED):
            raise KVInterlockRuntimeError("request contains unsupported fields")
        if request["schema_version"] != REQUEST_SCHEMA:
            raise KVInterlockRuntimeError("request schema mismatch")
        if request["operation"] not in ALLOWED_OPERATIONS:
            raise KVInterlockRuntimeError("unsupported operation")
        for field in (
            "request_id", "purpose", "record_class",
            "minimum_necessary_justification", "authority_ref",
        ):
            if not isinstance(request[field], str) or not request[field]:
                raise KVInterlockRuntimeError(f"{field} required")
        requester = request["requester"]
        if (
            not isinstance(requester, dict)
            or set(requester) != {"module", "component"}
            or not all(isinstance(requester[key], str) and requester[key] for key in requester)
        ):
            raise KVInterlockRuntimeError("requester invalid")
        if not _unique_strings(request["requested_scope"]):
            raise KVInterlockRuntimeError("requested_scope invalid")
        if any(_contains_forbidden_name(scope) for scope in request["requested_scope"]):
            raise KVInterlockRuntimeError("secret-bearing scope prohibited")
        if request["disclosure_mode"] not in {
            "BOUNDED_CONTEXT", "SOURCE_REFERENCE_ONLY", "ORIGINAL_ARTIFACT_REVIEW"
        }:
            raise KVInterlockRuntimeError("disclosure_mode invalid")
        selector = request.get("selector")
        if selector is not None:
            if request["operation"] != "REQUEST":
                raise KVInterlockRuntimeError("selector only allowed for REQUEST")
            if (
                not isinstance(selector, dict)
                or set(selector) != {"directory_id", "canonical_path"}
                or not all(isinstance(selector.get(key), str) and selector.get(key) for key in ("directory_id", "canonical_path"))
            ):
                raise KVInterlockRuntimeError("selector invalid")
        candidate = request.get("candidate_writeback")
        if request["operation"] == "COMMIT_CANDIDATE":
            if (
                not isinstance(candidate, dict)
                or not isinstance(candidate.get("candidate_type"), str)
                or not candidate.get("candidate_type")
                or not isinstance(candidate.get("payload_ref"), str)
                or not candidate.get("payload_ref")
            ):
                raise KVInterlockRuntimeError("candidate_writeback required")
            if set(candidate) - {"candidate_type", "payload_ref", "requested_destination"}:
                raise KVInterlockRuntimeError("candidate_writeback fields invalid")
        elif candidate is not None:
            raise KVInterlockRuntimeError("candidate_writeback only allowed for COMMIT_CANDIDATE")

    def _validate_intr_admission(
        self,
        request: dict[str, Any],
        envelope: dict[str, Any],
        intr_receipt_ref: str,
    ) -> None:
        if not _is_sha256_uri(intr_receipt_ref):
            raise KVInterlockRuntimeError("verified InTr receipt reference required")
        if not isinstance(envelope, dict):
            raise KVInterlockRuntimeError("InTr envelope required")
        if not ENVELOPE_REQUIRED.issubset(envelope):
            raise KVInterlockRuntimeError("InTr envelope missing required fields")
        if not set(envelope).issubset(ENVELOPE_ALLOWED):
            raise KVInterlockRuntimeError("InTr envelope contains unsupported fields")
        exact = {
            "schema": ENVELOPE_SCHEMA,
            "protocol": "InTr",
            "direction": "REQUEST",
            "source_role": "DEVICE",
            "next_role": "KV",
            "payload_schema_version": REQUEST_SCHEMA,
        }
        for key, expected in exact.items():
            if envelope.get(key) != expected:
                raise KVInterlockRuntimeError(f"InTr envelope {key} mismatch")
        if envelope.get("request_id") != request["request_id"]:
            raise KVInterlockRuntimeError("InTr request binding mismatch")
        if envelope.get("operation") != request["operation"]:
            raise KVInterlockRuntimeError("InTr operation binding mismatch")
        if envelope.get("payload_hash") != sha256_uri(request):
            raise KVInterlockRuntimeError("InTr payload hash mismatch")
        if not isinstance(envelope.get("packet_id"), str) or not envelope["packet_id"]:
            raise KVInterlockRuntimeError("InTr packet id required")
        if not isinstance(envelope.get("sealed_material_ref"), str) or not envelope["sealed_material_ref"]:
            raise KVInterlockRuntimeError("sealed material reference required")
        authority = envelope.get("authority")
        if authority != {
            "authority_transfer": False,
            "transport_grants_execution_authority": False,
            "model_output_grants_execution_authority": False,
            "credential_authority_effect": "NONE",
        }:
            raise KVInterlockRuntimeError("InTr authority boundary mismatch")
        proof = envelope.get("boundary_proof")
        if (
            not isinstance(proof, dict)
            or set(proof) != {
                "required", "source_identity_ref",
                "next_boundary_identity_ref", "verification_state",
            }
            or proof.get("required") is not True
            or proof.get("verification_state") != "VERIFIED"
            or not isinstance(proof.get("source_identity_ref"), str)
            or not proof.get("source_identity_ref")
            or not isinstance(proof.get("next_boundary_identity_ref"), str)
            or not proof.get("next_boundary_identity_ref")
        ):
            raise KVInterlockRuntimeError("verified boundary proof required")
        receipt_policy = envelope.get("receipt_policy")
        if receipt_policy != {
            "receipt_required": True,
            "receipt_contains_payload_plaintext": False,
            "receipt_chain_required": True,
            "ambiguous_disposition": "FAIL_CLOSED",
        }:
            raise KVInterlockRuntimeError("InTr receipt policy mismatch")
        expires_at = envelope.get("expires_at")
        if expires_at is not None and _parse_time(expires_at) <= self.clock():
            raise KVInterlockRuntimeError("InTr envelope expired")

    def _apply_policy_decision(
        self,
        request: dict[str, Any],
        intr_receipt_ref: str,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(policy, dict):
            raise KVInterlockRuntimeError("policy result must be an object")
        decision = policy.get("decision")
        if decision not in ALLOWED_DECISIONS:
            raise KVInterlockRuntimeError("policy decision invalid")
        granted = policy.get("granted_scope", [])
        context = policy.get("context", {})
        source_refs = policy.get("source_refs", [])
        if not _unique_strings(granted):
            raise KVInterlockRuntimeError("granted scope invalid")
        if not set(granted).issubset(request["requested_scope"]):
            raise KVInterlockRuntimeError("policy scope expansion")
        if any(_contains_forbidden_name(scope) for scope in granted):
            raise KVInterlockRuntimeError("secret-bearing grant prohibited")
        if not isinstance(context, dict):
            raise KVInterlockRuntimeError("context must be object")
        if not set(context).issubset(granted):
            raise KVInterlockRuntimeError("context exceeds granted scope")
        if not _context_is_safe(context):
            raise KVInterlockRuntimeError("secret-like context prohibited")
        if not _unique_strings(source_refs):
            raise KVInterlockRuntimeError("source refs invalid")
        policy_profile = policy.get("policy_profile")
        if not isinstance(policy_profile, str) or not policy_profile:
            raise KVInterlockRuntimeError("policy profile required")

        if decision != "ALLOW_BOUNDED_CONTEXT":
            granted = []
            context = {}

        candidate_ref = None
        if request["operation"] == "COMMIT_CANDIDATE":
            if decision == "ALLOW_BOUNDED_CONTEXT":
                if self.candidate_store is None:
                    raise KVInterlockRuntimeError("candidate persistence unavailable")
                candidate_record = {
                    "schema": "kv.interlock.candidate.v1",
                    "request_id": request["request_id"],
                    "authority_ref": request["authority_ref"],
                    "candidate_type": request["candidate_writeback"]["candidate_type"],
                    "payload_ref": request["candidate_writeback"]["payload_ref"],
                    "requested_destination": request["candidate_writeback"].get("requested_destination"),
                    "intr_receipt_ref": intr_receipt_ref,
                    "canonical_state_changed": False,
                    "candidate_only": True,
                    "authority_effect": "NONE",
                }
                candidate_ref = self.candidate_store(candidate_record)
                if not isinstance(candidate_ref, str) or not candidate_ref:
                    raise KVInterlockRuntimeError("candidate store did not return opaque reference")
            context = {}

        return self._build_response(
            request=request,
            intr_receipt_ref=intr_receipt_ref,
            decision=decision,
            granted_scope=granted,
            context=context,
            source_refs=source_refs,
            policy_profile=policy_profile,
            redaction_profile=policy.get("redaction_profile"),
            writeback_candidate_ref=candidate_ref,
        )

    def _fail_closed(
        self,
        request: dict[str, Any],
        intr_receipt_ref: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._build_response(
            request=request,
            intr_receipt_ref=intr_receipt_ref,
            decision="FAIL_CLOSED",
            granted_scope=[],
            context={},
            source_refs=[intr_receipt_ref],
            policy_profile=f"KV-INTERLOCK-v1:{reason}",
            redaction_profile=None,
            writeback_candidate_ref=None,
        )

    def _build_response(
        self,
        *,
        request: dict[str, Any],
        intr_receipt_ref: str,
        decision: str,
        granted_scope: list[str],
        context: dict[str, Any],
        source_refs: list[str],
        policy_profile: str,
        redaction_profile: str | None,
        writeback_candidate_ref: str | None,
    ) -> dict[str, Any]:
        now = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        all_source_refs = list(dict.fromkeys([intr_receipt_ref, *source_refs]))
        receipt_seed = {
            "request_id": request["request_id"],
            "decision": decision,
            "timestamp": now,
            "intr_receipt_ref": intr_receipt_ref,
        }
        receipt: dict[str, Any] = {
            "receipt_id": "kv-interlock-receipt:" + sha256_hex(receipt_seed),
            "policy_profile": policy_profile,
            "authority_ref": request["authority_ref"],
            "requested_scope": list(request["requested_scope"]),
            "granted_scope": list(granted_scope),
            "source_refs": all_source_refs,
            "redaction_profile": redaction_profile,
            "decision": decision,
            "timestamp": now,
            "response_hash": "",
            "writeback_candidate_ref": writeback_candidate_ref,
        }
        response = {
            "schema_version": RESPONSE_SCHEMA,
            "request_id": request["request_id"],
            "decision": decision,
            "granted_scope": list(granted_scope),
            "context": copy.deepcopy(context),
            "source_refs": all_source_refs,
            "receipt": receipt,
        }
        receipt["response_hash"] = response_hash(response)
        persisted_ref = self.receipt_store(copy.deepcopy(receipt))
        if not isinstance(persisted_ref, str) or not persisted_ref:
            raise KVInterlockRuntimeError("receipt persistence failed")
        return response