#!/bin/bash

# Setup script for local development environment
echo "Setting up local development environment for Photo Agent..."

# Create necessary directories if they don't exist
mkdir -p data/downloads data/metadata data/analysis data/upload/metadata data/uploaded data/reports data/registry data/processed logs

# Set permissions
chmod -R 755 data logs

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and Docker Compose first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image for local development..."
docker-compose -f docker-compose.local.yml build

echo ""
echo "Local development environment setup complete!"
echo ""
echo "To start the application in local mode, run:"
echo "  docker-compose -f docker-compose.local.yml up"
echo ""
echo "The web interface will be available at: http://localhost:8080"
echo ""
echo "Note: In local mode, SharePoint and OpenAI services are mocked."
echo "To use real services, edit config/config.local.env and set:"
echo "  MOCK_SHAREPOINT=false"
echo "  MOCK_OPENAI=false"
echo "And provide valid credentials/API keys."
