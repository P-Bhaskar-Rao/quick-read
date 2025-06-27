#!/bin/bash

# Cloud Run Deployment Script for Quick Read Wizard
# Make sure you have gcloud CLI installed and authenticated

set -e  # Exit on any error

# Configuration - UPDATE THESE VALUES
PROJECT_ID="${PROJECT_ID:-your-project-id}"  # Replace with your actual project ID or set env var
REGION="${REGION:-asia-south1}"               # Changed to Asia South (Mumbai)
SERVICE_NAME="quick-read-wizard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Quick Read Wizard to Google Cloud Run${NC}"

# Validate project ID
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}❌ Please update PROJECT_ID in the script or set PROJECT_ID environment variable${NC}"
    echo -e "${YELLOW}   Example: export PROJECT_ID=my-actual-project-id${NC}"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    echo -e "${BLUE}   Install: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  You are not authenticated with gcloud. Authenticating now...${NC}"
    gcloud auth login
fi

# Set the project
echo -e "${YELLOW}📋 Setting project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Verify project exists and we have access
if ! gcloud projects describe $PROJECT_ID &> /dev/null; then
    echo -e "${RED}❌ Project $PROJECT_ID not found or no access. Please check the project ID.${NC}"
    exit 1
fi

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com  # For Cloud SQL
gcloud services enable storage.googleapis.com   # For Cloud Storage

# Check if cloudbuild.yaml exists
if [ ! -f "cloudbuild.yaml" ]; then
    echo -e "${RED}❌ cloudbuild.yaml not found in current directory${NC}"
    exit 1
fi

# Build and deploy using Cloud Build
echo -e "${YELLOW}🏗️  Building and deploying with Cloud Build...${NC}"
echo -e "${BLUE}   This may take 5-10 minutes...${NC}"

if ! gcloud builds submit --config cloudbuild.yaml; then
    echo -e "${RED}❌ Build failed. Check the logs above for details.${NC}"
    exit 1
fi

# Wait a moment for deployment to complete
sleep 10

# Get the service URL
echo -e "${YELLOW}🔍 Getting service URL...${NC}"
if ! SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null); then
    echo -e "${RED}❌ Failed to get service URL. The service might not be deployed yet.${NC}"
    echo -e "${BLUE}   Check Cloud Console: https://console.cloud.google.com/run${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo -e "${GREEN}📊 Monitor service: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/overview?project=$PROJECT_ID${NC}"

# Test the health endpoint
echo -e "${YELLOW}🏥 Testing health endpoint...${NC}"
if curl -s -f "$SERVICE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed. Service might still be starting up.${NC}"
fi

# Optional: Open the service URL
echo ""
read -p "Do you want to open the service URL in your browser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v open &> /dev/null; then
        open "$SERVICE_URL"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$SERVICE_URL"
    else
        echo -e "${YELLOW}Please open this URL manually: $SERVICE_URL${NC}"
    fi
fi

echo -e "${GREEN}🎉 Deployment complete! Your service is running at: $SERVICE_URL${NC}"