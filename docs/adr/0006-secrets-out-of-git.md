# ADR-0006: Secrets are created out of band, never committed

**Status:** Accepted
**Date:** 2026-09-29

## Context

The repository is public. GitOps tooling for secrets exists (Sealed Secrets,
SOPS, External Secrets with a vault), but each adds a controller or key
management to run, and the number of secrets is small.

## Decision

Manifests reference Secrets by name only. Each component's README documents
the `kubectl create secret` commands. Argo CD does not create, update or
prune Secrets. CI runs `gitleaks` over the full history on every push.

## Consequences

- Rebuilding the cluster needs a manual step per component to recreate its
  Secrets, from values kept outside Git.
- No encryption keys to manage or leak.
- Revisit with External Secrets if the count grows or rotation becomes routine.
