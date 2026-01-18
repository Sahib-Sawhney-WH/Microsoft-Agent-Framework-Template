# Azure Resource Setup Guide

Comprehensive guide for configuring Azure resources required by the Microsoft Agent Framework.

## Overview

The framework uses the following Azure services:

| Service | Purpose | Required |
|---------|---------|----------|
| **Azure OpenAI** | LLM backend | Yes |
| **Azure Cache for Redis** | Session cache | No (recommended) |
| **Azure Blob Storage** | Session persistence | No (recommended) |
| **Azure Key Vault** | Secrets management | No (recommended) |
| **Azure Monitor** | Observability | No (recommended) |

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Azure subscription with appropriate permissions
- Python 3.10+ with `azure-identity` package

```bash
# Verify Azure CLI login
az account show

# Set subscription (if needed)
az account set --subscription "Your Subscription Name"
```

## Quick Setup Script

```bash
#!/bin/bash
# Quick setup script for all Azure resources

# Configuration
RESOURCE_GROUP="msft-agent-rg"
LOCATION="eastus"
AOAI_NAME="msft-agent-openai"
REDIS_NAME="msft-agent-redis"
STORAGE_NAME="msftagentstorage"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure OpenAI
az cognitiveservices account create \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0

# Deploy model
az cognitiveservices account deployment create \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 10

# Create Redis (Premium for AAD auth)
az redis create \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Premium \
  --vm-size P1

# Create Storage Account
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --name chat-history \
  --account-name $STORAGE_NAME \
  --auth-mode login

echo "Setup complete!"
echo "OpenAI Endpoint: https://$AOAI_NAME.openai.azure.com/"
echo "Redis Host: $REDIS_NAME.redis.cache.windows.net"
echo "Storage Account: $STORAGE_NAME"
```

---

## Azure OpenAI Setup

### Create Resource

```bash
AOAI_NAME="your-openai"
RESOURCE_GROUP="your-rg"
LOCATION="eastus"

az cognitiveservices account create \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0
```

### Deploy Model

```bash
# Deploy GPT-4o (recommended)
az cognitiveservices account deployment create \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 10

# Optional: Deploy GPT-4o-mini for lighter tasks
az cognitiveservices account deployment create \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini \
  --model-version "2024-07-18" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 50
```

### Configure Access

```bash
# Get your object ID
YOUR_OID=$(az ad signed-in-user show --query id -o tsv)

# Get resource ID
AOAI_ID=$(az cognitiveservices account show \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query id -o tsv)

# Assign Cognitive Services OpenAI User role
az role assignment create \
  --assignee "$YOUR_OID" \
  --role "Cognitive Services OpenAI User" \
  --scope "$AOAI_ID"
```

### Get Endpoint

```bash
az cognitiveservices account show \
  --name $AOAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.endpoint -o tsv
# Output: https://your-openai.openai.azure.com/
```

---

## Azure Cache for Redis Setup

Azure Cache for Redis requires **Data Access Policy** configuration for AAD authentication. Standard RBAC roles are not sufficient.

### Create Redis Cache

```bash
REDIS_NAME="your-redis"

# Premium tier required for AAD auth
az redis create \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Premium \
  --vm-size P1 \
  --enable-non-ssl-port false \
  --minimum-tls-version 1.2
```

### Enable AAD Authentication

```bash
az redis update \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --set redisConfiguration.aad-enabled=true
```

### Create Data Access Policy

```bash
YOUR_OID=$(az ad signed-in-user show --query id -o tsv)
YOUR_EMAIL="your.email@company.com"

# Create Data Access Policy assignment
az redis access-policy-assignment create \
  --name "your-user-policy" \
  --policy-name "Data Owner" \
  --object-id "$YOUR_OID" \
  --object-id-alias "$YOUR_EMAIL" \
  --redis-cache-name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP
```

**Available Policies:**
| Policy | Permissions |
|--------|-------------|
| `Data Owner` | Full read/write (development) |
| `Data Contributor` | Read/write, no admin |
| `Data Reader` | Read-only |

### Get Connection Info

```bash
az redis show \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query hostName -o tsv
# Output: your-redis.redis.cache.windows.net
```

---

## Azure Blob Storage Setup

### Create Storage Account

```bash
STORAGE_ACCOUNT="yourstorageaccount"

az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false \
  --min-tls-version TLS1_2
```

### Create Container

```bash
az storage container create \
  --name chat-history \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login
```

### Assign Permissions

