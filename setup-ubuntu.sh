#!/bin/bash

# Setup script for Ubuntu 22.04 installation
echo "Setting up Photo Agent for Ubuntu 22.04..."

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo privileges"
  exit 1
fi

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully"
else
    echo "Docker is already installed"
fi

# Install Docker Compose if not already installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose is already installed"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/downloads data/metadata data/analysis data/upload/metadata data/uploaded data/reports data/registry data/processed logs

# Set permissions
echo "Setting permissions..."
chmod -R 755 data logs
chown -R $SUDO_USER:$SUDO_USER data logs

# Create local config file if it doesn't exist
if [ ! -f config/config.local.env ]; then
    echo "Creating local configuration file..."
    mkdir -p config
    cp config/config.local.env.example config/config.local.env 2>/dev/null || echo "# Local configuration for development and testing
# No real SharePoint credentials or API keys needed for local testing

# SharePoint connection settings (dummy values for local testing)
SHAREPOINT_SITE_URL=\"https://example.sharepoint.com/sites/test\"
SHAREPOINT_USERNAME=\"local.test@example.com\"
SHAREPOINT_PASSWORD=dummy_password

# Library settings
SOURCE_LIBRARY_TITLE=\"LocalPhotoLibrary\"
SHAREPOINT_LIBRARY=\"LocalTargetLibrary\"

# File settings
METADATA_SCHEMA_FILE=config/sharepoint_choices.json
TARGET_FILENAME_MASK=Local_Photo_{number}
# Maximum file size in bytes (15MB)
MAX_FILE_SIZE=15728640

# Connection settings
MAX_CONNECTION_ATTEMPTS=3
CONNECTION_RETRY_DELAY=5

# OpenAI settings (use your own API key for testing with real AI)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_CONCURRENCY_LIMIT=\"5\"
MAX_TOKENS=\"1000\"

# Logging settings
LOG_LEVEL=\"DEBUG\"
LOG_FILE=\"local_development.log\"
LOG_MODE=development
LOG_VERBOSE_DIRS=true

# OpenAI Prompt settings
OPENAI_PROMPT_TYPE=\"structured_simple\"
MODEL_NAME=\"gpt-4o\"
TEMPERATURE=\"0.2\"
IMAGE_DETAIL=\"high\"

# Web server settings
WEB_HOST=0.0.0.0
WEB_PORT=5000
FLASK_APP=src.web_server
FLASK_ENV=development
SECRET_KEY=local-development-secret-key

# Local development flags
LOCAL_MODE=true
MOCK_SHAREPOINT=true
MOCK_OPENAI=true" > config/config.local.env
    chown $SUDO_USER:$SUDO_USER config/config.local.env
fi

# Build the Docker images
echo "Building Docker images for Ubuntu 22.04..."
docker-compose -f docker-compose.ubuntu.yml build
docker-compose -f docker-compose.network.yml build
docker-compose -f docker-compose.remote.yml build

# Add current user to docker group to run docker without sudo
if ! groups $SUDO_USER | grep -q '\bdocker\b'; then
    echo "Adding user to docker group..."
    usermod -aG docker $SUDO_USER
    echo "You may need to log out and log back in for this to take effect"
fi

echo ""
echo "Installation complete!"
echo ""
echo "To start the application in standard mode, run:"
echo "  ./run-ubuntu.sh start"
echo ""
echo "The web interface will be available at: http://localhost:8080"
echo ""
echo "To start with local network access, run:"
echo "  ./run-ubuntu.sh network"
echo ""
echo "The web interface will be available at: http://localhost:5000"
echo ""
echo "To start with access from other computers in local network, run:"
echo "  ./run-ubuntu.sh remote"
echo ""
local_ip=$(hostname -I | awk '{print $1}')
echo "The web interface will be available at: http://$local_ip:5001"
echo "Other computers in your network can access the service at this address"
echo ""
echo "To stop the application, run:"
echo "  ./run-ubuntu.sh stop"
echo ""
echo "For more options, run:"
echo "  ./run-ubuntu.sh help"
echo ""
echo "Note: In local mode, SharePoint and OpenAI services are mocked."
echo "To use real services, edit config/config.local.env and set:"
echo "  MOCK_SHAREPOINT=false"
echo "  MOCK_OPENAI=false"
echo "And provide valid credentials/API keys."
