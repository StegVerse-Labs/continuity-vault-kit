"""Exact-byte application contract for KV <-> Publisher document InTr.

StegOS owns Universal InTr transport and hop receipts. This module only builds
the Publisher application payload and validates returned application bytes.
"""
from __future__ import annotations
import base64, copy, hashlib, json
from pathlib import Path
from typing import Any, Mapping
from runtime.document_export import BUNDLE_SCHEMA, PUBLISHER_DESTINATION

TRANSFER_SCHEMA="stegverse.publisher.artifact-transfer/v1"
RETURN_SCHEMA="stegverse.publisher.artifact-return/v1"
IMPORT_CANDIDATE_SCHEMA="stegverse.kv.publisher-artifact-import-candidate/v1"
IMPORT_RECEIPT_SCHEMA="stegverse.kv.publisher-artifact-import-receipt/v1"

class DocumentInTrTransferError(ValueError): pass

def canonical_json(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_bytes(value:bytes)->str:
    return "sha256:"+hashlib.sha256(value).hexdigest()

def sha256_value(value:Any)->str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))

def verify_bundle(bundle:Mapping[str,Any])->None:
    if not isinstance(bundle,Mapping) or bundle.get("schema_version")!=BUNDLE_SCHEMA:
        raise DocumentInTrTransferError("publisher bundle schema mismatch")
    body=copy.deepcopy(dict(bundle)); claimed=body.pop("export_sha256",None)
    if claimed!=sha256_value(body):
        raise DocumentInTrTransferError("publisher bundle hash mismatch")
    auth=bundle.get("authorization")
    if not isinstance(auth,Mapping) or auth.get("destination")!=PUBLISHER_DESTINATION:
        raise DocumentInTrTransferError("Publisher authorization destination mismatch")
    if auth.get("status")!="active" or auth.get("revoked") is not False:
        raise DocumentInTrTransferError("Publisher authorization inactive")
    if any(bundle.get(k) is not False for k in ("publication_authorized","release_authorized","execution_authorized")):
        raise DocumentInTrTransferError("publisher bundle authority expansion")
    if bundle.get("authority_effect")!="NONE":
        raise DocumentInTrTransferError("publisher bundle authority effect invalid")

def build_artifact_transfer(bundle:Mapping[str,Any],*,transfer_id:str)->tuple[dict[str,Any],bytes]:
    verify_bundle(bundle)
    if not isinstance(transfer_id,str) or not transfer_id:
        raise DocumentInTrTransferError("transfer_id required")
    payload={
      "schema":TRANSFER_SCHEMA,"transfer_id":transfer_id,"operation":"TRANSFER",
      "export_bundle":copy.deepcopy(dict(bundle)),
      "export_sha256":bundle["export_sha256"],
      "requested_formats":copy.deepcopy(bundle["requested_formats"]),
      "authorization_ref":bundle["authorization"]["authority_ref"],
      "publication_authorized":False,"release_authorized":False,
      "execution_authorized":False,"authority_effect":"NONE",
    }
    return payload,canonical_json(payload).encode("utf-8")

