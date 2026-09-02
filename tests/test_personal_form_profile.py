from runtime.personal_form_profile import new_profile, validate_profile, validated_copy

def test_default_profile_valid_and_non_signing():
    p=new_profile()
    assert validate_profile(p)==[]
    assert p["signature"]["auto_apply"] is False
    assert p["signature"]["skap_ref"] is None

def test_skap_ref_is_reference_only():
    p=new_profile()
    p["signature"]["skap_ref"]="skap://signing/personal-primary"
    assert validate_profile(p)==[]
    p["signature"]["auto_apply"]=True
    assert "signature auto_apply must be false" in validate_profile(p)

def test_private_identifier_shape():
    p=new_profile()
    p["identifiers"].append({"kind":"TVC_UNIQUE_ID","value":"example","label":"TVC"})
    assert validate_profile(p)==[]
    assert validated_copy(p)==p

def test_unknown_fields_fail_closed():
    p=new_profile(); p["signature"]["image_data"]="data:image/png;base64,abc"
    assert "signature invalid" in validate_profile(p)
