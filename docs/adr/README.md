# Architecture Decision Records

One file per decision, numbered, never deleted. To reverse a decision, write a
new ADR that supersedes the old one and link both ways. Copy
`0000-template.md` to start.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-talos-on-proxmox.md) | Talos Linux VMs on Proxmox for the cluster nodes | Accepted |
| [0002](0002-rook-ceph-storage.md) | Rook-Ceph for persistent storage (replacing Longhorn) | Accepted |
| [0003](0003-metallb-and-cloudflare-tunnel.md) | MetalLB for LAN services, Cloudflare Tunnel for the internet | Accepted |
| [0004](0004-argocd-app-of-apps.md) | Argo CD app of apps, adopting the running cluster in place | Accepted |
| [0005](0005-sync-policy.md) | Automated sync, manual prune, selective self-heal | Accepted |
| [0006](0006-secrets-out-of-git.md) | Secrets are created out of band, never committed | Accepted |
| [0007](0007-seaweedfs-object-store.md) | SeaweedFS as the S3 store for ML artifacts | Accepted |
| [0008](0008-kserve-standard-mode.md) | KServe in Standard (raw Deployment) mode | Accepted |
| [0009](0009-one-postgres-per-consumer.md) | One PostgreSQL instance per consumer, no operator | Accepted |
| [0010](0010-platform-and-workload-repos.md) | Platform lives here, workloads live in their own repos | Accepted |
