# Argo CD

GitOps controller for the cluster. Everything under `Kubernetes/` that runs on
the cluster is declared here as an Argo CD `Application`; a change merged to
`main` is what deploys it.

- **UI:** http://192.168.2.217 (MetalLB), user `admin`
- **Namespace:** `argocd`
- **Chart:** `oci://ghcr.io/argoproj/argo-helm/argo-cd` `10.9.4` (Argo CD v3.5.3), values in `values.yaml`
- **Pattern:** app of apps. `root.yaml` is applied once by hand and points at
  `apps/`; every file in `apps/` is one or more `Application`s. Argo CD also
  manages its own Helm release (`apps/argocd.yaml`).

## Layout

```
argocd/
  values.yaml          Argo CD Helm values (also used by the self-managed app)
  root.yaml            app of apps, the only manifest applied with kubectl
  apps/
    projects.yaml      AppProjects: platform (this repo), fraud (payments-fraud-detection)
    argocd.yaml        Argo CD itself
    metallb.yaml       upstream native manifest + ../metallb/metallb.yaml (kustomize)
    rook-ceph.yaml     operator + cluster charts, values in ../ceph-rook/
    monitoring.yaml    kube-prometheus-stack, values in ../grafana/
    cert-manager.yaml  values in ../cert-manager/
    kserve.yaml        kserve-crd, kserve, kserve-runtimes, kserve-mlflow-initializer
    seaweedfs.yaml     ../seaweedfs/seaweedfs.yaml
    mlflow.yaml        ../mlflow/ (namespace, postgres, server)
    registry.yaml      ../registry/registry.yaml
    cloudflared.yaml   ../cloudflare/cloudflare.yaml
    fraud.yaml         fraud namespace, payments Postgres, and the
                       payments-fraud-detection app from its own repo
```

Sync waves order creation on a fresh cluster: projects, Argo CD, MetalLB,
Rook-Ceph, monitoring and cert-manager, KServe, then the workloads.

## Conventions

- **Secrets are not in Git.** Manifests reference Secrets by name; each
  component's README has the `kubectl create secret` commands. Argo CD never
  creates, changes or prunes them.
- **Charts are pinned** (`targetRevision`) and values live next to the
  component, not inline in the `Application`.
- **Release names match the original `helm install`** so Argo CD adopted the
  existing resources in place instead of recreating them.
- **Automated sync, manual prune.** Every app syncs on merge. Pruning is
  never automatic for platform apps: a removed file shows up as "requires
  pruning" and is deleted with `argocd app sync <app> --prune` after a look,
  so a bad commit can't take CRDs, namespaces or PVCs (and their data) with it.
  The exception is `payments-fraud-detection`, which prunes its own resources
  per that repo's ADR-0008.
- **Self-heal** is on for components that only change through Git (Argo CD,
  MetalLB, Rook-Ceph, monitoring, registry, cloudflared). It is off for the ML
  stack (cert-manager, KServe, SeaweedFS, MLflow, fraud) while that is still
  being built out with `kubectl`/`helm`; switch it on once those READMEs say
  "merge to deploy".
- **No `resources-finalizer`.** Deleting an `Application` leaves its resources
  running; nothing is cascade-deleted by accident.
- **One-off Jobs stay out.** e.g. `mlflow/migrate-artifacts-job.yaml` and
  `kserve/smoke-test.yaml` are excluded with `directory.include`.

## Bootstrap (new cluster)

```
helm install argocd oci://ghcr.io/argoproj/argo-helm/argo-cd \
  --version 10.9.4 --namespace argocd --create-namespace -f values.yaml
kubectl apply -f root.yaml
```

Then create the Secrets listed in each component README. Argo CD takes over
its own release from the first sync.

## Day to day

```
# Admin password (delete the secret once you've changed it)
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

argocd login 192.168.2.217 --plaintext --username admin
argocd app list
argocd app diff <app>
```

To change something: edit the manifest or values file, open a PR, merge.
Upgrading a chart is a one-line `targetRevision` bump in `apps/`.
