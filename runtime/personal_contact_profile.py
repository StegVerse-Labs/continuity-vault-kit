"""Personal-contact profile helpers for multi-email KnowledgeVault identity data."""

from __future__ import annotations

from copy import deepcopy

from runtime.email_continuity import EmailAccountMapping, mapping_id_for


class PersonalContactProfileError(ValueError):
    pass


def new_profile() -> dict:
    return {
        "schema": "stegverse.kv.personal-contact-profile/v1",
        "email_addresses": [],
        "authority_effect": "NONE",
    }


def _normalize(address: str) -> str:
    value = str(address).strip().lower()
    if "@" not in value:
        raise PersonalContactProfileError("valid email address required")
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        raise PersonalContactProfileError("valid routable email address required")
    return value


def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    if profile.get("schema") != "stegverse.kv.personal-contact-profile/v1":
        errors.append("profile schema mismatch")
    if profile.get("authority_effect") != "NONE":
        errors.append("personal contact profile may not grant authority")

    entries = profile.get("email_addresses")
    if not isinstance(entries, list):
        return errors + ["email_addresses must be an array"]

    seen: set[str] = set()
    primary_count = 0
    allowed_states = {
        "UNMAPPED",
        "MAPPED_CREDENTIAL_REQUIRED",
        "CREDENTIAL_BOUND",
        "SESSION_VERIFIED",
        "REVOKED",
    }

    for index, entry in enumerate(entries):
        prefix = f"email_addresses[{index}]"
        try:
            address = _normalize(entry.get("address", ""))
        except PersonalContactProfileError as exc:
            errors.append(f"{prefix}: {exc}")
            continue
        if address in seen:
            errors.append(f"{prefix}: duplicate email address")
        seen.add(address)

        if not isinstance(entry.get("label"), str) or not entry["label"].strip():
            errors.append(f"{prefix}: label required")
        if entry.get("primary") is True:
            primary_count += 1
        elif entry.get("primary") is not False:
            errors.append(f"{prefix}: primary must be boolean")

        if entry.get("email_continuity_enabled") not in {True, False}:
            errors.append(f"{prefix}: email_continuity_enabled must be boolean")

        state = entry.get("connection_state")
        mapping_id = entry.get("mapping_id")
        if state not in allowed_states:
            errors.append(f"{prefix}: invalid connection_state")
        if state == "UNMAPPED":
            if mapping_id is not None:
                errors.append(f"{prefix}: UNMAPPED address may not have mapping_id")
        else:
            expected = mapping_id_for(address)
            if mapping_id != expected:
                errors.append(f"{prefix}: mapped state requires deterministic mapping_id")
            if entry.get("email_continuity_enabled") is not True:
                errors.append(f"{prefix}: mapped state requires email_continuity_enabled=true")

    if primary_count > 1:
        errors.append("at most one primary email address is allowed")
    return errors


def add_email(
    profile: dict,
    *,
    address: str,
    label: str = "personal",
    primary: bool = False,
    enable_email_continuity: bool = False,
) -> dict:
    updated = deepcopy(profile)
    normalized = _normalize(address)
    if any(_normalize(item.get("address", "")) == normalized for item in updated.get("email_addresses", [])):
        raise PersonalContactProfileError("email address already exists")

    if primary:
        for item in updated.get("email_addresses", []):
            item["primary"] = False

    updated.setdefault("email_addresses", []).append(
        {
            "address": normalized,
            "label": label.strip() or "personal",
            "primary": bool(primary),
            "email_continuity_enabled": bool(enable_email_continuity),
            "mapping_id": None,
            "connection_state": "UNMAPPED",
        }
    )
    errors = validate_profile(updated)
    if errors:
        raise PersonalContactProfileError("; ".join(errors))
    return updated


def map_email_entry(profile: dict, mapping: EmailAccountMapping) -> dict:
    updated = deepcopy(profile)
    matches = [
        item for item in updated.get("email_addresses", [])
        if _normalize(item.get("address", "")) == mapping.email_address
    ]
    if len(matches) != 1:
        raise PersonalContactProfileError("mapped email must already exist exactly once in personal profile")
    item = matches[0]
    item["email_continuity_enabled"] = True
    item["mapping_id"] = mapping.mapping_id
    item["connection_state"] = mapping.mapping_state

    errors = validate_profile(updated)
    if errors:
        raise PersonalContactProfileError("; ".join(errors))
    return updated


def sync_mapping_state(profile: dict, mapping: EmailAccountMapping) -> dict:
    updated = deepcopy(profile)
    for item in updated.get("email_addresses", []):
        if item.get("mapping_id") == mapping.mapping_id:
            if _normalize(item.get("address", "")) != mapping.email_address:
                raise PersonalContactProfileError("mapping_id/email address binding mismatch")
            item["email_continuity_enabled"] = True
            item["connection_state"] = mapping.mapping_state
            errors = validate_profile(updated)
            if errors:
                raise PersonalContactProfileError("; ".join(errors))
            return updated
    raise PersonalContactProfileError("mapping_id not found in personal profile")
