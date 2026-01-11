#!/bin/bash

# Deploy script for Market Workflow App
# Usage: ./deploy.sh

VPS_USER="admin"
VPS_HOST="91.98.137.192"
REMOTE_PATH="/home/admin/market_workflow_app"

echo "Deploying to $VPS_USER@$VPS_HOST..."

# Use rsync to sync files, excluding .git and __pycache__
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude '.venv' \
    ./ $VPS_USER@$VPS_HOST:$REMOTE_PATH/

echo "Files synced. Rebuilding container..."

# SSH and rebuild
ssh $VPS_USER@$VPS_HOST "cd $REMOTE_PATH && docker compose up --build -d"

echo "Deployment complete!"
