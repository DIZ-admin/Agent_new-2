#!/bin/bash

# Function to display help
show_help() {
    echo "Usage: ./run-ubuntu.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start       Start the container in detached mode (standard network)"
    echo "  network     Start the container with host network mode for local network access"
    echo "  remote      Start the container with access from other computers in local network"
    echo "  stop        Stop the container"
    echo "  restart     Restart the container"
    echo "  logs        Show container logs"
    echo "  shell       Open a shell in the container"
    echo "  web         Start the web interface in interactive mode (standard network)"
    echo "  web-network Start the web interface with host network mode"
    echo "  web-remote  Start the web interface with access from other computers"
    echo "  process     Run the full processing pipeline"
    echo "  schema      Get metadata schema"
    echo "  photos      Process photos"
    echo "  analyze     Analyze photos with OpenAI"
    echo "  metadata    Generate metadata"
    echo "  upload      Upload to SharePoint"
    echo "  build       Rebuild the Docker image"
    echo "  ip          Show the IP address of this computer in local network"
    echo "  help        Show this help message"
    echo ""
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Function to get local IP address
get_local_ip() {
    local_ip=$(hostname -I | awk '{print $1}')
    echo $local_ip
}

# Process command
case "$1" in
    start)
        echo "Starting Photo Agent container in detached mode (standard network)..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.ubuntu.yml up -d
        echo "Container started. Web interface available at http://localhost:8080"
        ;;
    network)
        echo "Starting Photo Agent container with host network mode..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml up -d
        echo "Container started. Web interface available at http://localhost:5000"
        ;;
    remote)
        echo "Starting Photo Agent container with remote access..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml up -d
        local_ip=$(get_local_ip)
        echo "Container started. Web interface available at:"
        echo "  - Local access:  http://localhost:5001"
        echo "  - Remote access: http://$local_ip:5001"
        echo ""
        echo "Other computers in your network can access the service at:"
        echo "http://$local_ip:5001"
        ;;
    stop)
        echo "Stopping Photo Agent containers..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        ;;
    ip)
        local_ip=$(get_local_ip)
        echo "Local IP address: $local_ip"
        echo ""
        echo "Other computers in your network can access the service at:"
        echo "http://$local_ip:5001 (when using 'remote' mode)"
        ;;
    restart)
        echo "Restarting Photo Agent container (standard network)..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.ubuntu.yml up -d
        echo "Container restarted. Web interface available at http://localhost:8080"
        ;;
    restart-network)
        echo "Restarting Photo Agent container with host network mode..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml up -d
        echo "Container restarted. Web interface available at http://localhost:5000"
        ;;
    restart-remote)
        echo "Restarting Photo Agent container with remote access..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml up -d
        local_ip=$(get_local_ip)
        echo "Container restarted. Web interface available at:"
        echo "  - Local access:  http://localhost:5001"
        echo "  - Remote access: http://$local_ip:5001"
        ;;
    logs)
        echo "Showing container logs (press Ctrl+C to exit)..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml logs -f
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml logs -f
        else
            docker-compose -f docker-compose.ubuntu.yml logs -f
        fi
        ;;
    shell)
        echo "Opening shell in the container..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml exec photo-agent bash
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml exec photo-agent bash
        else
            docker-compose -f docker-compose.ubuntu.yml exec photo-agent bash
        fi
        ;;
    web)
        echo "Starting web interface in interactive mode (standard network)..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.ubuntu.yml up
        ;;
    web-network)
        echo "Starting web interface with host network mode..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml up
        ;;
    web-remote)
        echo "Starting web interface with remote access..."
        docker-compose -f docker-compose.ubuntu.yml down 2>/dev/null
        docker-compose -f docker-compose.network.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml down 2>/dev/null
        docker-compose -f docker-compose.remote.yml up
        local_ip=$(get_local_ip)
        echo "Web interface will be available at:"
        echo "  - Local access:  http://localhost:5001"
        echo "  - Remote access: http://$local_ip:5001"
        ;;
    process)
        echo "Running full processing pipeline..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.auto_process
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.auto_process
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.auto_process
        fi
        ;;
    schema)
        echo "Getting metadata schema..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.metadata_schema
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.metadata_schema
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.metadata_schema
        fi
        ;;
    photos)
        echo "Processing photos..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.photo_metadata
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.photo_metadata
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.photo_metadata
        fi
        ;;
    analyze)
        echo "Analyzing photos with OpenAI..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.openai_analyzer
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.openai_analyzer
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.openai_analyzer
        fi
        ;;
    metadata)
        echo "Generating metadata..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.metadata_generator
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.metadata_generator
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.metadata_generator
        fi
        ;;
    upload)
        echo "Uploading to SharePoint..."
        if docker ps | grep -q photo-agent-network; then
            docker-compose -f docker-compose.network.yml run --rm photo-agent python -m src.sharepoint_uploader
        elif docker ps | grep -q photo-agent-remote; then
            docker-compose -f docker-compose.remote.yml run --rm photo-agent python -m src.sharepoint_uploader
        else
            docker-compose -f docker-compose.ubuntu.yml run --rm photo-agent python -m src.sharepoint_uploader
        fi
        ;;
    build)
        echo "Rebuilding Docker images..."
        docker-compose -f docker-compose.ubuntu.yml build
        docker-compose -f docker-compose.network.yml build
        docker-compose -f docker-compose.remote.yml build
        ;;
    help|*)
        show_help
        ;;
esac
