#!/bin/bash

# Script for running the local Photo Agent container

# Function to display help
show_help() {
    echo "Usage: ./run-local.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start       Start the container in detached mode"
    echo "  stop        Stop the container"
    echo "  restart     Restart the container"
    echo "  logs        Show container logs"
    echo "  shell       Open a shell in the container"
    echo "  web         Start the web interface (default)"
    echo "  process     Run the full processing pipeline"
    echo "  schema      Get metadata schema"
    echo "  photos      Process photos"
    echo "  analyze     Analyze photos with OpenAI"
    echo "  metadata    Generate metadata"
    echo "  upload      Upload to SharePoint"
    echo "  build       Rebuild the Docker image"
    echo "  help        Show this help message"
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Process command
case "$1" in
    start)
        echo "Starting Photo Agent container in detached mode..."
        docker-compose -f docker-compose.local.yml up -d
        echo "Container started. Web interface available at http://localhost:8080"
        ;;
    stop)
        echo "Stopping Photo Agent container..."
        docker-compose -f docker-compose.local.yml down
        ;;
    restart)
        echo "Restarting Photo Agent container..."
        docker-compose -f docker-compose.local.yml down
        docker-compose -f docker-compose.local.yml up -d
        echo "Container restarted. Web interface available at http://localhost:8080"
        ;;
    logs)
        echo "Showing container logs (press Ctrl+C to exit)..."
        docker-compose -f docker-compose.local.yml logs -f
        ;;
    shell)
        echo "Opening shell in the container..."
        docker-compose -f docker-compose.local.yml exec agent bash
        ;;
    web)
        echo "Starting web interface..."
        docker-compose -f docker-compose.local.yml down
        docker-compose -f docker-compose.local.yml up
        ;;
    process)
        echo "Running full processing pipeline..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.auto_process
        ;;
    schema)
        echo "Getting metadata schema..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.metadata_schema
        ;;
    photos)
        echo "Processing photos..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.photo_metadata
        ;;
    analyze)
        echo "Analyzing photos with OpenAI..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.openai_analyzer
        ;;
    metadata)
        echo "Generating metadata..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.metadata_generator
        ;;
    upload)
        echo "Uploading to SharePoint..."
        docker-compose -f docker-compose.local.yml run --rm agent python -m src.sharepoint_uploader
        ;;
    build)
        echo "Rebuilding Docker image..."
        docker-compose -f docker-compose.local.yml build
        ;;
    help|*)
        show_help
        ;;
esac
