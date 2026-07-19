# Dojo Infra - Terraform & Kubernetes Infrastructure

Infrastructure as Code for Dojo Admin application on OCI (Oracle Cloud Infrastructure).

## Structure

```
dojo-infra/
├── terraform/          # Terraform modules and configurations
│   ├── modules/       # Reusable modules
│   │   ├── networking/ # VCN, subnets, security lists
│   │   ├── oke/        # Kubernetes cluster
│   │   ├── registry/   # Container registry (OCIR)
│   │   └── storage/    # Object storage buckets
│   └── environments/
│       └── prod/        # Production environment
├── k8s/               # Kubernetes manifests
│   ├── namespaces/    # Namespace definitions
│   ├── backend/        # Backend deployment & service
│   ├── frontend/       # Frontend deployment & service
│   ├── database/       # MySQL deployment & PVC
│   └── kustomization.yaml
├── scripts/           # Deployment and backup scripts
└── .github/workflows/  # CI/CD for infrastructure
    ├── terraform-apply.yml
    └── deploy-k8s.yml
```

## Setup

### Automated Setup

```bash
cd dojo-infra
./scripts/setup-infrastructure.sh
```

### Manual Setup

1. Configure OCI CLI and Terraform backend
2. Initialize Terraform: `cd terraform/environments/prod && terraform init`
3. Plan changes: `terraform plan`
4. Apply: `terraform apply`
5. Configure kubectl: `oci ce cluster create-kubeconfig --cluster-id <id> --file ~/.kube/config`
6. Deploy application: `./scripts/deploy.sh prod "<region>.ocir.io/<tenancy>"`

## Prerequisites

- OCI account with Always Free tier
- Terraform >= 1.7.0
- kubectl configured for OKS

## Operations

### Backup MySQL
```bash
./scripts/backup.sh dojo-terraform-state <namespace>
```

### View Logs
```bash
kubectl logs -f deployment/dojo-backend -n dojo
kubectl logs -f deployment/dojo-frontend -n dojo
```

## Notes

- State is stored in OCI Object Storage (S3-compatible)
- All resources use Always Free tier where possible
- Backups of MySQL are done via Object Storage
- ARM VM shape (VM.Standard.A1.Flex) used for cost efficiency
