# Orbit Bhyve Python Package - User Guide

A Python package for controlling and monitoring Orbit Bhyve irrigation controllers via MQTT.

## 🚀 Quick Start

### Option 1: Simple Installation (Recommended)

```bash
# 1. Install the package
pip install orbit-bhyve

# 2. Set up your credentials
export BHYVE_USERNAME="your@email.com"
export BHYVE_PASSWORD="your_password"

# 3. Run the complete system
python -m orbit_bhyve
```

This will start:
- MQTT broker (Mosquitto)
- Bhyve gateway (connects to your devices)
- Web dashboard at http://localhost:5001

### Option 2: Docker Deployment

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/orbit-bhyve-python-package.git
cd orbit-bhyve-python-package

# 2. Create .env file
cp env.example .env
# Edit .env with your credentials

# 3. Run with Docker Compose
docker-compose up -d
```

### Option 3: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install package
pip install -e .

# 3. Set up MQTT broker (Mosquitto)
# See setup_mqtt_broker.sh for details

# 4. Run gateway
python bhyve_mqtt_gateway.py

# 5. Run dashboard (in another terminal)
python start_mqtt_dashboard.py
```

## 📱 Using the Web Dashboard

1. **Open your browser** to `http://localhost:5001`
2. **View devices** - See all your Bhyve devices and their status
3. **Control watering** - Start/stop watering on specific zones
4. **Monitor status** - Real-time updates on device status

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BHYVE_USERNAME` | Your Bhyve account email | Required |
| `BHYVE_PASSWORD` | Your Bhyve account password | Required |
| `MQTT_BROKER` | MQTT broker address | localhost |
| `MQTT_PORT` | MQTT broker port | 1883 |
| `BHYVE_LOG_LEVEL` | Logging level | INFO |

### MQTT Topics

The package publishes device data to these MQTT topics:

- `bhyve/devices` - List of all devices
- `bhyve/device/{device_id}/status` - Device status
- `bhyve/device/{device_id}/details` - Device details
- `bhyve/device/{device_id}/zone/{zone}/info` - Zone information
- `bhyve/device/{device_id}/zone/{zone}/set` - Zone control commands

## 🐍 Python API Usage

```python
from orbit_bhyve import BhyveClient

# Create MQTT client
client = BhyveClient(
    mqtt_broker="localhost",
    mqtt_port=1883
)

# Connect to MQTT broker
await client.connect()

# Get devices
devices = client.get_devices()
print(f"Found {len(devices)} devices")

# Start watering
await client.start_watering("device_id", 1, 5)  # Zone 1 for 5 minutes

# Stop watering
await client.stop_watering("device_id")

# Disconnect
await client.disconnect()
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bhyve API    │    │  MQTT Broker     │    │  Web Dashboard  │
│   (WebSocket)   │◄──►│   (Mosquitto)    │◄──►│   (Flask)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│  Bhyve Gateway  │◄─────────────┘
                        │  (Python)       │
                        └─────────────────┘
```

## 🔍 Troubleshooting

### Common Issues

1. **No devices found**
   - Check your Bhyve credentials in .env file
   - Ensure your Bhyve account has devices
   - Check MQTT broker is running

2. **Connection failed**
   - Verify MQTT broker is running on localhost:1883
   - Check firewall settings
   - Ensure no port conflicts

3. **Authentication failed**
   - Verify BHYVE_USERNAME and BHYVE_PASSWORD are correct
   - Check if your Bhyve account is active

### Logs

- **Gateway logs**: Check terminal output
- **MQTT logs**: `mosquitto_sub -h localhost -t "#" -v`
- **Dashboard logs**: Check Flask output

## 📚 Advanced Usage

### Custom MQTT Configuration

```python
from orbit_bhyve import BhyveClient

client = BhyveClient(
    mqtt_broker="your-mqtt-broker.com",
    mqtt_port=8883,
    mqtt_username="mqtt_user",
    mqtt_password="mqtt_pass",
    use_tls=True
)
```

### Environment Variable Configuration

```bash
# Set all configuration via environment variables
export BHYVE_MQTT_BROKER="your-broker.com"
export BHYVE_MQTT_PORT="8883"
export BHYVE_MQTT_USERNAME="mqtt_user"
export BHYVE_MQTT_PASSWORD="mqtt_pass"
export BHYVE_MQTT_USE_TLS="true"
export BHYVE_LOG_LEVEL="DEBUG"

python -m orbit_bhyve
```

## 🤝 Support

- **Documentation**: [GitHub Repository](https://github.com/yourusername/orbit-bhyve-python-package)
- **Issues**: [GitHub Issues](https://github.com/yourusername/orbit-bhyve-python-package/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/orbit-bhyve-python-package/discussions)

## 📄 License

MIT License - see LICENSE file for details.
