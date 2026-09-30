# ADR-0003: MetalLB for LAN services, Cloudflare Tunnel for the internet

**Status:** Accepted
**Date:** 2026-09-29 (recorded)

## Context

Clusters outside a cloud have no load balancer integration, so `LoadBalancer` Services
stay pending. Some services must be reachable from the LAN (UIs, the
registry, MLflow), and a few from the internet, without opening ports on the
home router or exposing the home IP.

## Decision

MetalLB in L2 mode assigns addresses from `192.168.2.201-250` to
`LoadBalancer` Services. Internet traffic enters only through a Cloudflare
Tunnel whose `cloudflared` connectors run in the cluster (2 replicas) and dial
out to Cloudflare.

## Consequences

- Every LAN-facing service gets its own IP with no ingress controller to run.
  An address can be pinned with the `metallb.universe.tf/loadBalancerIPs`
  annotation (Argo CD uses `.217`).
- No inbound firewall rules; TLS for public hostnames terminates at Cloudflare.
- L2 mode sends all traffic for an IP through one node. Failover takes seconds
  and there is no load spreading, which is acceptable at homelab scale.
- There is no in-cluster TLS or hostname routing. An ingress or Gateway API
  controller is the next step if that becomes necessary.
