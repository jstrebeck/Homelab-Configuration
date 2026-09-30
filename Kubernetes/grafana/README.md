# Monitoring (kube-prometheus-stack)

Prometheus, Alertmanager, Grafana, node-exporter and kube-state-metrics from
the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
chart, plus the dashboards in `dashboards/`.

- **Namespace:** `monitoring`
- **Chart:** `kube-prometheus-stack` `81.0.0`, values in `values.yaml`
- **Delivered by:** Argo CD, `../argocd/apps/monitoring.yaml` (apps
  `kube-prometheus-stack` and `grafana-dashboards`)
- **Grafana:** http://192.168.2.204 (MetalLB), 10Gi `ceph-block` volume
- **Prometheus:** 7 days or 18GB of metrics, whichever comes first, on a 20Gi
  `ceph-block` volume. In-cluster at
  `http://kube-prometheus-stack-prometheus.monitoring.svc:9090`
- **Alertmanager:** in-cluster only; no receiver configured yet

## What gets scraped

Prometheus selects every `ServiceMonitor`, `PodMonitor`, `Probe` and
`PrometheusRule` in the cluster, whatever its labels
(`*SelectorNilUsesHelmValues: false`). To monitor something, ship a
`ServiceMonitor` with it:

| Source | Defined in |
|---|---|
| Nodes, kubelet, API server, CoreDNS, kube-state-metrics | this chart |
| Ceph mgr + exporter, and Rook's Ceph alert rules | `../ceph-rook/values-*.yaml` (`monitoring.enabled`) |
| Argo CD controller, server, repo server | `../argocd/values.yaml` |
| SeaweedFS | `../seaweedfs/seaweedfs.yaml` |
| payments-fraud-detection | that repo's `deploy/` |

The controller manager, scheduler and kube-proxy are not scraped: Talos binds
their metrics endpoints to localhost. Re-enable them in `values.yaml` after
changing their bind addresses in the Talos machine config.

## Dashboards

Dashboards are ConfigMaps labelled `grafana_dashboard: "1"`. Grafana's sidecar
watches all namespaces and loads them without a restart; the `grafana_folder`
annotation picks the folder. Anything built by hand in the UI lives only on
Grafana's volume, so export it into `dashboards/` to keep it.

| Folder | Dashboard | Source |
|---|---|---|
| Homelab | Homelab overview: nodes, Ceph, Argo CD sync, alerts | `dashboards/homelab-overview.py` generates the JSON |
| Homelab | Kubernetes Dashboard: resource counts, requests vs limits, per-namespace CPU/memory, throttling, restarts | `dashboards/kubernetes-overview.json` |
| Ceph | Ceph Cluster, Ceph - OSD (Single), Ceph - Pools | Rook v1.18.8 `deploy/examples/monitoring/grafana` |
| General | ~28 Kubernetes and node dashboards | this chart |

To add one: export the JSON from Grafana (Share → Export, "Export for sharing
externally" off), save it in `dashboards/`, list it in
`dashboards/kustomization.yaml`, open a PR.

## Grafana login

User `admin`. The password was generated at install and lives in Secret
`kube-prometheus-stack-grafana`; Argo CD is set to leave it alone.

```
kubectl -n monitoring get secret kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

## Manual install (without Argo CD)

```
helm install kube-prometheus-stack kube-prometheus-stack \
  --repo https://prometheus-community.github.io/helm-charts --version 81.0.0 \
  -n monitoring --create-namespace -f values.yaml
kubectl label namespace monitoring pod-security.kubernetes.io/enforce=privileged
kubectl apply -k dashboards/
```

The namespace label lets node-exporter use the host network and filesystem.
Under Argo CD it's set by `managedNamespaceMetadata` in the Application.
