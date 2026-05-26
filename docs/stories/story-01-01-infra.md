# Story 01-01: Infrastructure and CI/CD

**Parent Epic:** [Epic 1: MVP](../epics/epic-01-mvp.md)  
**PR:** PR-0-infra

## User Story

As a **developer**, I want a fully configured monorepo with CI/CD pipeline and Kubernetes deployment manifests, so that I can develop, test, and deploy the Dojo Manager application to OCI Kubernetes Engine with minimal manual effort.

## Acceptance Criteria

### AC-1: Monorepo Structure

**Given** the repository is initialized  
**When** I inspect the directory structure  
**Then** I see:
- `backend/` directory with Python 3.13 + FastAPI project skeleton
- `frontend/` directory with React 19 + TypeScript + Vite project skeleton
- `k8s/` directory with Kubernetes manifests
- `.github/workflows/` directory with CI/CD pipelines
- `docker-compose.yml` for local development

### AC-2: Docker Configuration

**Given** I run `docker compose up`  
**When** all services start  
**Then**:
- MySQL 8.4 container is running with persistent volume
- Backend container is running and responds to `/health`
- Frontend container is running and serves the SPA
- All services are on an isolated network

### AC-3: Kubernetes Manifests

**Given** the k8s manifests are applied to an OKE cluster  
**When** I check pod status  
**Then**:
- MySQL pod is running with resource limits (500m CPU, 1Gi memory)
- Backend pod is running with resource limits (500m CPU, 512Mi memory)
- Frontend pod is running with resource limits (250m CPU, 256Mi memory)
- Ingress routes `/api/*` to backend and `/*` to frontend
- cert-manager is configured with Let's Encrypt issuers (staging + production)

### AC-4: CI Pipeline (develop branch)

**Given** a PR is opened against `develop`  
**When** CI runs  
**Then**:
- Backend linting (Ruff) passes
- Backend tests (pytest) pass
- Frontend linting (ESLint) passes
- Frontend tests (Jest) pass
- Docker images build successfully for linux/arm64

### AC-5: CD Pipeline (main branch)

**Given** a PR is merged to `main`  
**When** the deploy workflow runs  
**Then**:
- CI checks pass (reused from develop)
- Docker images are pushed to OCIR
- Kubernetes manifests are applied via `kubectl apply`
- Rollout status is verified

### AC-6: MySQL Backup

**Given** the backup CronJob is configured  
**When** the scheduled time arrives (daily at 2AM)  
**Then**:
- `mysqldump` runs against the MySQL container
- Output is gzip compressed
- Backup is uploaded to OCI Object Storage

## Domain Model References

No domain models in this story — infrastructure only.

## UI Requirements

None — this is infrastructure-only.

## API Requirements

- `GET /health` — Health check endpoint (returns 200 OK)

## Dependencies

| Dependency | Type | Details |
|------------|------|---------|
| OCI Account | External | Always Free tier with compartment, API key, OCIR token |
| OKE Cluster | External | ARM node pool on Always Free VM |
| GitHub Repository | External | With Actions enabled |

## Technical Notes

- ARM Always Free VM: 4 OCPUs, 24GB RAM
- OCIR Always Free: 500MB storage limit (use slim images)
- MySQL uses hostPath PersistentVolume for MVP (free, single-node)
- Namespace: `dojo` for app, `cert-manager` and `ingress-nginx` for system
- No staging environment — only `develop` and `main` branches
