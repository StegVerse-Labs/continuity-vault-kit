from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable

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
# (INTR_DEVICE_KV). It first requires REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE, decided by the healthy-node
# evaluator that InTr owns: LC-KV-13/14, Lane B, StegVerse-org/LLM-adapter llm_adapter/healthy_node_evaluator.py at the
# pinned commit. It is vendored byte-identical in runtime/intr_pinned/ and verified by sha256 before every resolution.
# This runtime never decides health itself.
# * It calls the evaluator with require_admission=True over the node-exchange transition ledger bound to this runtime.
#   The ledger is never supplied by the requester.
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
#: The source is byte-identical at #428 @0b37fe3b, at the producer PR #429 @5f5f7bbe (contains #428), and at #430
#: @4e1499ab (now @3c106de4, same evaluator bytes), which carries #429 and adds the class B inputs. The ALLOW shape is
#: unchanged. Admission order: #429 lands
#: with or before #428. #429 and #430 only append sections to the interface doc, so each doc digest is recorded.
#: A final re-vendor follows once Lane B's stack settles.
#:   evaluate(node_id, *, ledger_root, transport_state, report_receipt_sha256, require_admission, repository) -> dict
PINNED_HEALTHY_NODE_EVALUATOR = {
    "repository": "StegVerse-org/LLM-adapter",
    "commit": "0b37fe3b786a2de687235f5d9d146af49ffee9cd",
    "pull_request": "StegVerse-org/LLM-adapter#428 (draft)",
    "module": "llm_adapter.healthy_node_evaluator",
    "callable": "evaluate",
    "source_path": "llm_adapter/healthy_node_evaluator.py",
    "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
    "interface_doc": "docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md",
    "interface_doc_sha256": "sha256:757d697ca385f5d4709d8b26e51119330bb685b4770512312313fc42460bb76d",
    "vendored_module": "runtime.intr_pinned.healthy_node_evaluator",
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
    ],
    "admission_order": "StegVerse-org/LLM-adapter#429 lands with or before #428",
    "re_vendor": "a final re-vendor follows once Lane B's stack (#429, #430 and the #431 onboarding) settles",
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
    "StegVerse-org/LLM-adapter#431 (Lane B G-8 draft, the StegVerse-org/LLM-adapter organization-ledger onboarding, "
    "modelled on StegVerse-org/StegVerse-SDK#558). It binds repository_ledger_location in "
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


def _callable_source_sha256(fn: Any) -> str | None:
    """sha256 of the bytes of the file that defines fn (the observed source, never the pin's claim)."""
    try:
        return _file_sha256(inspect.getsourcefile(fn))
    except Exception:
        return None


def resolve_pinned_healthy_node_evaluator() -> tuple[Callable[..., Any] | None, str]:
    """(the pinned evaluator, "") when the vendored bytes re-derive the pinned sha256, else (None, why not)."""
    try:
        module = importlib.import_module("runtime.intr_pinned.healthy_node_evaluator")
    except Exception as exc:
        return None, f"the vendored pinned evaluator does not import ({type(exc).__name__})"
    observed = _file_sha256(getattr(module, "__file__", None))
    if observed != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return None, (f"the vendored evaluator source hashes to {observed}, not the pinned "
                      f"{PINNED_HEALTHY_NODE_EVALUATOR['source_sha256']}")
    candidate = getattr(module, PINNED_HEALTHY_NODE_EVALUATOR["callable"], None)
    return (candidate, "") if callable(candidate) else (None, "the vendored evaluator has no evaluate callable")


def evaluator_identity(evaluator: Any) -> str:
    module = getattr(evaluator, "__module__", "?")
    if module == PINNED_HEALTHY_NODE_EVALUATOR["vendored_module"]:
        module = PINNED_HEALTHY_NODE_EVALUATOR["module"]
    return f"{module}.{getattr(evaluator, '__qualname__', type(evaluator).__name__)}"


