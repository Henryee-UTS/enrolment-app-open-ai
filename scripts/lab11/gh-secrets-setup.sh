#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="lab11-rg"
IDENTITY_NAME="lab11-github-oidc"
REPO="Henryee-UTS/enrolment-app-open-ai"
BRANCH="lab11-testing-deployment"

echo "=== Lab 11 Managed Identity OIDC Setup ==="

CURRENT_BRANCH=$(git branch --show-current)
CURRENT_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

if [[ "$CURRENT_BRANCH" != "$BRANCH" || "$CURRENT_REPO" != "$REPO" ]]; then
  echo "Incorrect GitHub repository or branch." >&2
  exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

CLIENT_ID=$(az identity show \
  --name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query clientId -o tsv)

PRINCIPAL_ID=$(az identity show \
  --name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query principalId -o tsv)

OWNER_ID=$(gh api "repos/$REPO" --jq .owner.id)
REPO_ID=$(gh api "repos/$REPO" --jq .id)

EXPECTED_SUBJECT="repo:Henryee-UTS@${OWNER_ID}/enrolment-app-open-ai@${REPO_ID}:ref:refs/heads/${BRANCH}"

ACTUAL_SUBJECT=$(az identity federated-credential show \
  --name lab11-github-actions \
  --identity-name "$IDENTITY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query subject -o tsv)

if [[ "$ACTUAL_SUBJECT" != "$EXPECTED_SUBJECT" ]]; then
  echo "OIDC subject mismatch. No secrets were changed." >&2
  exit 1
fi

ASSIGNED_ROLES=$(az role assignment list \
  --assignee "$PRINCIPAL_ID" \
  --scope "$SCOPE" \
  --query "[].roleDefinitionName" -o tsv)

for ROLE in "Contributor" "User Access Administrator"; do
  if ! grep -Fxq "$ROLE" <<< "$ASSIGNED_ROLES"; then
    echo "Missing role: $ROLE. No secrets were changed." >&2
    exit 1
  fi
done

gh secret set AZURE_CLIENT_ID --repo "$REPO" --body "$CLIENT_ID"
gh secret set AZURE_TENANT_ID --repo "$REPO" --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "$SUBSCRIPTION_ID"

echo "=== GitHub OIDC Secrets Setup Complete ==="
