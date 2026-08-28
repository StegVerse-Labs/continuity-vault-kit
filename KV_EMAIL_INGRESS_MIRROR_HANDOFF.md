# KV Governed Email Ingress Mirror Handoff

Status: SOURCE_READY_VALIDATED_MERGED / LIVE_ACTIVATION_PENDING  
Repository: StegVerse-Labs/continuity-vault-kit  
Branch: `main`  
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
- `schemas/kv-email-ingress-receipt.schema.json`
- `runtime/email_ingress_pipeline.py`
- `tests/test_email_ingress_pipeline.py`
- `runtime/email_provider_adapter.py`
- `tests/test_email_provider_adapter.py`
- `runtime/email_interlock.py`
- `tests/test_email_interlock.py`
- `schemas/kv-email-provider-registry.schema.json`
- `specs/kv-email-provider-registry.v1.json`
- `tools/check_kv_email_provider_registry.py`
- `runtime/documented_email_providers.py`
- `tests/test_documented_email_providers.py`

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

## Staging / admission runtime extension

The current runtime-extension branch adds:

- deterministic canonical message identifiers bound to mailbox mapping + provider message ID;
- `STAGED_UNTRUSTED` pre-admission state;
- governed decisions `ADMIT | QUARANTINE | REVIEW | REJECT | FAIL_CLOSED`;
- trusted projection creation only for `ADMIT`;
- payload-free governance receipts;
- deterministic duplicate reconciliation;
- fail-closed content-drift detection when the same provider message identity presents changed content.

This remains provider-neutral and uses caller-supplied classification signals. It does not claim production spam/phishing detection or live provider access.

## Provider adapter / post-mapping activation interface

The runtime extension now includes a concrete provider-adapter protocol/registry:

- domain/provider discovery must resolve exactly one registered route or fail closed;
- discovery produces `MAPPED_CREDENTIAL_REQUIRED`, never an authenticated session;
- provider session descriptors are metadata-only and are rejected if they expose password/secret/token fields;
- the mapping runtime returns `COMPLETE_SKAP_CREDENTIAL_SETUP` immediately after mapping;
- the next action explicitly names `SKAP_VAULT` as credential destination and `PROHIBITED_IN_KV` as raw-secret destination;
- after SKAP reference binding, the next action becomes `VERIFY_PROVIDER_SESSION`;
- only after session verification can the runtime surface `BEGIN_GOVERNED_INGRESS`, still subject to Interlock admission;
- email-specific Interlock builders now use the canonical `DISCOVER`, `REQUEST`, and `COMMIT_CANDIDATE` operations;
- Interlock requests disclose source references/metadata only and contain no mailbox secret;
- admitted email writeback is represented as a candidate-only projection until canonical policy admission.

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


## Runtime-extension merge evidence

- PR: `#91`
- exact validated head: `9f685e0480a039c53c29a7e74cadc5722b756d7a`
- merge: `ef285d5ed03bd92657e23c085734ea8c41b9bf6a`

Exact-head validation:
- Validate KV Email Ingress Policy run `33136048073`: PASS
- Security Baseline run `33136048069`: PASS
- Repository validation diagnostics run `33136048085`: PASS
- KV Guardrails run `33136048087`: PASS
- Release integrity run `33136048075`: PASS

Release state:
- persistent VERSION remains `0.1.9`;
- successor release/tag/publication remains TV/TVC-admitted only;
- issue `#90` tracks downstream propagation verification after the next admitted release.

## Current remaining boundary

Machine-executable source for provider-neutral discovery, SKAP completion guidance, staged admission, receipts/replay, and KV Interlock specialization is merged.

Remaining work that is not yet proven:
1. execute a real owner-authorized mailbox mapping against one documented/supported provider route;
2. where the address is outside the documented domains, add a separately evidenced provider adapter rather than guessing;
3. complete the prompted SKAP Vault credential setup;
4. verify the provider session using SKAP-backed resolution;
5. observe one real inbound staged message before trust;
6. observe at least one real ADMIT and one real governed non-admit outcome;
7. verify KV projection/readback, receipt chains, duplicate reconciliation, revocation, and interruption recovery;
8. only then consider `email-continuity` ACTIVE.


## Documented concrete provider adapters

A provider-specific metadata set is now implemented as `DOCUMENTED_UNVERIFIED`, not runtime verified:

