#!/bin/bash
set -e

# Lab 11: Create Azure Container Apps Environment

echo "=== Lab 11 Container Apps Environment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"

# Read deployment configuration from resource group tags
ENV_NAME=$(az group show \
  --name "$RESOURCE_GROUP" \
  --query "tags.envName" -o tsv)

LOCATION=$(az group show \
  --name "$RESOURCE_GROUP" \
  --query "tags.location" -o tsv)

if [[ -z "$ENV_NAME" || "$ENV_NAME" == "None" ||
      -z "$LOCATION" || "$LOCATION" == "None" ]]; then
  echo "Missing deployment configuration. Run env-setup.sh first." >&2
  exit 1
fi

echo "Environment: $ENV_NAME"
echo "Location: $LOCATION"

# Create the environment if it does not already exist
if az containerapp env show \
  --name "$ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "Container Apps environment already exists."
else
  echo "Creating Container Apps environment..."

  az containerapp env create \
    --name "$ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION"
fi

echo "=== Container Apps Environment Ready ==="
