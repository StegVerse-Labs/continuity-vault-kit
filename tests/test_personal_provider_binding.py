import importlib.util, json, os, stat, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("binding",ROOT/"runtime/personal_provider_binding.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_binding_is_deterministic_and_non_authorizing():
    b=m.build_binding(root_folder_id="folder-1234567890")
    assert b["binding_id"]==m.deterministic_binding_id("GOOGLE_DRIVE","folder-1234567890")
    assert b["credential_authority"]=="TV/TVC"
    assert b["credential_material_present"] is False
    assert b["provider_operation_authorized"] is False
    assert b["authority_effect"]=="NONE"
    assert b["activation_effect"] is False

def test_scope_cannot_expand():
    try:
        m.build_binding(root_folder_id="folder-1234567890",materialization_scope=["_Vault/**"])
        assert False
    except m.PersonalProviderBindingError:
        pass

def test_token_file_requires_private_permissions():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"token";p.write_text("example-token")
        os.chmod(p,0o644)
        try:
            m._read_tvc_bearer(p)
            assert False
        except m.PersonalProviderBindingError:
            pass
        os.chmod(p,0o600)
        assert m._read_tvc_bearer(p)=="example-token"

def test_safe_destination_rejects_escape():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/"kv";root.mkdir()
        try:
            m._safe_destination(root,"../escape")
            assert False
        except m.PersonalProviderBindingError:
            pass

def test_exact_write_round_trip():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/"kv";root.mkdir()
        receipt=m._write_exact(root,"_System/installation.receipt.json",b'{"ok":true}\n')
        assert receipt["path"]=="_System/installation.receipt.json"
        assert receipt["size_bytes"]==12
        assert (root/"_System/installation.receipt.json").read_bytes()==b'{"ok":true}\n'
