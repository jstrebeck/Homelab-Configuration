# ADR-0004: Argo CD, app of apps, adopting the running cluster in place

**Status:** Accepted
**Date:** 2026-09-29

## Context

Components were deployed by following per-directory README runbooks
(`kubectl apply`, `helm install`). Nothing reconciled the cluster against the
repo, and some live resources had drifted from the files: hand-applied
patches, resized Ceph requests. Services on the cluster were in active use, so
the move to GitOps could not recreate anything.

## Decision

Argo CD, installed with Helm and then managing its own release. A single
`root` Application points at `Kubernetes/argocd/apps/`; each file there
declares the `Application`s for one component. Existing resources were
adopted in place:

- annotation-based resource tracking, so Argo CD doesn't touch the
  `app.kubernetes.io/instance` labels Helm charts use in selectors;
- Helm release names matching the original installs;
- apps created without automated sync, diffed with `argocd app diff`, and
  live drift either written into Git (Ceph resources, operator tolerations) or
  explicitly ignored (runtime-injected CA bundles, generated passwords) before
  the first sync.

## Consequences

- The migration restarted exactly one pod (the Rook operator, which regained
  a default toleration) and no workloads.
- Git is the source of truth; `helm upgrade` or `kubectl apply` on a managed
  resource is drift.
- Helm release Secrets from the original installs are left in place and are
  now inert.
