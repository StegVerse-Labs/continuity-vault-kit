"""KV-SKAP-LEDGER-LOCATION-001: where KV layer-1 and SKAP Vault layer-2 receipts are ledgered (E0, stdlib only).

Under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324). Rigel's model: each receipt ledger corresponds to
the Org Ledger. Two ledgers are designated, each a subtree of StegVerse-org/.github refs/stegverse/organization-ledger:

* ``kv`` = ``01_KV_Ledger``: KV layer-1 receipts (stegverse.kv-access-receipt/v1, INTR_DEVICE_KV).
* ``skap_vault`` = ``02_SKAP_Vault_Ledger``: layer-2 receipts (stegverse.skap-access-receipt/v1, INTR_KV_SKAP),
  TV/TVC custody-issuance receipts (stegverse.tvc.skap-custody-reference-issuance/v1, StegVerse-Labs/TVC#537) and
  custody-result receipts (stegverse.tvc.skap-custody-operation-result/v1).

``kv`` / ``skap_vault`` are the consumer keys of StegVerse-Labs/TVC#542's config/org_ledger_head_signer.json
``org_ledger.custody_ledgers`` (also read by TVC#540 and TVC#541). ``##_<name>`` names a storage location (the ``##_``
prefix only keeps data-location names distinct for human review); both are presented under ``_StegVerse-org``, the
Org whose ledger coordinates them, so each ledger's #431 repository name is ``_StegVerse-org/##_<name>`` and its
namespace ``repository-ledger/_StegVerse-org/##_<name>`` (the consumer's ``repository-ledger/<org>/<repo>`` form).

Each designation is a contract in StegVerse-org/LLM-adapter#431's ``repository_ledger_location`` shape, exactly
(same keys, same ref, same subtree rule), committed under ``.stegverse/receipt-ledgers/`` and digest-pinned here.
There is no new ref type and no new mechanism: the genesis is pinned only by the REPOSITORY_LEDGER_GENESIS_PIN
transition (#431) after it is observed (Coordination ruling, StegVerse-org/.github#162 comment 6371352606), so
``expected_genesis_receipt_sha256`` is null and every read is a six-field FAIL_CLOSED ORG_LEDGER_GENESIS_NOT_PINNED
until then. A read-back reuses #432's pinned code: org_ledger_location's tree unpack, healthy_node_evaluator's
read_chain, the published ORG_LEDGER_HEAD attesters and the stdlib Ed25519 verify. The caller names only where a
local object store is; the ref, namespace and genesis come from the committed contract. Nothing here writes a ledger.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Mapping

ALLOW, FAIL_CLOSED = "ALLOW", "FAIL_CLOSED"
DESIGNATED_BY = "StegVerse-Labs/continuity-vault-kit"
ORG_LEDGER_REPOSITORY = "StegVerse-org/.github"
ORG_LEDGER_REF = "refs/stegverse/organization-ledger"
PRESENTED_UNDER = "_StegVerse-org"
TASK = "KV-SKAP-LEDGER-LOCATION-001 under KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324)"
GENESIS_CLASS = "REPOSITORY_LEDGER_INITIALIZATION"
GENESIS_PIN_TRANSITION = "REPOSITORY_LEDGER_GENESIS_PIN"
GENESIS_PIN_RULING = "StegVerse-org/.github#162 comment 6371352606 (Coordination: pin after observe)"
GENESIS_PIN_ENTRYPOINT = ("StegVerse-org/LLM-adapter#431 scripts/llm_adapter_repository_ledger_genesis_pin.py "
                          "plan(org_ledger, genesis_receipt_sha256, contract_bytes) over a read-only copy of "
                          "refs/stegverse/organization-ledger, with contract_bytes = this ledger's committed contract")
#: StegVerse-org/LLM-adapter#431's repository_ledger_location keys, in order (contract fixture d97cd4dc)
LOCATION_SHAPE = ("repository", "ref", "namespace", "locator_form", "new_ledger_root", "designation_source",
                  "initialization", "rule", "expected_genesis_receipt_sha256", "expected_genesis_note")
CONTRACT_SCHEMA = "stegverse.repo-transition-ledger-contract/v1"
HEAD_ATTESTATION_SCHEMA = "stegverse.org-ledger-head-attestation/v1"
HEAD_ATTESTATION_FIELDS = ("schema", "org_ledger_location", "genesis_receipt_sha256", "head_receipt_sha256",
                           "namespace_tree_oid", "appended_through")
APPEND_ROUTE = "ADMITTED_ORG_LEDGER_APPEND_ROUTE"
_ROOT = Path(__file__).resolve().parents[1]
KV_LEDGER, SKAP_VAULT_LEDGER = "kv", "skap_vault"  # TVC#542 org_ledger.custody_ledgers keys
RECEIPT_LEDGERS: dict[str, dict[str, Any]] = {
    KV_LEDGER: {
        "storage_location": "01_KV_Ledger",
        "presented_under": PRESENTED_UNDER,
        "contract_path": ".stegverse/receipt-ledgers/01_KV_Ledger.contract.json",
        "contract_sha256": "sha256:81dbc78b0cb21c8ce06faadbca0b9b0521636800ca99a886c24742a2aa35af57",
        "repository": "_StegVerse-org/01_KV_Ledger",
        "namespace": "repository-ledger/_StegVerse-org/01_KV_Ledger",
        "carries": ["stegverse.kv-access-receipt/v1 (L1)"],
        "read_by": "runtime.kv_interlock_endpoint.KVInterlockRuntime (layer 1)",
        "not_designated_code": "KV_RECEIPT_NAMESPACE_NOT_DESIGNATED",
    },
    SKAP_VAULT_LEDGER: {
        "storage_location": "02_SKAP_Vault_Ledger",
        "presented_under": PRESENTED_UNDER,
        "contract_path": ".stegverse/receipt-ledgers/02_SKAP_Vault_Ledger.contract.json",
        "contract_sha256": "sha256:153c32e62450b105805abb9e1d366bb32ece768b5caf497ca2dc54e095565c7f",
        "repository": "_StegVerse-org/02_SKAP_Vault_Ledger",
        "namespace": "repository-ledger/_StegVerse-org/02_SKAP_Vault_Ledger",
        "carries": ["stegverse.skap-access-receipt/v1 (L2)",
                    "stegverse.tvc.skap-custody-reference-issuance/v1 (TVC#537)",
                    "stegverse.tvc.skap-custody-operation-result/v1"],
        "read_by": "runtime.kv_skap_layer2.SkapLayer2Gate (layer 2) and the custody verifier",
        "not_designated_code": "CUSTODY_RECEIPT_NAMESPACE_NOT_DESIGNATED",
    },
}
PREDICATE = "RECEIPTS_READ_BACK_FROM_ORG_LEDGER_CHAIN_ONLY"
RETRY = "runtime.kv_receipt_ledgers.read_receipt_ledger(<ledger>, <local StegVerse-org/.github object store>)"


def _sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _refuse(which: str, code: str, klass: str, repair: str, next_attempt: str, detail: str,
            owner: str = TASK) -> dict[str, Any]:
    spec = RECEIPT_LEDGERS.get(which) or {}
    return {"disposition": FAIL_CLOSED, "receipt_ledger": which, "storage_location": spec.get("storage_location"),
            "failure_code": code, "failure_class": klass, "failed_predicate": PREDICATE,
            "required_evidence_or_repair": repair, "retry_entrypoint": RETRY, "owning_existing_goal": owner,
            "next_attempt": next_attempt, "detail": detail, "ledger_written": False, "authority_effect": "NONE"}


def _not_pinned(which: str, location: str) -> dict[str, Any]:
    return _refuse(which, "ORG_LEDGER_GENESIS_NOT_PINNED", "B",
                   f"repository_ledger_location.expected_genesis_receipt_sha256 in "
                   f"{RECEIPT_LEDGERS[which]['contract_path']}, written by the {GENESIS_PIN_TRANSITION} transition "
                   f"(StegVerse-org/LLM-adapter#431) from the observed {GENESIS_CLASS} genesis receipt_sha256 at "
                   f"{location}, never by hand and never invented ({GENESIS_PIN_RULING})",
                   f"when the {GENESIS_PIN_TRANSITION} transition ({GENESIS_PIN_ENTRYPOINT}) runs on the receipted "
                   f"{GENESIS_CLASS} genesis record for {location} and its contract write is admitted; "
                   "event-triggered by that record, no cron, no polling, no person",
                   f"{location}: expected_genesis_receipt_sha256 is null; any store can mint a genesis, so none is "
                   "accepted", owner=f"{TASK}; dependency owner the org's own genesis append + Lane B (#431 "
                   f"{GENESIS_PIN_TRANSITION})")


def designation(which: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(designation, None) from the committed, digest-pinned contract, or (None, six-field refusal). Never caller-chosen."""
    spec = RECEIPT_LEDGERS.get(which)
    if spec is None:
        return None, _refuse(which, "RECEIPT_LEDGER_UNKNOWN", "A", f"one of {sorted(RECEIPT_LEDGERS)}",
                             "on the corrected call", f"{which!r} is not a designated receipt ledger")
    code = spec["not_designated_code"]
    repair = (f"{spec['contract_path']} in StegVerse-org/LLM-adapter#431's repository_ledger_location shape at "
              f"{spec['contract_sha256']}, designating {ORG_LEDGER_REPOSITORY} {ORG_LEDGER_REF}:{spec['namespace']}")
    try:
        raw = (_ROOT / spec["contract_path"]).read_bytes()
    except OSError as exc:
        return None, _refuse(which, code, "D", repair, "when the designation is committed", f"unreadable: {exc}")
    if _sha_bytes(raw) != spec["contract_sha256"]:
        return None, _refuse(which, code, "C", repair, "on an admitted change that re-pins the contract digest",
                             f"{spec['contract_path']} is {_sha_bytes(raw)}, the pin is {spec['contract_sha256']}")
    try:
        contract = json.loads(raw)
    except ValueError:
        return None, _refuse(which, code, "C", repair, "on a well-formed contract", "the contract is not JSON")
    loc = contract.get("repository_ledger_location") if isinstance(contract, Mapping) else None
    if not isinstance(loc, Mapping) or tuple(loc) != LOCATION_SHAPE or contract.get("schema") != CONTRACT_SCHEMA \
            or contract.get("repository") != spec["repository"] or loc.get("repository") != ORG_LEDGER_REPOSITORY \
            or loc.get("ref") != ORG_LEDGER_REF or loc.get("namespace") != spec["namespace"] \
            or loc.get("new_ledger_root") is not False:
        return None, _refuse(which, code, "C", repair, "on a contract in #431's shape",
                             "the contract is not #431's repository_ledger_location shape for this ledger")
    genesis = loc.get("expected_genesis_receipt_sha256")
    pinned = isinstance(genesis, str) and len(genesis) == 71 and genesis.startswith("sha256:")
    return {"receipt_ledger": which, "storage_location": spec["storage_location"],
            "presented_under": spec["presented_under"], "repository": spec["repository"],
            "repository_ledger_location": dict(loc),
            "org_ledger_repository": loc["repository"], "ref": loc["ref"], "namespace": loc["namespace"],
            "location": f"{loc['repository']}#{loc['ref']}:{loc['namespace']}",
            "contract_path": spec["contract_path"], "contract_sha256": spec["contract_sha256"],
            "expected_genesis_receipt_sha256": genesis if pinned else None}, None


