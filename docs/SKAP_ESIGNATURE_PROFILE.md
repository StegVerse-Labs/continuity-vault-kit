# SKAP Vault E-Signature Profile

Reusable e-signature/signing material belongs in SKAP Vault.

KnowledgeVault may retain a bounded reference:

`skap://signing/<profile-id>`

but never the reusable signature image/key/material itself.

A signing operation must bind:
- signer identity reference;
- exact unsigned document SHA-256;
- document purpose and business/workspace;
- explicit owner approval;
- signing method;
- signed artifact SHA-256;
- timestamp;
- resulting SKAP signing receipt.

The default is `auto_apply=false`.

A stored signature is capability material, not standing authorization. No form mapper may apply it merely because a SKAP reference exists.
