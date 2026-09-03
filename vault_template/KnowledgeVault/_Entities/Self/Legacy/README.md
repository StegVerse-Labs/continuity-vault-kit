# Legacy

Private owner-controlled continuity capsules live under this directory.

- `Capsules/` — sealed capsule records and sealed payload references.
- `Policies/` — owner-authored release, disclosure, alternate-disposition, and participation policies.
- `Recipients/` — private recipient references and resolution policy.

Do not store reusable credentials, private keys, recovery codes, or provider tokens here. Those remain behind SKAP/TV/TVC boundaries.

A recipient candidate must not be able to infer that a capsule exists merely from discovery or invitation. Disclosure is governed separately from custody.

Repository template presence does not arm a capsule, verify a death/life-continuity trigger, authorize a recipient, transfer StegCoin/StegToken, or activate runtime release.
