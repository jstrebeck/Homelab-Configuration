# ADR-0002: Rook-Ceph for persistent storage

**Status:** Accepted
**Date:** 2026-09-29 (recorded; Rook-Ceph replaced Longhorn in 2026-01)

## Context

Stateful workloads (Postgres, Prometheus, Grafana, SeaweedFS, the registry)
need volumes that survive a node loss. Longhorn was used first
(`Kubernetes/Longhorn/`). It provides block volumes, with RWX only through an
NFS layer and no object storage, while several workloads want shared
filesystems or buckets as well.

## Decision

Rook-Ceph, installed with the `rook-ceph` and `rook-ceph-cluster` Helm charts:
three OSDs (one 500 GiB disk per worker), three monitors, host failure domain,
3-way replication. It exposes `ceph-block` (default StorageClass),
`ceph-filesystem` (RWX) and `ceph-bucket` (object).

## Consequences

- Block, file and object storage from one system, surviving the loss of any
  single worker.
- 3x replication means 1.5 TiB raw gives about 500 GiB usable.
- Ceph is the most operationally demanding component in the cluster. Its
  daemons' CPU requests are sized down from the chart defaults to fit the
  nodes, and it is the one app Argo CD will never prune.
