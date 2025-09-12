#!/usr/bin/env python3
"""
MQTT Control Example for Orbit Bhyve

This example demonstrates how to use the MQTT client for both monitoring
and controlling Bhyve devices. It connects to an MQTT broker and provides
real-time device monitoring and control capabilities.
"""

import asyncio
import json
import os
import time
from dotenv import load_dotenv
from orbit_bhyve.mqtt_client import BhyveMQTTClient

# Load environment variables
load_dotenv()

async def mqtt_control_example():
    """Example of using MQTT client for Bhyve device control."""
    
    # MQTT configuration
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    
    print("🌱 Orbit Bhyve MQTT Control Example")
    print("=" * 50)
    print(f"🔧 MQTT Configuration:")
    print(f"   Broker: {mqtt_broker}:{mqtt_port}")
    print(f"   Username: {mqtt_username or 'None'}")
    print(f"   Password: {'***' if mqtt_password else 'None'}")
    print()
    
    # Create MQTT client
    client = BhyveMQTTClient(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        use_tls=False
    )
    
    # Set up event handlers
    def on_device_status(device_id, status):
        print(f"📊 Device {device_id} status: {json.dumps(status, indent=2)}")
    
    def on_device_details(device_id, details):
        print(f"📱 Device {device_id} details received")
        print(f"   Name: {details.get('name', 'Unknown')}")
        print(f"   Zones: {len(details.get('zones', {}))}")
    
    def on_watering_started(device_id, message):
        print(f"🌊 Device {device_id} started watering!")
        print(f"   Station: {message.get('current_station')}")
        print(f"   Duration: {message.get('run_time')} minutes")
        print(f"   Started at: {message.get('started_watering_station_at')}")
    
    def on_watering_completed(device_id, message):
        print(f"✅ Device {device_id} completed watering")
    
    def on_mode_changed(device_id, message):
        print(f"🔄 Device {device_id} mode changed to: {message.get('mode')}")
    
    def on_devices_list(device_ids):
        print(f"📋 Devices list: {device_ids}")
    
    # Register event handlers
    client.on_event('device_status', on_device_status)
    client.on_event('device_details', on_device_details)
    client.on_event('watering_started', on_watering_started)
    client.on_event('watering_completed', on_watering_completed)
    client.on_event('mode_changed', on_mode_changed)
    client.on_event('devices_list', on_devices_list)
    
    try:
        # Connect to MQTT broker
        print("🌐 Connecting to MQTT broker...")
        connected = await client.connect()
        
        if not connected:
            print("❌ Failed to connect to MQTT broker")
            print("💡 Make sure MQTT broker is running and accessible")
            return
        
        print("✅ Connected to MQTT broker")
        
        # Request device refresh
        print("\n📱 Requesting device refresh...")
        client.refresh_devices()
        
        # Wait for devices
        print("⏳ Waiting for device data...")
        await asyncio.sleep(10)
        
        # Get devices
        devices = client.get_devices()
        print(f"\n📊 Found {len(devices)} devices:")
        
        if not devices:
            print("❌ No devices found. Make sure the MQTT gateway is running.")
            print("💡 The MQTT gateway should be publishing device data to MQTT topics.")
            return
        
        for device_id, device_data in devices.items():
            print(f"  - {device_id}: {device_data.get('name', 'Unknown')}")
            print(f"    Mode: {client.get_device_mode(device_id)}")
            print(f"    Watering: {client.is_device_watering(device_id)}")
            if client.is_device_watering(device_id):
                print(f"    Station: {client.get_watering_station(device_id)}")
        
        # Interactive control loop
        print(f"\n🎮 Interactive Control Mode")
        print("Commands:")
        print("  start <device_id> <station> <minutes> - Start watering")
        print("  stop <device_id> - Stop watering")
        print("  status <device_id> - Show device status")
        print("  refresh - Refresh device data")
        print("  quit - Exit")
        print()
        
        while True:
            try:
                command = input("> ").strip().split()
                
                if not command:
                    continue
                
                if command[0] == "quit":
                    break
                elif command[0] == "start" and len(command) >= 4:
                    device_id = command[1]
                    station = int(command[2])
                    minutes = float(command[3])
                    
                    print(f"🌊 Starting watering: Device {device_id}, Station {station}, {minutes} minutes")
                    success = client.start_watering(device_id, station, minutes)
                    print(f"✅ Command sent: {success}")
                    
                elif command[0] == "stop" and len(command) >= 2:
                    device_id = command[1]
                    
                    print(f"🛑 Stopping watering: Device {device_id}")
                    success = client.stop_watering(device_id)
                    print(f"✅ Command sent: {success}")
                    
                elif command[0] == "status" and len(command) >= 2:
                    device_id = command[1]
                    
                    print(f"📊 Device {device_id} status:")
                    print(f"   Mode: {client.get_device_mode(device_id)}")
                    print(f"   Watering: {client.is_device_watering(device_id)}")
                    if client.is_device_watering(device_id):
                        print(f"   Station: {client.get_watering_station(device_id)}")
                    
                    device_data = client.get_device_status(device_id)
                    print(f"   Data: {json.dumps(device_data, indent=2)}")
                    
                elif command[0] == "refresh":
                    print("🔄 Refreshing device data...")
                    client.refresh_devices()
                    await asyncio.sleep(2)
                    
                else:
                    print("❌ Invalid command. Type 'quit' to exit.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n👋 Exiting...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("🔌 Disconnecting from MQTT broker...")
        await client.disconnect()
        print("✅ Disconnected")

if __name__ == "__main__":
    asyncio.run(mqtt_control_example())
