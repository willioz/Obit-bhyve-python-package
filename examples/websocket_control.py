#!/usr/bin/env python3
"""
WebSocket-based control example for the Orbit Bhyve Python package.

This example demonstrates real-time control and monitoring using WebSocket connections:
1. Real-time device monitoring
2. Live watering control
3. Event-driven programming
4. Real-time status updates
"""

import os
import sys
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from orbit_bhyve import BhyveClient, BhyveDevice
from orbit_bhyve.exceptions import (
    BhyveError,
    BhyveConnectionError,
    BhyveAuthenticationError,
)

# Load environment variables from .env file
load_dotenv()


class WebSocketBhyveController:
    """WebSocket-based controller for Bhyve devices."""

    def __init__(self, username: str, password: str):
        """Initialize the WebSocket controller."""
        self.client = BhyveClient(username=username, password=password)
        self.devices = {}
        self.running = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.authenticate()
        await self.client.connect()
        await self.setup_event_handlers()
        await self.load_devices()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()

    async def setup_event_handlers(self):
        """Set up WebSocket event handlers."""
        # Handle watering events
        self.client.on_event("watering_in_progress_notification", self.on_watering_started)
        self.client.on_event("device_idle", self.on_device_idle)
        self.client.on_event("change_mode", self.on_mode_changed)
        self.client.on_event("device_connected", self.on_device_connected)

    async def load_devices(self):
        """Load all devices."""
        devices_data = await self.client.get_devices()
        self.devices = {}
        
        for device_data in devices_data:
            device = BhyveDevice(device_data, self.client)
            self.devices[device.id] = device
        
        print(f"✓ Loaded {len(self.devices)} devices")

    async def on_watering_started(self, data):
        """Handle watering started event."""
        device_id = data.get("device_id")
        if device_id in self.devices:
            device = self.devices[device_id]
            station = data.get("current_station")
            duration = data.get("total_run_time_sec", 0)
            print(f"🌊 {device.name}: Started watering station {station} for {duration} seconds")

    async def on_device_idle(self, data):
        """Handle device idle event."""
        device_id = data.get("device_id")
        if device_id in self.devices:
            device = self.devices[device_id]
            print(f"💤 {device.name}: Device is now idle")

    async def on_mode_changed(self, data):
        """Handle mode change event."""
        device_id = data.get("device_id")
        if device_id in self.devices:
            device = self.devices[device_id]
            mode = data.get("mode")
            print(f"🔄 {device.name}: Mode changed to {mode}")

    async def on_device_connected(self, data):
        """Handle device connected event."""
        device_id = data.get("device_id")
        if device_id in self.devices:
            device = self.devices[device_id]
            print(f"📡 {device.name}: Device connected")

    def display_devices(self):
        """Display all devices with current status."""
        print("\n" + "="*80)
        print("🌱 ORBIT BHYVE DEVICES (WebSocket)")
        print("="*80)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for device in self.devices.values():
            self.display_device_status(device)
            print()

    def display_device_status(self, device: BhyveDevice):
        """Display status for a single device."""
        print(f"📱 {device.name} ({device.id})")
        print(f"   Type: {device.type}")
        print(f"   Status: {'🟢 Online' if device.is_online else '🔴 Offline'}")
        print(f"   Mode: {device.run_mode.upper()}")
        
        # Watering status
        watering_info = device.get_current_watering_info()
        if watering_info['is_watering']:
            station = watering_info['current_station']
            remaining = watering_info['time_remaining']
            print(f"   💧 WATERING: Station {station} - {remaining}s remaining")
            if watering_info['started_at']:
                print(f"   ⏱️  Started: {watering_info['started_at']}")
        else:
            print(f"   💧 Watering: Idle")
        
        # Device info
        if device.firmware_version:
            print(f"   🔧 Firmware: {device.firmware_version}")
        if device.hardware_version:
            print(f"   🔧 Hardware: {device.hardware_version}")
        if device.num_stations:
            print(f"   🌿 Stations: {device.num_stations}")
        
        # WebSocket status
        if device.last_websocket_update:
            print(f"   📡 Last Update: {device.last_websocket_update.strftime('%H:%M:%S')}")

    async def start_watering(self, device_id: str, station: int, duration_seconds: int = 300):
        """Start watering a specific station."""
        if device_id not in self.devices:
            print(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        print(f"🌊 Starting watering on {device.name} station {station} for {duration_seconds} seconds...")
        
        success = await device.start_watering_station(station, duration_seconds)
        if success:
            print(f"✓ Command sent successfully")
        else:
            print(f"✗ Failed to send command")
        
        return success

    async def stop_watering(self, device_id: str):
        """Stop all watering on a device."""
        if device_id not in self.devices:
            print(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        print(f"🛑 Stopping watering on {device.name}...")
        
        success = await device.stop_watering()
        if success:
            print(f"✓ Command sent successfully")
        else:
            print(f"✗ Failed to send command")
        
        return success

    async def set_device_mode(self, device_id: str, mode: str):
        """Set device mode."""
        if device_id not in self.devices:
            print(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        print(f"🔄 Setting {device.name} to {mode} mode...")
        
        success = await device.set_mode(mode)
        if success:
            print(f"✓ Command sent successfully")
        else:
            print(f"✗ Failed to send command")
        
        return success

    async def monitor_devices(self, duration_minutes: int = 5):
        """Monitor devices for a specified duration."""
        print(f"\n🔍 MONITORING DEVICES FOR {duration_minutes} MINUTES")
        print("-" * 60)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            # Refresh device data
            await self.load_devices()
            
            # Display current status
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{current_time}] Device Status:")
            
            for device in self.devices.values():
                watering_info = device.get_current_watering_info()
                if watering_info['is_watering']:
                    station = watering_info['current_station']
                    remaining = watering_info['time_remaining']
                    print(f"  {device.name}: Station {station} - {remaining}s remaining")
                else:
                    print(f"  {device.name}: Idle")
            
            await asyncio.sleep(30)  # Check every 30 seconds

    async def interactive_control(self):
        """Run interactive control session."""
        print("\n🎮 INTERACTIVE WEBSOCKET CONTROL")
        print("Commands: list, start <device_id> <station> [duration], stop <device_id>, mode <device_id> <mode>, monitor [minutes], quit")
        print("-" * 80)
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == "quit" or command == "q":
                    break
                elif command == "list":
                    self.display_devices()
                elif command.startswith("start "):
                    parts = command.split()
                    if len(parts) >= 3:
                        device_id = parts[1]
                        station = int(parts[2])
                        duration = int(parts[3]) if len(parts) > 3 else 300
                        await self.start_watering(device_id, station, duration)
                    else:
                        print("Usage: start <device_id> <station> [duration]")
                elif command.startswith("stop "):
                    device_id = command.split(" ", 1)[1]
                    await self.stop_watering(device_id)
                elif command.startswith("mode "):
                    parts = command.split()
                    if len(parts) >= 3:
                        device_id = parts[1]
                        mode = parts[2]
                        await self.set_device_mode(device_id, mode)
                    else:
                        print("Usage: mode <device_id> <mode>")
                elif command.startswith("monitor"):
                    parts = command.split()
                    duration = int(parts[1]) if len(parts) > 1 else 5
                    await self.monitor_devices(duration)
                else:
                    print("Unknown command. Try: list, start, stop, mode, monitor, quit")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Main function for WebSocket control example."""
    print("🌱 Orbit Bhyve WebSocket Controller")
    print("===================================")

    # Get credentials from environment
    username = os.getenv('BHYVE_USERNAME')
    password = os.getenv('BHYVE_PASSWORD')

    if not username or not password:
        print("Error: BHYVE_USERNAME and BHYVE_PASSWORD must be set in environment")
        print("Create a .env file with your credentials or set environment variables")
        sys.exit(1)

    try:
        async with WebSocketBhyveController(username, password) as controller:
            # Display initial device status
            controller.display_devices()
            
            # Run interactive control
            await controller.interactive_control()

    except BhyveAuthenticationError as e:
        print(f"Authentication error: {e}")
        sys.exit(1)
    except BhyveConnectionError as e:
        print(f"Connection error: {e}")
        sys.exit(1)
    except BhyveError as e:
        print(f"Bhyve error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
