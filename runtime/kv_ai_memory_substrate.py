#!/usr/bin/env python3
"""Governed KnowledgeVault AI memory substrate.

This module builds bounded, deterministic context packets from already-readable KV
entries and creates non-authorizing write proposals. It never authenticates a
provider, resolves credentials, decides Interlock/InTr admission, or writes to KV.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

CLASS_BINDINGS = {
    "PERSONAL_KV": ("PERSON", "PERSONAL_ASSISTANT_AI"),
    "ORGANIZATIONAL_KV": ("ORGANIZATION", "ORGANIZATIONAL_AI"),
    "STEGVERSE_KV": ("STEGVERSE_ECOSYSTEM", "STEGVERSE_AI"),
    "MACHINE_KV": ("MACHINE_EXECUTION_ENTITY", "EXECUTION_AGENT"),
}
RETENTION_CLASSES = {"SESSION", "PROJECT", "DURABLE"}


class MemorySubstrateError(ValueError):
    """Fail-closed contract error."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MemorySubstrateError(message)


def _safe_relative_path(path: str) -> bool:
    if not path or path.startswith(("/", "\\")):
        return False
    normalized = path.replace("\\", "/")
    return all(part not in {"", ".", ".."} for part in normalized.split("/"))


def validate_context_request(request: dict[str, Any]) -> None:
    _require(request.get("schema") == "stegverse.kv.ai-memory-context-request/v1", "invalid request schema")
    kv_class = request.get("kv_class")
    _require(kv_class in CLASS_BINDINGS, "unknown kv_class")
    expected_authority, expected_role = CLASS_BINDINGS[kv_class]
    _require(request.get("authority_domain") == expected_authority, "authority_domain does not match kv_class")
    _require(request.get("consumer_ai_role") == expected_role, "consumer_ai_role does not match kv_class")
    _require(bool(str(request.get("request_id") or "").strip()), "request_id required")
    instances = request.get("source_kv_instance_ids")
    _require(isinstance(instances, list) and instances, "source_kv_instance_ids must be non-empty")
    _require(all(isinstance(item, str) and item.strip() for item in instances), "invalid source_kv_instance_id")
    _require(len(instances) == len(set(instances)), "source_kv_instance_ids must be unique")
    terms = request.get("query_terms")
    _require(isinstance(terms, list) and terms, "query_terms must be non-empty")
    _require(all(isinstance(term, str) and term.strip() for term in terms), "query_terms contain empty term")
    _require(bool(str(request.get("purpose") or "").strip()), "purpose required")
    max_items = request.get("max_items")
    max_bytes = request.get("max_bytes")
    _require(isinstance(max_items, int) and 1 <= max_items <= 100, "max_items outside allowed range")
    _require(isinstance(max_bytes, int) and 256 <= max_bytes <= 1048576, "max_bytes outside allowed range")
    _require(request.get("intr_admission_required") is True, "InTr admission must be required")
    _require(request.get("authority_effect") == "NONE_CONTEXT_REQUEST_ONLY", "request may not grant authority")


def _validate_entry_shape(entry: dict[str, Any]) -> None:
    for key in (
        "entry_id",
        "kv_class",
        "authority_domain",
        "source_kv_instance_id",
        "relative_path",
        "title",
        "content",
        "tags",
        "retention_class",
        "provenance_ref",
        "ai_context_allowed",
        "secret_material",
    ):
        _require(key in entry, f"entry missing {key}")
    _require(entry["kv_class"] in CLASS_BINDINGS, "entry has unknown kv_class")
    expected_authority, _ = CLASS_BINDINGS[entry["kv_class"]]
    _require(entry["authority_domain"] == expected_authority, "entry authority_domain does not match kv_class")
    _require(_safe_relative_path(str(entry["relative_path"])), "entry relative_path is unsafe")
    _require(isinstance(entry["content"], str), "entry content must be text")
    _require(isinstance(entry["title"], str), "entry title must be text")
    _require(isinstance(entry["tags"], list) and all(isinstance(tag, str) for tag in entry["tags"]), "entry tags invalid")
    _require(entry["retention_class"] in RETENTION_CLASSES, "entry retention_class invalid")
    _require(isinstance(entry["ai_context_allowed"], bool), "entry ai_context_allowed must be boolean")
    _require(isinstance(entry["secret_material"], bool), "entry secret_material must be boolean")
    priority = entry.get("priority", 0)
    _require(isinstance(priority, int), "entry priority must be integer")


def _entry_matches_query(entry: dict[str, Any], query_terms: Iterable[str]) -> bool:
    haystack = "\n".join(
        [entry.get("title", ""), entry.get("content", ""), " ".join(entry.get("tags", []))]
    ).casefold()
    return any(term.casefold() in haystack for term in query_terms)