def validate_artifact_return(return_bytes:bytes,*,source_bundle:Mapping[str,Any])->dict[str,Any]:
    verify_bundle(source_bundle)
    if not isinstance(return_bytes,bytes) or not return_bytes:
        raise DocumentInTrTransferError("exact Publisher return bytes required")
    try: value=json.loads(return_bytes.decode("utf-8"))
    except Exception as exc: raise DocumentInTrTransferError("Publisher return JSON invalid") from exc
    if canonical_json(value).encode("utf-8")!=return_bytes:
        raise DocumentInTrTransferError("Publisher return bytes are not canonical JSON")
    if value.get("schema")!=RETURN_SCHEMA or value.get("authority_effect")!="NONE":
        raise DocumentInTrTransferError("Publisher return boundary invalid")
    if any(value.get(k) is not False for k in ("publication_authorized","release_authorized","execution_authorized")):
        raise DocumentInTrTransferError("Publisher return authority expansion")
    if value.get("source_export_id")!=source_bundle.get("export_id") or value.get("source_export_sha256")!=source_bundle.get("export_sha256"):
        raise DocumentInTrTransferError("Publisher return source export binding mismatch")
    manifest=value.get("manifest"); receipt=value.get("rendering_receipt"); artifacts=value.get("artifacts")
    if not isinstance(manifest,Mapping) or not isinstance(receipt,Mapping) or not isinstance(artifacts,list) or not artifacts:
        raise DocumentInTrTransferError("Publisher return content missing")
    if receipt.get("export_id")!=source_bundle.get("export_id") or receipt.get("export_sha256")!=source_bundle.get("export_sha256") or receipt.get("result")!="GENERATED_VALIDATED_NOT_PUBLISHED":
        raise DocumentInTrTransferError("rendering receipt source binding invalid")
    expected=set(source_bundle.get("requested_formats") or [])
    manifest_by_path={x.get("path"):x for x in manifest.get("artifacts",[]) if isinstance(x,Mapping)}
    normalized=[]; observed=set()
    for item in artifacts:
        if not isinstance(item,Mapping): raise DocumentInTrTransferError("artifact entry invalid")
        try: raw=base64.b64decode(item.get("content_base64",""),validate=True)
        except Exception as exc: raise DocumentInTrTransferError("artifact base64 invalid") from exc
        if sha256_bytes(raw)!=item.get("sha256") or len(raw)!=item.get("bytes"):
            raise DocumentInTrTransferError("artifact exact-byte hash mismatch")
        m=manifest_by_path.get(item.get("path"))
        if not isinstance(m,Mapping) or m.get("sha256")!=item.get("sha256") or m.get("bytes")!=item.get("bytes") or m.get("format")!=item.get("format"):
            raise DocumentInTrTransferError("artifact manifest binding mismatch")
        observed.add(item.get("format")); normalized.append(dict(item))
    if observed!=expected:
        raise DocumentInTrTransferError("returned artifact formats differ from owner authorization")
    return {
      "schema":IMPORT_CANDIDATE_SCHEMA,
      "source_export_id":source_bundle["export_id"],
      "source_export_sha256":source_bundle["export_sha256"],
      "authorization_ref":source_bundle["authorization"]["authority_ref"],
      "generation_id":value.get("generation_id"),
      "manifest":copy.deepcopy(dict(manifest)),
      "rendering_receipt":copy.deepcopy(dict(receipt)),
      "artifacts":normalized,
      "candidate_only":True,
      "canonical_kv_mutation_authorized":False,
      "publication_authorized":False,"release_authorized":False,
      "execution_authorized":False,"authority_effect":"NONE",
    }

def build_import_receipt(candidate:Mapping[str,Any],*,return_transport_terminal_receipt_hash:str)->dict[str,Any]:
    if candidate.get("schema")!=IMPORT_CANDIDATE_SCHEMA or candidate.get("candidate_only") is not True:
        raise DocumentInTrTransferError("valid import candidate required")
    if not isinstance(return_transport_terminal_receipt_hash,str) or not return_transport_terminal_receipt_hash.startswith("sha256:") or len(return_transport_terminal_receipt_hash)!=71:
        raise DocumentInTrTransferError("return transport terminal receipt hash required")
    body={
      "schema":IMPORT_RECEIPT_SCHEMA,
      "source_export_id":candidate["source_export_id"],
      "source_export_sha256":candidate["source_export_sha256"],
      "authorization_ref":candidate["authorization_ref"],
      "generation_id":candidate.get("generation_id"),
      "return_transport_terminal_receipt_hash":return_transport_terminal_receipt_hash,
      "artifact_hashes":[{"format":x["format"],"sha256":x["sha256"],"bytes":x["bytes"]} for x in candidate["artifacts"]],
      "result":"VALIDATED_IMPORT_CANDIDATE_NOT_COMMITTED",
      "canonical_kv_mutation_performed":False,
      "publication_authorized":False,"release_authorized":False,
      "execution_authorized":False,"authority_effect":"NONE",
    }
    return {**body,"receipt_sha256":sha256_value(body)}


def retain_private_export_bundle(bundle:Mapping[str,Any], *, root:Path) -> Path:
    """Persist one verified private export bundle write-once for return validation."""
    verify_bundle(bundle)
    export_id=bundle.get("export_id")
    if not isinstance(export_id,str) or not export_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in export_id):
        raise DocumentInTrTransferError("export_id invalid for private retention")
    target_root=root.expanduser().resolve()
    target_root.mkdir(parents=True,exist_ok=True)
    path=target_root/f"{export_id}.json"
    raw=(json.dumps(dict(bundle),sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    if path.exists():
        existing=path.read_bytes()
        if existing==raw:
            return path
        raise DocumentInTrTransferError("private export bundle write-once collision")
    path.write_bytes(raw)
    if path.read_bytes()!=raw:
        raise DocumentInTrTransferError("private export bundle persistence verification failed")
    return path
