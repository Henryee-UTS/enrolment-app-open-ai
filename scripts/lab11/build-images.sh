#!/bin/bash
set -euo pipefail

# Lab 11: Build and push Docker images to Azure Container Registry
RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
IMAGE_TAG="latest"

echo "=== Lab 11 Image Build ==="

REGISTRY_NAME=$(az group show \
  --name "$RESOURCE_GROUP" \
  --query "tags.registryName" -o tsv)

if [[ -z "$REGISTRY_NAME" || "$REGISTRY_NAME" == "None" ]]; then
  echo "Missing registry name. Run env-setup.sh first." >&2
  exit 1
fi

echo "Registry: $REGISTRY_NAME"

# Create ACR Basic only if it does not already exist
if ! az acr show --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$REGISTRY_NAME" \
    --sku Basic
fi

# Wait until the registry hostname is available
LOGIN_SERVER="${REGISTRY_NAME}.azurecr.io"
echo "Checking registry DNS..."

for i in $(seq 1 24); do
  if python3 -c 'import socket,sys; socket.getaddrinfo(sys.argv[1],443)' "$LOGIN_SERVER" 2>/dev/null; then
    break
  fi

  if [[ "$i" -eq 24 ]]; then
    echo "Registry DNS lookup timed out." >&2
    exit 1
  fi

  sleep 5
done

echo "Logging in to Azure Container Registry..."
az acr login --name "$REGISTRY_NAME"

echo "Building database-service..."
docker build -t "${LOGIN_SERVER}/database-service:${IMAGE_TAG}" ./database-service
docker push "${LOGIN_SERVER}/database-service:${IMAGE_TAG}"

echo "Building enrolment-service..."
docker build -f enrolment-service/Dockerfile -t "${LOGIN_SERVER}/enrolment-service:${IMAGE_TAG}" .
docker push "${LOGIN_SERVER}/enrolment-service:${IMAGE_TAG}"

echo "Building frontend-service..."
docker build -t "${LOGIN_SERVER}/frontend-service:${IMAGE_TAG}" ./frontend-service
docker push "${LOGIN_SERVER}/frontend-service:${IMAGE_TAG}"

echo "=== Image Build Complete ==="