def receipt_ledger_binding(which: str) -> dict[str, Any]:
    """What a minted receipt records about the ledger it belongs on (where, under which contract, pinned or not)."""
    d, refusal = designation(which)
    if refusal:
        return {"receipt_ledger": which, "disposition": FAIL_CLOSED, "failure_code": refusal["failure_code"]}
    out = {k: d[k] for k in ("receipt_ledger", "storage_location", "presented_under", "repository", "location",
                             "contract_sha256",
                             "expected_genesis_receipt_sha256")}
    out["disposition"] = "DESIGNATED_GENESIS_PINNED" if d["expected_genesis_receipt_sha256"] else FAIL_CLOSED
    if not d["expected_genesis_receipt_sha256"]:
        out["failure_code"] = "ORG_LEDGER_GENESIS_NOT_PINNED"
    return out


def _pinned():
    from runtime.kv_interlock_endpoint import load_pinned_intr  # lazy: kv_interlock_endpoint imports this module
    modules, why = load_pinned_intr()
    return modules, why


def head_attestation_body(location: str, genesis_sha: str, head_sha: str, tree_oid: str) -> dict[str, Any]:
    """#432's org-ledger head attestation body, for this ledger's location. Pure."""
    return {"schema": HEAD_ATTESTATION_SCHEMA, "org_ledger_location": location.split("#", 1)[1],
            "genesis_receipt_sha256": genesis_sha, "head_receipt_sha256": head_sha,
            "namespace_tree_oid": tree_oid, "appended_through": APPEND_ROUTE}