# --- LC-KV-15: the trust anchors layer 1 binds to (StegVerse-Labs/.github#3330, P1 DENY on cvk#258 @61104a57) -------
# Layer 1 no longer trusts anything its constructor or a requester hands it for the three inputs P1 found bypassable:
# * the ledger root, which is bound only by contract location at an exactly observed org-ledger head, or to a node's
#   temporary ledger anchored by a NODE_LEDGER_OPENED receipt (Coordination ruling, Oct 23);
# * the requester identity, which is derived from the installed InTr transport's verification of the envelope and never
#   read from a caller field;
# * the transport state, which is the observed transport's state, else UNKNOWN_NOT_AUTHENTICALLY_OBSERVED.
# TRUST_ANCHORS holds what KV pins for those. Production code never mutates it. Every value is None or empty today,
# because none of it is authentically observed yet, so the real path is a six-field FAIL_CLOSED until
# StegVerse-Labs/.github#3255 (org-ledger genesis), StegVerse-org/LLM-adapter#431 (onboarding) and #429 (producer) are
# admitted and the InTr transport is installed. The tests' E0 harness (tests/kv_two_layer_e0.py) swaps in labelled E0
# anchors inside an explicit scope and restores these afterwards. Every receipt records the anchors' label, and layer 2
# and the finish point refuse a receipt minted under different anchors than the ones in force.
UNKNOWN = "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED"
PRODUCTION_TRUST_ANCHORS_LABEL = "PRODUCTION"
TRUST_ANCHORS: dict[str, Any] = {
    "label": PRODUCTION_TRUST_ANCHORS_LABEL,
    # sha256 of the LLM-adapter chain's genesis receipt at the contract location. UNKNOWN until #431 onboards it.
    "healthy_node_ledger_genesis_receipt_sha256": None,
    # The installed InTr transport: an object with transport_id, state and authenticate(envelope) ->
    # {"node_id", "node_identity_key"} | None. No installed transport is observed (Lane B / InTr).
    "intr_transport": None,
    # issuer ("ORGANIZATION_LEDGER" | "TV/TVC") -> verify(node_ledger_opened_receipt) -> bool. Empty: Lane B's anchor
    # schema is pending, and TV/TVC receipts are unsigned (TVC#537, LC-KV-08), so no anchor issuer is verifiable.
    "node_ledger_anchor_issuers": {},
}
#: The NODE_HEALTH_REPORTED producer (LC-KV-13/#429). An anchored temporary ledger's health receipts must carry it.
PINNED_NODE_HEALTH_REPORT_PRODUCER = {
    "repository": "StegVerse-org/LLM-adapter",
    "source_path": "llm_adapter/node_health_report_producer.py",
    "source_sha256": "sha256:21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361",
    "observed_at": [
        {"pull_request": "StegVerse-org/LLM-adapter#429 (draft)", "commit": "5f5f7bbeea96d5f313effaa02f86b01196465247"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (draft)", "commit": "3c106de4d9b87da498e620e5db33f8b922773c26"},
    ],
}
# Org InTr endpoint model (Coordination/Lane B, Oct 23): every InTr endpoint declares endpoint_kind, one of ORG, KV,
# SKAP_VAULT, PERMANENT, EPHEMERAL or GATEWAY, reusing the org InTr classes (INTR_MESH_PATH_TRANSFER,
# ORGANIZATION_INTR_DESTINATION_INGRESS, intr_path_ingress, protocol.json). Lane B has not published the endpoint_kind
# schema, so KV declares only endpoint_kind and the ledger binding, marked pending; cvk references none of those
# class names yet and does not adopt them before the schema exists. KV is endpoint_kind KV (layer 1's receipts), the
# SKAP Vault is SKAP_VAULT (layer 2's receipts, reachable only via InTr from inside KV), the contract-location chain is
# ORG and an anchored temporary node ledger is EPHEMERAL (StegApp/StegBrowser/StegNode generated through StegOS, with
# NODE_LEDGER_OPENED at generation time). KV's and the SKAP Vault's own ledgers and ingress/egress are not built here:
# six-field FAIL_CLOSED ENDPOINT_KIND_SCHEMA_PENDING (class B, retry Lane B's endpoint_kind schema draft).
ENDPOINT_KINDS = ("ORG", "KV", "SKAP_VAULT", "PERMANENT", "EPHEMERAL", "GATEWAY")
ENDPOINT_KIND_SCHEMA = "PENDING_LANE_B_ENDPOINT_KIND_SCHEMA"
LEDGER_SOURCE_ORGANIZATION = "ORGANIZATION_LEDGER_CONTRACT_LOCATION"
LEDGER_SOURCE_TEMPORARY = "ANCHORED_TEMPORARY_NODE_LEDGER"
TEMP_LEDGER_REFUSAL_CODE = "TEMP_NODE_LEDGER_NOT_ANCHORED"
TEMP_LEDGER_PREDICATE = "TEMPORARY_NODE_LEDGER_ANCHORED_BY_NODE_LEDGER_OPENED"
#: The minimal NODE_LEDGER_OPENED anchor shape KV checks. PENDING Lane B's schema; the schema string says so on purpose
#: and is replaced by Lane B's once it exists. No IDs are invented: issuer_receipt_ref is the issuer's own receipt
#: address, whatever Lane B names it.
NODE_LEDGER_OPENED_SCHEMA = "stegverse.node-ledger-opened/PENDING_LANE_B_SCHEMA"
NODE_LEDGER_OPENED_CLASS = "NODE_LEDGER_OPENED"
NODE_LEDGER_ANCHOR_ISSUERS = ("ORGANIZATION_LEDGER", "TV/TVC")
NODE_LEDGER_OPENED_FIELDS = ("schema", "transition_class", "node_id", "node_identity_key", "genesis_receipt_sha256",
                             "issuer", "issuer_receipt_ref", "receipt_sha256")
TEMP_LEDGER_RETRY = (
    "Lane B's NODE_LEDGER_OPENED anchor receipt (issued by the org ledger or TV/TVC, binding node_id, "
    "node_identity_key and the genesis hash) and its node-ledger dissolution/disbursement transition back to "
    "StegVerse-org/.github refs/stegverse/organization-ledger:repository-ledger/StegVerse-org/LLM-adapter "
    "(LLM-adapter#431), then runtime.kv_interlock_endpoint.KVInterlockRuntime.handle")
TEMP_LEDGER_OWNER = GOAL_REF
INTR_TRANSPORT_PREDICATE = "REQUESTER_IDENTITY_AUTHENTICATED_BY_INSTALLED_INTR_TRANSPORT"
INTR_TRANSPORT_RETRY = ("the installed InTr DEVICE->KV transport (Lane B, InTr and Mesh Destinations, "
                        "StegVerse-org/.github#162), then runtime.kv_interlock_endpoint.KVInterlockRuntime.handle")
GENESIS_RETRY = ("StegVerse-Labs/.github#3255 (organization-ledger genesis) and StegVerse-org/LLM-adapter#431 "
                 "(onboarding); KV then pins the observed genesis receipt in TRUST_ANCHORS")


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


def _temp_refused(cause: str, detail: str, failure_class: str = "B") -> LedgerBindingRefused:
    return LedgerBindingRefused(cause, detail, failure_class=failure_class, predicate=TEMP_LEDGER_PREDICATE,
                                retry=TEMP_LEDGER_RETRY, owner=TEMP_LEDGER_OWNER, failure_code=TEMP_LEDGER_REFUSAL_CODE,
                                next_attempt="when Lane B's NODE_LEDGER_OPENED anchor and dissolution transition "
                                             "exist and an issuer verifier is pinned")


def _read_chain(ledger_root: str) -> tuple[list[dict[str, Any]], str | None, str]:
    module = importlib.import_module("runtime.intr_pinned.healthy_node_evaluator")
    if _file_sha256(getattr(module, "__file__", None)) != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return [], "EVALUATOR_NOT_PINNED", "the vendored evaluator does not hash to the pin"
    return module.read_chain(ledger_root, HEALTHY_NODE_LEDGER_LOCATION["chain_repository"])


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


def _bind_organization_ledger(git_path: Any) -> tuple[dict[str, Any], str]:
    """Materialize the contract-location namespace from the exactly observed org-ledger head. (binding, ledger_root)."""
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
            f"{loc['ref']}@{observed_head[:12]} has no {loc['namespace']} (LLM-adapter#431 has not onboarded it)"))
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
        pinned = TRUST_ANCHORS.get("healthy_node_ledger_genesis_receipt_sha256")
        if pinned is None:
            raise LedgerBindingRefused("HEALTHY_NODE_LEDGER_GENESIS_NOT_PINNED", (
                f"KV has no pinned genesis for the chain at the contract location (observed {genesis} at "
                f"{observed_head[:12]} is {UNKNOWN} until the genesis is admitted)"), retry=GENESIS_RETRY)
        if genesis != pinned:
            raise LedgerBindingRefused("HEALTHY_NODE_LEDGER_GENESIS_MISMATCH", (
                f"the chain at {loc['ref']}@{observed_head[:12]} starts at {genesis}, not the pinned {pinned}"),
                failure_class="C", retry=GENESIS_RETRY)
    except BaseException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    return {"kind": LEDGER_SOURCE_ORGANIZATION, "endpoint_kind": "ORG", "repository": loc["repository"], "ref": loc["ref"],
            "namespace": loc["namespace"], "observed_head": observed_head, "genesis_receipt_sha256": genesis,
            "chain_head_receipt_sha256": chain[0].get("receipt_sha256"), "node_ledger_opened": None}, workdir


