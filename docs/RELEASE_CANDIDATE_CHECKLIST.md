# Release Candidate Checklist

Use this checklist before changing `VERSION`, creating a release tag, or publishing a Continuity Vault Kit bundle.

The checklist verifies repository packaging and release continuity. It does not certify the truth, safety, completeness, authority, or admissibility of user-authored vault content.

## 1. Entry conditions

- [ ] Issue #7 contains a successful release-integrity workflow run.
- [ ] The run URL and uploaded artifact name are recorded.
- [ ] `tools/test_release_tools.py` passed.
- [ ] The negative missing-sidecar test returned the expected non-zero result.
- [ ] The generated ZIP, `.sha256`, and `.manifest.json` files were inspected.
- [ ] Any builder/verifier mismatch has been resolved.

Do not change `VERSION` if any entry condition is incomplete.

## 2. Change classification

Review the Unreleased section of `CHANGELOG.md` and select one classification:

- **Patch:** compatible documentation, safety, onboarding, validation, or tooling improvements that do not require existing vaults to reorganize.
- **Minor:** a backward-compatible format capability or optional structural addition that materially expands the vault contract.
- **Major:** an incompatible format or migration requirement. Major changes require explicit migration artifacts and are not assumed by this checklist.

Record the decision and rationale in issue #8.

## 3. Migration review

- [ ] Read `vault_template/KnowledgeVault/_migration/README.md`.
- [ ] Confirm whether existing `0.1.x` vaults require any action.
- [ ] Confirm no new release silently overwrites an existing vault.
- [ ] Confirm any structural change has a source version, target version, affected paths, ordered steps, verification steps, rollback guidance, and owner acceptance point.
- [ ] Ensure release notes distinguish a new template file from a mandatory vault reorganization.

## 4. Version commit

- [ ] Update `VERSION` once.
- [ ] Convert `CHANGELOG.md` from `[Unreleased]` to the selected version and exact release date.
- [ ] Keep a new empty `[Unreleased]` section at the top when appropriate.
- [ ] Confirm README and onboarding claims match the release contents.
- [ ] Commit the version and changelog changes together.

## 5. Candidate verification

Run or observe `.github/workflows/release-integrity.yml` on the exact version commit.

- [ ] Workflow completed successfully.
- [ ] Manifest contains `schema_version`, artifact name, version, timestamp, bundle SHA-256, contents root, file count, and complete file inventory.
- [ ] Manifest file count equals the inventory length.
- [ ] Every packaged file hash and size verifies.
- [ ] Checksum sidecar names the correct ZIP.
- [ ] Required vault files are present.
- [ ] Archive contains no duplicate or unsafe paths.
- [ ] Uploaded evidence corresponds to the exact version commit.

## 6. Tagging

- [ ] Tag only the verified version commit.
- [ ] Tag name matches the repository's established version convention.
- [ ] Release notes match `CHANGELOG.md`.
- [ ] Attach or reference the verified ZIP, checksum, and manifest.
- [ ] Record the tag, commit SHA, workflow run, and artifact name in issue #8 and the mirror handoff.

## 7. Downstream verification

After tagging, complete issue #10. For each destination, record whether an update is required and why:

- `StegVerse-Labs/Site`
- `GCAT-BCAT-Engine/Publisher`
- `admissibility-wiki`
- `stegguardian-wiki`

Downstream publication must preserve the baseline position:

> Standalone by default, StegVerse-compatible by design.

## 8. Completion condition

The release process is complete only when the verified commit is tagged, release evidence is durably referenced, the handoff reflects the new state, and downstream verification ownership is recorded.
