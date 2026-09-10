# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_MERGED / STORAGE_PROVIDER_ADAPTERS_MERGED / PROVIDER_OPERATION_STATE_MERGED / DEVICE_LOCAL_KV_OWNER_OBSERVED / GOOGLE_DRIVE_EXISTING_PEER_EXACT_EVIDENCE_RECOVERED / GOOGLE_DRIVE_KV2_OWNER_REQUEST_INGRESS_OBSERVED / KV2_ADOPTION_PROVIDER_BINDING_MERGED / IDENTITY_PRESERVING_KV2_MATERIALIZER_IMPLEMENTED_AWAITING_VALIDATION / GOOGLE_DRIVE_CONNECT_VERIFY_EXECUTION_PENDING / KV2_RUNTIME_MATERIALIZATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `skap-kv-device-roundtrip-001`
Updated: 2026-09-10
Authority effect: NONE
Activation effect: false

## Canonical task binding

```text
GOAL TASK ID: KV-CONNECTION-REVALIDATION-WORKER-001
COSV ID: 50000000102000
CANONICAL COSV HANDOFF: StegVerse-Labs/.github/KV_CONNECTION_REVALIDATION_COSV_MIRROR_HANDOFF.md
CANONICAL OWNER REPOSITORY: StegVerse-Labs/continuity-vault-kit
```

## Proven baseline

- Multi-instance identity, relationship tiers, MyKV projection, provider adapters, provider-operation state, and existing-KV adoption source are merged.
- Current iPhone resident KV #1 remains `kvi_0d5d4cfd531db51bbcf7fdfc0311f5dc` with exact local readback and BEST_EFFORT_BROWSER_ORIGIN durability.
- Existing Google Drive cloud vault remains exact-byte identified as `kvi_a31335d2cc3745fa987b635432cfed2c`.
- Authentic owner request `SITE-CLOUD-KV-4347408852127319cbda574f02e03edb` reached resident ingress but has not executed Google Drive, materialized KV #2, or changed relationship state.
- PR #205 merged the provider-binding source that creates canonical CONNECT and VERIFY requests and requires admitted Interlock/InTr + SKAP-reference + provider-result evidence before readiness.

## Identity-preserving KV #2 materialization

`runtime/cloud_peer_set_membership_materialization.py` closes the source gap left by the generic existing-KV adoption tool. The generic tool creates a new `kvi_...` identity and therefore MUST NOT be used for the recovered Google Drive vault.

The new materializer consumes only `materialization_ready=true` evidence after both CONNECT and VERIFY are admitted. It requires:

```text
existing_cloud_instance_id = kvi_a31335d2cc3745fa987b635432cfed2c
requested_instance_number = 2
materialization_mode = SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY
cloud_identity_rewrite_required = false
private_content_rewrite_authorized = false
relationship_tier_after_materialization = NOT_CONNECTED
credential_material_present = false
```

It refuses ordinal collisions, cross-set or cross-ordinal identity reuse, missing CONNECT/VERIFY receipt references, premature readiness, credential material, and identity/private-content rewrite semantics. Output preserves the existing cloud identity and binds only set membership/ordinal; it grants no relationship, provider, transport, credential, or activation authority.

Tests: `tests/test_cloud_peer_set_membership_materialization.py` cover identity preservation, not-ready refusal, KV #2 ordinal collision, rewrite refusal, and mutation/digest verification.

## README maintenance determination

Root README was reviewed on current main. No wording change is required for this internal materializer because the README already establishes all repository-level semantics changed/consumed here: KV numbering is not authority, identities remain separately rooted, relationship transitions require Interlock/InTr, provider requests require SKAP references and admitted evidence, and provider-operation state cannot infer execution. This handoff records the new implementation-specific identity-preserving materialization contract.

## Remaining end-to-end sequence

1. Validate and merge the identity-preserving materializer.
2. Complete the existing TVC/Service-Gateway query-secret-safe callback prerequisite before Google owner-consent execution.
3. Execute authentic owner consent inside TV/TVC/SKAP; never expose credential plaintext to Site, ordinary KV, repositories, logs, argv, or environment.
4. Execute canonical Google Drive CONNECT and VERIFY through Interlock/InTr and retain exact provider-result evidence.
5. Re-evaluate readiness and bind the existing cloud identity into `personal` as KV #2 without rewriting cloud identity/private content.
6. Return the result through SKAP -> KV -> current StegOS Device and require the canonical four-leg roundtrip proof plus exact device-side readback.
7. Only after authentic roundtrip evidence may the lane be called runtime-functional.

## Manual work

None now. Do not repeat the adoption request, authorize Google Drive, clear Safari/stegverse.org data, reinstall KV, or create KV #3 until the callback safety prerequisite and downstream provider execution lane are ready.