def _head_failure(modules: dict[str, Any], which: str, location: str, attestation: Any, genesis_sha: str,
                  head_sha: str, tree_oid: str) -> dict[str, Any] | None:
    """#432's head-authentication rule (published ORG_LEDGER_HEAD attesters, stdlib Ed25519), for this location."""
    signers = modules["org_ledger_location"].load_head_signers()
    if not signers:
        return _refuse(which, "MERGE_APPEND_PATH_NOT_ADMITTED", "B",
                       "a TV/TVC-custodied Ed25519 ORG_LEDGER_HEAD key published in org-ledger-head-signers.v1.json "
                       "and the admitted append route attesting each org-ledger head (LC-KV-18)",
                       "when TV/TVC publishes the head attester and the append route is admitted; event-driven",
                       f"{location}: no org-ledger head attester is published, so a store's head is never "
                       "authenticated", owner=f"{TASK}; dependency owner TV/TVC + Lane C")
    not_auth = "ORG_LEDGER_HEAD_NOT_AUTHENTICATED"
    repair = f"a {HEAD_ATTESTATION_SCHEMA} by a published attester over exactly this genesis, head and tree"
    if not isinstance(attestation, Mapping):
        return _refuse(which, not_auth, "C", repair, "with the append route's attestation", "no head attestation")
    body = {k: attestation.get(k) for k in HEAD_ATTESTATION_FIELDS}
    if body != head_attestation_body(location, genesis_sha, head_sha, tree_oid):
        return _refuse(which, not_auth, "C", repair, "with the append route's attestation",
                       f"the attestation names another location, genesis, head or tree (head {head_sha})")
    key = next((k for k in signers if k.get("key_id") == attestation.get("key_id")), None)
    try:
        public = base64.b64decode(key.get("public_key_b64"), validate=True) if key else None
        signature = base64.b64decode(attestation.get("signature_b64"), validate=True)
    except (binascii.Error, ValueError, TypeError):
        public, signature = None, None
    message = HEAD_ATTESTATION_SCHEMA.encode("utf-8") + b"\n" + modules["healthy_node_evaluator"].canon(body)
    if public is None or len(public) != 32 or signature is None or len(signature) != 64 \
            or not modules["ed25519_verify"].verify(public, message, signature):
        return _refuse(which, not_auth, "C", repair, "with the append route's attestation",
                       "the attestation does not verify under a published ORG_LEDGER_HEAD key")
    return None


