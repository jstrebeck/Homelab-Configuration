# payments Postgres

Postgres 17 for the payments API in
[payments-fraud-detection](https://github.com/jstrebeck/payments-fraud-detection).
Stores every scored transaction and its fraud decision (and, later, delayed
chargeback labels used for retraining).

- **Namespace:** `fraud`
- **In-cluster address:** `payments-postgres.fraud.svc:5432`, database `payments`
- **Storage:** 5Gi `ceph-block` PVC via the StatefulSet's volumeClaimTemplate
  (`data-payments-postgres-0`)
- **Schema:** owned by the payments API (migrations run from that repo), not
  by this manifest.

## Deploy

The `fraud` namespace must exist first (`../../fraud/`).

```
# 1. Credentials for Postgres itself
PGPASS=$(openssl rand -hex 24)
kubectl -n fraud create secret generic payments-postgres \
  --from-literal=POSTGRES_USER=payments \
  --from-literal=POSTGRES_PASSWORD="$PGPASS"

# 2. Connection string the payments API reads (Secret name is part of the
#    contract in payments-fraud-detection/docs/homelab-integration.md)
kubectl -n fraud create secret generic payments-db \
  --from-literal=DATABASE_URL="postgresql+asyncpg://payments:${PGPASS}@payments-postgres.fraud.svc:5432/payments"

# 3. The database
kubectl apply -f postgres.yaml
kubectl -n fraud rollout status statefulset/payments-postgres
```

## Verify

```
kubectl -n fraud exec payments-postgres-0 -- psql -U payments -d payments -c 'select version();'
```

## Teardown

```
kubectl delete -f postgres.yaml --ignore-not-found
# The PVC is kept by the StatefulSet. Delete it only if the data can go:
kubectl -n fraud delete pvc data-payments-postgres-0
```
