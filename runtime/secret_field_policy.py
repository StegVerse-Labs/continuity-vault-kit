"""Shared field-name secret policy for KV runtime boundaries.

Every KV runtime module that governs a boundary refuses payloads carrying
secret-bearing fields. Each module had grown its own substring scanner, and
those scanners reject the ecosystem's own *governance assertions* — the
non-secret fields that exist precisely to record that no credential is
present.

Concretely, `credential_authority: "TV/TVC"` is required on governed
surfaces, and a scanner banning the substring ``credential`` rejects it. The
same happens to ``contains_secret_material: false``,
``secret_plaintext_present: false`` and ``github_token_runtime_authority:
"NONE"``. The field that proves safety is read as the danger.

This module keeps the substring scan (a module still supplies its own token
set, so no module silently starts permitting something it used to refuse)
and adds an exact-name allow-list in front of it.

The allow-list is *not* a bare name exemption. An allow-listed name is
admitted only when its value also looks like an assertion rather than
material — see `value_is_assertion_like`. Otherwise the allow-list would
become the one guaranteed place to smuggle a secret past every boundary in
the system.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

#: Exact field names that are governance assertions, not secret material.
#:
#: Every entry here contains a substring that the per-module token sets ban,
#: which is why it needs naming. Each was taken from live payloads across
#: continuity-vault-kit, StegOS, Site, TVC and the organization boundary
#: repository — not invented here.
#:
#: Deliberately excluded, because a real secret could legitimately land in
#: them: ``credential``, ``secret_ref``, ``credential_environment_variable``.
GOVERNANCE_ASSERTION_FIELDS: frozenset[str] = frozenset(
    {
        # credential-authority assertions
        "credential_authority",
        "credential_boundary",
        "credential_class",
        "credential_custody_target",
        "credential_material_present",
        "credential_material_transferred",
        "credential_provider_release",
        "credential_requirement",
        "credential_value_exposed",
        # secret-absence assertions
        "contains_secret_material",
        "secret_plaintext_present",
        "provider_secret_exported",
        "uses_secrets",
        "non_tv_tvc_secret_or_token_used",
        "non_tv_tvc_secret_or_token_allowed",
        "non_tv_tvc_secret_or_token_required",
        # GitHub-runtime authority assertions
        "github_token_required",
        "github_token_runtime_authority",
        "github_token_production_authority",
        "id_token_write",
        # concurrency fences and counters — never credential material
        "fencing_token",
        "minimum_fencing_token_exclusive",
        "token_units",
        "chat_owned_credentials",
        # authorization provenance, not authorization material
        "authorization_ref",
        "authorization_required",
        # raw-identifier absence assertion
        "raw_provider_account_identifier_present",
    }
)

#: An allow-listed string value longer than this is treated as material.
MAX_ASSERTION_STRING = 200

#: A run of base64/hex-ish characters this long in an allow-listed value is
#: treated as material regardless of the field name.
_BLOB = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def value_is_assertion_like(value: Any) -> bool:
    """True when `value` is shaped like an assertion rather than material.

    Booleans, integers and None always qualify. A string qualifies when it is
    short and carries no long opaque run. Containers never qualify: an
    allow-listed name must not smuggle a nested object past the scan.
    """
    if isinstance(value, bool) or value is None:
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        if len(value) > MAX_ASSERTION_STRING:
            return False
        return not _BLOB.search(value)
    return False


def is_governance_assertion(name: str, value: Any) -> bool:
    """True when `name`/`value` is an admitted non-secret governance assertion."""
    return name in GOVERNANCE_ASSERTION_FIELDS and value_is_assertion_like(value)


def field_name_is_forbidden(name: str, value: Any, tokens: Iterable[str]) -> bool:
    """True when `name` is secret-bearing under `tokens`, allow-list applied.

    `tokens` stays the caller's own set, so migrating a module to this policy
    never widens what that module accepts beyond the governance assertions.
    """
    if is_governance_assertion(name, value):
        return False
    lowered = str(name).lower()
    return any(token in lowered for token in tokens)


def find_forbidden_field(
    value: Any, tokens: Iterable[str], path: str = "payload"
) -> str | None:
    """Return the dotted path of the first secret-bearing field, or None.

    Returning the path rather than a bare bool means callers can say *which*
    field failed, which is what made the original collisions hard to see.
    """
    tokens = tuple(tokens)
    if isinstance(value, Mapping):
        for key, child in value.items():
            if field_name_is_forbidden(str(key), child, tokens):
                return f"{path}.{key}"
            nested = find_forbidden_field(child, tokens, f"{path}.{key}")
            if nested is not None:
                return nested
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            nested = find_forbidden_field(child, tokens, f"{path}[{index}]")
            if nested is not None:
                return nested
    return None


def contains_forbidden_field(value: Any, tokens: Iterable[str]) -> bool:
    """True when any field below `value` is secret-bearing under `tokens`."""
    return find_forbidden_field(value, tokens) is not None
