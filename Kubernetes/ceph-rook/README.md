#Read this first
https://docs.siderolabs.com/kubernetes-guides/csi/ceph-with-rook

#Patch to allow scheduling on the controlplane to help with scheduling issues
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
