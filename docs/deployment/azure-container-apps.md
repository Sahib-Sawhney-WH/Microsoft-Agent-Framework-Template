# Azure Container Apps Deployment

Deploy the Microsoft Agent Framework to Azure Container Apps for serverless, auto-scaling container hosting.

## Overview

Azure Container Apps provides:
- **Serverless containers** — Pay only for what you use
- **Built-in autoscaling** — Scale to zero or thousands
- **Dapr integration** — Microservices patterns built-in
- **Managed ingress** — HTTPS with custom domains
- **Managed Identity** — Secure access to Azure resources

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps Environment                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  ┌─────────────┐     ┌─────────────────────────────────────────┐  │  │
│  │  │   Ingress   │────▶│        msft-agent Container App         │  │  │
│  │  │  (HTTPS)    │     │                                         │  │  │
│  │  └─────────────┘     │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │  │  │
│  │                      │  │Replica 1│  │Replica 2│  │Replica N│ │  │  │
│  │                      │  └─────────┘  └─────────┘  └─────────┘ │  │  │
│  │                      │                                         │  │  │
│  │                      │  Scale: 0-10 based on HTTP traffic      │  │  │
│  │                      └─────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │Azure OpenAI │ │ Azure Redis │ │ Azure Blob  │
            │             │ │  (Optional) │ │  (Optional) │
            └─────────────┘ └─────────────┘ └─────────────┘
```

## Prerequisites

- **Azure CLI** (2.50+) with Container Apps extension
- **Azure subscription** with contributor access
- **Azure OpenAI** resource with deployed model
- **Azure Container Registry** (optional, for private images)

```bash
# Install Container Apps extension
az extension add --name containerapp --upgrade

# Verify installation
az containerapp --help
```

## Quick Deployment

### Option 1: Deploy from Source

```bash
# Set variables
RESOURCE_GROUP="msft-agent-rg"
LOCATION="eastus"
ENVIRONMENT="msft-agent-env"
APP_NAME="msft-agent"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy directly from source code
az containerapp up \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --source . \
  --env-vars \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    LOG_LEVEL="INFO"
```

### Option 2: Deploy from ACR

```bash
# Create Container Apps environment
az containerapp env create \
  --name $ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Deploy from Azure Container Registry
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT \
  --image myregistry.azurecr.io/msft-agent:latest \
  --registry-server myregistry.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8080 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 1 \
  --memory 2Gi \
  --env-vars \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o"
```

## Detailed Deployment

### Step 1: Create Resource Group

```bash
RESOURCE_GROUP="msft-agent-rg"
LOCATION="eastus"

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 2: Create Container Apps Environment

```bash
ENVIRONMENT="msft-agent-env"

# Basic environment
az containerapp env create \
  --name $ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# With VNet integration (recommended for production)
az containerapp env create \
  --name $ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id "/subscriptions/.../subnets/container-apps" \
  --internal-only false
```

### Step 3: Create Managed Identity

```bash
IDENTITY_NAME="msft-agent-identity"

# Create user-assigned managed identity
az identity create \
  --name $IDENTITY_NAME \
  --resource-group $RESOURCE_GROUP

# Get identity details
IDENTITY_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)
CLIENT_ID=$(az identity show --name $IDENTITY_NAME --resource-group $RESOURCE_GROUP --query clientId -o tsv)
```

### Step 4: Assign Permissions

```bash
# Azure OpenAI access
AOAI_ID=$(az cognitiveservices account show --name your-openai --resource-group $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
  --assignee $CLIENT_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $AOAI_ID

# Redis access (if using)
REDIS_ID=$(az redis show --name your-redis --resource-group $RESOURCE_GROUP --query id -o tsv)
# Note: Redis requires Data Access Policy, not RBAC

# Storage access (if using)
STORAGE_ID=$(az storage account show --name yourstorage --resource-group $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
  --assignee $CLIENT_ID \
  --role "Storage Blob Data Contributor" \
  --scope $STORAGE_ID
```

### Step 5: Deploy Container App

```bash
APP_NAME="msft-agent"

az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT \
  --image myregistry.azurecr.io/msft-agent:v1.0.0 \
  --registry-server myregistry.azurecr.io \
  --user-assigned $IDENTITY_ID \
  --target-port 8080 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 1 \
  --memory 2Gi \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50 \
  --env-vars \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    AZURE_CLIENT_ID="$CLIENT_ID" \
    LOG_LEVEL="INFO"
```

### Step 6: Configure Secrets

```bash
# Add secrets
az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets \
    redis-host="your-redis.redis.cache.windows.net" \
    storage-account="yourstorageaccount"

# Update app to use secrets
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    REDIS_HOST=secretref:redis-host \
    STORAGE_ACCOUNT_NAME=secretref:storage-account
```

## Bicep Deployment

For infrastructure-as-code deployment, use Bicep templates.

### Main Template

```bicep
// main.bicep
targetScope = 'resourceGroup'

@description('The location for all resources')
param location string = resourceGroup().location

@description('Azure OpenAI endpoint')
param azureOpenAIEndpoint string

@description('Azure OpenAI deployment name')
param azureOpenAIDeployment string = 'gpt-4o'

@description('Container image')
param containerImage string

// Container Apps Environment
resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'msft-agent-env'
  location: location
  properties: {
    zoneRedundant: true
  }
}

// User-Assigned Managed Identity
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'msft-agent-identity'
  location: location
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'msft-agent'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
        }
      }
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'agent'
          image: containerImage
          resources: {
            cpu: json('1')
            memory: '2Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: azureOpenAIDeployment
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identity.properties.clientId
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/live'
                port: 8080
              }
              initialDelaySeconds: 30
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready'
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output identityClientId string = identity.properties.clientId
```

### Deploy with Bicep

```bash
# Deploy
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters \
    azureOpenAIEndpoint="https://your-resource.openai.azure.com/" \
    containerImage="myregistry.azurecr.io/msft-agent:v1.0.0"

# Get outputs
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs
```

## Scaling Configuration

### HTTP-Based Scaling

```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 10 \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50
```

### CPU-Based Scaling

```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name cpu-scaling \
  --scale-rule-type cpu \
  --scale-rule-metadata type=Utilization value=70
```

## Custom Domain & SSL

```bash
# Add custom domain
az containerapp hostname add \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname agent.example.com

# Bind certificate (managed)
az containerapp hostname bind \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname agent.example.com \
  --environment $ENVIRONMENT \
  --validation-method CNAME
```

## Monitoring

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app msft-agent-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get connection string
CONNECTION_STRING=$(az monitor app-insights component show \
  --app msft-agent-insights \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

# Update container app
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars APPLICATIONINSIGHTS_CONNECTION_STRING="$CONNECTION_STRING"
```

### View Logs

```bash
# Stream logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Query logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --tail 100
```

## Troubleshooting

### App Not Starting

```bash
# Check container app status
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.runningStatus"

# Check revision status
az containerapp revision list \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table

# View system logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --type system
```

### Authentication Errors

```bash
# Verify managed identity
az containerapp identity show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# Check role assignments
az role assignment list \
  --assignee $CLIENT_ID \
  --output table
```

## Related Documentation

- [Azure Setup Guide](azure-setup.md)
- [Kubernetes Deployment](kubernetes.md)
- [Production Checklist](production-checklist.md)
- [Monitoring Guide](../operations/monitoring.md)
