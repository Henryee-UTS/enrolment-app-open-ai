#!/bin/bash
set -euo pipefail

# Lab 11: Deploy three microservices to Azure Container Apps

echo "=== Lab 11 Azure Deployment ==="

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
IMAGE_TAG="latest"

# Read deployment names from resource group tags
REGISTRY_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.registryName" -o tsv)
ENV_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.envName" -o tsv)
FRONTEND_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.frontendAppName" -o tsv)
ENROLMENT_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.enrolmentAppName" -o tsv)
DB_APP_NAME=$(az group show --name "$RESOURCE_GROUP" --query "tags.dbAppName" -o tsv)

for value in "$REGISTRY_NAME" "$ENV_NAME" "$FRONTEND_APP_NAME" "$ENROLMENT_APP_NAME" "$DB_APP_NAME"; do
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "Missing deployment configuration. Run env-setup.sh first." >&2
    exit 1
  fi
done

REGISTRY_SERVER=$(az acr show \
  --name "$REGISTRY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query loginServer -o tsv)

# 1. Database service: internal access only
echo "Deploying database-service..."

az containerapp create \
  --name "$DB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/database-service:${IMAGE_TAG}" \
  --target-port 5002 \
  --ingress internal \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 1 --max-replicas 1

DB_FQDN=$(az containerapp show \
  --name "$DB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# 2. Enrolment service: internal access only
echo "Deploying enrolment-service..."

JWT_SECRET=$(openssl rand -hex 32)

az containerapp create \
  --name "$ENROLMENT_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/enrolment-service:${IMAGE_TAG}" \
  --target-port 5001 \
  --ingress internal \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 1 --max-replicas 3 \
  --secrets "jwt-secret=$JWT_SECRET" \
  --env-vars \
    "JWT_SECRET_KEY=secretref:jwt-secret" \
    "DATABASE_SERVICE_URL=https://$DB_FQDN" \
    AI_MODE_ENABLED=false \
    MCP_ENABLED=false \
    RAG_ENABLED=false \
    MULTI_AGENT_ENABLED=false

unset JWT_SECRET

ENROLMENT_FQDN=$(az containerapp show \
  --name "$ENROLMENT_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# 3. Frontend service: public access
echo "Deploying frontend-service..."

az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "${REGISTRY_SERVER}/frontend-service:${IMAGE_TAG}" \
  --target-port 80 \
  --ingress external \
  --registry-server "$REGISTRY_SERVER" \
  --registry-identity system \
  --cpu 0.25 --memory 0.5Gi \
  --min-replicas 1 --max-replicas 3 \
  --env-vars "ENROLMENT_SERVICE_URL=https://$ENROLMENT_FQDN"

FRONTEND_FQDN=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "=== Deployment Complete ==="
echo "Frontend URL: https://$FRONTEND_FQDN"
