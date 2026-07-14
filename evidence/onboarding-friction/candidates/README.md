# Automation Candidate Evidence

This directory is maintained by `.github/workflows/automation-candidate-lifecycle.yml`.

For every issue labeled `automation-candidate`, the workflow preserves a readable and machine-readable evidence packet containing:

- the normalized friction signature;
- the candidate issue and URL;
- the configured report threshold;
- the current matching-report count;
- the exact source report issue references;
- duplicate or supersession relationships;
- the current lifecycle state;
- the evidence-generation time.

## Lifecycle

1. Three matching structured reports cause `onboarding-friction.yml` to create one candidate issue.
2. `automation-candidate-lifecycle.yml` independently checks the durable registry.
3. Supported candidates receive `candidate-supported`.
4. Candidates below threshold receive `candidate-insufficient-evidence`.
5. Duplicate candidates are linked to the earliest canonical issue and closed as superseded.
6. A merged pull request that explicitly fixes a supported candidate causes `automation-candidate-implementation.yml` to add `candidate-implemented`.
7. The lifecycle workflow preserves the final evidence packet and closes the implemented candidate.

A supported candidate authorizes investigation and implementation of the smallest repository-native correction that addresses the demonstrated setup friction. It never authorizes access to or mutation of user vault content.
