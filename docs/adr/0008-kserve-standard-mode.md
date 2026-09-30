# ADR-0008: KServe in Standard (raw Deployment) mode

**Status:** Accepted
**Date:** 2026-09-29

## Context

KServe's serverless mode needs Knative and Istio: two large control planes to
run for scale-to-zero, which a few always-on models don't need.

## Decision

KServe v0.20 in Standard mode (formerly "RawDeployment"): each
`InferenceService` becomes a plain Deployment, Service and HPA, called
in-cluster at `<isvc>-predictor.<namespace>.svc`. cert-manager is installed
only to issue KServe's self-signed webhook certificate.

## Consequences

- No Knative, Istio or ingress controller to operate.
- No scale-to-zero or canary traffic splitting; rollouts are normal
  Deployment rollouts.
