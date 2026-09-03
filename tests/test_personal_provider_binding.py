import base64, hashlib, importlib.util, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("binding",ROOT/"runtime/personal_provider_binding.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def binding():
    return m.build_binding(root_folder_id="folder-1234567890",materialization_scope=[
        "_System/installation.receipt.json",
        "_Entities/Self/Personal_Form_Profile.json",
    ])

def broker_response():
    rows=[]
    for path,data,file_id in [
        ("_System/installation.receipt.json",b'{"ok":true}\n',"f1"),
        ("_Entities/Self/Personal_Form_Profile.json",b'{"profile":true}\n',"f2"),
    ]:
        rows.append({"canonical_path":path,"provider_file_id":file_id,"sha256":"sha256:"+hashlib.sha256(data).hexdigest(),"size_bytes":len(data),"content_base64":base64.b64encode(data).decode("ascii")})
    return {
      "decision":"ALLOW_OPERATION_RESULT",
      "result":{"schema":m.BROKER_RESULT_SCHEMA,"provider":"GOOGLE_DRIVE","binding_id":binding()["binding_id"],"records":rows,"total_size_bytes":sum(r["size_bytes"] for r in rows),"read_only":True,"provider_mutation_performed":False,"credential_material_returned":False,"credential_authority":"TV/TVC","authority_effect":"NONE"},
      "use_receipt":{"provider":"google_drive","operation":"personal_kv_materialize","secret_material_returned":False,"secret_material_logged":False,"secret_material_retained":False,"wallet_contacted":False,"signed":False,"broadcast":False,"single_use_consumed":True},
    }

def test_binding_is_deterministic_and_non_authorizing():
    b=binding()
    assert b["binding_id"]==m.deterministic_binding_id("GOOGLE_DRIVE","folder-1234567890")
    assert b["credential_authority"]=="TV/TVC"
    assert b["credential_reference_class"]==m.CREDENTIAL_REFERENCE_CLASS
    assert b["credential_material_present"] is False
    assert b["provider_operation_authorized"] is False

def test_scope_cannot_expand():
    try:m.build_binding(root_folder_id="folder-1234567890",materialization_scope=["_Vault/**"])
    except m.PersonalProviderBindingError:pass
    else:raise AssertionError("scope expansion must fail")

def test_legacy_token_materializer_is_retired():
    try:m.materialize_google_drive_scope(token_file=Path("/tmp/token"))
    except m.PersonalProviderBindingError as exc:assert "retired" in str(exc)
    else:raise AssertionError("legacy token path must fail closed")
    assert not hasattr(m,"_read_tvc_bearer")

def test_safe_destination_rejects_escape():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/"kv";root.mkdir()
        try:m._safe_destination(root,"../escape")
        except m.PersonalProviderBindingError:pass
        else:raise AssertionError("escape must fail")

def test_broker_materialization_exact_round_trip():
    with tempfile.TemporaryDirectory() as d:
        receipt=m.materialize_broker_result(binding=binding(),broker_response=broker_response(),destination_root=Path(d)/"kv")
        assert receipt["schema"]=="stegverse.kv.provider-materialization-receipt/v2"
        assert receipt["consumer_received_provider_credential"] is False
        assert receipt["provider_operation_authority_transferred"] is False
        assert (Path(d)/"kv/_System/installation.receipt.json").read_bytes()==b'{"ok":true}\n'

def test_broker_hash_tamper_fails_closed():
    response=broker_response();response["result"]["records"][0]["sha256"]="sha256:"+"0"*64
    try:m.validate_broker_materialization(binding=binding(),broker_response=response)
    except m.PersonalProviderBindingError as exc:assert "hash" in str(exc)
    else:raise AssertionError("tampered broker record must fail")

def test_broker_scope_expansion_fails_closed():
    response=broker_response();data=b"x"
    response["result"]["records"].append({"canonical_path":"_Vault/secret","provider_file_id":"x","sha256":"sha256:"+hashlib.sha256(data).hexdigest(),"size_bytes":1,"content_base64":base64.b64encode(data).decode("ascii")})
    try:m.validate_broker_materialization(binding=binding(),broker_response=response)
    except m.PersonalProviderBindingError as exc:assert "path_not_admitted" in str(exc)
    else:raise AssertionError("scope expansion must fail")
