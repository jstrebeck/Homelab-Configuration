# MLflow Tracking Server

MLflow tracking server + model registry in the `mlops` namespace. Shared by ML projects in the homelab (demand-forecast-mlops, payments-fraud-detection).

- **URL:** http://192.168.2.202 (LoadBalancer via MetalLB); in-cluster `http://mlflow.mlops.svc`
- **Version:** MLflow 3.16.1
- **Image:** `192.168.2.203:5000/mlflow:3.16.1`, built from `Dockerfile` in this directory (upstream `ghcr.io/mlflow/mlflow` plus psycopg2 and boto3). Always use a version tag, never `latest`.
- **Backend store:** in-cluster PostgreSQL (`mlflow-postgres` ClusterIP service, 5Gi `ceph-block` PVC). The `db-upgrade` init container migrates the schema to the image's MLflow version on every start (no-op when current).
- **Artifacts:** S3 bucket `mlflow-artifacts` on SeaweedFS (`../seaweedfs/`), proxied by the server (`--serve-artifacts`), so clients only need the MLflow URL. Credentials in Secret `mlflow-s3` (identity `mlflow`, read/write on that bucket only). An artifact at `mlflow-artifacts:/<path>` is stored at `s3://mlflow-artifacts/<path>`, which is what KServe reads. The old 10Gi PVC (`mlflow-artifacts-pvc`) is no longer mounted; it is kept until the S3 copy is verified.
- **Allowed hosts:** MLflow 3 rejects requests whose `Host` header is not allowed. `--allowed-hosts` in `mlflow.yaml` covers the service DNS names, localhost and private IP ranges. Add any new hostname (e.g. a Cloudflare tunnel name) there, or clients get `403 Invalid Host header`.

## Deploy
Requires SeaweedFS (`../seaweedfs/`) with the `mlflow-artifacts` bucket, and
Secret `mlflow-s3` (see "Moving artifacts to S3", step 1).
```
docker build -t 192.168.2.203:5000/mlflow:3.16.1 .
docker push 192.168.2.203:5000/mlflow:3.16.1
kubectl apply -f namespace.yaml
kubectl apply -f postgres.yaml
kubectl apply -f mlflow.yaml
```

## Upgrading MLflow

Schema migrations are one-way. Back up first.

```
# 1. Back up the backend store
kubectl -n mlops exec deploy/mlflow-postgres -- pg_dump -U mlflow -Fc mlflow > mlflow-$(date +%F).dump

# 2. Build and push the new version (update the tag in Dockerfile comments, FROM line and mlflow.yaml, both containers)
docker build -t 192.168.2.203:5000/mlflow:<version> .
docker push 192.168.2.203:5000/mlflow:<version>

# 3. Roll out; the init container migrates the schema before the server starts
kubectl apply -f mlflow.yaml
kubectl -n mlops rollout status deploy/mlflow
kubectl -n mlops logs deploy/mlflow -c db-upgrade

# 4. Verify
curl -s http://192.168.2.202/version
curl -s http://192.168.2.202/api/2.0/mlflow/experiments/search -H 'content-type: application/json' -d '{"max_results":5}'
```

Rollback: scale the deployment to 0, restore the dump
(`kubectl -n mlops exec -i deploy/mlflow-postgres -- pg_restore -U mlflow -d mlflow --clean < mlflow-<date>.dump`),
set both images back to the previous tag, apply.

### 2.21.3 to 3.16.1 (2026-09-29)

The previous image was `192.168.2.203:5000/mlflow:latest` (MLflow 2.21.3, built
from demand-forecast-mlops; that Dockerfile says 2.19.0, so the tag had
drifted). It is the rollback image; do not overwrite `latest`. The upgrade
was rehearsed locally against a 2.21.3 schema: existing runs, registered
models and aliases survive, 3.x clients can log/register/load models, and
2.x clients (demand-forecast) can still read models through the artifact proxy.

## Moving artifacts to S3 (one-off, 2026-09-29)

Before this, artifacts lived on `mlflow-artifacts-pvc`. Paths are copied 1:1,
so existing runs (demand-forecast) keep working with no database changes.

```
# 1. S3 credentials for MLflow (the `mlflow` identity from ../seaweedfs/)
kubectl -n mlops create secret generic mlflow-s3 \
  --from-literal=AWS_ACCESS_KEY_ID=$MLFLOW_AK \
  --from-literal=AWS_SECRET_ACCESS_KEY=$MLFLOW_SK

# 2. Stop the server (the PVC is RWO) and copy
kubectl -n mlops scale deploy/mlflow --replicas=0
kubectl apply -f migrate-artifacts-job.yaml
kubectl -n mlops wait job/mlflow-migrate-artifacts --for=condition=complete --timeout=10m
kubectl -n mlops logs job/mlflow-migrate-artifacts

# 3. Switch the server to S3 (also scales it back to 1)
kubectl apply -f mlflow.yaml
kubectl -n mlops rollout status deploy/mlflow

# 4. Verify an old artifact comes back through the proxy
curl -s "http://192.168.2.202/api/2.0/mlflow-artifacts/artifacts/2/07bab07c03de4a159e854c8d2d271650/artifacts/per_sku_metrics.csv" | head -3
```

Rollback: `git revert` the S3 change to `mlflow.yaml` and apply; the PVC still
holds the original files. Anything logged while on S3 would be missing, so
roll back quickly or copy it back with the same Job reversed.

Once verified: delete the Job, and remove the PVC block from `mlflow.yaml`
and the PVC itself (`kubectl -n mlops delete pvc mlflow-artifacts-pvc`) in a
follow-up change.

## Teardown
```
kubectl delete -f mlflow.yaml --ignore-not-found
kubectl delete -f postgres.yaml --ignore-not-found
kubectl delete -f namespace.yaml --ignore-not-found
```
