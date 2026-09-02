# KV Personal Form Profile Mirror Handoff

Repository: StegVerse-Labs/continuity-vault-kit
Updated: 2026-09-02
State: SOURCE_IMPLEMENTED_RUNTIME_NOT_OBSERVED
Authority effect: NONE

## Goal

Provide one private KnowledgeVault record that can populate recurring business/government forms without requiring repeated manual entry on a phone.

Canonical path:

`_Entities/Self/Personal_Form_Profile.json`

The profile is personal data only. It grants no filing, signing, credential, identity, tax, procurement, banking, or execution authority.

## Boundary

Ordinary KV may hold the user's reusable factual form data.

SKAP Vault, not ordinary KV, owns reusable e-signature/signing material.

The KV profile may contain only a non-secret SKAP reference such as:

`skap://signing/personal-primary`

Possession of that reference does not authorize signature use.

## Initial field domains

- legal/display names
- date of birth
- phone/email
- mailing/residential addresses
- government/veteran identifier records
- organizer/governing-person defaults
- registered-agent defaults
- entity-filing defaults
- tax/EIN form defaults
- signature reference only

## Runtime completion

Runtime completion requires a current-device write of a validated profile into the canonical path, exact readback, and a later form-mapping read. Source presence alone is not runtime proof.
