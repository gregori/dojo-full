# OCI Setup Guide for Dojo Manager

This guide walks through setting up Oracle Cloud Infrastructure (OCI) for deploying Dojo Manager on OKE (OCI Kubernetes Service).

## Prerequisites

- OCI Free Tier account (Always Free eligible)
- GitHub account with repository access
- Basic familiarity with Kubernetes and Docker

## Table of Contents

1. [Create Compartment](#1-create-compartment)
2. [Create API Key](#2-create-api-key)
3. [Create OCIR Auth Token](#3-create-ocir-auth-token)
4. [Create Object Storage Bucket](#4-create-object-storage-bucket)
5. [Create OKE Cluster](#5-create-oke-cluster)
6. [Generate kubeconfig](#6-generate-kubeconfig)
7. [Install Nginx Ingress Controller](#7-install-nginx-ingress-controller)
8. [Install cert-manager](#8-install-cert-manager)
9. [Configure GitHub Secrets](#9-configure-github-secrets)

---

## 1. Create Compartment

1. Log in to the [OCI Console](https://cloud.oracle.com/)
2. Navigate to **Identity & Security** → **Compartments**
3. Click **Create Compartment**
4. Fill in:
   - **Name**: `dojo-manager`
   - **Description**: `Compartment for Dojo Manager application`
   - **Parent Compartment**: Root (or your development compartment)
5. Click **Create Compartment**
6. Note the **OCID** of the new compartment (needed later)

## 2. Create API Key

### Generate RSA Key Pair

```bash
# Generate private key (2048-bit minimum, 4096 recommended)
openssl genrsa -out oci_api_key.pem 4096

# Generate public key
openssl rsa -pubout -in oci_api_key.pem -out oci_api_key_public.pem
```

### Upload Public Key to OCI

1. Navigate to **Identity & Security** → **Users**
2. Click on your user
3. Scroll to **API Keys** section
4. Click **Add Public Key**
5. Choose **Public Key File** and upload `oci_api_key_public.pem`
6. Note the **Fingerprint** displayed after upload

### Store Private Key Securely

```bash
# Keep the private key secure
chmod 600 oci_api_key.pem
```

You'll need:
- **User OCID** (from your user page)
- **Tenancy OCID** (from Tenancy details)
- **Fingerprint** (from the API key upload)
- **Private key file** (`oci_api_key.pem`)

## 3. Create OCIR Auth Token

1. Navigate to **Identity & Security** → **Users**
2. Click on your user
3. Scroll to **Auth Tokens** section
4. Click **Generate Token**
5. Give it a description: `OCIR GitHub Actions`
6. **Copy the token immediately** — it won't be shown again
7. This token will be used as `OCI_AUTH_TOKEN` in GitHub Secrets

### Find Your OCIR Namespace

1. Navigate to **Developer Services** → **Container Registry**
2. Your namespace is displayed at the top (e.g., `abc123xyz`)
3. This will be used as `OCIR_NAMESPACE` in GitHub Secrets

## 4. Create Object Storage Bucket

1. Navigate to **Storage** → **Buckets**
2. Select your compartment (`dojo-manager`)
3. Click **Create Bucket**
4. Fill in:
   - **Bucket Name**: `dojo-backups`
   - **Storage Tier**: Standard
   - **Encryption**: Use Oracle-managed keys (default)
5. Click **Create**
6. Note the bucket name for the backup CronJob configuration

## 5. Create OKE Cluster

### Using OCI Console

1. Navigate to **Developer Services** → **Kubernetes Clusters (OKE)**
2. Select your compartment (`dojo-manager`)
3. Click **Create Cluster**
4. Choose **Quick Create** (simpler) or **Custom Create** (more control)

### Quick Create Configuration

- **Cluster Name**: `dojo-manager`
- **Kubernetes Version**: Latest available (1.29+)
- **Compartment**: `dojo-manager`

### Node Pool Configuration (ARM Always Free)

After cluster creation, configure the node pool:

1. Navigate to your cluster → **Node Pools**
2. Edit or create a node pool with:
   - **Shape**: `VM.Standard.A1.Flex` (ARM)
   - **OCPU Count**: 4 (or all available for Always Free)
   - **Memory**: 24 GB
   - **Image**: Oracle Linux 8+ (ARM compatible)
   - **Node Count**: 1 (single node for MVP)

### Network Configuration

Quick Create will automatically create:
- VCN with public and private subnets
- Internet Gateway
- NAT Gateway
- Service Gateway

Ensure port 80 and 443 are open in the security lists for the public subnet (for ingress traffic).

## 6. Generate kubeconfig

### Install OCI CLI

```bash
# macOS/Linux
curl -sSf https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh | sh

# Or use pip
pip install oci-cli
```

### Configure OCI CLI

```bash
oci setup config
```

You'll need:
- User OCID
- Tenancy OCID
- Region (e.g., `us-ashburn-1`, `sa-saopaulo-1`)
- API key path

### Generate kubeconfig

```bash
# Replace with your cluster OCID and region
oci ce cluster create-kubeconfig \
  --cluster-id <cluster-ocid> \
  --file $HOME/.kube/config \
  --region <region> \
  --token-version 2.0.0
```

### Verify Connection

```bash
kubectl get nodes
# Should show your ARM node in Ready state
```

### Encode kubeconfig for GitHub Secrets

```bash
# Base64 encode the kubeconfig file
base64 -i ~/.kube/config | tr -d '\n'
# Copy the output for GitHub Secrets (KUBECONFIG)
```

## 7. Install Nginx Ingress Controller

### Add Helm Repository

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

### Install Nginx Ingress Controller

```bash
kubectl create namespace ingress-nginx

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.replicaCount=1 \
  --set controller.resources.requests.cpu=100m \
  --set controller.resources.requests.memory=128Mi \
  --set controller.resources.limits.cpu=250m \
  --set controller.resources.limits.memory=256Mi
```

### Verify Installation

```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

Note the **EXTERNAL-IP** of the `ingress-nginx-controller` service. This is the IP address you'll use for DNS.

## 8. Install cert-manager

### Add Helm Repository

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

### Install cert-manager

```bash
kubectl create namespace cert-manager

# Install with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --set installCRDs=true \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi \
  --set resources.limits.cpu=100m \
  --set resources.limits.memory=128Mi
```

### Verify Installation

```bash
kubectl get pods -n cert-manager
```

## 9. Configure GitHub Secrets

Navigate to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `OCI_TENANCY` | Tenancy OCID | From Tenancy details page |
| `OCI_USER` | User OCID | From your user page |
| `OCI_FINGERPRINT` | API Key Fingerprint | From API key upload |
| `OCI_PRIVATE_KEY` | Base64-encoded private key | `base64 -i oci_api_key.pem \| tr -d '\n'` |
| `OCI_REGION` | Region identifier | e.g., `us-ashburn-1` |
| `OCI_AUTH_TOKEN` | Auth Token | From OCIR auth token creation |
| `OCIR_NAMESPACE` | OCIR namespace | From Container Registry page |
| `KUBECONFIG` | Base64-encoded kubeconfig | `base64 -i ~/.kube/config \| tr -d '\n'` |
| `OCI_OSS_BUCKET` | Bucket name | `dojo-backups` |
| `OCI_OSS_NAMESPACE` | Object storage namespace | From Object Storage page |

## Post-Setup Checklist

- [ ] Compartment created
- [ ] API key generated and uploaded
- [ ] OCIR auth token created
- [ ] Object Storage bucket created
- [ ] OKE cluster created with ARM node pool
- [ ] kubeconfig generated and tested
- [ ] Nginx Ingress Controller installed
- [ ] cert-manager installed
- [ ] All GitHub secrets configured
- [ ] DNS pointed to ingress controller IP (optional, for custom domain)

## Troubleshooting

### Node Not Ready

```bash
kubectl describe node <node-name>
kubectl get events -n kube-system
```

### Ingress Not Working

```bash
kubectl get ingress -n dojo
kubectl describe ingress dojo-ingress -n dojo
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### cert-manager Issues

```bash
kubectl get certificates -n dojo
kubectl get certificaterequests -n dojo
kubectl get challenges -n dojo
kubectl get orders -n dojo
kubectl logs -n cert-manager -l app=cert-manager
```

### OCIR Pull Errors

Ensure the `imagePullSecrets` are configured or use the OCIR namespace format correctly:
```
<region>.ocir.io/<namespace>/<image>:<tag>
```
