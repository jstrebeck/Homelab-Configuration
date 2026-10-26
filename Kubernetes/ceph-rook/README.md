#Read this first
https://docs.siderolabs.com/kubernetes-guides/csi/ceph-with-rook

#Patch to allow scheduling on the controlplane to help with scheduling issues
(Now set in `values-operator.yaml` `tolerations`; kept for reference.)

kubectl patch deploy rook-ceph-operator -n rook-ceph --type=json -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/tolerations",
    "value": [
      {
        "key": "node-role.kubernetes.io/control-plane",
        "operator": "Exists",
        "effect": "NoSchedule"
      }
    ]
  }
]'

kubectl rollout restart deploy rook-ceph-operator -n rook-ceph

## Versions

Rook and Ceph are pinned separately (`../argocd/apps/rook-ceph.yaml` for the
charts, `cephImage` in `values-cluster.yaml` for Ceph) so an upgrade changes
one of them at a time. Rook upgrades go one minor version at a time; read
that version's upgrade guide first.

## CSI

The CSI drivers run under the Ceph CSI operator (`ceph-csi-controller-manager`,
installed by the `rook-ceph` chart). Since Rook v1.20 the `Driver` and
`OperatorConfig` CRs, and the drivers' ServiceAccounts and RBAC, come from the
separate `ceph-csi-drivers` chart (`values-csi-drivers.yaml`, Argo app
`ceph-csi-drivers`). The CSI images still come from the `rook-ceph` chart, in
`rook-csi-operator-image-set-configmap`. Rook itself only writes the
`CephConnection` and `ClientProfile` CRs. The operator turns all of these into
the `*-ctrlplugin` Deployments and `*-nodeplugin` DaemonSets. If the operator
isn't running, the CSI pods silently stay on their old images. Both drivers use
kernel clients (krbd, kernel CephFS), so restarting node plugins leaves mounted
volumes alone.

Upgrade the charts in this order: `rook-ceph`, `ceph-csi-drivers`,
`rook-ceph-cluster`. Keep `ceph-csi-drivers` at the `ceph-csi-operator`
version listed in that Rook release's `rook-ceph` Chart.yaml, and compare
`values-csi-drivers.yaml` with the release's recommended values
(`deploy/charts/ceph-csi-drivers/values.yaml`). The driver names must stay
`rook-ceph.{rbd,cephfs}.csi.ceph.com`, because they are the provisioners in
the StorageClasses and existing PVs.

## CephX keys (CVE-2025-30156)

Ceph v19.2.6 adds the AES256K key type; the CVE is closed once the core
daemon keys (mon, mgr, OSD, MDS, RGW) are rotated to it, which
`security.cephx.daemon` in `values-cluster.yaml` does. Check with:

```
kubectl -n rook-ceph get cephcluster rook-ceph -o jsonpath='{.status.cephx}'
kubectl -n rook-ceph get cephfilesystem,cephobjectstore -o jsonpath='{range .items[*]}{.metadata.name} {.status.cephx}{"\n"}{end}'
```

CSI keys stay on `aes`: AES256K kernel mounts need Linux 7.0+ and Talos 1.11
runs 6.12. That is safe once the daemons have rotated (clients get AES256K
service tickets either way). The resulting `AUTH_INSECURE_*` health warnings
are muted in `healthCheck.muteHealthWarning`. Once the nodes run kernel 7.0+,
follow Rook's "Migrating CSI keys to a new key type" guide (rotate with
`keyType: aes256k` and `keepPriorKeyCountMax: 1`, drain each node), then
unmute the warnings. Leave `allowedCiphers` alone until every key reports
`aes256k`: restricting it early locks the daemons out.
