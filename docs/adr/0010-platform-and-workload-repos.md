# ADR-0010: Platform lives here, workloads live in their own repos

**Status:** Accepted
**Date:** 2026-09-29

## Context

Applications running on the cluster have their own repositories and release
cadence. Their manifests could be copied here, or stay with the code they
deploy.

## Decision

This repo holds the platform and, for each application, only its Argo CD
`AppProject` and `Application`. The application repo owns
`deploy/overlays/homelab`; its CI bumps image tags there and Argo CD rolls
them out. AppProjects restrict each application to its own repo and
namespace. Only public projects are referenced from this repo; private
workloads are managed from a private repo.

## Consequences

- Manifests version with the code that uses them; this repo doesn't churn on
  every application release.
- The contract between the two repos is the namespace, the Secret names and
  the overlay path, documented in the application repo.
