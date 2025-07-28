#!/bin/bash
chmod +x start.sh

echo "🧹 Cleaning up local virtual environment..."
rm -rf venv

echo "🛑 Stopping any running Docker containers..."
docker compose -f docker-deploy.yaml stop

echo "🔨 Rebuilding Docker containers..."
docker compose -f docker-deploy.yaml build

echo "🚀 Starting Docker services..."
docker compose -f docker-deploy.yaml up --remove-orphans --force-recreate
