#!/bin/bash
# MQTT Broker Setup Script for Orbit Bhyve Package

echo "🚀 Setting up MQTT Broker for Orbit Bhyve Package"
echo "=================================================="

# Detect the operating system
if command -v dnf &> /dev/null; then
    PACKAGE_MANAGER="dnf"
    echo "📦 Detected Fedora/RHEL system (dnf)"
elif command -v apt &> /dev/null; then
    PACKAGE_MANAGER="apt"
    echo "📦 Detected Debian/Ubuntu system (apt)"
elif command -v brew &> /dev/null; then
    PACKAGE_MANAGER="brew"
    echo "📦 Detected macOS system (brew)"
else
    echo "❌ Unsupported package manager. Please install Mosquitto manually."
    exit 1
fi

# Install Mosquitto
echo ""
echo "🔧 Installing Mosquitto MQTT Broker..."

case $PACKAGE_MANAGER in
    "dnf")
        sudo dnf install -y mosquitto mosquitto-clients
        ;;
    "apt")
        sudo apt update
        sudo apt install -y mosquitto mosquitto-clients
        ;;
    "brew")
        brew install mosquitto
        ;;
esac

if [ $? -eq 0 ]; then
    echo "✅ Mosquitto installed successfully"
else
    echo "❌ Failed to install Mosquitto"
    exit 1
fi

# Create basic configuration
echo ""
echo "⚙️  Creating Mosquitto configuration..."

# Create config directory if it doesn't exist
sudo mkdir -p /etc/mosquitto/conf.d

# Create a basic configuration file
sudo tee /etc/mosquitto/conf.d/bhyve.conf > /dev/null << 'EOF'
# Orbit Bhyve MQTT Broker Configuration

# Listen on all interfaces
listener 1883
protocol mqtt

# Allow anonymous connections (for development)
allow_anonymous true

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# Persistence
persistence true
persistence_location /var/lib/mosquitto/

# Auto-save interval (seconds)
autosave_interval 1800
EOF

echo "✅ Configuration file created: /etc/mosquitto/conf.d/bhyve.conf"

# Create log directory
sudo mkdir -p /var/log/mosquitto
sudo chown mosquitto:mosquitto /var/log/mosquitto

# Start and enable Mosquitto service
echo ""
echo "🚀 Starting Mosquitto service..."

case $PACKAGE_MANAGER in
    "dnf"|"apt")
        sudo systemctl enable mosquitto
        sudo systemctl start mosquitto
        sudo systemctl status mosquitto --no-pager
        ;;
    "brew")
        brew services start mosquitto
        ;;
esac

# Test the broker
echo ""
echo "🧪 Testing MQTT broker connection..."

# Wait a moment for the service to start
sleep 2

# Test connection
if command -v mosquitto_pub &> /dev/null; then
    mosquitto_pub -h localhost -t "test/bhyve" -m "Hello from Orbit Bhyve!" -q 1
    if [ $? -eq 0 ]; then
        echo "✅ MQTT broker is working correctly!"
    else
        echo "❌ MQTT broker test failed"
    fi
else
    echo "⚠️  mosquitto_pub not found, skipping test"
fi

echo ""
echo "🎉 MQTT Broker Setup Complete!"
echo "==============================="
echo ""
echo "📋 Configuration Summary:"
echo "   • Broker Address: localhost"
echo "   • Port: 1883"
echo "   • Protocol: MQTT (no TLS)"
echo "   • Authentication: Anonymous (development mode)"
echo ""
echo "🔧 Service Management:"
echo "   • Start: sudo systemctl start mosquitto"
echo "   • Stop: sudo systemctl stop mosquitto"
echo "   • Status: sudo systemctl status mosquitto"
echo "   • Logs: sudo journalctl -u mosquitto -f"
echo ""
echo "📖 Next Steps:"
echo "   1. Set environment variables:"
echo "      export MQTT_BROKER=localhost"
echo "      export MQTT_PORT=1883"
echo ""
echo "   2. Test with the Bhyve package:"
echo "      python examples/mqtt_control_example.py"
echo ""
echo "   3. Or start the dashboard:"
echo "      python start_mqtt_dashboard.py"
echo ""