def node_ledger_opened_digest(anchor: dict[str, Any]) -> str:
    return sha256_uri({k: v for k, v in anchor.items() if k != "receipt_sha256"})


def verify_node_ledger_anchor(anchor: Any, *, ledger_root: Any, identity: Any) -> dict[str, Any]:
    """Check a temporary node ledger's NODE_LEDGER_OPENED anchor. Returns the binding or raises (six fields,
    TEMP_NODE_LEDGER_NOT_ANCHORED). The anchor shape is PENDING Lane B's schema (NODE_LEDGER_OPENED_FIELDS)."""
    if not isinstance(anchor, dict):
        raise _temp_refused("NODE_LEDGER_OPENED_ANCHOR_ABSENT",
                            "a temporary node ledger is bound only with its NODE_LEDGER_OPENED anchor receipt")
    if set(anchor) != set(NODE_LEDGER_OPENED_FIELDS) or anchor.get("schema") != NODE_LEDGER_OPENED_SCHEMA \
            or anchor.get("transition_class") != NODE_LEDGER_OPENED_CLASS \
            or anchor.get("issuer") not in NODE_LEDGER_ANCHOR_ISSUERS \
            or not all(isinstance(anchor.get(f), str) and anchor[f] for f in NODE_LEDGER_OPENED_FIELDS):
        raise _temp_refused("NODE_LEDGER_OPENED_ANCHOR_MALFORMED", (
            f"the anchor must carry exactly {list(NODE_LEDGER_OPENED_FIELDS)} with transition_class "
            f"{NODE_LEDGER_OPENED_CLASS} and issuer in {list(NODE_LEDGER_ANCHOR_ISSUERS)}"), "C")
    if node_ledger_opened_digest(anchor) != anchor["receipt_sha256"]:
        raise _temp_refused("NODE_LEDGER_OPENED_ANCHOR_HASH_MISMATCH", "receipt_sha256 does not re-derive", "C")
    if not isinstance(identity, dict):
        raise _temp_refused("NODE_LEDGER_OPENED_IDENTITY_UNAUTHENTICATED",
                            "the anchor is checked against the transport-authenticated identity, which is absent")
    if anchor["node_id"] != identity.get("node_id"):
        raise _temp_refused("NODE_LEDGER_OPENED_NODE_ID_MISMATCH", (
            f"the anchor opens a ledger for {anchor['node_id']!r}, not the authenticated {identity.get('node_id')!r}"),
            "C")
    if anchor["node_identity_key"] != identity.get("node_identity_key"):
        raise _temp_refused("NODE_LEDGER_OPENED_NODE_IDENTITY_KEY_MISMATCH",
                            "the anchor's node_identity_key is not the transport-authenticated node identity key", "C")
    chain, reason, detail = _read_chain(str(ledger_root)) if isinstance(ledger_root, (str, os.PathLike)) \
        else ([], "LEDGER_ROOT_ABSENT", "no ledger_root")
    if reason is not None or not chain:
        raise _temp_refused("TEMPORARY_NODE_LEDGER_UNREADABLE", f"the temporary ledger does not read back ({reason}: "
                                                                f"{detail})", "C")
    genesis = chain[-1].get("receipt_sha256")
    if genesis != anchor["genesis_receipt_sha256"]:
        raise _temp_refused("NODE_LEDGER_OPENED_GENESIS_MISMATCH",
                            f"the temporary ledger starts at {genesis}, not the anchored "
                            f"{anchor['genesis_receipt_sha256']}", "C")
    pinned = {"evaluator_source_sha256": PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"],
              "producer_source_sha256": PINNED_NODE_HEALTH_REPORT_PRODUCER["source_sha256"]}
    for receipt in chain:
        if receipt.get("transition_class") == "NODE_HEALTH_REPORTED":
            carried = (receipt.get("evidence") or {}).get("pinned_digests") \
                if isinstance(receipt.get("evidence"), dict) else None
            if carried != pinned:
                raise _temp_refused("TEMPORARY_LEDGER_HEALTH_RECEIPT_NOT_PINNED", (
                    f"health receipt {receipt.get('receipt_sha256')} does not carry evidence.pinned_digests {pinned}"),
                    "C")
    verifier = (TRUST_ANCHORS.get("node_ledger_anchor_issuers") or {}).get(anchor["issuer"])
    try:
        issued = callable(verifier) and verifier(copy.deepcopy(anchor)) is True
    except Exception:
        issued = False
    if not issued:
        raise _temp_refused("NODE_LEDGER_OPENED_ISSUER_NOT_VERIFIED", (
            f"no verifier for issuer {anchor['issuer']!r} is pinned in TRUST_ANCHORS (Lane B's anchor schema is "
            "pending and TV/TVC receipts are unsigned: TVC#537, LC-KV-08); an unverifiable anchor is refused"))
    return {"kind": LEDGER_SOURCE_TEMPORARY, "endpoint_kind": "EPHEMERAL", "repository": None, "ref": None, "namespace": None,
            "observed_head": None, "genesis_receipt_sha256": genesis,
            "chain_head_receipt_sha256": chain[0].get("receipt_sha256"), "node_ledger_opened": copy.deepcopy(anchor)}