def read_receipt_ledger(which: str, org_ledger_git_dir: Any, head_attestation: Any = None) -> dict[str, Any]:
    """Read one receipt ledger back from its designated location. ALLOW carries the chain (newest first).

    Refusal order: not designated; genesis not pinned; location unreadable; genesis mismatch; head not
    authenticated (MERGE_APPEND_PATH_NOT_ADMITTED while no attester is published). Read-only, no network."""
    d, refusal = designation(which)
    if refusal:
        return refusal
    if d["expected_genesis_receipt_sha256"] is None:
        return _not_pinned(which, d["location"])
    modules, why = _pinned()
    if modules is None:
        return _refuse(which, "PINNED_INTR_CODE_UNAVAILABLE", "C", "the digest-pinned #432 modules", "on re-vendor", why)
    unreadable = "ORG_LEDGER_LOCATION_UNREADABLE"
    repair = f"a local {ORG_LEDGER_REPOSITORY} object store holding {d['ref']}:{d['namespace']}"
    if not isinstance(org_ledger_git_dir, (str, Path)) or not str(org_ledger_git_dir):
        return _refuse(which, unreadable, "B", repair, "with the store named", "no object store named")
    git = ["git", "--git-dir", str(org_ledger_git_dir), "-c", "protocol.allow=never"]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1",
           "HOME": "/nonexistent"}
    try:
        commit = subprocess.run(git + ["rev-parse", "--verify", "--quiet", d["ref"] + "^{commit}"],
                                capture_output=True, check=False, timeout=60, env=env).stdout.decode().strip()
        tree_oid = subprocess.run(git + ["rev-parse", "--verify", "--quiet", f"{commit}:{d['namespace']}"],
                                  capture_output=True, check=False, timeout=60, env=env).stdout.decode().strip() \
            if commit else ""
        tree = subprocess.run(git + ["archive", "--format=tar", commit, d["namespace"]], capture_output=True,
                              check=False, timeout=60, env=env) if tree_oid else None
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        return _refuse(which, unreadable, "B", repair, "when git is available", type(exc).__name__)
    if tree is None or tree.returncode != 0 or not tree.stdout:
        return _refuse(which, unreadable, "B", repair, "when the store holds the namespace",
                       f"{d['ref']}:{d['namespace']} is not in the object store")
    with tempfile.TemporaryDirectory(prefix="kv-receipt-ledger-readback-") as scratch:
        try:
            modules["org_ledger_location"]._unpack(tree.stdout, Path(scratch), d["namespace"])
        except (tarfile.TarError, OSError, ValueError) as exc:
            return _refuse(which, unreadable, "C", repair, "on a well-formed tree", f"unreadable tree: {exc}")
        chain, failure, detail = modules["healthy_node_evaluator"].read_chain(Path(scratch) / d["namespace"],
                                                                             d["repository"])
    if failure or not chain or chain[-1].get("transition_class") != GENESIS_CLASS \
            or chain[-1].get("previous_receipt_sha256") is not None:
        return _refuse(which, unreadable, "C", repair, "on an intact chain",
                       f"{d['namespace']} has no {GENESIS_CLASS} genesis for {d['repository']} ({failure or ''} {detail})")
    if chain[-1].get("receipt_sha256") != d["expected_genesis_receipt_sha256"]:
        return _refuse(which, "ORG_LEDGER_GENESIS_MISMATCH", "C",
                       f"the store's {d['namespace']} genesis must be the contract's pinned genesis",
                       "never: a store that minted its own genesis is not this ledger",
                       f"the store's genesis is {chain[-1].get('receipt_sha256')}, the contract pins "
                       f"{d['expected_genesis_receipt_sha256']}")
    head = _head_failure(modules, which, d["location"], head_attestation, chain[-1]["receipt_sha256"],
                         chain[0]["receipt_sha256"], tree_oid)
    if head:
        return head
    return {**receipt_ledger_binding(which), "disposition": ALLOW, "head_receipt_sha256": chain[0]["receipt_sha256"],
            "namespace_tree_oid": tree_oid, "chain": chain, "authority_effect": "NONE"}


