#!/bin/bash

# Azure App Service deployment script for Python FastAPI application

set -e

echo "Starting deployment..."

# Install Python dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (if needed)
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

echo "Deployment completed successfully!" 