def select_context_entries(request: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select bounded context deterministically.

    The function is intentionally lexical rather than claiming semantic retrieval.
    It fails closed if an allowed source instance contains an AI-eligible entry with
    secret material or authority/class mismatch.
    """
    validate_context_request(request)
    allowed_instances = set(request["source_kv_instance_ids"])

    candidates: list[dict[str, Any]] = []
    for entry in entries:
        _require(isinstance(entry, dict), "entry must be object")
        _validate_entry_shape(entry)
        if entry["source_kv_instance_id"] not in allowed_instances:
            continue
        if not entry["ai_context_allowed"]:
            continue
        _require(entry["secret_material"] is False, "AI-eligible entry contains secret material")
        _require(entry["kv_class"] == request["kv_class"], "cross-class AI context is forbidden")
        _require(entry["authority_domain"] == request["authority_domain"], "cross-authority AI context is forbidden")
        if not _entry_matches_query(entry, request["query_terms"]):
            continue
        candidates.append(entry)

    candidates.sort(key=lambda item: (-int(item.get("priority", 0)), item["entry_id"], item["relative_path"]))

    selected: list[dict[str, Any]] = []
    byte_count = 0
    for entry in candidates:
        if len(selected) >= request["max_items"]:
            break
        content_bytes = len(entry["content"].encode("utf-8"))
        if content_bytes > request["max_bytes"] - byte_count:
            continue
        selected.append(entry)
        byte_count += content_bytes
    return selected


def _project_packet_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": entry["entry_id"],
        "source_kv_instance_id": entry["source_kv_instance_id"],
        "relative_path": entry["relative_path"],
        "title": entry["title"],
        "content": entry["content"],
        "content_sha256": sha256_bytes(entry["content"].encode("utf-8")),
        "tags": list(entry["tags"]),
        "retention_class": entry["retention_class"],
        "provenance_ref": entry["provenance_ref"],
    }


def build_context_packet(request: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [_project_packet_entry(item) for item in select_context_entries(request, entries)]
    request_hash = sha256_json(request)
    entries_hash = sha256_json(selected)
    packet_seed = f"{request_hash}:{entries_hash}".encode("utf-8")
    packet_id = f"KVMEM-{sha256_bytes(packet_seed)[:24]}"
    return {
        "schema": "stegverse.kv.ai-memory-context-packet/v1",
        "packet_id": packet_id,
        "request_id": request["request_id"],
        "request_sha256": request_hash,
        "kv_class": request["kv_class"],
        "authority_domain": request["authority_domain"],
        "consumer_ai_role": request["consumer_ai_role"],
        "purpose": request["purpose"],
        "entries": selected,
        "entries_sha256": entries_hash,
        "selected_item_count": len(selected),
        "selected_content_bytes": sum(len(item["content"].encode("utf-8")) for item in selected),
        "secret_material_included": False,
        "cross_authority_content_included": False,
        "intr_admission_required": True,
        "model_is_authority": False,
        "context_transfers_authority": False,
        "authority_effect": "NONE_CONTEXT_ONLY",
    }


def build_write_proposal(
    *,
    source_packet: dict[str, Any],
    target_kv_instance_id: str,
    relative_path: str,
    content: str,
    retention_class: str,
) -> dict[str, Any]:
    _require(source_packet.get("schema") == "stegverse.kv.ai-memory-context-packet/v1", "invalid source packet")
    _require(source_packet.get("authority_effect") == "NONE_CONTEXT_ONLY", "source packet authority effect invalid")
    _require(source_packet.get("model_is_authority") is False, "source packet cannot make model authority")
    _require(bool(target_kv_instance_id.strip()), "target_kv_instance_id required")
    _require(_safe_relative_path(relative_path), "write proposal relative_path is unsafe")
    _require(isinstance(content, str), "write proposal content must be text")
    _require(retention_class in RETENTION_CLASSES, "write proposal retention_class invalid")
    content_hash = sha256_bytes(content.encode("utf-8"))
    seed = f"{source_packet['packet_id']}:{target_kv_instance_id}:{relative_path}:{content_hash}".encode("utf-8")
    return {
        "schema": "stegverse.kv.ai-memory-write-proposal/v1",
        "proposal_id": f"KVMEM-WRITE-{sha256_bytes(seed)[:24]}",
        "source_packet_id": source_packet["packet_id"],
        "target_kv_class": source_packet["kv_class"],
        "target_authority_domain": source_packet["authority_domain"],
        "target_kv_instance_id": target_kv_instance_id,
        "relative_path": relative_path,
        "content": content,
        "content_sha256": content_hash,
        "retention_class": retention_class,
        "intr_admission_required": True,
        "execution_authorized": False,
        "model_is_authority": False,
        "authority_effect": "NONE_PROPOSAL_ONLY",
    }
