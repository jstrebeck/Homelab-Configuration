# ADR-0005: Automated sync, manual prune, selective self-heal

**Status:** Accepted
**Date:** 2026-09-29

## Context

Automated sync with pruning and self-heal is the usual Argo CD default. Here
the platform apps own CRDs, namespaces and PVCs. Pruning a CRD deletes every
custom resource of that kind in the cluster (all CephClusters, all
InferenceServices), and pruning a namespace or PVC deletes data. Some
components are also still being developed with `kubectl`/`helm` while their
manifests settle.

## Decision

- Every app syncs automatically on merge to `main`.
- Pruning is manual for all platform apps: a removed resource shows as
  "requires pruning" and is deleted with `argocd app sync <app> --prune` after
  review. Application repos that own only stateless workloads may prune.
- Self-heal is on for components that only change through Git (Argo CD,
  MetalLB, Rook-Ceph, monitoring, registry, cloudflared). It is off for the ML
  stack (cert-manager, KServe, SeaweedFS, MLflow, fraud) until that work is
  merge-to-deploy only.
- No `resources-finalizer` on Applications, so deleting an Application never
  cascades.

## Consequences

- A bad commit cannot destroy data; the worst case is an OutOfSync app.
- Cleanup after removing manifests is a deliberate, reviewed step.
- Revisit self-heal for the ML stack once it stops changing by hand.
