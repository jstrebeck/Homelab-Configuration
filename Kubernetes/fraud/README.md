# fraud namespace

Platform side of the
[payments-fraud-detection](https://github.com/jstrebeck/payments-fraud-detection)
project. That repo deploys its own workloads into `fraud`; this folder holds
what the cluster has to provide first.

| Resource | Purpose | Source |
|---|---|---|
| Namespace `fraud` | Home for the project | `namespace.yaml` |
| ServiceAccount `kserve-sa` | KServe storage initializer identity for raw `s3://` storage URIs. `fraud-detector` itself uses `models:/fraud-detector@champion` via `../kserve/mlflow-storage-initializer/` and needs no S3 keys. | `namespace.yaml` |
| Secret `s3-credentials` | Read-only S3 keys for pulling models from `mlflow-artifacts` | created by hand, see below |
| Postgres `payments-postgres` + Secrets `payments-postgres`, `payments-db` | Payments API database | [`../databases/payments/`](../databases/payments/) |

## Deploy

```
kubectl apply -f namespace.yaml
```

Then deploy the database from `../databases/payments/`.

## S3 credentials

Uses the read-only `kserve-fraud` identity from `../seaweedfs/`. KServe reads
the endpoint and TLS setting from annotations on the Secret:

```
kubectl -n fraud create secret generic s3-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=$KSERVE_AK \
  --from-literal=AWS_SECRET_ACCESS_KEY=$KSERVE_SK
kubectl -n fraud annotate secret s3-credentials \
  serving.kserve.io/s3-endpoint=seaweedfs.seaweedfs.svc:8333 \
  serving.kserve.io/s3-usehttps=0 \
  serving.kserve.io/s3-region=us-east-1
```

## Teardown

```
kubectl delete -f namespace.yaml   # deletes everything in the namespace, including the DB PVC
```
