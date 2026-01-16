#Patch
talosctl patch mc -p @longhorn-patch.yaml -n <node-ip-1>,<node-ip-2>

talosctl patch mc -p @directory.yaml -n <node-ip-1>,<node-ip-2>

#Install
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.7.2/deploy/longhorn.yaml

#Test
kubectl get storageclass