def bind_healthy_node_ledger(source: Any, *, identity: Any = None) -> tuple[dict[str, Any], str, str | None]:
    """The single ledger-root binding. Returns (binding, ledger_root, scratch dir to remove or None) or raises
    LedgerBindingRefused.

    source is the deployment's binding, never a requester's:
    * a git repository of StegVerse-org/.github (a path, or {"kind": LEDGER_SOURCE_ORGANIZATION, "git_dir": path}):
      the namespace is read from refs/stegverse/organization-ledger at the head observed now, and its genesis must be
      the pinned one;
    * {"kind": LEDGER_SOURCE_TEMPORARY, "ledger_root": path, "node_ledger_opened": anchor}: a node's temporary ledger,
      only with a verified NODE_LEDGER_OPENED anchor for the authenticated identity.
    Anything else is unbound and refused.
    """
    if source is None:
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, "no ledger source is bound to KV")
    if isinstance(source, dict):
        kind = source.get("kind")
        if kind == LEDGER_SOURCE_ORGANIZATION and set(source) == {"kind", "git_dir"}:
            binding, workdir = _bind_organization_ledger(source["git_dir"])
            return binding, os.path.join(workdir, *HEALTHY_NODE_LEDGER_LOCATION["namespace"].split("/")), workdir
        if kind == LEDGER_SOURCE_TEMPORARY and set(source) <= {"kind", "ledger_root", "node_ledger_opened"}:
            binding = verify_node_ledger_anchor(source.get("node_ledger_opened"), ledger_root=source.get("ledger_root"),
                                                identity=identity)
            return binding, str(source["ledger_root"]), None
        raise _temp_refused("LEDGER_SOURCE_NOT_BOUND_BY_CONTRACT", (
            "a ledger root is bound only by contract location or as an anchored temporary node ledger; a "
            "caller-supplied root without a NODE_LEDGER_OPENED anchor is refused"), "C")
    binding, workdir = _bind_organization_ledger(source)
    return binding, os.path.join(workdir, *HEALTHY_NODE_LEDGER_LOCATION["namespace"].split("/")), workdir


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
    """None when a KV-access receipt was minted under the pinned evaluator and the trust anchors in force; else why.
    Layer 2 (LC-KV-10) and the finish point both use this; neither trusts the receipt's own say-so."""
    if not isinstance(receipt, dict):
        return "LAYER1_RECEIPT_ABSENT"
    if receipt.get("healthy_node_evaluator") != PINNED_HEALTHY_NODE_EVALUATOR_ID \
            or receipt.get("healthy_node_evaluator_source_sha256") != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"
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
    if binding.get("kind") == LEDGER_SOURCE_ORGANIZATION and binding.get("endpoint_kind") == "ORG":
        pinned = TRUST_ANCHORS.get("healthy_node_ledger_genesis_receipt_sha256")
        loc = HEALTHY_NODE_LEDGER_LOCATION
        if pinned is None or binding.get("genesis_receipt_sha256") != pinned \
                or (binding.get("repository"), binding.get("ref"), binding.get("namespace")) != (
                    loc["repository"], loc["ref"], loc["namespace"]) or not binding.get("observed_head"):
            return "LAYER1_LEDGER_NOT_BOUND_BY_CONTRACT_LOCATION"
        return None
    if binding.get("kind") == LEDGER_SOURCE_TEMPORARY and binding.get("endpoint_kind") == "EPHEMERAL":
        anchor = binding.get("node_ledger_opened")
        verifier = (TRUST_ANCHORS.get("node_ledger_anchor_issuers") or {}).get(
            anchor.get("issuer") if isinstance(anchor, dict) else None)
        try:
            ok = (isinstance(anchor, dict) and node_ledger_opened_digest(anchor) == anchor.get("receipt_sha256")
                  and anchor.get("genesis_receipt_sha256") == binding.get("genesis_receipt_sha256")
                  and anchor.get("node_id") == identity.get("node_id")
                  and anchor.get("node_identity_key") == identity.get("node_identity_key")
                  and callable(verifier) and verifier(copy.deepcopy(anchor)) is True)
        except Exception:
            ok = False
        return None if ok else TEMP_LEDGER_REFUSAL_CODE
    return "LAYER1_LEDGER_NOT_BOUND_BY_CONTRACT_LOCATION"


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
        # Layer 1 consumes the InTr-owned evaluator; it never supplies one of its own. An injected evaluator (tests
        # only) is recorded with its own identity and source digest, never with the pin's.
        if healthy_node_evaluator is None:
            healthy_node_evaluator, self._evaluator_unavailable = resolve_pinned_healthy_node_evaluator()
        else:
            self._evaluator_unavailable = ""
        self.healthy_node_evaluator = healthy_node_evaluator
        # A checkout of HEALTHY_NODE_LEDGER_LOCATION's ref, bound by KV and never supplied by a requester. The evaluator
        # reads only <checkout>/<namespace>.
        self.healthy_node_ledger_checkout = healthy_node_ledger_checkout
        self._kv_access_receipts: dict[str, dict[str, Any]] = {}

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
        """LC-KV-15: bind the ledger, observe the transport and derive the requester identity from it.

        Returns (context, None) or (None, six-field refusal). Nothing here is read from a caller field: the envelope's
        boundary_proof.source_identity_ref is only compared with the identity the installed transport authenticated.
        """
        claimed = envelope["boundary_proof"]["source_identity_ref"]
        source = self.healthy_node_ledger_checkout
        temporary = isinstance(source, dict) and source.get("kind") == LEDGER_SOURCE_TEMPORARY
        binding = root = scratch = None
        try:
            if not temporary:
                binding, root, scratch = bind_healthy_node_ledger(source)
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
                    or not identity["node_id"] or not isinstance(identity.get("node_identity_key"), str) \
                    or not identity["node_identity_key"]:
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
            if temporary:
                binding, root, scratch = bind_healthy_node_ledger(source, identity=identity)
        except LedgerBindingRefused as exc:
            if scratch:
                shutil.rmtree(scratch, ignore_errors=True)
            return None, self._refused(request, exc)
        return {"ledger_root": root, "binding": binding, "scratch": scratch, "transport_state": state,
                "transport_id": transport_id, "trust_anchors_label": TRUST_ANCHORS.get("label"),
                "identity": {"node_id": identity["node_id"], "node_identity_key": identity["node_identity_key"],
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
        loc = HEALTHY_NODE_LEDGER_LOCATION
        node_ref = ctx["identity"]["node_id"]
        try:
            out = self.healthy_node_evaluator(node_ref, ledger_root=ctx["ledger_root"],
                                              transport_state=ctx["transport_state"],
                                              report_receipt_sha256=cite, require_admission=True,
                                              repository=loc["chain_repository"])
        except Exception as exc:  # an evaluator fault is a refusal, never an admission
            out = {"disposition": "FAIL_CLOSED", "failure_code": HEALTHY_NODE_REFUSAL_CODE, "reason": "EVALUATOR_FAULT",
                   "required_evidence_or_repair": f"the evaluator raised {type(exc).__name__}"}
        if not isinstance(out, dict) or out.get("disposition") != "ALLOW":
            evaluation = copy.deepcopy(out) if isinstance(out, dict) else None
            reason = (evaluation or {}).get("reason")
            if reason == "LEDGER_HEAD_UNREADABLE":  # the bound ledger has no HEAD.json: not onboarded, no genesis
                return None, None, self._refused(request, LedgerBindingRefused(
                    HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, "the bound ledger's HEAD.json is unreadable",
                    evaluation=evaluation))
            # No receipted report yet (the #429 producer is not admitted): class B.
            failure_class = "B" if reason == "HEALTH_REPORT_MISSING" else "C"
            return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"the pinned healthy-node evaluator did not ALLOW {node_ref!r}"
                + (f" ({(evaluation or {}).get('disposition')} {reason}: "
                   f"{(evaluation or {}).get('required_evidence_or_repair')})" if evaluation else "")),
                predicate=HEALTHY_NODE_PREDICATE, failure_class=failure_class, health_evaluation=evaluation,
                next_attempt=(evaluation or {}).get("next_attempt") or "on the node's next receipted HEALTHY report")
        problem = None
        if any(out.get(k) != v for k, v in _HEALTHY_RECEIPT_EXACT.items()):
            problem = "the evaluator's ALLOW does not carry the pinned interface fields (require_admission=True)"
        elif out.get("node_id") != node_ref:
            problem = "the evaluator's ALLOW names another node than the transport-authenticated identity"
        elif not _is_sha256_uri(out.get("health_report_receipt_sha256")) \
                or not _is_sha256_uri(out.get("chain_head_receipt_sha256")):
            problem = "the evaluator's ALLOW binds no receipted health report on a ledger chain"
        elif cite is not None and out.get("health_report_receipt_sha256") != cite:
            problem = "the evaluator's ALLOW is for another health report than the one cited"
        if problem:
            return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, problem,
                                              predicate=HEALTHY_NODE_PREDICATE, failure_class="C",
                                              health_evaluation=copy.deepcopy(out))
        return copy.deepcopy(out), ctx, None

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
            "healthy_node_evaluator": evaluator_identity(self.healthy_node_evaluator),
            "healthy_node_evaluator_source_sha256": _callable_source_sha256(self.healthy_node_evaluator),
            "granted_scope": list(response["granted_scope"]),
            "response_hash": response["receipt"]["response_hash"],
            "prior_receipt_hash": None,
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
