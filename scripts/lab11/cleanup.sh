#!/bin/bash
set -euo pipefail

# Lab 11: Remove Azure resources after completing the lab

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"

echo "=== Lab 11 Azure Cleanup ==="

# Check whether the resource group exists
if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "Resource group does not exist. Nothing to clean up."
  exit 0
fi

# Read deployment configuration
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)
FRONTEND_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.frontendAppName" -o tsv)
ENROLMENT_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.enrolmentAppName" -o tsv)
DB_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.dbAppName" -o tsv)

# Prevent deletion of an unrelated resource group
if [[ -z "$REGISTRY_NAME" || "$REGISTRY_NAME" == "None" ||
      -z "$ENV_NAME" || "$ENV_NAME" == "None" ]]; then
  echo "Missing Lab 11 deployment tags. Refusing to delete." >&2
  exit 1
fi

echo "WARNING: The following Azure resources will be deleted."
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "Registry:       $REGISTRY_NAME"
echo "Environment:    $ENV_NAME"
echo "Frontend:       $FRONTEND_APP_NAME"
echo "Enrolment:      $ENROLMENT_APP_NAME"
echo "Database:       $DB_APP_NAME"
echo ""

read -r -p "Type $RESOURCE_GROUP to confirm deletion: " CONFIRM

if [[ "$CONFIRM" != "$RESOURCE_GROUP" ]]; then
  echo "Cleanup cancelled."
  exit 1
fi

az group delete \
  --name "$RESOURCE_GROUP" \
  --yes \
  --no-wait

echo "=== Azure resource group deletion started ==="
echo "Deletion may take several minutes."
