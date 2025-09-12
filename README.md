# Orbit Bhyve Python Package

A comprehensive Python package for controlling and managing Orbit Bhyve irrigation controllers. This package provides an easy-to-use interface for interacting with Bhyve devices through their API and local network communication.

[![PyPI version](https://badge.fury.io/py/orbit-bhyve.svg)](https://badge.fury.io/py/orbit-bhyve)
[![Python Support](https://img.shields.io/pypi/pyversions/orbit-bhyve.svg)](https://pypi.org/project/orbit-bhyve/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🌐 **WebSocket Support**: Real-time communication with instant control and live updates
- 📱 **Device Management**: Discover and manage multiple Bhyve irrigation controllers
- 💧 **Live Watering Control**: Start and stop watering with real-time feedback
- 📅 **Schedule Management**: WebSocket commands for schedule management (may be limited via API)
- 📊 **Real-time Monitoring**: Live status updates and watering progress tracking
- 🎮 **Interactive Control**: Command-line interface with live event handling
- ⚡ **Event-Driven**: React to device events as they happen
- 🔧 **Device Management**: Control device modes and settings in real-time
- 📡 **Connection Monitoring**: Track device connectivity and status changes
- 🔐 **Secure Authentication**: Support for both username/password and token-based authentication
- 🖥️ **CLI Interface**: Command-line tool for easy device management
- 📊 **Comprehensive API**: Full-featured Python API for integration into your projects
- 🧪 **Well Tested**: Comprehensive test suite with high coverage

## Installation

### From PyPI (Recommended)

```bash
pip install orbit-bhyve
```

### From Source

```bash
git clone https://github.com/yourusername/orbit-bhyve-python-package.git
cd orbit-bhyve-python-package
pip install -e .
```

## Quick Start

### Basic Usage

```python
from orbit_bhyve import BhyveClient

# Initialize client with your credentials
client = BhyveClient(username="your@email.com", password="yourpassword")

# Authenticate
client.authenticate()

# Get all devices
devices = client.get_devices()
print(f"Found {len(devices)} devices")

# Get a specific device
device = client.get_device("DEVICE_ID")
if device:
    print(f"Device: {device.name} - Status: {device.status}")

# Start watering a valve for 10 minutes
client.start_watering("DEVICE_ID", "VALVE_ID", duration_minutes=10)

# Stop watering
client.stop_watering("DEVICE_ID", "VALVE_ID")

# Close the client
client.close()
```

### Using Environment Variables

For better security, you can store your credentials in a `.env` file:

1. Create a `.env` file in your project directory:
```bash
# .env file
BHYVE_USERNAME=your@email.com
BHYVE_PASSWORD=yourpassword
```

2. Use the examples that automatically load from `.env`:
```python
from dotenv import load_dotenv
import os
from orbit_bhyve import BhyveClient

# Load environment variables from .env file
load_dotenv()

# Initialize client with credentials from environment
client = BhyveClient(username=os.getenv('BHYVE_USERNAME'), password=os.getenv('BHYVE_PASSWORD'))
client.authenticate()
# ... rest of your code
```

The included example files (`examples/basic_usage.py`, `examples/smart_watering.py`, etc.) automatically load credentials from `.env` files.

**Quick Setup**: Run the included setup script to create your `.env` file:
```bash
python setup_env.py
```

### WebSocket Real-time Control (NEW!)

For real-time control and monitoring, use the WebSocket client:

```python
import asyncio
from orbit_bhyve import BhyveClient, BhyveDevice

async def main():
    # Initialize WebSocket client
    client = BhyveClient(username="your@email.com", password="yourpassword")
    
    # Authenticate and connect
    await client.authenticate()
    await client.connect()
    
    # Set up event handlers for real-time updates
    def on_watering_started(data):
        print(f"🌊 Watering started: {data}")
    
    client.on_event("watering_in_progress_notification", on_watering_started)
    
    # Get devices
    devices = await client.get_devices()
    print(f"Found {len(devices)} devices")
    
    # Start watering station 1 for 5 minutes
    await client.start_watering("DEVICE_ID", station=1, duration_seconds=300)
    
    # Stop all watering
    await client.stop_watering("DEVICE_ID")
    
    # Set device mode
    await client.set_device_mode("DEVICE_ID", "manual")
    
    # Schedule management (WebSocket commands - may be limited via API)
    schedules = await client.get_schedules("DEVICE_ID")
    print(f"Requested schedules for device (data received via WebSocket events)")
    
    # Create a new schedule (WebSocket command)
    schedule_data = {
        "name": "Morning Watering",
        "enabled": True,
        "program_type": "recurring",
        "frequency": {
            "type": "interval",
            "interval": 1,
            "days": [0, 1, 2, 3, 4, 5, 6]  # Every day
        },
        "start_times": ["06:00"],
        "stations": [
            {
                "station": 1,
                "run_time": 15,
                "enabled": True
            }
        ]
    }
    await client.create_schedule("DEVICE_ID", schedule_data)
    
    # Close connection
    await client.close()

# Run the async function
asyncio.run(main())
```

### Using Context Manager

```python
from orbit_bhyve import BhyveClient

with BhyveClient(username="your@email.com", password="yourpassword") as client:
    client.authenticate()
    devices = client.get_devices()
    
    for device in devices:
        print(f"Device: {device.name}")
        if device.is_online:
            print("  Status: Online")
            for valve in device.get_valves():
                print(f"  Valve: {valve['name']} (ID: {valve['id']})")
        else:
            print("  Status: Offline")
```

### Command Line Interface

```bash
# List all devices
orbit-bhyve list-devices --username your@email.com --password yourpassword

# Get device information
orbit-bhyve device-info --username your@email.com --password yourpassword --device-id DEVICE123

# Start watering
orbit-bhyve start-watering --username your@email.com --password yourpassword --device-id DEVICE123 --valve-id VALVE1 --duration 15

# Stop watering
orbit-bhyve stop-watering --username your@email.com --password yourpassword --device-id DEVICE123 --valve-id VALVE1

# List schedules
orbit-bhyve list-schedules --username your@email.com --password yourpassword

# Get weather information
orbit-bhyve weather --username your@email.com --password yourpassword
```

## API Reference

### BhyveClient

The main client class for interacting with Bhyve devices.

#### Methods

- `authenticate()`: Authenticate with the Bhyve API
- `connect()`: Connect to WebSocket for real-time control
- `disconnect()`: Disconnect from WebSocket
- `get_devices()`: Get all devices associated with the account
- `start_watering(device_id, station, duration_seconds)`: Start watering a station
- `stop_watering(device_id)`: Stop all watering on a device
- `set_device_mode(device_id, mode)`: Set device run mode (auto, manual, off)
- `get_schedules(device_id)`: Get all schedules for a device
- `create_schedule(device_id, schedule_data)`: Create a new schedule
- `update_schedule(device_id, program_id, schedule_data)`: Update an existing schedule
- `delete_schedule(device_id, program_id)`: Delete a schedule
- `enable_schedule(device_id, program_id)`: Enable a schedule
- `disable_schedule(device_id, program_id)`: Disable a schedule
- `on_event(event_type, handler)`: Register event handlers for real-time updates

### BhyveDevice

Represents an individual Bhyve irrigation controller.

#### Properties

- `id`: Device ID
- `name`: Device name
- `type`: Device type
- `status`: Current device status
- `battery_level`: Battery level percentage (if applicable)
- `signal_strength`: Signal strength (if applicable)
- `last_seen`: Last time the device was seen
- `is_online`: Whether the device is currently online

#### Methods

- `get_valves()`: Get all valves on this device
- `get_schedules()`: Get all schedules for this device
- `create_schedule(schedule_data)`: Create a new schedule
- `update_schedule(program_id, schedule_data)`: Update an existing schedule
- `delete_schedule(program_id)`: Delete a schedule
- `enable_schedule(program_id)`: Enable a schedule
- `disable_schedule(program_id)`: Disable a schedule
- `start_watering_station(station, duration_seconds)`: Start watering a station
- `stop_watering()`: Stop all watering on this device
- `set_mode(mode)`: Set device run mode (auto, manual, off)
- `get_device_info()`: Get comprehensive device information

## Examples

### Smart Watering Based on Weather

```python
from orbit_bhyve import BhyveClient
import time

def smart_watering():
    with BhyveClient(username="your@email.com", password="yourpassword") as client:
        client.authenticate()
        
        # Get weather data
        weather = client.get_weather_data()
        precipitation_chance = weather.get('precipitation_chance', 0)
        
        # Only water if precipitation chance is low
        if precipitation_chance < 30:
            devices = client.get_devices()
            for device in devices:
                if device.is_online:
                    for valve in device.get_valves():
                        # Water for 15 minutes
                        client.start_watering(device.id, valve['id'], 15)
                        print(f"Started watering {valve['name']} on {device.name}")
                        time.sleep(1)  # Small delay between valves
        else:
            print(f"High precipitation chance ({precipitation_chance}%), skipping watering")

smart_watering()
```

### Schedule Management

```python
import asyncio
from orbit_bhyve import BhyveClient, BhyveDevice

async def manage_schedules():
    client = BhyveClient(username="your@email.com", password="yourpassword")
    
    try:
        await client.authenticate()
        await client.connect()
        
        # Get devices
        devices = await client.get_devices()
        device = BhyveDevice(devices[0], client) if devices else None
        
        if device:
            # Get existing schedules
            schedules = await device.get_schedules()
            print(f"Found {len(schedules)} schedules")
            
            # Create a new daily schedule
            schedule_data = {
                "name": "Morning Watering",
                "enabled": True,
                "program_type": "recurring",
                "frequency": {
                    "type": "interval",
                    "interval": 1,
                    "days": [0, 1, 2, 3, 4, 5, 6]  # Every day
                },
                "start_times": ["06:00"],
                "stations": [
                    {
                        "station": 1,
                        "run_time": 15,
                        "enabled": True
                    }
                ]
            }
            
            success = await device.create_schedule(schedule_data)
            if success:
                print("✅ Schedule created successfully")
            else:
                print("❌ Failed to create schedule")
            
            # Create a weekly schedule for weekends
            weekend_schedule = {
                "name": "Weekend Watering",
                "enabled": True,
                "program_type": "recurring",
                "frequency": {
                    "type": "interval",
                    "interval": 1,
                    "days": [5, 6]  # Saturday and Sunday
                },
                "start_times": ["08:00"],
                "stations": [
                    {
                        "station": 2,
                        "run_time": 20,
                        "enabled": True
                    },
                    {
                        "station": 3,
                        "run_time": 25,
                        "enabled": True
                    }
                ]
            }
            
            await device.create_schedule(weekend_schedule)
            
            # List all schedules
            schedules = await device.get_schedules()
            for schedule in schedules:
                print(f"📅 {schedule.get('name')} - {'Enabled' if schedule.get('enabled') else 'Disabled'}")
                
    finally:
        await client.disconnect()

# Run the async function
asyncio.run(manage_schedules())
```

### Device Monitoring

```python
from orbit_bhyve import BhyveClient
import time

def monitor_devices():
    with BhyveClient(username="your@email.com", password="yourpassword") as client:
        client.authenticate()
        
        while True:
            devices = client.get_devices()
            print(f"\n--- Device Status ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
            
            for device in devices:
                status = "🟢 Online" if device.is_online else "🔴 Offline"
                battery = f" ({device.battery_level}%)" if device.battery_level else ""
                print(f"{device.name}: {status}{battery}")
                
                if device.is_online:
                    for valve in device.get_valves():
                        print(f"  └─ Valve: {valve['name']}")
            
            time.sleep(60)  # Check every minute

# Uncomment to run monitoring
# monitor_devices()
```

## Error Handling

The package includes comprehensive error handling with custom exceptions:

```python
from orbit_bhyve import BhyveClient
from orbit_bhyve.exceptions import BhyveError, BhyveConnectionError, BhyveAuthenticationError

try:
    client = BhyveClient(username="your@email.com", password="yourpassword")
    client.authenticate()
    devices = client.get_devices()
except BhyveAuthenticationError:
    print("Authentication failed. Please check your credentials.")
except BhyveConnectionError:
    print("Connection failed. Please check your internet connection.")
except BhyveError as e:
    print(f"Bhyve error: {e}")
```

## Development

### Setting up Development Environment

```bash
git clone https://github.com/yourusername/orbit-bhyve-python-package.git
cd orbit-bhyve-python-package
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black orbit_bhyve/
flake8 orbit_bhyve/
```

### Type Checking

```bash
mypy orbit_bhyve/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Orbit for creating the Bhyve irrigation controllers
- The Python community for excellent libraries and tools
- Contributors and users who help improve this package

## Support

If you encounter any issues or have questions, please:

1. Check the [documentation](https://github.com/yourusername/orbit-bhyve-python-package#readme)
2. Search existing [issues](https://github.com/yourusername/orbit-bhyve-python-package/issues)
3. Create a new issue with detailed information about your problem

## Changelog

### v0.1.0 (2024-01-XX)
- Initial release
- Basic device management functionality
- Valve control (start/stop watering)
- Schedule management
- Weather data integration
- Command-line interface
- Comprehensive error handling
- Full test coverage
