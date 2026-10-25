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

Rook runs the CSI drivers through the Ceph CSI operator
(`ceph-csi-controller-manager`, `ROOK_USE_CSI_OPERATOR: true`): Rook writes
`Driver` CRs and the image set in `rook-csi-operator-image-set-configmap`, the
operator turns them into the `*-ctrlplugin` Deployments and `*-nodeplugin`
DaemonSets. If the operator isn't running, the CSI pods silently stay on
their old images through Rook upgrades. Both drivers use kernel clients
(krbd, kernel CephFS), so restarting node plugins leaves mounted volumes
alone.

From Rook v1.20 the CSI drivers come from a separate `ceph-csi-drivers` chart,
installed between the `rook-ceph` and `rook-ceph-cluster` charts.

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
