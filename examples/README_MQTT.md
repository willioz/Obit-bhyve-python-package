# MQTT Support for Orbit Bhyve

This package now includes comprehensive MQTT support for both monitoring and controlling Bhyve devices. The MQTT implementation is based on the analysis of the JavaScript `bhyve-mqtt` project and provides real-time device monitoring and control capabilities.

## 🌟 Features

- **Real-time Monitoring**: Receive live updates about device status, watering events, and mode changes
- **Device Control**: Start and stop watering on specific stations
- **MQTT Dashboard**: Web-based dashboard for monitoring and control
- **Event-driven Architecture**: Subscribe to specific device events
- **Automatic Reconnection**: Robust connection handling with automatic reconnection

## 📋 Prerequisites

1. **MQTT Broker**: You need a running MQTT broker (e.g., Mosquitto, Eclipse Mosquitto, or cloud-based)
2. **Bhyve MQTT Gateway**: The JavaScript `bhyve-mqtt` gateway must be running to bridge between Bhyve API and MQTT

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up MQTT Broker

#### Option A: Local MQTT Broker (Mosquitto)

```bash
# Install Mosquitto
sudo apt-get install mosquitto mosquitto-clients

# Start Mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

#### Option B: Docker MQTT Broker

```bash
docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### 3. Set Up Bhyve MQTT Gateway

The MQTT functionality requires the JavaScript `bhyve-mqtt` gateway to be running. This gateway connects to the Bhyve API and publishes device data to MQTT topics.

```bash
# Clone the bhyve-mqtt project
git clone https://github.com/billchurch/bhyve-mqtt.git
cd bhyve-mqtt/app

# Install dependencies
npm install

# Configure environment variables
cp .env-sample .env
# Edit .env with your Bhyve credentials and MQTT broker settings

# Start the gateway
npm start
```

### 4. Configure Environment Variables

Create a `.env` file with your MQTT broker settings:

```env
# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password

# Bhyve Credentials (for the gateway)
BHYVE_USERNAME=your_email@example.com
BHYVE_PASSWORD=your_password
```

## 📖 Usage Examples

### Basic MQTT Client

```python
import asyncio
from orbit_bhyve.mqtt_client import BhyveMQTTClient

async def main():
    # Create MQTT client
    client = BhyveMQTTClient(
        mqtt_broker="localhost",
        mqtt_port=1883,
        mqtt_username="your_username",
        mqtt_password="your_password"
    )
    
    # Set up event handlers
    def on_watering_started(device_id, message):
        print(f"Device {device_id} started watering!")
    
    client.on_event('watering_started', on_watering_started)
    
    # Connect and start monitoring
    await client.connect()
    
    # Start watering
    client.start_watering("device_id", 1, 5.0)  # Station 1, 5 minutes
    
    # Keep running
    await asyncio.sleep(60)
    
    # Stop watering
    client.stop_watering("device_id")
    
    await client.disconnect()

asyncio.run(main())
```

### MQTT Dashboard

Start the MQTT-based web dashboard:

```bash
python start_mqtt_dashboard.py
```

Then open your browser to `http://localhost:5001`

### Interactive Control Example

```bash
python examples/mqtt_control_example.py
```

## 🔧 MQTT Topics

The MQTT implementation uses the following topic structure:

### Status Topics
- `bhyve/online` - Gateway online status
- `bhyve/alive` - Keep-alive messages
- `bhyve/devices` - List of all device IDs

### Device Topics
- `bhyve/device/{device_id}/status` - Device status updates
- `bhyve/device/{device_id}/details` - Device configuration
- `bhyve/device/{device_id}/message` - Real-time device messages
- `bhyve/device/{device_id}/zone/{station}` - Zone information

### Control Topics
- `bhyve/device/{device_id}/zone/{station}/set` - Control specific zone
- `bhyve/device/refresh` - Request device refresh

## 📡 Event Types

The MQTT client supports the following event types:

- `device_status` - Device status updates
- `device_details` - Device configuration changes
- `device_message` - Real-time device messages
- `watering_started` - Watering started event
- `watering_completed` - Watering completed event
- `mode_changed` - Device mode changes
- `devices_list` - List of available devices

## 🎮 Control Commands

### Start Watering
```python
client.start_watering(device_id, station, duration_minutes)
```

### Stop Watering
```python
client.stop_watering(device_id)
```

### Refresh Devices
```python
client.refresh_devices()
```

### Check Device Status
```python
is_watering = client.is_device_watering(device_id)
mode = client.get_device_mode(device_id)
station = client.get_watering_station(device_id)
```

## 🔍 Monitoring

### Real-time Status Updates
```python
def on_device_status(device_id, status):
    print(f"Device {device_id}: {status}")

client.on_event('device_status', on_device_status)
```

### Watering Events
```python
def on_watering_started(device_id, message):
    print(f"Started watering station {message['current_station']}")

def on_watering_completed(device_id, message):
    print("Watering completed")

client.on_event('watering_started', on_watering_started)
client.on_event('watering_completed', on_watering_completed)
```

## 🛠️ Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Check if MQTT broker is running
   - Verify broker address and port
   - Check authentication credentials

2. **No Device Data**
   - Ensure the `bhyve-mqtt` gateway is running
   - Check if gateway is connected to Bhyve API
   - Verify MQTT topic subscriptions

3. **Commands Not Working**
   - Check if device is in the correct mode
   - Verify station numbers are valid
   - Check MQTT broker logs for errors

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔗 Integration Examples

### Home Assistant
The MQTT topics are compatible with Home Assistant's MQTT integration:

```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "Bhyve Device Status"
      state_topic: "bhyve/device/DEVICE_ID/status"
      value_template: "{{ value_json.status }}"
  
  switch:
    - name: "Bhyve Watering"
      state_topic: "bhyve/device/DEVICE_ID/status"
      command_topic: "bhyve/device/DEVICE_ID/zone/1/set"
      payload_on: '{"state": "ON", "time": 5}'
      payload_off: '{"state": "OFF"}'
```

### Node-RED
Use the MQTT nodes to connect to Bhyve devices:

1. Add MQTT In node for status updates
2. Add MQTT Out node for control commands
3. Configure topics according to the structure above

## 📚 Additional Resources

- [bhyve-mqtt GitHub Repository](https://github.com/billchurch/bhyve-mqtt)
- [MQTT Protocol Specification](https://mqtt.org/mqtt-specification/)
- [Eclipse Mosquitto Documentation](https://mosquitto.org/documentation/)

## 🤝 Contributing

Contributions to the MQTT functionality are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This MQTT implementation is part of the orbit-bhyve-python-package and follows the same license terms.
