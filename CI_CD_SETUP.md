# CI/CD Setup Guide - Dojo Admin

This guide explains how to configure continuous deployment for Dojo Admin on Oracle Cloud Infrastructure (OCI).

## Overview

The CI/CD pipeline consists of:

1. **GitHub Actions Workflows**:
   - `ci-backend.yml` - Lint, test, and build backend
   - `ci-frontend.yml` - Lint, test, and build frontend
   - `cd-backend.yml` - Build Docker image and deploy to OKE
   - `cd-frontend.yml` - Build Docker image and deploy to OKE
   - `cd-migrations.yml` - Run database migrations manually

2. **Container Registry**: OCI Container Registry (OCIR)
3. **Deployment Target**: Oracle Kubernetes Engine (OKE)

## Prerequisites

Before configuring CI/CD, you must have:

1. ✅ OCI Account with Always Free tier
2. ✅ Terraform infrastructure created (Fase 4)
3. ✅ OKE Cluster running
4. ✅ OCIR repositories created
5. ✅ GitHub repository for `dojo-app`

## Step 1: Get Your OCI Credentials

### Required Information

| Secret Name | How to Get | Example |
|-------------|-----------|---------|
| `OCI_TENANCY_OCID` | OCI Console → Profile → Tenancy | `ocid1.tenancy.oc1..xxxxx` |
| `OCI_USER_OCID` | OCI Console → Profile → User Settings | `ocid1.user.oc1..xxxxx` |
| `OCI_FINGERPRINT` | OCI Console → API Keys | `aa:bb:cc:dd:ee:ff` |
| `OCI_PRIVATE_KEY` | Content of `~/.oci/oci_api_key.pem` | Full PEM content |
| `OCI_REGION` | Your OCI region | `sa-saopaulo-1` |
| `OCI_COMPARTMENT_ID` | OCI Console → Compartments | `ocid1.compartment.oc1..xxxxx` |
| `OCI_AVAILABILITY_DOMAIN` | OCI Console → Compute → Create Instance (see AD) | `Uocm:SA-SAOPAULO-1-AD-1` |
| `OCI_CLUSTER_ID` | `terraform output cluster_id` | `ocid1.cluster.oc1..xxxxx` |
| `OCI_BUCKET_NAMESPACE` | OCI Console → Object Storage | `idhjkcblf5qw` |
| `OCI_REGISTRY` | Based on region | `sa-saopaulo-1.ocir.io` |
| `OCI_TENANCY_NAMESPACE` | Object Storage Namespace | `idhjkcblf5qw` |
| `OCI_REGISTRY_USERNAME` | `<namespace>/<email>` | `idhjkcblf5qw/user@email.com` |
| `OCI_REGISTRY_PASSWORD` | OCI Console → User Settings → Auth Tokens | Generated token |
| `MYSQL_PASSWORD` | Password set in K8s secret | `your-mysql-password` |
| `VITE_API_URL` | API URL for frontend build | `https://api.dojo.app` |

### How to Get Each Credential

#### 1. OCI Tenancy OCID
1. Log in to OCI Console
2. Click on Profile (top right)
3. Click "Tenancy: your-tenancy-name"
4. Copy the **OCID**

#### 2. OCI User OCID
1. OCI Console → Profile → User Settings
2. Copy the **OCID**

#### 3. OCI Fingerprint
1. OCI Console → Profile → User Settings → API Keys
2. If no key exists:
   - Click "Add API Key"
   - Select "Generate API Key Pair"
   - Download the private key
   - Save as `~/.oci/oci_api_key.pem`
3. Copy the **Fingerprint** shown after adding the key

#### 4. OCI Private Key
1. Open `~/.oci/oci_api_key.pem` in a text editor
2. Copy the entire content (including `BEGIN` and `END` lines)

#### 5. OCI Cluster ID
```bash
cd dojo-infra/terraform/environments/prod
terraform output cluster_id
```

