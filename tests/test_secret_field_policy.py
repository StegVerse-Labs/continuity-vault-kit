from __future__ import annotations

import pathlib

import pytest

from runtime.secret_field_policy import (
    GOVERNANCE_ASSERTION_FIELDS,
    contains_forbidden_field,
    field_name_is_forbidden,
    find_forbidden_field,
    is_governance_assertion,
    value_is_assertion_like,
)

TOKENS = ("password", "secret", "token", "credential", "private_key")


def test_governance_assertions_are_admitted() -> None:
    """The fields that prove no credential is present must not be refused."""
    for name, value in [
        ("credential_authority", "TV/TVC"),
        ("contains_secret_material", False),
        ("secret_plaintext_present", False),
        ("credential_material_present", False),
        ("credential_material_transferred", False),
        ("github_token_runtime_authority", "NONE"),
        ("credential_requirement", "NONE"),
        ("fencing_token", 23),
        ("raw_provider_account_identifier_present", False),
    ]:
        assert is_governance_assertion(name, value), name
        assert not field_name_is_forbidden(name, value, TOKENS), name


def test_real_secret_bearing_names_still_refused() -> None:
    for name in ["password", "api_token", "client_secret", "credential", "private_key"]:
        assert field_name_is_forbidden(name, "x", TOKENS), name


def test_allow_list_is_not_a_smuggling_channel() -> None:
    """An allow-listed name must not launder material past the scan."""
    blob = "sk-" + "A1b2C3d4" * 6
    assert not value_is_assertion_like(blob)
    assert field_name_is_forbidden("credential_authority", blob, TOKENS)

    assert not value_is_assertion_like("x" * 201)
    assert field_name_is_forbidden("credential_authority", "x" * 201, TOKENS)

    # Containers never qualify, so a nested object cannot ride in on the name.
    assert not value_is_assertion_like({"password": "hunter2"})
    assert field_name_is_forbidden("credential_authority", {"a": 1}, TOKENS)


def test_nested_secret_is_found_with_its_path() -> None:
    payload = {
        "credential_authority": "TV/TVC",
        "items": [{"ok": 1}, {"inner": {"client_secret": "s"}}],
    }
    assert find_forbidden_field(payload, TOKENS) == "payload.items[1].inner.client_secret"
    assert contains_forbidden_field(payload, TOKENS)


def test_clean_payload_reports_no_path() -> None:
    payload = {
        "schema": "stegverse.kv-skap.account-metadata-transfer/v1",
        "credential_authority": "TV/TVC",
        "contains_secret_material": False,
        "items": [{"account_class": "social"}],
    }
    assert find_forbidden_field(payload, TOKENS) is None
    assert not contains_forbidden_field(payload, TOKENS)


def test_caller_tokens_are_respected() -> None:
    """Migrating a module must not widen what that module accepts."""
    assert field_name_is_forbidden("my_cookie", "v", ("cookie",))
    assert not field_name_is_forbidden("my_cookie", "v", ("password",))


def test_every_allow_listed_name_would_otherwise_be_banned() -> None:
    """The allow-list carries no dead entries.

    Every name here exists because some module's token set would refuse it.
    A name that no token matches does not belong in the allow-list.
    """
    union = (
        "password", "secret", "token", "private_key", "access_key", "refresh_token",
        "client_secret", "authorization", "cookie", "session_key", "account_id",
        "provider_account_id", "credential", "seed", "mnemonic", "refresh_key",
        "recovery_code", "raw_secret",
    )
    for name in GOVERNANCE_ASSERTION_FIELDS:
        assert any(t in name.lower() for t in union), f"{name} needs no exemption"


@pytest.mark.parametrize("path", sorted(pathlib.Path("runtime").glob("*.py")))
def test_every_runtime_module_imports(path: pathlib.Path) -> None:
    """Guard against unimportable committed source.

    `portable_direct_source_ingress.py` shipped a raw NUL byte and two
    `"\\"` literals that ended their own string; `portable_directory_projection.py`
    shipped the same backslash defect. No workflow referenced either file, so
    both sat unimportable on main. Compiling every runtime module keeps that
    class of break from landing again.
    """
    compile(path.read_bytes(), str(path), "exec")
