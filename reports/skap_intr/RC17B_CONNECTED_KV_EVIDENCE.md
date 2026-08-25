# RC-17B Connected KnowledgeVault Evidence

Status: PASS — SYNTHETIC CIPHERTEXT ONLY
Date: 2026-08-25
Goal: SV-KV-SKAP-INTR-001

## Canonical live path

```text
KnowledgeVault/
_Vault/
  SKAP/
    Sealed/
    Lifecycle/
    Receipts/
    Revocations/
```

Canonical storage-layout contract: `specs/skap-kv-storage-layout.v1.json` at commit `c7880b2a31f71a1f069a4f510e9977c840415369`.

## Connected Drive folders

- `_Vault`: `1xNvbptiLxHc0ZfxAu0v8IuPVmaZoyYyp`
- `_Vault/SKAP`: `1Mc3WXasLM8JLqplEl1ZLIXLIWTO4zp6O`
- `Sealed`: `1zoFRW2dywVan8d8NhdxbedvbERDZEzDz`
- `Lifecycle`: `1DwpsezAOBi-wWBbsa3sUR2K_xcz9tcQF`
- `Receipts`: `12Z-0BIxRroICYeUr2Bl8M2lHVj0P3BXU`
- `Revocations`: `1cGgKzd0wgOmGARU4-1Ewf8sq-RVBreIW`

## Synthetic live records

Stored as unconverted `text/plain` with JSON filenames:

- `Sealed/rc17-synthetic-coinbase-v1.sealed.json` — Drive id `1mVRvXIfx-a_iqVEBLuoy-wR_LK38MjR7`
- `Sealed/rc17-synthetic-coinbase-v1.object.json` — Drive id `1Pzrj3TIwJRgPO6BtDeVCGdvMnU_9f2kJ`
- `Lifecycle/rc17-synthetic-coinbase-v1.lifecycle.json` — Drive id `1i0cOBoc8P9E1TX4z4ax-bfVB0aYj5yU1`
- `Receipts/rc17-synthetic-coinbase-v1.ingress.json` — Drive id `1kpb6lj1LqlL2-W1yAyVp6s9SY0bZzyo-`

No production credential or production SKAP root key was used.

## Hash/readback proof

Readback of the actual connected Drive ciphertext envelope recomputed:

`sha256:3e00a8d61eca1df510132d3b82624b148aca6f4f4027960251dc49251a5960bc`

The persisted sealed-object metadata contains that exact `sealed_material_hash` and recomputes to object hash:

`sha256:2208e31d8ba72b10e840c7ff3ac17deaa7e39e8b9b7d61bb67f9fc918705840e`

The live object preserves:

```text
plaintext_persisted=false
kv_decryption_authority=false
device_secret_custody_authority=false
model_secret_access=false
```

The live ingress receipt independently preserves:

```text
plaintext_persisted=false
device_durable_secret_custody=false
kv_decryption_authority=false
model_secret_access=false
authority_transfer=false
synthetic_material_only=true
```

## Conclusion

`RC-17B actual connected KnowledgeVault synthetic sealed write/read` = PASS.

This proves the real connected KnowledgeVault can preserve and return hash-identical SKAP ciphertext plus non-secret lifecycle/ingress evidence without gaining decryption authority. It is not real credential ingress, production key provisioning, a provider-bound authenticated credential session, or an external effect.
