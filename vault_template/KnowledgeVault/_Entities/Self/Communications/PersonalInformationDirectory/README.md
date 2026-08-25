# Personal Information Directory

The personal directory maps owner-known subjects to any attributed communication modes.

Each subject record should contain:

- stable `subject_id`;
- `subject_type`: `person` or `organization`;
- owner-facing display name;
- zero or more `communication_modes`, each with `mode`, `value`, optional label, verification state, and provenance reference;
- optional relationship and organization references.

Phone-family modes (`phone`, `voice`, `sms`, `mms`, `rcs`, `imessage_phone`) share a normalized endpoint family. Email and `imessage_email` share another. Other handles remain mode-scoped.

Resolution must fail closed: one match is attributed, no match is unattributed, and multiple matches are ambiguous. Directory contents are private personal information and are not caller-identification authority.
