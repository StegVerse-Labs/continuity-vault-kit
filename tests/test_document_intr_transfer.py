from __future__ import annotations
import base64, copy, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from runtime import document_export as de
from runtime import document_intr_transfer as intr

def bundle():
    request=json.loads(open("fixtures/document-export/admitted.json",encoding="utf-8").read())
    value,_=de.prepare_document_export(request,now=datetime(2026,8,29,8,30,tzinfo=timezone.utc))
    return value

def publisher_return(b):
    artifacts=[]; manifest=[]
    for fmt,raw in [("markdown",b"# doc\n"),("html",b"<p>doc</p>"),("pdf",b"%PDF-x"),("docx",b"PK-x"),("json",b'{"x":1}')]:
        h=intr.sha256_bytes(raw); path=f"doc.{fmt}"
        artifacts.append({"format":fmt,"path":path,"sha256":h,"bytes":len(raw),"content_base64":base64.b64encode(raw).decode()})
        manifest.append({"format":fmt,"path":path,"sha256":h,"bytes":len(raw)})
    receipt={"export_id":b["export_id"],"export_sha256":b["export_sha256"],"result":"GENERATED_VALIDATED_NOT_PUBLISHED"}
    value={"schema":intr.RETURN_SCHEMA,"transfer_id":"t","source_export_id":b["export_id"],"source_export_sha256":b["export_sha256"],"generation_id":"g1","manifest":{"artifacts":manifest},"rendering_receipt":receipt,"artifacts":artifacts,"publication_authorized":False,"release_authorized":False,"execution_authorized":False,"authority_effect":"NONE"}
    return intr.canonical_json(value).encode()

class DocumentInTrTransferTests(unittest.TestCase):
    def test_build_transfer_is_exact_non_authorizing(self):
        b=bundle(); payload,raw=intr.build_artifact_transfer(b,transfer_id="transfer-1")
        self.assertEqual(json.loads(raw),payload)
        self.assertEqual(raw,intr.canonical_json(payload).encode())
        self.assertFalse(payload["publication_authorized"])
        self.assertEqual(payload["export_sha256"],b["export_sha256"])

    def test_return_becomes_candidate_not_mutation(self):
        b=bundle(); candidate=intr.validate_artifact_return(publisher_return(b),source_bundle=b)
        self.assertTrue(candidate["candidate_only"])
        self.assertFalse(candidate["canonical_kv_mutation_authorized"])
        receipt=intr.build_import_receipt(candidate,return_transport_terminal_receipt_hash="sha256:"+"a"*64)
        self.assertEqual(receipt["result"],"VALIDATED_IMPORT_CANDIDATE_NOT_COMMITTED")
        self.assertFalse(receipt["canonical_kv_mutation_performed"])

    def test_return_source_drift_rejected(self):
        b=bundle(); value=json.loads(publisher_return(b)); value["source_export_sha256"]="sha256:"+"f"*64
        with self.assertRaisesRegex(intr.DocumentInTrTransferError,"source export binding"):
            intr.validate_artifact_return(intr.canonical_json(value).encode(),source_bundle=b)

    def test_return_format_expansion_rejected(self):
        b=bundle(); b["requested_formats"]=["markdown"]; unhashed=copy.deepcopy(b); unhashed.pop("export_sha256"); b["export_sha256"]=intr.sha256_value(unhashed)
        with self.assertRaisesRegex(intr.DocumentInTrTransferError,"formats differ"):
            intr.validate_artifact_return(publisher_return(b),source_bundle=b)

    def test_private_bundle_retention_is_write_once_and_idempotent(self):
        b=bundle()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            first=intr.retain_private_export_bundle(b,root=root)
            second=intr.retain_private_export_bundle(b,root=root)
            self.assertEqual(first,second)
            self.assertEqual(json.loads(first.read_text()),b)
            altered=copy.deepcopy(b); altered["document"]["title"]="collision"
            unhashed=copy.deepcopy(altered); unhashed.pop("export_sha256"); altered["export_sha256"]=intr.sha256_value(unhashed)
            with self.assertRaisesRegex(intr.DocumentInTrTransferError,"write-once collision"):
                intr.retain_private_export_bundle(altered,root=root)

if __name__=="__main__": unittest.main()