```bash
YOUR_OID=$(az ad signed-in-user show --query id -o tsv)

STORAGE_ID=$(az storage account show \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query id -o tsv)

az role assignment create \
  --assignee "$YOUR_OID" \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_ID"
```

---

## Infrastructure as Code (Bicep)

### Complete Infrastructure Template

```bicep
// infrastructure.bicep
targetScope = 'resourceGroup'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Base name for resources')
param baseName string = 'msft-agent'

@description('Azure OpenAI model deployment name')
param modelDeploymentName string = 'gpt-4o'

// Azure OpenAI
resource openai 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: '${baseName}-openai'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: '${baseName}-openai'
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openai
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
  }
}

// Azure Cache for Redis
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${baseName}-redis'
  location: location
  properties: {
    sku: {
      name: 'Premium'
      family: 'P'
      capacity: 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'aad-enabled': 'true'
    }
  }
}

// Storage Account
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${baseName}storage', '-', '')
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource chatHistoryContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'chat-history'
  properties: {
    publicAccess: 'None'
  }
}

// User-Assigned Managed Identity
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${baseName}-identity'
  location: location
}

// Role Assignments
resource openaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, identity.id, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, 'Storage Blob Data Contributor')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output openaiEndpoint string = openai.properties.endpoint
output redisHost string = redis.properties.hostName
output storageAccountName string = storage.name
output identityClientId string = identity.properties.clientId
output identityPrincipalId string = identity.properties.principalId
```

### Deploy with Bicep

```bash
# Create resource group
az group create --name msft-agent-rg --location eastus

# Deploy infrastructure
az deployment group create \
  --resource-group msft-agent-rg \
  --template-file infrastructure.bicep \
  --parameters baseName=msft-agent

# Get outputs
az deployment group show \
  --resource-group msft-agent-rg \
  --name infrastructure \
  --query properties.outputs
```

---

## Terraform Alternative

```hcl
# main.tf
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  default = "eastus"
}

variable "base_name" {
  default = "msft-agent"
}

resource "azurerm_resource_group" "main" {
  name     = "${var.base_name}-rg"
  location = var.location
}

# Azure OpenAI
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.base_name}-openai"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name = "${var.base_name}-openai"
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  scale {
    type     = "Standard"
    capacity = 10
  }
}

# Azure Redis Cache
resource "azurerm_redis_cache" "main" {
  name                = "${var.base_name}-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 1
  family              = "P"
  sku_name            = "Premium"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    aad_enabled = true
  }
}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = replace("${var.base_name}storage", "-", "")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "chat_history" {
  name                  = "chat-history"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Outputs
output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}
```

### Deploy with Terraform

```bash
terraform init
terraform plan
terraform apply
```

---

## Authentication

All Azure services use `DefaultAzureCredential`, which tries authentication methods in order:

1. **Environment variables** — `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`
2. **Managed Identity** — In Azure VMs, App Service, Container Apps
3. **Azure CLI** — `az login`
4. **Visual Studio Code** — Azure extension
5. **Interactive browser** — Fallback

### Local Development

```bash
az login
az account set --subscription "Your Subscription"
```

### Production (Managed Identity)

For production deployments (AKS, Container Apps, etc.):

1. Enable Managed Identity on your compute resource
2. Assign appropriate RBAC roles to the identity
3. `DefaultAzureCredential` automatically uses the managed identity

### Verify Authentication

```python
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()

# Test Azure OpenAI access
token = credential.get_token("https://cognitiveservices.azure.com/.default")
print(f"OpenAI token: {len(token.token)} chars")

# Test Redis access
token = credential.get_token("https://redis.azure.com/.default")
print(f"Redis token: {len(token.token)} chars")

# Test Storage access
token = credential.get_token("https://storage.azure.com/.default")
print(f"Storage token: {len(token.token)} chars")
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `NOAUTH Authentication required` (Redis) | Configure Data Access Policy |
| `AuthorizationPermissionMismatch` (Storage) | Assign RBAC role, wait for propagation |
| `Unauthorized` (OpenAI) | Assign Cognitive Services OpenAI User role |
| RBAC not working | Wait 5-15 min for propagation |

### Check Permissions

```bash
# List your role assignments
az role assignment list \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --output table

# Check Redis Data Access Policies
az redis access-policy-assignment list \
  --redis-cache-name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

---

## Related Documentation

- [Deployment Overview](index.md)
- [Azure Container Apps](azure-container-apps.md)
- [Kubernetes Deployment](kubernetes.md)
- [Production Checklist](production-checklist.md)
