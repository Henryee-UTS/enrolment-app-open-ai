#!/bin/bash
set -euo pipefail

# Lab 11: GitHub Actions Azure OIDC setup
# Run manually only after creating the Lab 11 resource group.

APP_NAME="lab11-github-oidc"
RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
REPO="Henryee-UTS/enrolment-app-open-ai"
BRANCH="lab11-testing-deployment"

echo "=== Lab 11 GitHub OIDC Setup ==="

# Verify the correct repository and branch
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

if [[ "$CURRENT_BRANCH" != "$BRANCH" || "$CURRENT_REPO" != "$REPO" ]]; then
  echo "Incorrect GitHub repository or branch." >&2
  exit 1
fi

# Do not assign permissions until the resource group exists
if [[ "$(az group exists --name "$RESOURCE_GROUP")" != "true" ]]; then
  echo "Resource group $RESOURCE_GROUP does not exist." >&2
  echo "Run env-setup.sh first, after approving Azure resource creation." >&2
  exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# Locate or create the Azure application
CLIENT_ID=$(az ad app list \
  --display-name "$APP_NAME" \
  --query "[0].appId" -o tsv)

if [[ -z "$CLIENT_ID" || "$CLIENT_ID" == "None" ]]; then
  CLIENT_ID=$(az ad app create \
    --display-name "$APP_NAME" \
    --query appId -o tsv)
fi

# Create service principal if necessary
if [[ -z "$(az ad sp list --filter "appId eq '$CLIENT_ID'" --query "[0].id" -o tsv)" ]]; then
  az ad sp create --id "$CLIENT_ID"
fi

# GitHub OIDC identity
OWNER_ID=$(gh api "repos/$REPO" --jq .owner.id)
REPO_ID=$(gh api "repos/$REPO" --jq .id)

SUBJECT="repo:Henryee-UTS@${OWNER_ID}/enrolment-app-open-ai@${REPO_ID}:ref:refs/heads/${BRANCH}"

FED_NAME="lab11-github-actions"
PARAMS=$(printf '{"name":"%s","issuer":"https://token.actions.githubusercontent.com","subject":"%s","audiences":["api://AzureADTokenExchange"]}' "$FED_NAME" "$SUBJECT")

EXISTING=$(az ad app federated-credential list \
  --id "$CLIENT_ID" \
  --query "[?name=='$FED_NAME'].name" -o tsv)

if [[ -z "$EXISTING" ]]; then
  az ad app federated-credential create \
    --id "$CLIENT_ID" \
    --parameters "$PARAMS"
else
  az ad app federated-credential update \
    --id "$CLIENT_ID" \
    --federated-credential-id "$FED_NAME" \
    --parameters "$PARAMS"
fi

# Restrict GitHub deployment permissions to Lab 11 resource group
for ROLE in "Contributor" "User Access Administrator"; do
  EXISTING_ROLE=$(az role assignment list \
    --assignee "$CLIENT_ID" \
    --role "$ROLE" \
    --scope "$SCOPE" \
    --query "[0].id" -o tsv)

  if [[ -z "$EXISTING_ROLE" ]]; then
    az role assignment create \
      --assignee "$CLIENT_ID" \
      --role "$ROLE" \
      --scope "$SCOPE"
  fi
done

# Save identifiers in GitHub Actions secrets
gh secret set AZURE_CLIENT_ID --repo "$REPO" --body "$CLIENT_ID"
gh secret set AZURE_TENANT_ID --repo "$REPO" --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "$SUBSCRIPTION_ID"

echo "=== GitHub OIDC Setup Complete ==="
