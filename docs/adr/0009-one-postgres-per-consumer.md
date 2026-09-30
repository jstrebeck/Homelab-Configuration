# ADR-0009: One PostgreSQL instance per consumer, no operator

**Status:** Accepted
**Date:** 2026-09-29

## Context

Several applications need PostgreSQL. Options were a shared server, an
operator (CloudNativePG), or one small instance per application.

## Decision

Each consumer gets its own Postgres StatefulSet in its own namespace, with a
pinned image, non-root, `pg_isready` probes and a `ceph-block` PVC. Manifests
are grouped under `Kubernetes/databases/`.

## Consequences

- Isolation: a noisy or broken database affects one application, and
  credentials never cross namespaces.
- No replicas, PITR or managed backups. Adopt CloudNativePG when any database
  needs them.
