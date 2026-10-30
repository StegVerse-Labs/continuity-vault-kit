from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import sys
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
# (LC-KV-13/14): StegVerse-org/LLM-adapter's llm_adapter/healthy_node_evaluator.py evaluate(), the evaluator the
# LLM-adapter producer stack #428, #429 and #430 lands on LLM-adapter main (not yet merged), vendored byte-identical in
# runtime/intr_pinned/ and verified by sha256 before every resolution. This runtime never decides health itself.
# The InTr model this is founded on: there is no InTr hop inside one organization. A requester is a machine that has
# established itself as a healthy node and then becomes an endpoint; the node's health is read from the node's OWN
# transition ledger, which the deployment binds together with that ledger's pinned genesis receipt. No organization
# ledger is read, and nothing here crosses from an organization to LLM-adapter.
# * It calls evaluate with require_admission=True over the node ledger chain bound to this runtime. The chain, its
#   pinned genesis and the transport state are never supplied by the requester.
# * It accepts only the evaluator's exact ALLOW shape for the transport-authenticated node, then re-reads the chain
#   itself: genesis equal to the deployment's pin, head equal to the evaluator's, every receipt one the pinned
#   producers write (KV-owned check below), and the authenticated node_identity_key equal to the key the chain's own
#   NODE_IDENTITY_BINDING receipt binds.
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
#: The evaluator bytes (fdaa2005...1f58) are byte-identical at #428 @f2ccfc28, #429 @6a51553a and #430 @919851cb. None
#: of the three is merged: all are open drafts, and LLM-adapter main (e6af8c18) has no healthy_node_evaluator.py.
#:   evaluate(node_id, *, ledger_root, transport_state, report_receipt_sha256, require_admission, repository) -> dict
PINNED_HEALTHY_NODE_EVALUATOR = {
    "repository": "StegVerse-org/LLM-adapter",
    "commit": "919851cb092d353bfe6a4271d3893f129dbc1c91",
    "pull_request": "StegVerse-org/LLM-adapter#430 (open draft; carries #429 and #428)",
    "module": "llm_adapter.healthy_node_evaluator",
    "callable": "evaluate",
    "source_path": "llm_adapter/healthy_node_evaluator.py",
    "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58",
    "interface_doc": "docs/HEALTHY_NODE_EVALUATOR_INTERFACE.md",
    "interface_doc_sha256": "sha256:d4a534713ecb5d462f84b83867e30506b81839291102705497d225d4fdc9c6de",
    "vendored_path": "runtime/intr_pinned/llm_adapter/healthy_node_evaluator.py",
    "owning_task": "LC-KV-13/LC-KV-14 (InTr and Mesh Destinations lane, StegVerse-org/.github#162)",
    "provenance": [
        {"pull_request": "StegVerse-org/LLM-adapter#428 (open draft, the evaluator)",
         "commit": "f2ccfc28e1a2116d90f6a6b1f5b0baee31613036",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58"},
        {"pull_request": "StegVerse-org/LLM-adapter#429 (open draft, NODE_HEALTH_REPORTED producer; carries #428)",
         "commit": "6a51553aa5747e0e5b24e8a735022e3dc00bea5e",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (open draft, existence read-back, NODE_IDENTITY_BINDING and "
                         "NODE_HEALTH_CHECK_OBSERVED producers; carries #429 and #428)",
         "commit": "919851cb092d353bfe6a4271d3893f129dbc1c91",
         "source_sha256": "sha256:fdaa20053c527927067d16b011889ca84089b9750e95e291021310c669451f58"},
    ],
    #: #430's ADMISSION_ORDER. KV depends on these in this order and never lands before them.
    "admission_order": ("StegVerse-Labs/StegOS#426, then StegVerse-org/LLM-adapter#430, then #429, then #428 "
                        "(#430's head carries #429 and #428, so admitting #430 admits all three as one unit)"),
    #: False until #428-#430 are on LLM-adapter main; the re-vendor that flips it is a pin change in this file.
    "on_upstream_main": False,
}
#: Every file vendored byte-identical under runtime/intr_pinned/, hashed before every resolution. All are
#: byte-identical to #430 @919851cb except supplied_epoch.py, which #430 does not carry (it exists only on the
#: closed, unmerged #432 branch @eecf4843; it is the shared supplied-epoch rule that KV's own receipt ledgers and
#: crossing records call, and nothing in it names an organization-ledger or adapter ledger placement).
#: node_ingress_boundary.py is hashed but never executed: it imports the StegVerse SDK, which is not a cvk dependency.
#: KV reads its four string constants from the pinned bytes by AST (constants_only).
PINNED_INTR_FILES = {
    "repository": "StegVerse-org/LLM-adapter",
    "pull_request": PINNED_HEALTHY_NODE_EVALUATOR["pull_request"],
    "commit": PINNED_HEALTHY_NODE_EVALUATOR["commit"],
    "vendored_root": "runtime/intr_pinned",
    "vendored_files": {
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
        "llm_adapter/supplied_epoch.py": "sha256:be91daad3d5557f810872731c3ea8cc36e1f13af569e1b7634f487fd36f44534",
        ".stegverse/transition-ledger/emit.py": "sha256:9579726de7ef915ac8cd61be1ba1c5ef6e34de4ca996504374b0dce7f7c2c9c3",
        # supporting data read by the pinned modules
        ".stegverse/transition-ledger/contract.json":
            "sha256:a59040e8cabe6dc618af0ba340cb5563ce726f645a76248ccb354961d29144e7",
        ".stegverse/heartbeat-awareness.json": "sha256:87b1c4006d3829ea70626d481012791c557e97bcd580a6c3d5ccc61389a6951b",
    },
    "constants_only": {"llm_adapter/node_ingress_boundary.py": ("ADMITTED_CLASS", "REFUSED_CLASS", "RECORD_SCHEMA",
                                                               "INTERLOCK_INTR")},
    "interface_doc_sha256": PINNED_HEALTHY_NODE_EVALUATOR["interface_doc_sha256"],
}
#: The chain the evaluator reads is the requesting node's OWN transition ledger, whose receipts name this repository
#: (the evaluator's REPOSITORY). The deployment binds it, with the genesis receipt it pins for it:
#:   {"kind": NODE_CHAIN_SOURCE, "ledger_root": <read-back copy of the node's ledger>, "genesis_receipt_sha256": ...}
#: A requester never names either. No organization ledger is involved.
HEALTHY_NODE_CHAIN_REPOSITORY = "StegVerse-org/LLM-adapter"
NODE_CHAIN_SOURCE = "NODE_OWN_LEDGER_CHAIN"
HEALTHY_NODE_LEDGER_PREDICATE = "HEALTHY_NODE_OWN_LEDGER_CHAIN_BOUND_WITH_PINNED_GENESIS"
HEALTHY_NODE_LEDGER_REFUSAL_CAUSE = "HEALTHY_NODE_LEDGER_NOT_BOUND"
HEALTHY_NODE_LEDGER_ONBOARDING = (
    "the deployment's binding of the requesting node's own transition ledger ({kind: NODE_OWN_LEDGER_CHAIN, "
    "ledger_root, genesis_receipt_sha256}); the healthy-node evaluator and producers it reads are StegVerse-org/"
    "LLM-adapter#428, #429 and #430, open drafts that are not on LLM-adapter main. It stays FAIL_CLOSED until they are "
    "admitted and the deployment binds a node ledger with its pinned genesis")
HEALTHY_NODE_LEDGER_OWNER = ("KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324) via LC-KV-13 "
                             "(Lane B, InTr and Mesh Destinations, StegVerse-org/.github#162)")
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
_PINNED_LOAD_ORDER = ("healthy_node_evaluator", "ed25519_verify", "supplied_epoch", "node_receipt_common",
                      "node_existence_readback", "node_health_check_projection", "node_health_report_producer",
                      "node_identity_binding_producer")
_PINNED_EXEC_SOURCES = tuple(os.path.join(_INTR_PINNED_ROOT, "llm_adapter", name + ".py")
                             for name in _PINNED_LOAD_ORDER)
_PINNED_LOCK = threading.Lock()
_PINNED_MODULES: dict[str, Any] = {}
#: LC-KV-10 (P1 rev 4, class A): what the pinned callable IS, recorded at load time. Each executed module is compiled
#: from the exact bytes whose sha256 was just checked against its pin (never re-read from disk), and the resulting
#: function object and its code-object digest are recorded here. A decider is pinned only if it `is` that object and
#: its code object still hashes to the digest recorded at load. Names, qualnames and source filenames a callable
#: reports about itself are never consulted.
_PINNED_LOADED: dict[str, dict[str, Any]] = {}


def _pinned_bytes() -> tuple[dict[str, bytes] | None, str]:
    """({relative path: bytes}, "") with every vendored file read once and checked against its pin, else (None, why)."""
    found: dict[str, bytes] = {}
    for rel, want in PINNED_INTR_FILES["vendored_files"].items():
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
        (boundary_rel, names), = PINNED_INTR_FILES["constants_only"].items()
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
                        PINNED_INTR_FILES["vendored_files"][rel] or pinned_source != blobs[rel]:
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
        pin = PINNED_HEALTHY_NODE_EVALUATOR
        evaluator = package.healthy_node_evaluator
        if getattr(evaluator, "RESULT_SCHEMA", None) != HEALTHY_NODE_RECEIPT_SCHEMA \
                or getattr(evaluator, "REPOSITORY", None) != HEALTHY_NODE_CHAIN_REPOSITORY:
            return None, "the pinned evaluator does not declare the result schema and chain repository KV pins"
        fn = getattr(evaluator, pin["callable"], None)
        code = _code_sha256(fn)
        if code is None:
            return None, f"{pin['source_path']} defines no plain function {pin['callable']}"
        _PINNED_LOADED[PINNED_HEALTHY_NODE_EVALUATOR_ID] = {
            "object": fn, "code_sha256": code, "source_sha256": pin["source_sha256"],
            "loaded_bytes_sha256": "sha256:" + hashlib.sha256(blobs[pin["source_path"]]).hexdigest()}
        _PINNED_MODULES.update({name: getattr(package, name) for name in _PINNED_LOAD_ORDER})
        _PINNED_MODULES["node_ingress_boundary"] = boundary  # constants only (class and schema names)
        return dict(_PINNED_MODULES), ""


def resolve_pinned_healthy_node_evaluator() -> tuple[Callable[..., Any] | None, str]:
    """(the pinned evaluate, "") when every vendored byte re-derives its pin, else (None, why not)."""
    modules, why = load_pinned_intr()
    if modules is None:
        return None, why
    candidate = getattr(modules["healthy_node_evaluator"], PINNED_HEALTHY_NODE_EVALUATOR["callable"], None)
    return (candidate, "") if callable(candidate) else (None, "the vendored evaluator module has no evaluate")


NOT_PINNED_DECIDER = "NOT_THE_PINNED_OBJECT"


def pinned_decider_identity(decider: Any, pin_id: str = PINNED_HEALTHY_NODE_EVALUATOR_ID) -> str | None:
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
    return PINNED_HEALTHY_NODE_EVALUATOR_ID if pinned_decider_identity(evaluator) else NOT_PINNED_DECIDER


def _layer1_decider_record(decider: Any) -> dict[str, Any]:
    """What a KV-access receipt records for the layer-1 health decision (LC-KV-10, pinned by identity).

    Only when decider IS the loaded evaluate (identity plus load-time code digest) is the pin recorded, with the source
    digest checked on the bytes that were compiled and the code-object digest observed at load. Anything else,
    however it names itself, is recorded as NOT_THE_PINNED_OBJECT with its code digest and no source digest, which
    layer 2 and the finish point refuse."""
    if pinned_decider_identity(decider) is not None:
        loaded = _PINNED_LOADED[PINNED_HEALTHY_NODE_EVALUATOR_ID]
        return {"healthy_node_evaluator": PINNED_HEALTHY_NODE_EVALUATOR_ID,
                "healthy_node_evaluator_source_sha256": loaded["loaded_bytes_sha256"],
                "healthy_node_evaluator_code_sha256": loaded["code_sha256"]}
    return {"healthy_node_evaluator": NOT_PINNED_DECIDER, "healthy_node_evaluator_source_sha256": None,
            "healthy_node_evaluator_code_sha256": _code_sha256(decider)}


# --- LC-KV-15: the trust anchors layer 1 binds to (StegVerse-Labs/.github#3330, P1 DENY on cvk#258 @61104a57) -------
# Layer 1 trusts nothing its constructor or a requester hands it for the inputs P1 found bypassable:
# * the node's ledger chain, which is bound only by the deployment together with the genesis receipt it pins; the
#   chain must read back from that genesis to the head the evaluator saw;
# * the requester identity, which is derived from the installed InTr transport's verification of the envelope and never
#   read from a caller field, and whose node_identity_key must be the key the node's own chain binds;
# * the transport state, which is the observed transport's state, else UNKNOWN_NOT_AUTHENTICALLY_OBSERVED.
# TRUST_ANCHORS holds what KV pins for those. Production code never mutates it. Every value is None today, because none
# of it is authentically observed yet, so the real path is a six-field FAIL_CLOSED until the evaluator stack (#428,
# #429, #430) is admitted, the deployment binds a node ledger and the InTr transport is installed. The tests' E0 harness
# (tests/kv_two_layer_e0.py) swaps in labelled E0 anchors inside an explicit scope and restores these afterwards. Every
# receipt records the anchors' label, and layer 2 and the finish point refuse a receipt minted under different anchors
# than the ones in force.
UNKNOWN = "UNKNOWN_NOT_AUTHENTICALLY_OBSERVED"
PRODUCTION_TRUST_ANCHORS_LABEL = "PRODUCTION"
TRUST_ANCHORS: dict[str, Any] = {
    "label": PRODUCTION_TRUST_ANCHORS_LABEL,
    # The installed InTr transport: an object with transport_id, state and authenticate(envelope) ->
    # {"node_id", "node_identity_key"} | None. No installed transport is observed (Lane B / InTr).
    "intr_transport": None,
}
#: The NODE_HEALTH_REPORTED producer (LC-KV-13/#429): the one producer whose reports the KV-owned provenance check
#: below accepts. Byte-identical at #429 @6a51553a and #430 @919851cb.
PINNED_NODE_HEALTH_REPORT_PRODUCER = {
    "repository": "StegVerse-org/LLM-adapter",
    "source_path": "llm_adapter/node_health_report_producer.py",
    "source_sha256": "sha256:21249f2505505afd60eb14188ea638202f2926b207d64cfcf8c3bc5db2d9f361",
    "observed_at": [
        {"pull_request": "StegVerse-org/LLM-adapter#429 (open draft)", "commit": "6a51553aa5747e0e5b24e8a735022e3dc00bea5e"},
        {"pull_request": "StegVerse-org/LLM-adapter#430 (open draft)", "commit": "919851cb092d353bfe6a4271d3893f129dbc1c91"},
    ],
}
FINISH_POINT_NODE_KIND = NODE_CHAIN_SOURCE
INTR_TRANSPORT_PREDICATE = "REQUESTER_IDENTITY_AUTHENTICATED_BY_INSTALLED_INTR_TRANSPORT"
INTR_TRANSPORT_RETRY = ("the installed InTr DEVICE->KV transport (Lane B, InTr and Mesh Destinations, "
                        "StegVerse-org/.github#162), then runtime.kv_interlock_endpoint.KVInterlockRuntime.handle")
NODE_KEY_REFUSAL_CODE = "REQUESTER_KEY_NOT_THE_BOUND_NODE_IDENTITY_KEY"
PROVENANCE_REFUSAL_CODE = "NODE_CHAIN_RECEIPT_NOT_WRITTEN_BY_THE_PINNED_PRODUCERS"


class LedgerBindingRefused(Exception):
    """Raised inside bind_healthy_node_ledger; layer 1 turns it into a six-field FAIL_CLOSED."""

    def __init__(self, cause: str, detail: str, *, failure_class: str = "B", predicate: str = HEALTHY_NODE_LEDGER_PREDICATE,
                 retry: str = HEALTHY_NODE_LEDGER_ONBOARDING, owner: str = HEALTHY_NODE_LEDGER_OWNER,
                 next_attempt: str = "when the deployment binds the node's own ledger chain with its pinned genesis",
                 failure_code: str | None = None, evaluation: Any = None) -> None:
        super().__init__(f"{cause}: {detail}")
        self.cause, self.detail, self.failure_class, self.predicate = cause, detail, failure_class, predicate
        self.retry, self.owner, self.next_attempt, self.failure_code = retry, owner, next_attempt, failure_code
        self.evaluation = evaluation


def _read_chain(ledger_root: str) -> tuple[list[dict[str, Any]], str | None, str]:
    modules, why = load_pinned_intr()
    if modules is None:
        return [], "EVALUATOR_NOT_PINNED", why
    return modules["healthy_node_evaluator"].read_chain(ledger_root, HEALTHY_NODE_CHAIN_REPOSITORY)


def _chain_evidence(receipt: Any) -> dict[str, Any]:
    value = receipt.get("evidence") if isinstance(receipt, dict) else None
    return value if isinstance(value, dict) else {}


def chain_provenance_failure(chain: list[dict[str, Any]], node_id: str) -> tuple[str, str] | None:
    """(code, detail) for the first receipt after the genesis that the pinned producers do not write, or None.

    The bare evaluator accepts any well-formed receipt, so KV re-derives what the pinned producers write: every receipt's
    successor_state_sha256 is the digest of its evidence; the node's existence, identity-binding and health-check
    receipts carry the pinned classes and schemas for this node; ingress records are the pinned ingress schema for this
    node; and every health report carries the pinned producer's exact transition manifest, cites receipts that are
    EARLIER on the chain with the pinned classes, and states the status its cited health check observed. Oldest first.
    The genesis is not checked here: the deployment pins it by digest."""
    modules, why = load_pinned_intr()
    if modules is None:
        return "EVALUATOR_NOT_PINNED", why
    hne, producer = modules["healthy_node_evaluator"], modules["node_health_report_producer"]
    readback, binding = modules["node_existence_readback"], modules["node_identity_binding_producer"]
    health_check, boundary = modules["node_health_check_projection"], modules["node_ingress_boundary"]
    ordered = list(reversed(chain))
    position = {r["receipt_sha256"]: i for i, r in enumerate(ordered)}
    last_report = None
    for i, r in enumerate(ordered[1:], start=1):
        cls, ev, addr = r.get("transition_class"), _chain_evidence(r), r["receipt_sha256"]
        if r.get("successor_state_sha256") != hne.sha(ev):
            return PROVENANCE_REFUSAL_CODE, f"{addr} successor_state_sha256 is not the digest of its evidence"
        if cls in (boundary.ADMITTED_CLASS, boundary.REFUSED_CLASS):
            node = ((ev.get("node_endpoint") or {}).get("node_id") if cls == boundary.ADMITTED_CLASS
                    else ev.get("evaluated_node_id"))
            if ev.get("schema") != boundary.RECORD_SCHEMA or node not in (node_id, None) \
                    or (cls == boundary.ADMITTED_CLASS and node != node_id):
                return PROVENANCE_REFUSAL_CODE, f"{addr} is not an ingress record for {node_id}"
            continue
        schemas = {readback.TRANSITION_CLASS: readback.EVIDENCE_SCHEMA, binding.TRANSITION_CLASS: binding.EVIDENCE_SCHEMA,
                   health_check.TRANSITION_CLASS: health_check.EVIDENCE_SCHEMA, producer.REPORT_CLASS: producer.REPORT_SCHEMA}
        if cls not in schemas:
            return PROVENANCE_REFUSAL_CODE, f"{addr} class {cls!r} is written by no pinned producer"
        if ev.get("node_id") != node_id or not str(r.get("transition_id", "")).startswith(f"{cls}:{node_id}:"):
            return PROVENANCE_REFUSAL_CODE, f"{addr} names another node or a foreign transition_id"
        if ev.get("schema") != schemas[cls]:
            return PROVENANCE_REFUSAL_CODE, f"{addr} evidence schema {ev.get('schema')!r} is not {schemas[cls]}"
        if cls == producer.REPORT_CLASS:
            manifest = {"schema": producer.TRANSITION_MANIFEST_SCHEMA, "intended_action": producer.INTENDED_ACTION,
                        "transition_class": producer.REPORT_CLASS, "inputs_are_receipts_on_chain": True,
                        "producer": producer.PRODUCER, "producer_version": producer.PRODUCER_VERSION}
            cited = ev.get("evidence_receipts") if isinstance(ev.get("evidence_receipts"), dict) else {}
            wanted = (("authenticated_reciprocal_node_existence", readback.TRANSITION_CLASS),
                      ("node_identity_binding", binding.TRANSITION_CLASS), ("health_check", health_check.TRANSITION_CLASS))
            trigger = (ev.get("trigger") or {}).get("receipt_sha256") if isinstance(ev.get("trigger"), dict) else None
            ok = ev.get("transition_manifest") == manifest and ev.get("previous_health_report_receipt_sha256") == last_report
            ok = ok and trigger in position and position[trigger] < i
            for field, want_cls in wanted:
                j = position.get(cited.get(field))
                ok = ok and j is not None and j < i and ordered[j].get("transition_class") == want_cls
            if ok:
                observed = _chain_evidence(ordered[position[cited["health_check"]]]).get("status")
                ok = ev.get("observed_health_check_status") == observed and \
                    ev.get("status") == (hne.HEALTHY if observed == hne.HEALTHY else producer.UNHEALTHY)
            if not ok:
                return PROVENANCE_REFUSAL_CODE, f"{addr} does not re-derive as the pinned producer's report"
            last_report = addr
    return None


def chain_bound_identity_key(chain: list[dict[str, Any]], node_id: str) -> dict[str, Any] | None:
    """{key_id, public_key_b64} of the newest NODE_IDENTITY_BINDING receipt for node_id on the chain, else None."""
    modules, _ = load_pinned_intr()
    if modules is None:
        return None
    binding = modules["node_identity_binding_producer"]
    for receipt in chain:  # newest first
        ev = _chain_evidence(receipt)
        if receipt.get("transition_class") == binding.TRANSITION_CLASS and ev.get("node_id") == node_id:
            key = {"key_id": (ev.get("key_ref") or {}).get("key_id") if isinstance(ev.get("key_ref"), dict) else None,
                   "public_key_b64": ev.get("public_key_b64")}
            return key if all(isinstance(v, str) and v for v in key.values()) else None
    return None


def bind_healthy_node_ledger(source: Any) -> dict[str, Any]:
    """The single ledger binding: the deployment's node chain, read back from its pinned genesis.

    source is the deployment's binding, never a requester's: {"kind": NODE_CHAIN_SOURCE, "ledger_root": path,
    "genesis_receipt_sha256": sha256 uri}. Returns the binding (with the local ledger_root, which is a deployment
    detail and is never recorded) or raises LedgerBindingRefused. The chain must read back as hash-linked receipts
    whose oldest receipt is exactly the pinned genesis. Anything else is unbound and refused."""
    if source is None:
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, "no node ledger chain is bound to KV")
    if not isinstance(source, dict) or source.get("kind") != NODE_CHAIN_SOURCE \
            or set(source) != {"kind", "ledger_root", "genesis_receipt_sha256"} \
            or not isinstance(source["ledger_root"], (str, os.PathLike)) or not str(source["ledger_root"]) \
            or not _is_sha256_uri(source["genesis_receipt_sha256"]):
        raise LedgerBindingRefused("LEDGER_SOURCE_NOT_BOUND_BY_DEPLOYMENT", (
            f"a node chain is bound only as {{kind: {NODE_CHAIN_SOURCE}, ledger_root, genesis_receipt_sha256}} by the "
            "deployment; any other caller-shaped source is refused"), failure_class="C")
    root = str(source["ledger_root"])
    chain, reason, detail = _read_chain(root)
    if reason == "LEDGER_HEAD_UNREADABLE":
        raise LedgerBindingRefused(HEALTHY_NODE_LEDGER_REFUSAL_CAUSE, "no HEAD.json is readable at the bound node chain")
    if reason is not None or not chain:
        raise LedgerBindingRefused("HEALTHY_NODE_LEDGER_CHAIN_UNREADABLE", (
            f"the bound node chain does not read back as a chain ({reason}: {detail})"), failure_class="C",
            evaluation={"disposition": "FAIL_CLOSED", "reason": reason, "detail": detail})
    genesis = chain[-1].get("receipt_sha256")
    if genesis != source["genesis_receipt_sha256"]:
        raise LedgerBindingRefused("NODE_LEDGER_GENESIS_MISMATCH", (
            f"the bound chain's oldest receipt is {genesis}, not the genesis {source['genesis_receipt_sha256']} the "
            "deployment pins"), failure_class="C")
    return {"kind": NODE_CHAIN_SOURCE, "ledger_root": root, "genesis_receipt_sha256": genesis,
            "genesis_pinned_by": "DEPLOYMENT_BINDING", "chain_head_receipt_sha256": chain[0].get("receipt_sha256"),
            "chain_length": len(chain)}


def layer1_prerequisites() -> list[dict[str, Any]]:
    """LC-KV-18: one row per upstream leg layer 1 waits on; FAIL_CLOSED class B rows for unmet legs. Pure."""
    transport, state, _ = observe_intr_transport()
    legs = (
        ("HEALTHY_NODE_EVALUATOR_STACK_NOT_ON_LLM_ADAPTER_MAIN", "HEALTHY_NODE_EVALUATOR_STACK_ADMITTED",
         bool(PINNED_HEALTHY_NODE_EVALUATOR["on_upstream_main"]),
         "Lane B (StegVerse-org/LLM-adapter#430, #429 and #428, open drafts; "
         f"ADMISSION_ORDER {PINNED_HEALTHY_NODE_EVALUATOR['admission_order']})",
         "the evaluator and producers admitted on LLM-adapter main, then a re-vendor that flips on_upstream_main in the pin",
         "when #430, #429 and #428 are admitted, in that order; event-driven, never on a timer"),
        ("INTR_TRANSPORT_NOT_INSTALLED", "INTR_TRANSPORT_INSTALLED_AND_OBSERVED",
         transport is not None and state == "INSTALLED",
         "Lane B (InTr and Mesh Destinations, StegVerse-org/.github#162)",
         "the installed InTr DEVICE->KV transport that authenticates each envelope's source",
         "when an installed InTr transport is authentically observed; event-driven, never on a timer"),
    )
    rows = []
    for code, predicate, met, owner, repair, next_attempt in legs:
        row = {"prerequisite": predicate, "tracked_by": "LC-KV-13 / LC-KV-15"}
        if met:
            row["disposition"] = "ALLOW"
        else:
            row.update(disposition="FAIL_CLOSED", failure_code=code, failure_class="B", failed_predicate=predicate,
                       required_evidence_or_repair=f"{code}: {repair}",
                       retry_entrypoint="python -m runtime.kv_skap_vault finish-point (StegVerse-Labs/continuity-vault-kit)",
                       owning_existing_goal=f"{GOAL_REF}; dependency owner {owner}", next_attempt=next_attempt,
                       dependency_owner=owner, gates="every layer-1 ALLOW, so the finish point")
        rows.append(row)
    return rows


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
    """None when a KV-access receipt was minted under the pinned evaluate and the trust anchors in force; else why.
    Layer 2 (LC-KV-10) and the finish point both use this; neither trusts the receipt's own say-so."""
    if not isinstance(receipt, dict):
        return "LAYER1_RECEIPT_ABSENT"
    if receipt.get("healthy_node_evaluator") != PINNED_HEALTHY_NODE_EVALUATOR_ID \
            or receipt.get("healthy_node_evaluator_source_sha256") != PINNED_HEALTHY_NODE_EVALUATOR["source_sha256"]:
        return "LAYER1_HEALTH_EVALUATOR_NOT_PINNED"
    if load_pinned_intr()[0] is None or receipt.get("healthy_node_evaluator_code_sha256") != (
            _PINNED_LOADED.get(PINNED_HEALTHY_NODE_EVALUATOR_ID) or {}).get("code_sha256"):
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
    if binding.get("kind") != NODE_CHAIN_SOURCE or binding.get("genesis_pinned_by") != "DEPLOYMENT_BINDING" \
            or not _is_sha256_uri(binding.get("genesis_receipt_sha256")) \
            or not _is_sha256_uri(binding.get("chain_head_receipt_sha256")):
        return "LAYER1_NODE_CHAIN_NOT_BOUND_BY_THE_DEPLOYMENT"
    healthy = receipt.get("healthy_node_receipt")
    if not isinstance(healthy, dict) or healthy.get("node_id") != identity.get("node_id") \
            or healthy.get("chain_head_receipt_sha256") != binding.get("chain_head_receipt_sha256"):
        return "LAYER1_HEALTH_RECEIPT_NOT_FOR_THE_BOUND_CHAIN"
    key, bound = identity.get("node_identity_key"), binding.get("node_identity_key")
    if not isinstance(key, dict) or not isinstance(bound, dict) or not bound.get("key_id") \
            or any(key.get(k) != bound.get(k) for k in ("key_id", "public_key_b64")):
        return NODE_KEY_REFUSAL_CODE
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
        healthy_node_chain: Any = None,
    ) -> None:
        self.authority_validator = authority_validator
        self.policy_evaluator = policy_evaluator
        self.receipt_store = receipt_store
        self.candidate_store = candidate_store
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        # Layer 1 consumes the InTr-owned evaluate; it never supplies one of its own. An injected decider is
        # refused at handle() unless it IS the loaded pinned object (LC-KV-10); only the exercise-only subclass in
        # runtime/kv_skap_vault.py runs one, and its receipts are recorded NOT_THE_PINNED_OBJECT and refused downstream.
        if healthy_node_evaluator is None:
            healthy_node_evaluator, self._evaluator_unavailable = resolve_pinned_healthy_node_evaluator()
        else:
            self._evaluator_unavailable = ""
        self.healthy_node_evaluator = healthy_node_evaluator
        # The deployment's binding of the requesting node's own ledger chain (bind_healthy_node_ledger): the chain and
        # the genesis receipt the deployment pins for it. Never supplied by a requester.
        self.healthy_node_chain = healthy_node_chain
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
        detail = exc.detail
        if exc.cause == HEALTHY_NODE_LEDGER_REFUSAL_CAUSE:
            detail += (". The healthy-node chain is the requesting node's own transition ledger, bound by the "
                       "deployment with its pinned genesis; no health report is readable until it is")
        return layer1_refusal(request, exc.cause, detail, predicate=exc.predicate, failure_class=exc.failure_class,
                              health_evaluation=exc.evaluation, retry_entrypoint=exc.retry,
                              owning_existing_goal=exc.owner, next_attempt=exc.next_attempt,
                              failure_code=exc.failure_code)

    def _access_context(self, request: dict[str, Any],
                        envelope: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """LC-KV-15: bind the node's own ledger chain, observe the transport and derive the requester identity from it.

        Returns (context, None) or (None, six-field refusal). Nothing here is read from a caller field: the envelope's
        boundary_proof.source_identity_ref is only compared with the identity the installed transport authenticated.
        """
        claimed = envelope["boundary_proof"]["source_identity_ref"]
        try:
            binding = bind_healthy_node_ledger(self.healthy_node_chain)
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
            return None, self._refused(request, exc)
        return {"ledger_root": binding.pop("ledger_root"), "binding": binding, "transport_state": state,
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
            return None, None, layer1_refusal(request, "LAYER1_NOT_EVALUATED_THROUGH_THE_PINNED_EVALUATE", (
                "the layer-1 health decider is not the evaluate object loaded from the digest-checked vendored "
                f"bytes ({pin['source_sha256']}); a callable's __module__, __qualname__ or source filename is never "
                "accepted as its identity"),
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
        return self._evaluate_health(request, ctx, cite)

    def _evaluate_health(self, request: dict[str, Any], ctx: dict[str, Any], cite: Any
                         ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """Layer 1's health decision: the pinned evaluate() over the bound node chain. KV passes only what it observed:
        the bound chain, the observed transport state, the transport-authenticated node and require_admission=True.
        KV then keeps its stricter checks: the exact ALLOW shape, the genesis the deployment pinned, the head the
        evaluator saw, producer provenance of every receipt, and the authenticated node_identity_key equal to the key
        the chain's own NODE_IDENTITY_BINDING receipt binds."""
        node_ref = ctx["identity"]["node_id"]
        try:
            out = self.healthy_node_evaluator(
                node_ref, ledger_root=ctx["ledger_root"], transport_state=ctx["transport_state"],
                report_receipt_sha256=cite, require_admission=True, repository=HEALTHY_NODE_CHAIN_REPOSITORY)
        except Exception as exc:  # an evaluator fault is a refusal, never an admission
            out = {"disposition": "FAIL_CLOSED", "failure_code": HEALTHY_NODE_REFUSAL_CODE, "reason": "EVALUATOR_FAULT",
                   "required_evidence_or_repair": f"the evaluator raised {type(exc).__name__}"}
        if not isinstance(out, dict) or out.get("disposition") != "ALLOW":
            evaluation = copy.deepcopy(out) if isinstance(out, dict) else None
            reason = (evaluation or {}).get("reason")
            # No receipted report or admission yet (the #429/#430 producers are not admitted): class B.
            failure_class = "B" if reason in ("HEALTH_REPORT_MISSING", "NODE_NOT_ADMITTED") else "C"
            return None, None, layer1_refusal(request, HEALTHY_NODE_REFUSAL_CODE, (
                f"the pinned healthy-node evaluator did not ALLOW {node_ref!r}"
                + (f" ({(evaluation or {}).get('disposition')} {reason}: "
                   f"{(evaluation or {}).get('required_evidence_or_repair')})" if evaluation else "")),
                predicate=HEALTHY_NODE_PREDICATE, failure_class=failure_class, health_evaluation=evaluation,
                next_attempt=(evaluation or {}).get("next_attempt") or "on the node's next receipted HEALTHY report")
        problem, cause = None, HEALTHY_NODE_REFUSAL_CODE
        bound_key = None
        if any(out.get(k) != v for k, v in _HEALTHY_RECEIPT_EXACT.items()):
            problem = "the evaluator's ALLOW does not carry the pinned interface fields (require_admission=True)"
        elif out.get("node_id") != node_ref:
            problem = "the evaluator's ALLOW names another node than the transport-authenticated identity"
        elif not _is_sha256_uri(out.get("health_report_receipt_sha256")) \
                or not _is_sha256_uri(out.get("chain_head_receipt_sha256")):
            problem = "the evaluator's ALLOW binds no receipted health report on a ledger chain"
        elif cite is not None and out.get("health_report_receipt_sha256") != cite:
            problem = "the evaluator's ALLOW is for another health report than the one cited"
        elif out.get("chain_head_receipt_sha256") != ctx["binding"]["chain_head_receipt_sha256"]:
            problem = "the evaluator's ALLOW is for another chain head than the one the deployment's binding read"
        else:
            chain, reason, _ = _read_chain(ctx["ledger_root"])
            if reason is not None or not chain or chain[0].get("receipt_sha256") != out["chain_head_receipt_sha256"] \
                    or chain[-1].get("receipt_sha256") != ctx["binding"]["genesis_receipt_sha256"]:
                problem = "the bound chain no longer reads back from the pinned genesis to the evaluated head"
            else:
                foreign = chain_provenance_failure(chain, node_ref)
                if foreign:
                    cause, problem = foreign[0], foreign[1]
                else:
                    bound_key = chain_bound_identity_key(chain, node_ref)
                    key = ctx["identity"]["node_identity_key"]
                    if bound_key is None or not isinstance(key, dict) \
                            or any(key.get(k) != bound_key[k] for k in ("key_id", "public_key_b64")):
                        cause = NODE_KEY_REFUSAL_CODE
                        problem = ("the transport-authenticated node_identity_key is not the key the node's own chain "
                                   "binds in its NODE_IDENTITY_BINDING receipt; a node is admitted only under that key")
        if problem:
            return None, None, layer1_refusal(request, cause, problem, predicate=HEALTHY_NODE_PREDICATE,
                                              failure_class="C", health_evaluation=copy.deepcopy(out))
        ctx["binding"] = {**ctx["binding"], "node_identity_key": copy.deepcopy(bound_key)}
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