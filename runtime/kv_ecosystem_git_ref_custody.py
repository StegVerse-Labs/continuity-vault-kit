"""Ecosystem-only durable custody for KV/SKAP Vault lineages: an ecosystem git ref (LC-KV-03(a)).

Owning goal: TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001 (consumes-extension for KV-SKAP-VAULT-FUNCTIONAL-001,
StegVerse-Labs/.github#3324). Ladder task LC-KV-03 in StegVerse-Labs/.github#3330.

The lineage is written as one blob ``lineage.json`` in a commit on ``refs/stegverse/kv-custody/<principal>``.
The write is manifest-directed: it executes only the WRITE request already built by
``build_vault_lineage_custody_binding`` for the ``ecosystem-git-ref`` provider, and it moves the ref by
compare-and-swap from the manifest's declared predecessor (``git update-ref <ref> <new> <old>``), so a stale or
concurrent writer fails closed instead of overwriting. Read-back is by exact lineage hash: the bytes on the ref
must re-derive to the bound ``lineage_sha256``.

E0: stdlib plus the local ``git`` binary only (the ecosystem's own substrate). No model, network, clock or
credential is used. This module never pushes, never chooses a remote, and decides no admission: the resulting
provider receipt carries the Interlock/InTr and SKAP references the caller supplies, and
``validate_vault_lineage_custody_result`` decides. Every refusal is a six-field FAIL_CLOSED, never an exception.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict

from runtime.kv_storage_provider_adapter import ECOSYSTEM_GIT_REF_PROVIDER_ID
from runtime.task_registry_event_sovereign_kv_binding import (
    PROVIDER_RECEIPT_SCHEMA,
    VAULT_LINEAGE_BINDING_SCHEMA,
    TaskRegistryEventCustodyBindingError,
    _sha256_uri,
    build_vault_lineage_record,
)

WRITE_MANIFEST_SCHEMA = "stegverse.kv.ecosystem-git-ref-custody-write-manifest/v1"
WRITE_RESULT_SCHEMA = "stegverse.kv.ecosystem-git-ref-custody-write-result/v1"
READBACK_SCHEMA = "stegverse.kv.ecosystem-git-ref-custody-readback/v1"
REF_PREFIX = "refs/stegverse/kv-custody/"
BLOB_PATH = "lineage.json"
ZERO_OID = "0" * 40
GOAL = "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001"
PREDICATE = "DURABLE_CUSTODY_HAS_AN_ECOSYSTEM_ONLY_PROVIDER"
RETRY = "runtime.kv_ecosystem_git_ref_custody (StegVerse-Labs/continuity-vault-kit), then " \
        "python -m runtime.kv_skap_vault finish-point"
_OID = re.compile(r"^[0-9a-f]{40}$")
_GIT_ENV = {"GIT_AUTHOR_NAME": "kv-ecosystem-git-ref-custody", "GIT_AUTHOR_EMAIL": "kv-custody@stegverse.invalid",
            "GIT_COMMITTER_NAME": "kv-ecosystem-git-ref-custody", "GIT_COMMITTER_EMAIL": "kv-custody@stegverse.invalid",
            # deterministic commits: time is not read from the clock
            "GIT_AUTHOR_DATE": "1970-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "1970-01-01T00:00:00Z",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/bin:/usr/bin:/bin"}


def fail_closed(code: str, repair: str, *, failure_class: str = "B",
                next_attempt: str = "on the next custody write manifest for this lineage") -> Dict[str, Any]:
    return {"disposition": "FAIL_CLOSED", "failure_code": code, "failed_predicate": PREDICATE,
            "required_evidence_or_repair": repair, "retry_entrypoint": RETRY, "owning_existing_goal": GOAL,
            "next_attempt": next_attempt, "failure_class": failure_class, "authority_effect": "NONE"}


def custody_ref(principal_ref: str) -> str:
    """refs/stegverse/kv-custody/<principal>; the principal is reduced to ref-safe characters plus its hash."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", principal_ref).strip("-.") or "principal"
    return REF_PREFIX + safe[:64] + "-" + _sha256_uri(principal_ref)[7:19]


def _git(git_dir: str, *args: str, stdin: bytes | None = None) -> tuple[int, bytes]:
    proc = subprocess.run(["git", "--git-dir", git_dir, *args], input=stdin, capture_output=True,
                          env=_GIT_ENV, check=False)
    return proc.returncode, proc.stdout.strip()


