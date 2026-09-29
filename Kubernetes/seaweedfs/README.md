# SeaweedFS

S3-compatible object store for the homelab. First bucket: `mlflow-artifacts`,
the MLflow artifact store, which KServe also reads models from. Chosen over
MinIO, which no longer publishes community container images.

- **Namespace:** `seaweedfs`
- **Version:** `chrislusf/seaweedfs:4.48`
- **Shape:** one StatefulSet pod running master, volume server, filer and the
  S3 gateway (`weed server -s3`). No replication; durability comes from the
  Ceph-backed PVC. Split into separate components (or the upstream Helm chart)
  only if this outgrows one pod.
- **S3 endpoint (in-cluster):** `http://seaweedfs.seaweedfs.svc:8333`,
  path-style, plain HTTP, region `us-east-1`. Not exposed on the LAN; laptops
  reach artifacts through MLflow's `--serve-artifacts` proxy.
- **Storage:** 50Gi `ceph-block` PVC (`data-seaweedfs-0`)
- **Metrics:** `:9327/metrics`, scraped via `ServiceMonitor`
  (`release: kube-prometheus-stack` label)

## Identities

Access is controlled by the static identity file `s3.json`, stored in Secret
`seaweedfs-s3-config` and never committed (`s3.json.example` is the template).
Each consumer gets its own keys, scoped to the buckets it needs:

| Identity | Used by | Permissions |
|---|---|---|
| `mlflow` | MLflow server (`mlops`) | Read, Write, List, Tagging on `mlflow-artifacts` |
| `kserve-fraud` | KServe storage initializer (`fraud`) | Read, List on `mlflow-artifacts` |

No identity has Admin, so none can create or delete buckets. Buckets are
created with `weed shell` from inside the pod.

## Deploy

```
# 1. Generate keys and write the identity file (keep the values; step 4 and
#    the consumers' Secrets need them)
MLFLOW_AK=$(openssl rand -hex 10); MLFLOW_SK=$(openssl rand -hex 20)
KSERVE_AK=$(openssl rand -hex 10); KSERVE_SK=$(openssl rand -hex 20)
sed -e "s/<mlflow-access-key>/$MLFLOW_AK/" -e "s/<mlflow-secret-key>/$MLFLOW_SK/" \
    -e "s/<kserve-access-key>/$KSERVE_AK/" -e "s/<kserve-secret-key>/$KSERVE_SK/" \
    s3.json.example > /tmp/s3.json

# 2. Namespace, config Secret, server
kubectl apply -f seaweedfs.yaml   # Secret not there yet: pod waits in ContainerCreating
kubectl -n seaweedfs create secret generic seaweedfs-s3-config --from-file=s3.json=/tmp/s3.json
rm /tmp/s3.json
kubectl -n seaweedfs rollout status statefulset/seaweedfs

# 3. Bucket
kubectl -n seaweedfs exec seaweedfs-0 -- sh -c \
  'echo "s3.bucket.create -name mlflow-artifacts" | weed shell -master=127.0.0.1:9333'

# 4. Consumer Secrets: see ../mlflow/README.md (mlflow-s3) and
#    ../fraud/README.md (s3-credentials)
```

## Verify

```
kubectl -n seaweedfs exec seaweedfs-0 -- sh -c 'echo "s3.bucket.list" | weed shell -master=127.0.0.1:9333'
kubectl -n mlops run s3check --rm -it --restart=Never --image=amazon/aws-cli:2.37.5 \
  --env AWS_ACCESS_KEY_ID=$MLFLOW_AK --env AWS_SECRET_ACCESS_KEY=$MLFLOW_SK -- \
  --endpoint-url http://seaweedfs.seaweedfs.svc:8333 s3 ls s3://mlflow-artifacts/
```

## Rotating keys / adding an identity

Edit the identity file, then replace the Secret and restart the pod:

```
kubectl -n seaweedfs create secret generic seaweedfs-s3-config \
  --from-file=s3.json=<file> --dry-run=client -o yaml | kubectl apply -f -
kubectl -n seaweedfs rollout restart statefulset/seaweedfs
```

## Teardown

```
kubectl delete -f seaweedfs.yaml --ignore-not-found   # deletes the namespace
# The PVC goes with the namespace. Back up the bucket first if the data matters.
```
