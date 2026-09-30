# Terraform (Proxmox VMs)

VM definitions for the Proxmox VE host, using the
[`telmate/proxmox`](https://registry.terraform.io/providers/Telmate/proxmox/latest)
provider. Each directory is an independent root module that clones the
`ubuntu-2204-cloudinit-template` VM template.

| Module | VMs | Purpose |
|---|---|---|
| `Kube/` | `kube01`–`kube03` | First-generation kubeadm cluster (see `../Ansible/`) |
| `EKS/` | `EKS1`–`EKS2` | EKS Anywhere experiments |
| `ECS/` | `ECS` | Amazon ECS Anywhere host |
| `Github-Actions/` | `ghactions` | Self-hosted GitHub Actions runner |
| `OVPN/` | `ovpn` | OpenVPN server |

> These modules target the original `192.168.1.0/24` network and predate the
> current Talos cluster, which is installed from the Talos ISO rather than
> cloned from this template.

## Cloud-init template

One-time setup on the Proxmox host (also in `../cloud-init/ubuntu-2204.sh`):

```
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

apt update -y && apt install libguestfs-tools -y
virt-customize -a jammy-server-cloudimg-amd64.img --install qemu-guest-agent

qm create 9000 --name "ubuntu-2204-cloudinit-template" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 jammy-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

## Credentials

Each module reads a git-ignored `credentials.auto.tfvars`:

```
proxmox_api_url          = "https://<proxmox-host>:8006/api2/json"
proxmox_api_token_id     = "terraform@pam!terraform"   # <user>@pam!<token id>
proxmox_api_token_secret = "<token secret>"
```

## Usage

```
cd Kube
terraform init
terraform plan
terraform apply
```
