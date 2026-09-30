# ADR-0007: SeaweedFS as the S3 store for ML artifacts

**Status:** Accepted
**Date:** 2026-09-29

## Context

MLflow artifacts, and the models KServe loads from them, need an
S3-compatible store with per-consumer credentials. MinIO no longer publishes
community container images. Ceph RGW is already running, but its bucket and
user management goes through Rook CRDs and the RGW admin API, which is heavier
than the use case needs.

## Decision

A single SeaweedFS pod (`weed server -s3`, image pinned) on a Ceph-backed PVC,
with a static identity file granting each consumer access only to the buckets
it needs (`mlflow` read/write, `kserve-fraud` read-only).

## Consequences

- Durability comes from Ceph underneath, so SeaweedFS runs without replication.
- Plain S3 for every client: MLflow, boto3 and KServe's storage initializer.
- One pod is a single point of failure for artifact reads. Split into
  separate components (or the upstream chart) if that starts to matter.
