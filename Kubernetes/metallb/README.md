#Install MetalLB

##Create namespace
kubectl create namespace metallb-system

##Apply MetalLB manifests
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.5/config/manifests/metallb-native.yaml


##Verify:
kubectl get pods -n metallb-system

##Deploy
kubectl apply -f metallb.yaml

