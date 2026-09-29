# cert-manager

Installed as a prerequisite for KServe (`../kserve/`). KServe's controller
runs an admission webhook, and the Kubernetes API server only calls webhooks
over TLS with a CA it trusts. The KServe Helm chart always renders a
cert-manager `Certificate` for that webhook, backed by a **self-signed**
`Issuer`, so cert-manager is the least-effort way to get (and auto-renew)
that cert.

This is not used for ingress TLS. No ClusterIssuer, no ACME, no public certs.
Services stay plain HTTP inside the homelab.

- **Namespace:** `cert-manager`
- **Chart:** `oci://quay.io/jetstack/charts/cert-manager` `v1.21.2`
- **Values:** `values.yaml` (CRDs managed by Helm and kept on uninstall,
  small resource requests)

## Deploy

```
helm install cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.21.2 \
  --namespace cert-manager --create-namespace \
  -f values.yaml
kubectl -n cert-manager rollout status deploy/cert-manager-webhook
```

## Upgrade

```
helm upgrade cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version <new> --namespace cert-manager -f values.yaml
```

## Teardown

Remove KServe first (its `Certificate`/`Issuer` depend on these CRDs).

```
helm uninstall cert-manager -n cert-manager
# CRDs are kept (crds.keep=true). Remove them only if nothing else uses cert-manager:
kubectl get crd -o name | grep cert-manager.io | xargs kubectl delete
```