- `google-gmail` for `gmail.com` / `googlemail.com`
  - Gmail API message list/get route
  - delegated OAuth 2.0
  - minimum read scope `https://www.googleapis.com/auth/gmail.readonly`
- `microsoft-outlook-graph` for `outlook.com` / `hotmail.com` / `live.com` / `msn.com`
  - Microsoft Graph mail route
  - delegated OAuth 2.0
  - minimum read permission `Mail.Read`
- `apple-icloud-mail` for `icloud.com` / `me.com` / `mac.com`
  - IMAP over TLS at `imap.mail.me.com:993`
  - app-specific password authorization for this documented third-party route

Every provider entry:
- requires explicit user authorization;
- maps credential destination to SKAP Vault;
- prohibits KV secret storage;
- carries dated provider-documentation evidence;
- remains `runtime_verified=false` until StegVerse performs a real conformance/activation observation.

Unknown domains remain fail-closed rather than guessing a provider.


## Documented-provider validation evidence

Provider-adapter PR: `#95`  
Validated head: `6ef27a1aec2b0c04dd3f0fcd047cba4d1c10a1fd`

Exact-head hosted validation:
- Validate KV Email Ingress Policy run `33136236584`: PASS
- Security Baseline run `33136236583`: PASS
- Repository validation diagnostics run `33136236577`: PASS
- KV Guardrails run `33136236557`: PASS
- Release integrity run `33136236581`: PASS

This validates repository source and documented provider metadata only. Gmail, Microsoft Graph mail, and iCloud Mail remain `DOCUMENTED_UNVERIFIED` until real owner-authorized provider sessions are observed.


## Documented-provider merge evidence

- PR: `#95`
- final validated head: `f01d45c4da710420da2976e7b388d267055b9a65`
- merge: `93cc683471d4012b538203f27c7cd8a1c509ebdf`
- merged state: DOCUMENTED_UNVERIFIED provider routes / LIVE ACTIVATION PENDING

Final exact-head validation:
- Validate KV Email Ingress Policy run `33136267560`: PASS
- Security Baseline run `33136267572`: PASS
- Repository validation diagnostics run `33136267603`: PASS
- KV Guardrails run `33136267622`: PASS
- Release integrity run `33136267563`: PASS


## Personal-information multi-email entry point

The governed email lane now has a second intuitive entry surface in addition to the dedicated Email/Connect Email flow.

Source:
- `schemas/kv-personal-contact-profile.schema.json`
- `vault_template/KnowledgeVault/_Entities/Self/Personal_Contact_Profile.json`
- `runtime/personal_contact_profile.py`
- `tests/test_personal_contact_profile.py`
- `USER_GUIDE.md`

Behavior:
- personal information may contain zero, one, or multiple email addresses;
- addresses are normalized and duplicate addresses are rejected case-insensitively;
- each address has its own owner-selected label;
- at most one address is marked primary, but primary status does not grant authority;
- an address may remain ordinary contact information with `email_continuity_enabled=false`;
- enabling continuity for one address maps only that address into the existing governed email flow;
- every mapped address has its own deterministic `mapping_id` and connection state;
- one address may be `SESSION_VERIFIED` while another remains `UNMAPPED`, `MAPPED_CREDENTIAL_REQUIRED`, `CREDENTIAL_BOUND`, or `REVOKED`;
- mailbox credentials remain SKAP-only and never become personal-profile fields.

Intended UX:

```text
Personal Information
 -> Email addresses
 -> + Add email
 -> label / optional primary
 -> [optional] Connect this email
 -> provider mapping
 -> Complete setup in SKAP Vault
 -> governed ingress for that address
```


## Personal-information multi-email merge evidence

- PR: `#103`
- validated head: `c1034161b7c1bab20740851858bd993b1a673533`
- merge: `11fba19b646f2d597c66d604f82663bd608ea65b`

Exact-head validation:
- Validate KV Email Ingress Policy run `33137954171`: PASS
- Security Baseline run `33137954127`: PASS
- Repository validation diagnostics run `33137954134`: PASS
- Release integrity run `33137954148`: PASS
- KnowledgeVault Execution Recovery run `33137954130`: PASS
- KV Guardrails run `33137954121`: PASS

Merged behavior:
- Personal Information can hold multiple email addresses;
- one address may be marked primary for preference/display, but primary status grants no mailbox authority;
- each address can independently opt into governed email continuity;
- each mapped address has its own mapping/session state and SKAP completion path;
- ordinary profile-only addresses remain `UNMAPPED` and require no provider credentials.
