#!/bin/bash
set -euo pipefail

# Lab 11: Azure deployment validation

RESOURCE_GROUP="${RESOURCE_GROUP:-lab11-rg}"
REPORT_FILE="reports/lab11/deployment-results.md"

echo "=== Lab 11 Deployment Testing ==="

# Read frontend app name
APP_NAME=$(az group show \
  --name "$RESOURCE_GROUP" \
  --query "tags.frontendAppName" -o tsv)

if [[ -z "$APP_NAME" || "$APP_NAME" == "None" ]]; then
  echo "Frontend app name not found." >&2
  exit 1
fi

# Get frontend URL
APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

if [[ -z "$APP_URL" || "$APP_URL" == "None" ]]; then
  echo "Frontend URL not found." >&2
  exit 1
fi

echo "Testing https://$APP_URL"

# Check HTTP response
HTTP_STATUS=$(curl -L -sS -o /dev/null \
  -w "%{http_code}" \
  --max-time 30 \
  "https://$APP_URL") || HTTP_STATUS="000"

if [[ "$HTTP_STATUS" == "200" ]]; then
  STATUS="Success"
  VALIDATION="HTTP 200 OK"
else
  STATUS="Failed"
  VALIDATION="HTTP $HTTP_STATUS"
fi

# Generate deployment evidence
mkdir -p reports/lab11

cat > "$REPORT_FILE" <<EOF
# Lab 11 Deployment Report

## Azure Container Apps

Deployment Status: $STATUS

Frontend App Name: $APP_NAME

Frontend URL: https://$APP_URL

Validation Result: $VALIDATION

Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Reviewer Notes: Pending Section 7 Agentic Review
EOF

echo "=== Deployment Testing Complete ==="
cat "$REPORT_FILE"

if [[ "$STATUS" != "Success" ]]; then
  exit 1
fi
