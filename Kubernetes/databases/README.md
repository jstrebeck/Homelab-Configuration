# Databases

Home for the PostgreSQL instances running on the cluster. One sub-folder per
database, each a single self-contained manifest plus a README.

## Conventions

- **Plain StatefulSet**, one Postgres per consumer, no operator. Enough for a
  homelab; revisit CloudNativePG if we ever want replicas, PITR or managed
  backups.
- **Runs in the consumer's namespace.** The folder groups the manifests, not
  the workloads. The app reaches its DB at `<name>-postgres.<namespace>.svc:5432`
  and the credentials Secret never has to cross namespaces.
- **Pinned image** (`postgres:<major>.<minor>`), non-root (uid 999), all
  capabilities dropped, `pg_isready` probes, requests/limits set.
- **Storage:** `ceph-block` (Rook-Ceph, the cluster default), `PGDATA` in a
  sub-directory so `lost+found` doesn't break `initdb`.
- **Credentials are never committed.** Each README has the `kubectl create
  secret` commands; the manifest only references the Secret by name.
- **ClusterIP only.** Nothing is exposed on a MetalLB IP; use
  `kubectl port-forward` for ad-hoc access.

## Inventory

| Database | Namespace | Service | Manifests |
|---|---|---|---|
| payments (payments-fraud-detection) | `fraud` | `payments-postgres.fraud.svc:5432` | [`payments/`](payments/) |
| mlflow (MLflow backend store) | `mlops` | `mlflow-postgres.mlops.svc:5432` | [`../mlflow/postgres.yaml`](../mlflow/postgres.yaml), not yet moved here |
| filtergroove | `filtergroove` | `postgres.filtergroove.svc:5432` (LB `192.168.2.205`) | lives in the filtergroove repo |

## Adding a database

Copy `payments/`, rename `payments` throughout, create the Secret in the
target namespace, `kubectl apply -f`, then add a row above.