def _current(git_dir: str, ref: str) -> str | None:
    code, out = _git(git_dir, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    return out.decode() if code == 0 else None


def build_write_manifest(*, binding: Dict[str, Any], exact_lineage: Dict[str, Any],
                         expected_predecessor_commit: str | None) -> Dict[str, Any]:
    """The direction for one append: the bound WRITE request, the exact lineage, and the ref's expected tip."""
    manifest = {"schema": WRITE_MANIFEST_SCHEMA, "binding": binding, "exact_lineage": exact_lineage,
                "custody_ref": custody_ref(str(binding.get("principal_ref"))),
                "expected_predecessor_commit": expected_predecessor_commit, "authority_effect": "NONE"}
    manifest["manifest_sha256"] = _sha256_uri(manifest)
    return manifest


def _check_manifest(manifest: Any) -> Dict[str, Any] | None:
    if not isinstance(manifest, dict) or manifest.get("schema") != WRITE_MANIFEST_SCHEMA:
        return fail_closed("KV_CUSTODY_WRITE_MANIFEST_INVALID", "supply a " + WRITE_MANIFEST_SCHEMA + " manifest")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if manifest.get("manifest_sha256") != _sha256_uri(body):
        return fail_closed("KV_CUSTODY_WRITE_MANIFEST_DIGEST_MISMATCH", "rebuild the manifest; it was edited")
    binding = manifest.get("binding")
    if not isinstance(binding, dict) or binding.get("schema") != VAULT_LINEAGE_BINDING_SCHEMA \
            or binding.get("provider_id") != ECOSYSTEM_GIT_REF_PROVIDER_ID:
        return fail_closed("KV_CUSTODY_BINDING_NOT_ECOSYSTEM_GIT_REF",
                           "bind the lineage with build_vault_lineage_custody_binding(provider_id='ecosystem-git-ref')")
    request = binding.get("provider_write_request") or {}
    if request.get("operation") != "WRITE" or request.get("object_ref") != binding.get("lineage_sha256"):
        return fail_closed("KV_CUSTODY_WRITE_REQUEST_NOT_BOUND", "the WRITE request must address the lineage hash")
    try:
        record = build_vault_lineage_record(exported_lineage=manifest.get("exact_lineage"))
    except TaskRegistryEventCustodyBindingError as exc:
        return fail_closed("KV_CUSTODY_LINEAGE_INVALID", f"{exc}; write only an untampered exported lineage",
                           failure_class="C")
    if record["lineage_sha256"] != binding.get("lineage_sha256") or manifest.get("custody_ref") != \
            custody_ref(str(binding.get("principal_ref"))):
        return fail_closed("KV_CUSTODY_LINEAGE_NOT_THE_BOUND_LINEAGE", "the manifest lineage must be the bound lineage")
    expected = manifest.get("expected_predecessor_commit")
    if expected is not None and not (isinstance(expected, str) and _OID.match(expected)):
        return fail_closed("KV_CUSTODY_PREDECESSOR_INVALID", "expected_predecessor_commit is null or a 40-hex oid")
    return None


def write_lineage(git_dir: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one manifest-directed append. Returns the write result (ALLOW) or a six-field FAIL_CLOSED."""
    refusal = _check_manifest(manifest)
    if refusal:
        return refusal
    code, _ = _git(git_dir, "rev-parse", "--git-dir")
    if code != 0:
        return fail_closed("KV_CUSTODY_GIT_DIR_UNAVAILABLE", "supply the ecosystem custody git directory")
    ref, expected = manifest["custody_ref"], manifest["expected_predecessor_commit"]
    current = _current(git_dir, ref)
    if current != expected:
        return fail_closed("KV_CUSTODY_REF_PREDECESSOR_MISMATCH",
                           f"{ref} is at {current}, manifest expects {expected}; rebuild the manifest on the observed tip",
                           failure_class="C", next_attempt="on the next manifest built on the observed tip")
    data = (json.dumps(manifest["exact_lineage"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            .encode("utf-8"))
    code, blob = _git(git_dir, "hash-object", "-w", "--stdin", stdin=data)
    if code != 0:
        return fail_closed("KV_CUSTODY_GIT_WRITE_FAILED", "git hash-object failed in the custody git directory")
    code, tree = _git(git_dir, "mktree", stdin=b"100644 blob " + blob + b"\t" + BLOB_PATH.encode() + b"\n")
    if code != 0:
        return fail_closed("KV_CUSTODY_GIT_WRITE_FAILED", "git mktree failed in the custody git directory")
    lineage_sha256 = manifest["binding"]["lineage_sha256"]
    message = f"kv-custody: {lineage_sha256}\n\nmanifest {manifest['manifest_sha256']}\n".encode()
    parents = ["-p", expected] if expected else []
    code, commit = _git(git_dir, "commit-tree", tree.decode(), *parents, stdin=message)
    if code != 0:
        return fail_closed("KV_CUSTODY_GIT_WRITE_FAILED", "git commit-tree failed in the custody git directory")
    code, _ = _git(git_dir, "update-ref", ref, commit.decode(), expected or ZERO_OID)
    if code != 0:
        return fail_closed("KV_CUSTODY_REF_COMPARE_AND_SWAP_LOST",
                           f"{ref} moved during the append; rebuild the manifest on the new tip", failure_class="C",
                           next_attempt="on the next manifest built on the observed tip")
    request = manifest["binding"]["provider_write_request"]
    return {"schema": WRITE_RESULT_SCHEMA, "disposition": "ALLOW", "custody_ref": ref, "commit": commit.decode(),
            "blob": blob.decode(), "predecessor_commit": expected, "lineage_sha256": lineage_sha256,
            "manifest_sha256": manifest["manifest_sha256"], "request_id": request["request_id"],
            "provider_result_ref": f"git:{ref}@{commit.decode()}", "authority_effect": "NONE"}


def read_back(git_dir: str, *, principal_ref: str, lineage_sha256: str) -> Dict[str, Any]:
    """Read the lineage on the principal's custody ref and accept it only if it re-derives to lineage_sha256."""
    ref = custody_ref(principal_ref)
    tip = _current(git_dir, ref)
    if tip is None:
        return fail_closed("KV_CUSTODY_REF_ABSENT", f"{ref} does not exist; append the lineage first",
                           next_attempt="after the first manifest-directed custody append")
    code, raw = _git(git_dir, "cat-file", "blob", f"{tip}:{BLOB_PATH}")
    if code != 0:
        return fail_closed("KV_CUSTODY_BLOB_ABSENT", f"{ref}@{tip} holds no {BLOB_PATH}", failure_class="C")
    try:
        lineage = json.loads(raw.decode("utf-8"))
    except ValueError:
        return fail_closed("KV_CUSTODY_BLOB_NOT_JSON", f"{ref}@{tip}:{BLOB_PATH} is not JSON", failure_class="C")
    if _sha256_uri(lineage) != lineage_sha256:
        return fail_closed("KV_CUSTODY_READBACK_HASH_MISMATCH",
                           f"{ref}@{tip} holds {_sha256_uri(lineage)}, not {lineage_sha256}", failure_class="C")
    return {"schema": READBACK_SCHEMA, "disposition": "ALLOW", "custody_ref": ref, "commit": tip,
            "lineage_sha256": lineage_sha256, "exact_lineage": lineage, "authority_effect": "NONE"}


def build_provider_receipt(*, binding: Dict[str, Any], write_result: Dict[str, Any], interlock_receipt_ref: str,
                           intr_receipt_ref: str, skap_credential_ref: str) -> Dict[str, Any]:
    """The existing provider WRITE receipt for an executed ecosystem-git-ref append. governance_state is ADMITTED
    only when Interlock and InTr references are supplied; this module verifies neither (they are consumed)."""
    request = binding["provider_write_request"]
    admitted = all(str(v or "").strip() for v in (interlock_receipt_ref, intr_receipt_ref))
    executed = write_result.get("disposition") == "ALLOW" and write_result.get("request_id") == request["request_id"]
    return {"schema": PROVIDER_RECEIPT_SCHEMA, "request_id": request["request_id"],
            "instance_id": request["instance_id"], "kv_set_id": request["kv_set_id"],
            "provider_id": request["provider_id"], "operation": "WRITE",
            "governance_state": "ADMITTED" if admitted else "PENDING_INTERLOCK_INTR",
            "provider_operation_executed": executed, "data_moved": executed, "replication_started": False,
            "interlock_receipt_ref": interlock_receipt_ref, "intr_receipt_ref": intr_receipt_ref,
            "skap_credential_ref": skap_credential_ref,
            "provider_result_ref": write_result.get("provider_result_ref", ""),
            "authority_effect": "NONE", "credential_material_present": False}
