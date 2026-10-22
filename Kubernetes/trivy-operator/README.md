# Trivy Operator

[Trivy Operator](https://aquasecurity.github.io/trivy-operator/) watches every
workload in the cluster and keeps security reports for it as Kubernetes
resources:

| Report | What it finds |
|---|---|
| `VulnerabilityReport` | CVEs in the OS packages and libraries of each running image |
| `ExposedSecretReport` | Keys, tokens and passwords baked into image layers |
| `ConfigAuditReport` | Risky workload and resource settings (root, no limits, host access, ...) |
| `RbacAssessmentReport` / `ClusterRbacAssessmentReport` | Roles granting dangerous permissions |
| `ClusterComplianceReport` | NSA hardening guide and Pod Security Standards (baseline, restricted) summaries |

A workload is scanned when it appears or its image changes. Reports expire
after 24 hours (`scannerReportTTL`) so every image is rescanned daily against
the latest vulnerability DB, picking up newly disclosed CVEs in images that
haven't changed.

- **Namespace:** `trivy-system` (Pod Security `baseline`)
- **Chart:** `trivy-operator` `0.37.0` from `https://aquasecurity.github.io/helm-charts`
- **Values:** `values.yaml`
- **Delivered by:** Argo CD, `../argocd/apps/trivy-operator.yaml`
- **Metrics:** `ServiceMonitor` scraped by Prometheus; dashboard
  **Security → Trivy Operator** in Grafana (`../grafana/dashboards/trivy-operator.py`)

## How it's configured

- **Built-in Trivy server.** One `trivy-server` StatefulSet keeps the
  vulnerability DB on a 5Gi `ceph-block` volume and refreshes it. Scan jobs
  run as clients against it, so each job doesn't download the ~1 GB DB.
- **In-cluster registry.** Scan jobs pull images themselves, and
  `192.168.2.203:5000` is plain HTTP, so it is listed under
  `nonSslRegistries` and `insecureRegistries`.
- **No node scanning.** The node-collector (`infraAssessmentScannerEnabled`)
  reads kubelet and etcd config from host paths that don't exist on Talos, and
  it needs `hostPath`, which the namespace's `baseline` level blocks. Node
  hardening is covered by Talos itself ([ADR-0001](../../docs/adr/0001-talos-on-proxmox.md)).
  For the same reason the CIS compliance spec is left out.
- **Three concurrent scan jobs**, so the first pass over all images doesn't
  compete with workloads.

See [ADR-0011](../../docs/adr/0011-trivy-operator-scanning.md) for why this
scanner.

## Verify

```
kubectl -n trivy-system get pods
kubectl -n trivy-system get jobs            # scan jobs come and go
kubectl get vulnerabilityreports -A         # fills in over ~30 minutes
kubectl get configauditreports -A
kubectl get clustercompliancereports
```

Detail for one workload, worst first:

```
kubectl -n mlops get vulnerabilityreports -o wide
kubectl -n mlops get vulnerabilityreport <name> -o yaml \
  | yq '.report.vulnerabilities | sort_by(.score) | reverse | .[:10]'
```

## Acting on findings

- **Fixable CVEs** (the dashboard's "fixed in" column is set): upgrade the
  chart or image. Renovate usually has the PR open already. Images built in
  other repos need a rebuild on a patched base image.
- **No fix upstream:** nothing to do but track it. To silence a CVE you've
  accepted, add it to a `trivy.ignoreFile` in `values.yaml` with a comment
  saying why.
- **Misconfigurations** in charts we install: fix through the chart's values
  where it allows, otherwise accept them. Several platform components (Ceph,
  node-exporter, MetalLB speaker) need host access by design.

## Teardown

```
# Remove ../argocd/apps/trivy-operator.yaml, merge, then:
argocd app delete trivy-operator --cascade
# CRDs and reports are kept by Helm. Remove them if not reinstalling:
kubectl get crd -o name | grep aquasecurity.github.io | xargs kubectl delete
kubectl -n trivy-system delete pvc data-trivy-server-0   # vulnerability DB cache
```
