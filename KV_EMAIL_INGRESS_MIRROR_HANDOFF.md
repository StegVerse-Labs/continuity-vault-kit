# KV Governed Email Ingress Mirror Handoff

Status: SOURCE_READY_VALIDATED_MERGED_RUNTIME_EXTENSION_ACTIVE  
Repository: StegVerse-Labs/continuity-vault-kit  
Branch: `kv-email-ingress-runtime-v2`  
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
- `schemas/kv-email-account-mapping.schema.json`
- `runtime/email_continuity.py`
- `tests/test_email_continuity_runtime.py`

## Governance invariants

1. Entering an email address does not itself activate a mailbox.
2. Provider authorization is required before mailbox access.
3. Once the mailbox address/provider route is mapped, the user should be prompted to complete the capability by placing the required credential or provider secret in SKAP Vault.
4. KnowledgeVault stores only the bounded credential reference/binding needed to request governed use; it does not store the mailbox secret itself.
5. Reusable plaintext passwords/secrets are not stored as ordinary KV content.
6. Mail is staged before admission and is not trusted KV knowledge while staged.
7. Ambiguous admission fails closed.
8. Canonical decisions are exactly:
   - `ADMIT`
   - `QUARANTINE`
   - `REVIEW`
   - `REJECT`
   - `FAIL_CLOSED`
9. Only `ADMIT` promotes a message into trusted KV content.
10. Spam, abuse, phishing/malware, sender/domain restrictions, attachment restrictions, and user-defined rules may block or divert admission.
11. Every evaluation produces a governance receipt.
12. Rejected payloads are not retained by default; a minimal rejection receipt may remain.
13. This policy grants no identity, provider, credential, governance, execution, or network authority.

## Intended user experience

```text
My KV
 -> Email
 -> Connect Email
 -> enter address
 -> provider discovery and mailbox mapping
 -> prompt: Complete setup in SKAP Vault
 -> user enters/authorizes required credential in SKAP Vault
 -> KV receives bounded credential reference / provider-session proof
 -> authorize provider session
 -> choose/default ingress governance
 -> mailbox mapped to email-continuity
 -> governed messages become reviewable within KV
```

Provider-specific authorization and transport adapters must conform to this provider-neutral contract rather than redefining admission semantics.

## Provider-neutral mapping runtime

The source lane now includes a deterministic provider-neutral account-mapping runtime:

```text
MAPPED_CREDENTIAL_REQUIRED
 -> CREDENTIAL_BOUND
 -> SESSION_VERIFIED
 -> REVOKED
```

Properties:

- mailbox mapping ID is deterministically derived from normalized email address;
- provider identity/route are recorded without granting provider authority;
- mapping completion explicitly requires a `skap://` credential reference;
- raw password/token/app-password fields are rejected from KV mapping payloads;
- session verification is impossible until the SKAP reference is bound;
- revoked mappings cannot be rebound without creating a new authorized mapping flow;
- this runtime does not itself authenticate to a provider or read mailbox contents.

## Hosted validation evidence

Validated implementation head before handoff reconciliation:

`c9b1dd040d0ee9bc28f9be235322c27214e31431`

Hosted results:

- Validate KV Email Ingress Policy run `33135794760`: PASS
- Security Baseline run `33135794754`: PASS
- Repository validation diagnostics run `33135794779`: PASS
- Release integrity run `33135794783`: PASS
- KV Guardrails run `33135794789`: PASS

The KV Guardrails lane initially exposed a nondeterministic tamper-test construction: changing the final unpadded Base64 character could alter only unused padding bits and decode to the original ciphertext. The test was repaired to mutate the first encoded ciphertext character, guaranteeing changed authenticated ciphertext. The repaired exact-head guardrail run passed all SKAP cryptographic, browser ingress, rotation/revocation, TVC key-provider, InTr persistence, reconstruction, and non-authorizing validation steps.

This evidence proves source/runtime-contract behavior only. It does not prove a live mailbox/provider session.

## Merge evidence

- PR: `#88`
- final validated head: `e2eb801b0b39619e950174e8bc29ed77f5f3a4b1`
- merge: `2784cdb6c39ee5fd95f3896e359de33472f04ac4`
- merge method: squash
- merged state: SOURCE_READY / NOT LIVE-ACTIVATED

Final exact-head validation:
- Validate KV Email Ingress Policy run `33135831775`: PASS
- Security Baseline run `33135831717`: PASS
- Repository validation diagnostics run `33135831685`: PASS
- Release integrity run `33135831849`: PASS
- KV Guardrails run `33135831764`: PASS

## Activation predicates

The service must remain `INSTALLED_INACTIVE` / source-ready until all applicable predicates are proven with real owner-authorized activity:

1. hosted source validation passes on the exact implementation head;
2. provider discovery resolves a supported mailbox route;
3. after mailbox mapping, the user is explicitly directed to complete credential setup in SKAP Vault;
4. the required credential/secret is present behind SKAP Vault and only a bounded reference/session proof is exposed to KV;
5. user authorizes a real provider session;
6. credential/session material remains outside ordinary KV plaintext state;
7. a real inbound message enters staging without becoming trusted KV content;
8. at least one real `ADMIT` path is observed and receipt-linked;
9. at least one non-admit path (`REJECT`, `QUARANTINE`, or `REVIEW`) is observed and receipt-linked;
10. ambiguous or unavailable governance proves `FAIL_CLOSED`;
11. admitted mail is projected into the intended semantic KV surfaces and can be reviewed;
12. disconnect/reconnect or interruption recovery reconciles without duplicate trusted admission;
13. provider/session or SKAP credential revocation blocks subsequent mailbox access;
14. live evidence distinguishes SKAP credential reference/session proof, provider receipt, governance receipt, and KV persistence receipt.

## Remaining machine-execution work

- implement concrete provider adapter discovery/auth/session interfaces around the provider-neutral mapping contract;
- implement the user-facing post-mapping SKAP Vault completion prompt around the now-implemented bounded credential-reference binding;
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
