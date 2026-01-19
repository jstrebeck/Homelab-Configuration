# Add the Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create a namespace
kubectl create namespace monitoring

# Install the stack
## May need to run twice for the CRDs to deploy first
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -f values.yaml \
  -n monitoring \
  --create-namespace




# Get temp password
kubectl get secret --namespace monitoring kube-pro-grafana -o jsonpath="{.data.grafana-admin-password}" | base64 --decode
