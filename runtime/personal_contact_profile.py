"""Personal-contact profile helpers for multi-email KnowledgeVault identity data."""

from __future__ import annotations

from copy import deepcopy

from runtime.email_continuity import EmailAccountMapping, mapping_id_for


class PersonalContactProfileError(ValueError):
    pass


def new_profile() -> dict:
    return {
        "schema": "stegverse.kv.personal-contact-profile/v1",
        "display_name": None,
        "legal_name": None,
        "date_of_birth": None,
        "phone_numbers": [],
        "postal_addresses": [],
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


def _validate_optional_profile_fields(profile: dict) -> list[str]:
    errors: list[str] = []
    for key, limit in (("display_name", 200), ("legal_name", 300)):
        value = profile.get(key)
        if value is not None and (not isinstance(value, str) or len(value.strip()) > limit):
            errors.append(f"{key} must be null or a string up to {limit} characters")
    dob = profile.get("date_of_birth")
    if dob is not None:
        if not isinstance(dob, str):
            errors.append("date_of_birth must be null or YYYY-MM-DD")
        else:
            from datetime import date
            try:
                date.fromisoformat(dob)
            except ValueError:
                errors.append("date_of_birth must be YYYY-MM-DD")

    phones = profile.get("phone_numbers", [])
    if not isinstance(phones, list):
        errors.append("phone_numbers must be an array")
    else:
        primary = 0
        for index, entry in enumerate(phones):
            prefix = f"phone_numbers[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: object required")
                continue
            number = entry.get("number")
            label = entry.get("label")
            if not isinstance(number, str) or not number.strip():
                errors.append(f"{prefix}: number required")
            if not isinstance(label, str) or not label.strip():
                errors.append(f"{prefix}: label required")
            if entry.get("primary") is True:
                primary += 1
            elif entry.get("primary") is not False:
                errors.append(f"{prefix}: primary must be boolean")
        if primary > 1:
            errors.append("at most one primary phone number is allowed")

    addresses = profile.get("postal_addresses", [])
    if not isinstance(addresses, list):
        errors.append("postal_addresses must be an array")
    else:
        primary = 0
        for index, entry in enumerate(addresses):
            prefix = f"postal_addresses[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: object required")
                continue
            for key in ("label", "line1", "city", "region", "postal_code", "country_code"):
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    errors.append(f"{prefix}: {key} required")
            if isinstance(entry.get("country_code"), str) and len(entry["country_code"]) != 2:
                errors.append(f"{prefix}: country_code must be ISO alpha-2")
            if entry.get("primary") is True:
                primary += 1
            elif entry.get("primary") is not False:
                errors.append(f"{prefix}: primary must be boolean")
        if primary > 1:
            errors.append("at most one primary postal address is allowed")
    return errors


def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    if profile.get("schema") != "stegverse.kv.personal-contact-profile/v1":
        errors.append("profile schema mismatch")
    if profile.get("authority_effect") != "NONE":
        errors.append("personal contact profile may not grant authority")
    errors.extend(_validate_optional_profile_fields(profile))

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


def set_identity_fields(profile: dict, *, display_name=None, legal_name=None, date_of_birth=None) -> dict:
    updated = deepcopy(profile)
    updated["display_name"] = display_name.strip() if isinstance(display_name, str) and display_name.strip() else None
    updated["legal_name"] = legal_name.strip() if isinstance(legal_name, str) and legal_name.strip() else None
    updated["date_of_birth"] = date_of_birth.strip() if isinstance(date_of_birth, str) and date_of_birth.strip() else None
    errors = validate_profile(updated)
    if errors:
        raise PersonalContactProfileError("; ".join(errors))
    return updated


def add_phone(profile: dict, *, number: str, label: str = "mobile", primary: bool = False) -> dict:
    updated = deepcopy(profile)
    value = str(number).strip()
    if not value:
        raise PersonalContactProfileError("phone number required")
    if primary:
        for item in updated.setdefault("phone_numbers", []):
            item["primary"] = False
    updated.setdefault("phone_numbers", []).append({"number": value, "label": str(label).strip() or "mobile", "primary": bool(primary)})
    errors = validate_profile(updated)
    if errors:
        raise PersonalContactProfileError("; ".join(errors))
    return updated


def add_postal_address(profile: dict, *, label: str, line1: str, city: str, region: str, postal_code: str, country_code: str, line2=None, primary: bool = False) -> dict:
    updated = deepcopy(profile)
    if primary:
        for item in updated.setdefault("postal_addresses", []):
            item["primary"] = False
    updated.setdefault("postal_addresses", []).append({
        "label": str(label).strip() or "home",
        "line1": str(line1).strip(),
        "line2": str(line2).strip() if isinstance(line2, str) and line2.strip() else None,
        "city": str(city).strip(),
        "region": str(region).strip(),
        "postal_code": str(postal_code).strip(),
        "country_code": str(country_code).strip().upper(),
        "primary": bool(primary),
    })
    errors = validate_profile(updated)
    if errors:
        raise PersonalContactProfileError("; ".join(errors))
    return updated
