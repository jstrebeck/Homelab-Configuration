# MLflow storage initializer

Lets an `InferenceService` load a model straight from the MLflow registry:

```yaml
storageUri: models:/fraud-detector@champion   # or models:/fraud-detector/2
```

KServe's built-in storage initializer does not understand `models:/`. This
`ClusterStorageContainer` claims that prefix, so KServe runs this image as the
predictor's init container instead. At pod start it:

1. resolves the alias (or fixed version) against the homelab MLflow
   (`http://mlflow.mlops.svc`) over its REST API,
2. lists and downloads the model's files through MLflow's artifact proxy
   (`--serve-artifacts`), checking each file's size, so it needs **no S3
   credentials**,
3. writes `mlflow-model.json` (what was resolved: name, alias, version, run,
   tags) and, unless the model ships one, `model-settings.json` with
   `{"parameters": {"version": "<n>"}}`, so MLServer reports the registry
   version as `model_version` in every V2 response.

Promotion and rollback are therefore "move the alias, restart the predictor
pods". Git does not change.

- **Image:** `192.168.2.203:5000/mlflow-storage-initializer:0.1.0`, built from
  `Dockerfile` (python:3.12 slim plus `initializer.py`, standard library only).
  The MLflow Python client is deliberately not used: its parallel downloader
  stalled against this server and left zero-filled files.
- **Runs as:** uid 65532, read-only root filesystem, writes only to
  `/mnt/models`.
- **Only proxied artifacts:** a model whose download URI is not
  `mlflow-artifacts:/...` fails with a clear error.

## Deploy

```
docker build -t 192.168.2.203:5000/mlflow-storage-initializer:0.1.0 .
docker push 192.168.2.203:5000/mlflow-storage-initializer:0.1.0
```

The `ClusterStorageContainer` is deployed by Argo CD
(`../../argocd/apps/kserve.yaml`, app `kserve-mlflow-initializer`); a new
image tag goes live by merging the tag change in `cluster-storage-container.yaml`.

## Test without the cluster

```
mkdir -m 777 /tmp/model
docker run --rm --read-only --user 65532:65532 -v /tmp/model:/mnt/models \
  -e MLFLOW_TRACKING_URI=http://192.168.2.202 \
  192.168.2.203:5000/mlflow-storage-initializer:0.1.0 models:/fraud-detector@champion /mnt/models
```

## Troubleshooting

The predictor pod stays in `Init` when resolution or download fails; the
reason is the last JSON line of
`kubectl -n <ns> logs <predictor-pod> -c storage-initializer`.
