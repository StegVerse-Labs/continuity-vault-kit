# KV Governed Email Ingress Mirror Handoff

Status: SOURCE_READY_VALIDATION_PENDING  
Repository: StegVerse-Labs/continuity-vault-kit  
Branch: `kv-governed-email-ingress`  
Updated: 2026-08-27

## Purpose

Extend the already-installed `email-continuity` Personal Services slot into a governed mailbox-ingress capability without claiming provider, credential, Interlock, network, or runtime activation.

This lane implements the canonical rule:

```text
Mailbox
 -> authenticated provider session
 -> pre-admission staging
 -> governance evaluation
 -> ADMIT | QUARANTINE | REVIEW | REJECT | FAIL_CLOSED
 -> trusted KnowledgeVault projection only after ADMIT
 -> governance receipt
```

## Existing source of truth

Parent handoffs:

- `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`
- `KV_PERSONAL_SERVICES_MIRROR_HANDOFF.md`
- `KNOWLEDGEVAULT_MODULE_INTEGRATIONS_MIRROR_HANDOFF.md`
- `KV_PROVIDER_SURFACE_CAPABILITIES_MIRROR_HANDOFF.md`

The `email-continuity` slot already exists under the 33-service Personal Services registry as `KV_DEVICE_PROVIDER` and remains `INSTALLED_INACTIVE`.

## Implemented in this lane

- `schemas/kv-email-ingress-policy.schema.json`
- `specs/kv-email-ingress-policy.v1.json`
- `tools/check_kv_email_ingress_policy.py`
- `tests/test_kv_email_ingress_policy.py`
- `.github/workflows/validate-kv-email-ingress-policy.yml`

## Governance invariants

1. Entering an email address does not itself activate a mailbox.
2. Provider authorization is required before mailbox access.
3. Reusable plaintext passwords/secrets are not stored as ordinary KV content.
4. Mail is staged before admission and is not trusted KV knowledge while staged.
5. Ambiguous admission fails closed.
6. Canonical decisions are exactly:
   - `ADMIT`
   - `QUARANTINE`
   - `REVIEW`
   - `REJECT`
   - `FAIL_CLOSED`
7. Only `ADMIT` promotes a message into trusted KV content.
8. Spam, abuse, phishing/malware, sender/domain restrictions, attachment restrictions, and user-defined rules may block or divert admission.
9. Every evaluation produces a governance receipt.
10. Rejected payloads are not retained by default; a minimal rejection receipt may remain.
11. This policy grants no identity, provider, credential, governance, execution, or network authority.

## Intended user experience

```text
My KV
 -> Email
 -> Connect Email
 -> enter address
 -> provider discovery
 -> authorize provider session
 -> choose/default ingress governance
 -> mailbox mapped to email-continuity
 -> governed messages become reviewable within KV
```

Provider-specific authorization and transport adapters must conform to this provider-neutral contract rather than redefining admission semantics.

## Activation predicates

The service must remain `INSTALLED_INACTIVE` / source-ready until all applicable predicates are proven with real owner-authorized activity:

1. hosted source validation passes on the exact implementation head;
2. provider discovery resolves a supported mailbox route;
3. user authorizes a real provider session;
4. credential/session material remains outside ordinary KV plaintext state;
5. a real inbound message enters staging without becoming trusted KV content;
6. at least one real `ADMIT` path is observed and receipt-linked;
7. at least one non-admit path (`REJECT`, `QUARANTINE`, or `REVIEW`) is observed and receipt-linked;
8. ambiguous or unavailable governance proves `FAIL_CLOSED`;
9. admitted mail is projected into the intended semantic KV surfaces and can be reviewed;
10. disconnect/reconnect or interruption recovery reconciles without duplicate trusted admission;
11. provider/session revocation blocks subsequent mailbox access;
12. live evidence distinguishes provider receipt, governance receipt, and KV persistence receipt.

## Remaining machine-execution work

- validate this branch through hosted CI;
- reconcile the Personal Services registry entry with this more precise ingress contract if validation passes;
- implement provider adapter discovery/auth/session interfaces;
- implement staged message normalization and canonical message identifiers;
- implement governed admission/quarantine projection;
- implement receipt/replay/reconciliation behavior;
- expose the bounded service through the applicable KV/Interlock runtime;
- perform real owner-authorized mailbox activation proof;
- only then change runtime state from inactive/source-ready.

## Non-claims

Current source work does not claim:

- a mailbox is connected;
- any user email has been read;
- Gmail, Outlook, IMAP, or another provider has been activated;
- provider credentials are installed;
- Interlock/InTr is activated;
- spam/phishing classification quality is production-proven;
- mail delivery or sending authority exists;
- live KV email review is active.

## Release / downstream propagation gate

When this lane becomes validated and release-worthy, verify pertinent contract/state propagation to:

- StegVerse-Labs/Site;
- GCAT-BCAT-Engine/Publisher;
- admissibility-wiki;
- stegguardian-wiki.

Do not propagate an activation claim before live provider and KV evidence exists.
