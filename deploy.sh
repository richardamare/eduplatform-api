#!/bin/bash

# Azure App Service deployment script for RAG Chatbot

set -e

echo "Starting deployment..."

# Configuration
RESOURCE_GROUP=${RESOURCE_GROUP:-"rag-chatbot-rg"}
APP_NAME=${APP_NAME:-"rag-chatbot-api"}
LOCATION=${LOCATION:-"eastus"}
APP_SERVICE_PLAN=${APP_SERVICE_PLAN:-"rag-chatbot-plan"}
POSTGRES_SERVER=${POSTGRES_SERVER:-"rag-chatbot-db"}
POSTGRES_DB=${POSTGRES_DB:-"ragchatbot"}

echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  App Name: $APP_NAME"
echo "  Location: $LOCATION"
echo "  App Service Plan: $APP_SERVICE_PLAN"
echo "  PostgreSQL Server: $POSTGRES_SERVER"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed. Please install it first."
    exit 1
fi

# Login check
if ! az account show &> /dev/null; then
    echo "Please login to Azure first:"
    az login
fi

# Create resource group
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service plan
echo "Creating App Service plan..."
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --sku B1 \
    --is-linux

# Create web app
echo "Creating web app..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --name $APP_NAME \
    --runtime "PYTHON|3.9" \
    --deployment-local-git

# Configure app settings (you'll need to update these with your actual values)
echo "Configuring app settings..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    WEBSITES_PORT=8000 \
    PYTHONPATH=/home/site/wwwroot

echo "Deployment configuration complete!"
echo ""
echo "Next steps:"
echo "1. Set your environment variables in Azure App Service:"
echo "   - DATABASE_URL"
echo "   - AZURE_OPENAI_ENDPOINT"
echo "   - AZURE_OPENAI_API_KEY"
echo "   - AZURE_OPENAI_DEPLOYMENT_NAME"
echo "   - AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
echo ""
echo "2. Deploy your code:"
echo "   git remote add azure <git-clone-url-from-azure>"
echo "   git push azure main"
echo ""
echo "3. Or use zip deployment:"
echo "   zip -r deploy.zip . -x '*.git*' '__pycache__/*' '*.pyc' 'venv/*'"
echo "   az webapp deployment source config-zip \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --name $APP_NAME \\"
echo "     --src deploy.zip"
echo ""
echo "App URL: https://$APP_NAME.azurewebsites.net" 