# HomeLab-Configuration
Configuration files deployed to my HomeLab

# Terraform
## Create cloud-init teplate 
```
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

apt update -y && sudo apt install libguestfs-tools -y
virt-customize -a jammy-server-cloudimg-amd64.img --install qemu-guest-agent
virt-customize -a jammy-server-cloudimg-amd64.img  --run-command 'echo PasswordAuthentication yes >> /etc/ssh/sshd_config'

qm create 9000 --name "ubuntu-2204-cloudinit-template" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 jammy-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1

#Make any cloud-init changes like add a user or SSH key in the cloud-init tab of the VM

qm template 9000
```

## credentials.auto.tfvars template
```
proxmox_api_url = "https://0.0.0.0:8006/api2/json"

# api token id is in the form of: <username>@pam!<tokenId>
proxmox_api_token_id = "terraform@pam!terraform"

# this is the full secret wrapped in quotes.`
proxmox_api_token_secret = "XXX"

```

# Kubernetes
Kubernetes configuration files deployed to my cluster.

# Ansible
The kubernetes folder contains scripts to start a Kubernetes cluster on your own devices.

You will need to creaate a hosts file with these labels.
```
# this is a basic file putting different hosts into categories
# used by ansible to determine which actions to run on which hosts
[all]


[kube_server]


[kube_agents]


[kube_storage]

```

## Fast-API-Docker-Image
This is a hello world docker image used for testing Kubernetes endpoints. 
