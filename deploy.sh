#!/bin/bash
# Production Deployment Script for Orbit Bhyve Package

set -e

echo "🚀 Deploying Orbit Bhyve to Production Server"
echo "=============================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root for security reasons"
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ssl
mkdir -p logs
mkdir -p data

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one from env.example"
    echo "   cp env.example .env"
    echo "   # Edit .env with your credentials"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$BHYVE_USERNAME" ] || [ -z "$BHYVE_PASSWORD" ]; then
    echo "❌ BHYVE_USERNAME and BHYVE_PASSWORD must be set in .env file"
    exit 1
fi

# Create MQTT password file if it doesn't exist
if [ ! -f mosquitto/passwd ]; then
    echo "🔐 Creating MQTT password file..."
    echo "Please enter MQTT broker password:"
    read -s MQTT_PASSWORD
    echo "mqtt_user:$MQTT_PASSWORD" | docker run --rm -i eclipse-mosquitto:2.0 mosquitto_passwd -c - > mosquitto/passwd
    echo "✅ MQTT password file created"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t orbit-bhyve:latest .

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check MQTT broker
if docker exec bhyve-mqtt-broker mosquitto_pub -h localhost -t "test/health" -m "test" -q 1; then
    echo "✅ MQTT broker is healthy"
else
    echo "❌ MQTT broker is not responding"
fi

# Check dashboard
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Dashboard is healthy"
else
    echo "❌ Dashboard is not responding"
fi

echo ""
echo "🎉 Deployment completed!"
echo "======================="
echo ""
echo "📱 Access your dashboard at:"
echo "   http://your-domain.com (if configured)"
echo "   http://localhost (local access)"
echo ""
echo "🔧 Management commands:"
echo "   View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose.prod.yml down"
echo "   Restart services: docker-compose -f docker-compose.prod.yml restart"
echo "   Update services: ./deploy.sh"
echo ""
echo "📊 Monitor services:"
echo "   docker-compose -f docker-compose.prod.yml ps"
echo "   docker stats"
