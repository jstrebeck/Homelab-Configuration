# MLflow Tracking Server

MLflow tracking server + model registry in the `mlops` namespace. Shared by ML projects in the homelab (e.g. demand-forecast-mlops).

- **URL:** http://192.168.2.202 (LoadBalancer via MetalLB)
- **Image:** `192.168.2.203:5000/mlflow:latest` (custom build with psycopg2, built from the demand-forecast-mlops repo `Dockerfiles/mlflow.Dockerfile`)
- **Backend store:** in-cluster PostgreSQL (`mlflow-postgres` ClusterIP service, 5Gi `ceph-block` PVC)
- **Artifacts:** 10Gi `ceph-block` PVC, proxied by the server (`--serve-artifacts`)

## Deploy
```
kubectl apply -f namespace.yaml
kubectl apply -f postgres.yaml
kubectl apply -f mlflow.yaml
```

## Teardown
```
kubectl delete -f mlflow.yaml --ignore-not-found
kubectl delete -f postgres.yaml --ignore-not-found
kubectl delete -f namespace.yaml --ignore-not-found
```