#### 6. OCI Auth Token (for Registry)
1. OCI Console → Profile → User Settings → Auth Tokens
2. Click "Generate Token"
3. Give it a name (e.g., "github-actions")
4. **Copy the token immediately** (you can't see it again)

#### 7. MySQL Password
This is the password you set in:
```bash
cat dojo-infra/k8s/database/secret.example.yaml
```

## Step 2: Configure GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Add each secret from the table above

### Required Secrets

You must add ALL of these secrets:

```
OCI_TENANCY_OCID
OCI_USER_OCID
OCI_FINGERPRINT
OCI_PRIVATE_KEY
OCI_REGION
OCI_COMPARTMENT_ID
OCI_AVAILABILITY_DOMAIN
OCI_CLUSTER_ID
OCI_BUCKET_NAMESPACE
OCI_REGISTRY
OCI_TENANCY_NAMESPACE
OCI_REGISTRY_USERNAME
OCI_REGISTRY_PASSWORD
MYSQL_PASSWORD
VITE_API_URL
```

## Step 3: First Deploy

### Manual First Setup

Before CI/CD can work, you need to do the first deploy manually:

```bash
# 1. Build images locally
cd dojo-app/backend
docker build -f Dockerfile.prod -t sa-saopaulo-1.ocir.io/<namespace>/dojo-backend:latest .

cd ../frontend
docker build -f Dockerfile.prod -t sa-saopaulo-1.ocir.io/<namespace>/dojo-frontend:latest .

# 2. Push to OCIR
docker login sa-saopaulo-1.ocir.io -u '<namespace>/<email>' -p '<auth-token>'
docker push sa-saopaulo-1.ocir.io/<namespace>/dojo-backend:latest
docker push sa-saopaulo-1.ocir.io/<namespace>/dojo-frontend:latest

# 3. Apply K8s manifests
kubectl apply -k dojo-infra/k8s/

# 4. Update image references
kubectl set image deployment/dojo-backend backend=sa-saopaulo-1.ocir.io/<namespace>/dojo-backend:latest -n dojo
kubectl set image deployment/dojo-frontend frontend=sa-saopaulo-1.ocir.io/<namespace>/dojo-frontend:latest -n dojo
```

### Verify Deployment

```bash
kubectl get pods -n dojo
kubectl get svc -n dojo
kubectl get ingress -n dojo
```

## Step 4: Test CI/CD

### Trigger Backend Deploy

1. Make a small change to any file in `dojo-app/backend/`
2. Commit and push to `main` branch
3. Go to GitHub → Actions → "CD - Deploy Backend"
4. Watch the workflow run

### Trigger Frontend Deploy

1. Make a small change to any file in `dojo-app/frontend/`
2. Commit and push to `main` branch
3. Go to GitHub → Actions → "CD - Deploy Frontend"

### Run Database Migration

1. Go to GitHub → Actions → "CD - Database Migrations"
2. Click "Run workflow"
3. Select command (default: `upgrade head`)
4. Click "Run workflow"

## How CI/CD Works

### Backend Pipeline

```
Push to backend/** or workflow file
    ↓
GitHub Actions triggered
    ↓
Build Docker image (Dockerfile.prod)
    ↓
Push to OCIR with tag: <sha> and :latest
    ↓
Update K8s deployment image
    ↓
Wait for rollout to complete
    ↓
Verify pods are running
```

### Frontend Pipeline

```
Push to frontend/** or workflow file
    ↓
GitHub Actions triggered
    ↓
Build Docker image (Dockerfile.prod) with VITE_API_URL
    ↓
Push to OCIR with tag: <sha> and :latest
    ↓
Update K8s deployment image
    ↓
Wait for rollout to complete
    ↓
Verify pods are running
```

## Rollback

If a deployment goes wrong, you can rollback:

### Option 1: GitHub Actions (Recommended)

1. Go to GitHub → Actions → Find last successful deployment
2. Click "Re-run all jobs"

### Option 2: Kubectl

```bash
# Rollback backend
kubectl rollout undo deployment/dojo-backend -n dojo

# Rollback frontend
kubectl rollout undo deployment/dojo-frontend -n dojo

# Check history
kubectl rollout history deployment/dojo-backend -n dojo
```

## Troubleshooting

### Image Pull Errors

```bash
# Check events
kubectl get events -n dojo --sort-by='.lastTimestamp'

# Check pod details
kubectl describe pod <pod-name> -n dojo

# Verify image exists in OCIR
oci artifacts container image list --repository-name dojo-backend
```

### Authentication Issues

```bash
# Test OCI CLI
oci iam user get --user-id <your-user-ocid>

# Test registry login
docker login <registry> -u '<namespace>/<email>' -p '<token>'
```

### Deployment Stuck

```bash
# Check rollout status
kubectl rollout status deployment/dojo-backend -n dojo

# Check logs
kubectl logs -f deployment/dojo-backend -n dojo

# Restart deployment
kubectl rollout restart deployment/dojo-backend -n dojo
```

## Security Best Practices

1. **Rotate Auth Tokens regularly** (every 90 days)
2. **Use short-lived tokens** when possible
3. **Never commit secrets** to the repository
4. **Review Actions logs** for any unauthorized access
5. **Enable branch protection** on `main` branch
6. **Require pull request reviews** before merging

## Next Steps

After CI/CD is configured:

1. Set up domain and SSL certificate
2. Configure monitoring (Prometheus/Grafana)
3. Set up log aggregation
4. Configure automated backups
5. Set up alerts for deployment failures

## Questions?

If you encounter issues:
1. Check GitHub Actions logs for detailed error messages
2. Verify all secrets are correctly configured
3. Test OCI CLI authentication locally
4. Check Kubernetes events and pod logs