def receipt_on_ledger(which: str, receipt_sha256: Any, org_ledger_git_dir: Any,
                      head_attestation: Any = None) -> dict[str, Any]:
    """ALLOW only if a receipt whose evidence carries receipt_sha256 is on the read-back chain of this ledger."""
    read = read_receipt_ledger(which, org_ledger_git_dir, head_attestation)
    if read["disposition"] != ALLOW:
        return read
    for r in read["chain"]:
        evidence = r.get("evidence") if isinstance(r.get("evidence"), Mapping) else {}
        if evidence.get("receipt_sha256") == receipt_sha256 or evidence.get("receipt_hash") == receipt_sha256:
            return {"disposition": ALLOW, "receipt_ledger": which, "ledger_receipt_sha256": r["receipt_sha256"],
                    "head_receipt_sha256": read["head_receipt_sha256"], "authority_effect": "NONE"}
    return _refuse(which, "RECEIPT_NOT_ON_DESIGNATED_LEDGER", "C",
                   f"a receipt on {read['location']} whose evidence carries {receipt_sha256}",
                   "after the receipt is appended through the admitted route",
                   f"{receipt_sha256} is not on the read-back chain")


def receipt_ledger_prerequisites() -> list[dict[str, Any]]:
    """One row per designated receipt ledger, for the finish point; FAIL_CLOSED until its genesis is pinned."""
    rows = []
    for which in RECEIPT_LEDGERS:
        d, refusal = designation(which)
        row = {"prerequisite": "RECEIPT_LEDGER_DESIGNATED_AND_GENESIS_PINNED", "receipt_ledger": which,
               "storage_location": RECEIPT_LEDGERS[which]["storage_location"],
               "presented_under": RECEIPT_LEDGERS[which]["presented_under"],
               "contract_sha256": RECEIPT_LEDGERS[which]["contract_sha256"], "tracked_by": TASK}
        if refusal is None and d["expected_genesis_receipt_sha256"] is None:
            refusal = _not_pinned(which, d["location"])
        if refusal is None:
            row.update(disposition=ALLOW, location=d["location"],
                       expected_genesis_receipt_sha256=d["expected_genesis_receipt_sha256"])
        else:
            row.update({k: refusal[k] for k in ("disposition", "failure_code", "failure_class", "failed_predicate",
                                                "required_evidence_or_repair", "retry_entrypoint",
                                                "owning_existing_goal", "next_attempt")})
            if d:
                row["location"] = d["location"]
        rows.append(row)
    return rows


def custody_ledgers_config() -> dict[str, Any]:
    """The designations in the shape StegVerse-Labs/TVC#542's config/org_ledger_head_signer.json reads at
    org_ledger.custody_ledgers: {"kv"|"skap_vault": {"carries": [...], "repository_ledger_location": {#431 shape}}}.
    A ledger whose contract is not designated is given with repository_ledger_location null (the consumer refuses
    CUSTODY_RECEIPT_NAMESPACE_NOT_DESIGNATED)."""
    out: dict[str, Any] = {}
    for which, spec in RECEIPT_LEDGERS.items():
        d, _ = designation(which)
        out[which] = {"carries": list(spec["carries"]), "storage_location": spec["storage_location"],
                      "presented_under": spec["presented_under"], "contract_path": spec["contract_path"],
                      "contract_sha256": spec["contract_sha256"],
                      "repository_ledger_location": d["repository_ledger_location"] if d else None}
    return out


__all__ = ["custody_ledgers_config", "KV_LEDGER", "SKAP_VAULT_LEDGER", "RECEIPT_LEDGERS", "designation", "read_receipt_ledger",
           "receipt_ledger_binding", "receipt_ledger_prerequisites", "receipt_on_ledger"]
