# metrics-server

Serves the `metrics.k8s.io` API (CPU and memory per node and pod) that
`kubectl top` and HorizontalPodAutoscalers read. KServe's predictor HPAs
depend on it.

- **Namespace:** `kube-system`
- **Source:** upstream `components.yaml` `v0.9.0`, pinned in `kustomization.yaml`
- **Delivered by:** Argo CD, `../argocd/apps/metrics-server.yaml`

It was first installed by hand with `kubectl apply`; the Argo CD app adopted
those resources in place (same names, same selector).

## Why `--kubelet-insecure-tls`

metrics-server scrapes each kubelet over HTTPS. Talos kubelets serve a
self-signed certificate unless `machine.kubelet.extraArgs.rotate-server-certificates`
is set and the CSRs are approved, so verification would fail. Traffic stays
TLS-encrypted; only the kubelet's identity isn't checked. To drop the flag,
enable kubelet serving-certificate rotation in the Talos machine config and
install a CSR approver first.

## Verify

```
kubectl get apiservice v1beta1.metrics.k8s.io   # AVAILABLE True
kubectl top nodes
```

## Upgrade

Change the version in the `components.yaml` URL and merge.
