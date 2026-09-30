# KServe

Model serving for ML projects in the homelab (first user:
payments-fraud-detection, which serves an MLflow model from the `fraud`
namespace).

Runs in **Standard** deployment mode (the renamed "RawDeployment"): each
`InferenceService` becomes a plain `Deployment`, `Service` and HPA. No
Knative, no Istio, no ingress controller. Clients call the predictor
in-cluster at `http://<isvc>-predictor.<namespace>.svc`.

- **Namespace:** `kserve`
- **Version:** `v0.20.0`. The v0.21.0 release exists on GitHub but its Helm
  charts were never published to ghcr (only `v0.21.0-rc1`); move up when they are.
- **Charts** (`oci://ghcr.io/kserve/charts/`):
  - `kserve-crd`: CRDs
  - `kserve-resources`: controller + webhook, values in `values.yaml`
  - `kserve-runtime-configs`: ClusterServingRuntimes (sklearn, xgboost,
    MLServer for `mlflow`, ...), values in `runtime-values.yaml`
- **MLflow storage initializer:** `mlflow-storage-initializer/`, a
  `ClusterStorageContainer` for `storageUri: models:/<name>@<alias>`.
- **Depends on:** cert-manager (`../cert-manager/`) for the webhook's
  self-signed cert.

## Deploy

```
helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd \
  --version v0.20.0 --namespace kserve --create-namespace

helm install kserve oci://ghcr.io/kserve/charts/kserve-resources \
  --version v0.20.0 --namespace kserve -f values.yaml
kubectl -n kserve rollout status deploy/kserve-controller-manager

helm install kserve-runtimes oci://ghcr.io/kserve/charts/kserve-runtime-configs \
  --version v0.20.0 --namespace kserve -f runtime-values.yaml

# models:/ storage URIs (MLflow registry); see mlflow-storage-initializer/README.md
kubectl apply -f mlflow-storage-initializer/cluster-storage-container.yaml
```

## Verify

```
kubectl get crd inferenceservices.serving.kserve.io
kubectl get clusterservingruntimes          # expect kserve-mlserver among them
kubectl -n kserve get configmap inferenceservice-config \
  -o jsonpath='{.data.deploy}'              # {"defaultDeploymentMode": "Standard"}

# End-to-end smoke test
kubectl create namespace kserve-test
kubectl apply -f smoke-test.yaml
kubectl -n kserve-test wait isvc/sklearn-iris --for=condition=Ready --timeout=5m
kubectl -n kserve-test run curl --rm -it --restart=Never --image=curlimages/curl -- \
  curl -s -H 'Content-Type: application/json' \
  -d '{"instances": [[6.8, 2.8, 4.8, 1.4], [6.0, 3.4, 4.5, 1.6]]}' \
  http://sklearn-iris-predictor.kserve-test.svc/v1/models/sklearn-iris:predict
# -> {"predictions":[1,1]}
kubectl delete namespace kserve-test
```

## Model storage

The storage initializer pulls models before the predictor starts. For
MLflow-registered models use `storageUri: models:/<name>@<alias>`: the
`mlflow` ClusterStorageContainer (`mlflow-storage-initializer/`) resolves it
against the homelab MLflow and downloads through the artifact proxy, with no
S3 credentials. Raw `s3://mlflow-artifacts/<path>` URIs still work with the
default initializer and a ServiceAccount referencing an S3 credentials Secret
(see `../fraud/`).

## Teardown

```
helm uninstall kserve-runtimes kserve -n kserve
helm uninstall kserve-crd -n kserve   # deletes every InferenceService in the cluster
kubectl delete namespace kserve
```
