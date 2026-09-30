# Ansible (kubeadm cluster)

Playbooks that built the first-generation cluster: kubeadm on the Ubuntu VMs
from `../Terraform/Kube/`. The cluster now runs on Talos Linux, which is
configured through its API rather than SSH, so these are kept for reference.

| Playbook | Does |
|---|---|
| `ansible-install-kubernetes-dependencies.yml` | Docker + containerd, kubeadm, kubelet, kubectl |
| `ansible-init-cluster.yml` | `kubeadm init` on the control plane, Calico CNI, kubeconfig |
| `ansible-get-join-command.yaml` | Generates the worker join command |
| `ansible-join-workers.yml` | Joins the workers |
| `ansible-vars.yml` | Shared variables |

## Inventory

Create a git-ignored `ansible-hosts.txt`:

```
[all]

[kube_server]

[kube_agents]

[kube_storage]
```

## Run

```
ansible-playbook -i ansible-hosts.txt Kubernetes/ansible-install-kubernetes-dependencies.yml
ansible-playbook -i ansible-hosts.txt Kubernetes/ansible-init-cluster.yml
ansible-playbook -i ansible-hosts.txt Kubernetes/ansible-get-join-command.yaml
ansible-playbook -i ansible-hosts.txt Kubernetes/ansible-join-workers.yml
```
