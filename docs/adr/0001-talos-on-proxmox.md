# ADR-0001: Talos Linux VMs on Proxmox for the cluster nodes

**Status:** Accepted
**Date:** 2026-09-29 (recorded; the migration predates this log)

## Context

The first cluster was kubeadm on Ubuntu VMs, built with Terraform
(`Terraform/Kube/`) and Ansible (`Ansible/`). Every node was a general-purpose
OS to patch, harden and keep consistent.

## Decision

Run Kubernetes on Talos Linux: four Proxmox VMs (one control plane, three
workers, 8 vCPU / 32 GiB each), configured only through the Talos API with
machine-config patches kept in this repo (e.g. `Kubernetes/registry/talos-patch.yaml`).

## Consequences

- No SSH, no package manager, read-only root: the node OS is not something to
  administer, and upgrades are an image swap per node.
- Anything that needs host access (Ceph OSDs, node-exporter) must be granted
  explicitly through Pod Security labels.
- Proxmox still provides snapshots and console access when a node won't boot.
- The Terraform and Ansible code is kept as history, not maintained.
