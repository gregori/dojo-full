#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TF_STATE="$PROJECT_ROOT/terraform/environments/prod/terraform.tfstate"
TFVARS="$PROJECT_ROOT/terraform/environments/prod/terraform.tfvars"

MODE="display"
REPO=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --set-gh) MODE="set-gh"; shift ;;
        --repo) REPO="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=== Dojo Admin - OCI Credentials Extractor ==="
echo ""

# 1. Extract from Terraform State
echo "--- Extracting from Terraform State ---"
if [[ ! -f "$TF_STATE" ]]; then
    echo "ERROR: terraform.tfstate not found at $TF_STATE"; exit 1
fi

BUCKET_NAMESPACE=$(python3 -c "
import json
with open('$TF_STATE') as f:
    state = json.load(f)
print(state.get('outputs',{}).get('bucket_namespace',{}).get('value',''))
")

K8S_NODE_PUBLIC_IP=$(python3 -c "
import json
with open('$TF_STATE') as f:
    state = json.load(f)
print(state.get('outputs',{}).get('k8s_node_public_ip',{}).get('value',''))
")

REPO_URLS=$(python3 -c "
import json
with open('$TF_STATE') as f:
    state = json.load(f)
print(json.dumps(state.get('outputs',{}).get('repository_urls',{}).get('value',{})))
")

OCI_REGISTRY=$(echo "$REPO_URLS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0].split('/')[0])")
OCI_TENANCY_NAMESPACE="$BUCKET_NAMESPACE"
OCI_BUCKET_NAMESPACE="$BUCKET_NAMESPACE"

echo "  BUCKET_NAMESPACE:      $BUCKET_NAMESPACE"
echo "  K8S_NODE_PUBLIC_IP:    $K8S_NODE_PUBLIC_IP"
echo "  OCI_REGISTRY:          $OCI_REGISTRY"
echo "  OCI_TENANCY_NAMESPACE: $OCI_TENANCY_NAMESPACE"
echo ""

# 2. Extract from terraform.tfvars
echo "--- Extracting from terraform.tfvars ---"
if [[ -f "$TFVARS" ]]; then
    OCI_COMPARTMENT_ID=$(grep 'compartment_id' "$TFVARS" | cut -d'=' -f2 | tr -d ' "' | head -1)
    OCI_AVAILABILITY_DOMAIN=$(grep 'availability_domain' "$TFVARS" | cut -d'=' -f2 | tr -d ' "' | head -1)
    SSH_PUB_KEY_PATH=$(grep 'ssh_public_key_path' "$TFVARS" | cut -d'=' -f2 | tr -d ' "' | head -1)
else
    echo "WARNING: terraform.tfvars not found"
fi
echo "  OCI_COMPARTMENT_ID:      $OCI_COMPARTMENT_ID"
echo "  OCI_AVAILABILITY_DOMAIN: $OCI_AVAILABILITY_DOMAIN"
echo "  SSH_PUB_KEY_PATH:        $SSH_PUB_KEY_PATH"
echo ""

# 3. Extract from OCI CLI config
echo "--- Extracting from OCI CLI config ---"
OCI_CONFIG="${OCI_CONFIG_FILE:-$HOME/.oci/config}"
if [[ ! -f "$OCI_CONFIG" ]]; then
    echo "ERROR: OCI config not found at $OCI_CONFIG"; exit 1
fi

OCI_TENANCY_OCID=$(grep '^tenancy=' "$OCI_CONFIG" | cut -d'=' -f2 | tr -d ' ')
OCI_USER_OCID=$(grep '^user=' "$OCI_CONFIG" | cut -d'=' -f2 | tr -d ' ')
OCI_FINGERPRINT=$(grep '^fingerprint=' "$OCI_CONFIG" | cut -d'=' -f2 | tr -d ' ')
OCI_REGION=$(grep '^region=' "$OCI_CONFIG" | cut -d'=' -f2 | tr -d ' ')
OCI_PRIVATE_KEY_PATH=$(grep '^key_file=' "$OCI_CONFIG" | cut -d'=' -f2 | tr -d ' ')
OCI_PRIVATE_KEY_PATH="${OCI_PRIVATE_KEY_PATH/#\~/$HOME}"

echo "  OCI_TENANCY_OCID:     $OCI_TENANCY_OCID"
echo "  OCI_USER_OCID:        $OCI_USER_OCID"
echo "  OCI_FINGERPRINT:      $OCI_FINGERPRINT"
echo "  OCI_REGION:           $OCI_REGION"
echo "  OCI_PRIVATE_KEY_PATH: $OCI_PRIVATE_KEY_PATH"
echo ""

# 4. Get cluster ID
echo "--- Getting OKE Cluster ID ---"
OCI_CLUSTER_ID=$(oci ce cluster list --compartment-id "$OCI_COMPARTMENT_ID" --query "data[0].id" --raw-output 2>/dev/null || echo "")
if [[ -z "$OCI_CLUSTER_ID" ]]; then
    echo "  WARNING: No OKE cluster found. Set OCI_CLUSTER_ID manually."
else
    echo "  OCI_CLUSTER_ID: $OCI_CLUSTER_ID"
fi
echo ""

# 5. Read key files
echo "--- Reading key files ---"
OCI_PRIVATE_KEY=""
if [[ -n "$OCI_PRIVATE_KEY_PATH" && -f "$OCI_PRIVATE_KEY_PATH" ]]; then
    OCI_PRIVATE_KEY=$(cat "$OCI_PRIVATE_KEY_PATH")
    echo "  OCI_PRIVATE_KEY: ✅ Read"
else
    echo "  OCI_PRIVATE_KEY: ❌ Not found"
fi

OCI_SSH_PUBLIC_KEY=""
if [[ -n "${SSH_PUB_KEY_PATH:-}" && -f "$SSH_PUB_KEY_PATH" ]]; then
    OCI_SSH_PUBLIC_KEY=$(cat "$SSH_PUB_KEY_PATH")
    echo "  OCI_SSH_PUBLIC_KEY: ✅ Read"
else
    echo "  OCI_SSH_PUBLIC_KEY: ❌ Not found"
fi
echo ""

# 6. Summary
echo "================================================================="
echo "  SUMMARY - GitHub Secrets Required"
echo "================================================================="
echo ""
echo "  # Auto-extracted secrets:"
echo "  OCI_TENANCY_OCID=$OCI_TENANCY_OCID"
echo "  OCI_USER_OCID=$OCI_USER_OCID"
echo "  OCI_FINGERPRINT=$OCI_FINGERPRINT"
echo "  OCI_COMPARTMENT_ID=$OCI_COMPARTMENT_ID"
echo "  OCI_AVAILABILITY_DOMAIN=$OCI_AVAILABILITY_DOMAIN"
echo "  OCI_CLUSTER_ID=$OCI_CLUSTER_ID"
echo "  OCI_BUCKET_NAMESPACE=$OCI_BUCKET_NAMESPACE"
echo "  OCI_REGISTRY=$OCI_REGISTRY"
echo "  OCI_TENANCY_NAMESPACE=$OCI_TENANCY_NAMESPACE"
echo ""
echo "  # Manual input required:"
echo "  OCI_PRIVATE_KEY=<PEM content from $OCI_PRIVATE_KEY_PATH>"
echo "  OCI_SSH_PUBLIC_KEY=<content of $SSH_PUB_KEY_PATH>"
echo "  OCI_REGISTRY_USERNAME=$OCI_TENANCY_NAMESPACE/<email>"
echo "  OCI_REGISTRY_PASSWORD=<Auth Token from OCI Console>"
echo "  MYSQL_ROOT_PASSWORD=<choose>"
echo "  MYSQL_PASSWORD=<choose>"
echo "  SECRET_KEY=<random string>"
echo ""
echo "  # Variables:"
echo "  OCI_REGION=$OCI_REGION"
echo "  VITE_API_URL=<your API URL>"
echo ""

# 7. Set via GitHub CLI
if [[ "$MODE" == "set-gh" ]]; then
    echo "================================================================="
    echo "  Setting GitHub Secrets via gh CLI"
    echo "================================================================="
    echo ""

    if ! command -v gh &>/dev/null; then
        echo "ERROR: gh CLI not found. Install with: brew install gh"; exit 1
    fi
    if ! gh auth status &>/dev/null 2>&1; then
        echo "ERROR: Not authenticated. Run: gh auth login"; exit 1
    fi

    if [[ -z "$REPO" ]]; then
        REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
    fi
    if [[ -z "$REPO" ]]; then
        echo "ERROR: Could not determine repo. Use --repo owner/repo"; exit 1
    fi

    echo "  Target: $REPO"
    echo ""
    echo "  Setting secrets..."
    gh secret set OCI_TENANCY_OCID --body "$OCI_TENANCY_OCID" --repo "$REPO" && echo "    ✅ OCI_TENANCY_OCID"
    gh secret set OCI_USER_OCID --body "$OCI_USER_OCID" --repo "$REPO" && echo "    ✅ OCI_USER_OCID"
    gh secret set OCI_FINGERPRINT --body "$OCI_FINGERPRINT" --repo "$REPO" && echo "    ✅ OCI_FINGERPRINT"
    gh secret set OCI_PRIVATE_KEY --body "$OCI_PRIVATE_KEY" --repo "$REPO" && echo "    ✅ OCI_PRIVATE_KEY"
    gh secret set OCI_COMPARTMENT_ID --body "$OCI_COMPARTMENT_ID" --repo "$REPO" && echo "    ✅ OCI_COMPARTMENT_ID"
    gh secret set OCI_AVAILABILITY_DOMAIN --body "$OCI_AVAILABILITY_DOMAIN" --repo "$REPO" && echo "    ✅ OCI_AVAILABILITY_DOMAIN"
    gh secret set OCI_BUCKET_NAMESPACE --body "$OCI_BUCKET_NAMESPACE" --repo "$REPO" && echo "    ✅ OCI_BUCKET_NAMESPACE"
    gh secret set OCI_REGISTRY --body "$OCI_REGISTRY" --repo "$REPO" && echo "    ✅ OCI_REGISTRY"
    gh secret set OCI_TENANCY_NAMESPACE --body "$OCI_TENANCY_NAMESPACE" --repo "$REPO" && echo "    ✅ OCI_TENANCY_NAMESPACE"

    if [[ -n "$OCI_CLUSTER_ID" ]]; then
        gh secret set OCI_CLUSTER_ID --body "$OCI_CLUSTER_ID" --repo "$REPO" && echo "    ✅ OCI_CLUSTER_ID"
    else
        echo "    ⏭️  OCI_CLUSTER_ID skipped"
    fi

    if [[ -n "$OCI_SSH_PUBLIC_KEY" ]]; then
        gh secret set OCI_SSH_PUBLIC_KEY --body "$OCI_SSH_PUBLIC_KEY" --repo "$REPO" && echo "    ✅ OCI_SSH_PUBLIC_KEY"
    else
        echo "    ⏭️  OCI_SSH_PUBLIC_KEY skipped"
    fi

    echo ""
    echo "  ✅ Auto-extracted secrets set."
    echo ""
    echo "  ⚠️  Set these manually:"
    echo "      gh secret set OCI_REGISTRY_USERNAME --body '$OCI_TENANCY_NAMESPACE/<email>' --repo '$REPO'"
    echo "      gh secret set OCI_REGISTRY_PASSWORD --body '<auth-token>' --repo '$REPO'"
    echo "      gh secret set MYSQL_ROOT_PASSWORD --body '<password>' --repo '$REPO'"
    echo "      gh secret set MYSQL_PASSWORD --body '<password>' --repo '$REPO'"
    echo "      gh secret set SECRET_KEY --body '<random-string>' --repo '$REPO'"
    echo ""

    echo "  Setting variables..."
    gh variable set OCI_REGION --body "$OCI_REGION" --repo "$REPO" && echo "    ✅ OCI_REGION"
    echo ""
    echo "  ⚠️  Set this manually:"
    echo "      gh variable set VITE_API_URL --body 'https://dojo.example.com/api' --repo '$REPO'"
    echo ""
fi

echo "=== Done ==="
