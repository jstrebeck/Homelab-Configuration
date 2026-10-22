# ADR-0011: Trivy Operator for in-cluster security scanning

**Status:** Accepted
**Date:** 2026-10-21

## Context

The cluster runs dozens of third-party images (MLflow, SeaweedFS, KServe
runtimes, the registry, monitoring) and several self-hosted projects have had
serious CVEs disclosed in the past year. Renovate keeps versions current, but
it only reports that a newer version exists, not that the running one is
vulnerable, and it can't see images built in other repos.

Options considered:

- **Trivy Operator:** in-cluster, scans what is actually running, results as
  CRDs plus Prometheus metrics. One Helm chart.
- **Kubescape:** strong on posture and frameworks, weaker on image CVEs;
  overlaps the config-audit half of Trivy.
- **Harbor with Trivy:** scans on push, but only images in that registry, and
  it would replace the current registry.
- **Greenbone/OpenVAS or Nuclei:** network-level scanners. They find exposed
  services and known web exploits, not vulnerable packages inside images.
  Complementary, not a substitute.

## Decision

Run Trivy Operator (chart `0.37.0`) in `trivy-system`, delivered by Argo CD,
with the built-in Trivy server, metrics into the existing Prometheus, and a
Grafana dashboard kept in Git. The node-collector and CIS spec are disabled
because their checks assume a kubeadm-style host, not Talos.

## Consequences

- Every running image is scanned on change and rescanned daily against a
  fresh vulnerability DB; CVE counts are on a dashboard next to cluster health.
- Findings are visible but not enforced: nothing blocks a vulnerable image
  from running. Admission policy (Kyverno) or scan-on-push (Harbor) would add
  that.
- No alerting yet. A `PrometheusRule` on fixable critical CVEs makes sense
  once the baseline backlog is worked down and Alertmanager has a receiver.
- Node and network exposure stay out of scope; a network scanner for the LAN
  is a separate decision.
