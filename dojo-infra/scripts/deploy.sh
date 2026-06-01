#!/bin/bash
set -e

ENV=${1:-prod}
REGISTRY=${2:-"<region>.ocir.io/<tenancy>"}

echo "=== Dojo Admin - Deploy to Kubernetes ==="
echo "Environment: $ENV"
echo "Registry: $REGISTRY"
echo ""

# Update image tags in manifests
sed -i.bak "s|<region>.ocir.io/<tenancy>|${REGISTRY}|g" k8s/backend/deployment.yaml
sed -i.bak "s|<region>.ocir.io/<tenancy>|${REGISTRY}|g" k8s/frontend/deployment.yaml

# Apply manifests
echo "=== Applying Kubernetes Manifests ==="
kubectl apply -k k8s/

# Wait for deployments
echo "=== Waiting for deployments to complete ==="
kubectl rollout status deployment/dojo-backend -n dojo --timeout=300s
kubectl rollout status deployment/dojo-frontend -n dojo --timeout=300s

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Get service URL:"
echo "kubectl get ingress -n dojo"
echo ""

# Restore original files
mv k8s/backend/deployment.yaml.bak k8s/backend/deployment.yaml
mv k8s/frontend/deployment.yaml.bak k8s/frontend/deployment.yaml
