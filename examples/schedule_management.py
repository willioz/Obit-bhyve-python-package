#!/usr/bin/env python3
"""
Orbit Bhyve Schedule Management Example

This example demonstrates how to manage irrigation schedules using the WebSocket client.
Note: Schedule management via API may be limited - schedules are typically managed
through the Bhyve mobile app. This example shows the WebSocket commands that would
be sent for schedule management.
"""

import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from orbit_bhyve import BhyveClient, BhyveDevice
from orbit_bhyve.exceptions import (
    BhyveError,
    BhyveConnectionError,
    BhyveAuthenticationError,
    BhyveDeviceError,
)

# Load environment variables
load_dotenv()


class ScheduleManager:
    """Schedule management helper class."""
    
    def __init__(self, username: str, password: str):
        """Initialize the schedule manager."""
        self.client = BhyveClient(username=username, password=password)
        self.devices = {}
        self.running = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.authenticate()
        await self.client.connect()
        await self.load_devices()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.disconnect()

    async def load_devices(self):
        """Load all devices."""
        devices_data = await self.client.get_devices()
        self.devices = {}
        
        for device_data in devices_data:
            device = BhyveDevice(device_data, self.client)
            self.devices[device.id] = device
        
        print(f"✓ Loaded {len(self.devices)} devices")

    def display_schedule(self, schedule: dict, device_name: str):
        """Display a schedule in a formatted way."""
        print(f"\n📅 Schedule: {schedule.get('name', 'Unnamed')}")
        print(f"   Device: {device_name}")
        print(f"   ID: {schedule.get('id', 'Unknown')}")
        print(f"   Enabled: {'✅ Yes' if schedule.get('enabled', False) else '❌ No'}")
        print(f"   Type: {schedule.get('program_type', 'Unknown')}")
        
        # Display frequency
        frequency = schedule.get('frequency', {})
        if frequency:
            print(f"   Frequency: {frequency.get('type', 'Unknown')}")
            if 'days' in frequency:
                days = frequency['days']
                if isinstance(days, list):
                    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                    selected_days = [day_names[i] for i in days if 0 <= i < 7]
                    print(f"   Days: {', '.join(selected_days)}")
                else:
                    print(f"   Days: {days}")
        
        # Display start time
        start_time = schedule.get('start_times', [])
        if start_time:
            print(f"   Start Times: {', '.join(start_time)}")
        
        # Display stations
        stations = schedule.get('stations', [])
        if stations:
            print(f"   Stations: {len(stations)} configured")
            for i, station in enumerate(stations[:3]):  # Show first 3
                print(f"     Station {station.get('station', i+1)}: {station.get('run_time', 0)} min")
            if len(stations) > 3:
                print(f"     ... and {len(stations) - 3} more")

    async def list_schedules(self, device_id: str = None):
        """List all schedules for a device or all devices."""
        if device_id:
            if device_id not in self.devices:
                print(f"❌ Device {device_id} not found")
                return
            
            device = self.devices[device_id]
            schedules = await device.get_schedules()
            
            print(f"\n📅 Schedules for {device.name}:")
            if schedules:
                for schedule in schedules:
                    self.display_schedule(schedule, device.name)
            else:
                print("   No schedules found (schedule data received via WebSocket events)")
        else:
            print("\n📅 All Schedules:")
            has_schedules = False
            for device in self.devices.values():
                schedules = await device.get_schedules()
                if schedules:
                    has_schedules = True
                    for schedule in schedules:
                        self.display_schedule(schedule, device.name)
            
            if not has_schedules:
                print("   No schedules found (schedule data received via WebSocket events)")
                print("   Note: Schedule management is primarily done through the Bhyve mobile app")
                print("   This example demonstrates WebSocket commands for schedule management")

    async def create_simple_schedule(self, device_id: str, name: str, station: int, 
                                   run_time_minutes: int, start_time: str = "06:00"):
        """Create a simple daily schedule."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        # Create a simple daily schedule
        schedule_data = {
            "name": name,
            "enabled": True,
            "program_type": "recurring",
            "frequency": {
                "type": "interval",
                "interval": 1,
                "days": [0, 1, 2, 3, 4, 5, 6]  # Every day
            },
            "start_times": [start_time],
            "stations": [
                {
                    "station": station,
                    "run_time": run_time_minutes,
                    "enabled": True
                }
            ]
        }
        
        try:
            success = await device.create_schedule(schedule_data)
            if success:
                print(f"✅ Created schedule '{name}' for {device.name}")
                return True
            else:
                print(f"❌ Failed to create schedule '{name}'")
                return False
        except Exception as e:
            print(f"❌ Error creating schedule: {e}")
            return False

    async def create_weekly_schedule(self, device_id: str, name: str, stations: list, 
                                   days: list, start_time: str = "06:00"):
        """Create a weekly schedule for specific days."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        # Create a weekly schedule
        schedule_data = {
            "name": name,
            "enabled": True,
            "program_type": "recurring",
            "frequency": {
                "type": "interval",
                "interval": 1,
                "days": days  # 0=Monday, 1=Tuesday, etc.
            },
            "start_times": [start_time],
            "stations": stations
        }
        
        try:
            success = await device.create_schedule(schedule_data)
            if success:
                print(f"✅ Created weekly schedule '{name}' for {device.name}")
                return True
            else:
                print(f"❌ Failed to create weekly schedule '{name}'")
                return False
        except Exception as e:
            print(f"❌ Error creating weekly schedule: {e}")
            return False

    async def update_schedule(self, device_id: str, program_id: str, updates: dict):
        """Update an existing schedule."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        try:
            success = await device.update_schedule(program_id, updates)
            if success:
                print(f"✅ Updated schedule {program_id}")
                return True
            else:
                print(f"❌ Failed to update schedule {program_id}")
                return False
        except Exception as e:
            print(f"❌ Error updating schedule: {e}")
            return False

    async def delete_schedule(self, device_id: str, program_id: str):
        """Delete a schedule."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        try:
            success = await device.delete_schedule(program_id)
            if success:
                print(f"✅ Deleted schedule {program_id}")
                return True
            else:
                print(f"❌ Failed to delete schedule {program_id}")
                return False
        except Exception as e:
            print(f"❌ Error deleting schedule: {e}")
            return False

    async def enable_schedule(self, device_id: str, program_id: str):
        """Enable a schedule."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        try:
            success = await device.enable_schedule(program_id)
            if success:
                print(f"✅ Enabled schedule {program_id}")
                return True
            else:
                print(f"❌ Failed to enable schedule {program_id}")
                return False
        except Exception as e:
            print(f"❌ Error enabling schedule: {e}")
            return False

    async def disable_schedule(self, device_id: str, program_id: str):
        """Disable a schedule."""
        if device_id not in self.devices:
            print(f"❌ Device {device_id} not found")
            return False

        device = self.devices[device_id]
        
        try:
            success = await device.disable_schedule(program_id)
            if success:
                print(f"✅ Disabled schedule {program_id}")
                return True
            else:
                print(f"❌ Failed to disable schedule {program_id}")
                return False
        except Exception as e:
            print(f"❌ Error disabling schedule: {e}")
            return False

    def display_devices(self):
        """Display all devices."""
        print("\n🌱 Available Devices:")
        for device in self.devices.values():
            print(f"   {device.id}: {device.name} ({device.type})")


async def main():
    """Main function demonstrating schedule management."""
    print("🌱 Orbit Bhyve Schedule Management Example")
    print("=" * 50)
    
    # Get credentials from environment
    username = os.getenv("BHYVE_USERNAME")
    password = os.getenv("BHYVE_PASSWORD")
    
    if not username or not password:
        print("❌ Please set BHYVE_USERNAME and BHYVE_PASSWORD environment variables")
        return
    
    try:
        async with ScheduleManager(username, password) as manager:
            # Display devices
            manager.display_devices()
            
            # List all schedules
            await manager.list_schedules()
            
            # Example: Create a simple daily schedule
            if manager.devices:
                device_id = list(manager.devices.keys())[0]
                device = manager.devices[device_id]
                
                print(f"\n🔧 Demonstrating schedule management commands for {device.name}...")
                print("Note: These are WebSocket commands - actual schedule management is typically done via the Bhyve mobile app")
                
                # Demonstrate creating a simple daily schedule
                print("\n📅 Sending WebSocket command to create daily schedule...")
                success = await manager.create_simple_schedule(
                    device_id=device_id,
                    name="Morning Watering",
                    station=1,
                    run_time_minutes=15,
                    start_time="06:00"
                )
                
                if success:
                    print("✅ WebSocket command sent successfully")
                else:
                    print("❌ WebSocket command failed - this may be expected if schedules are not supported via API")
                
                # Demonstrate creating a weekly schedule
                print("\n📅 Sending WebSocket command to create weekly schedule...")
                weekly_stations = [
                    {"station": 2, "run_time": 20, "enabled": True},
                    {"station": 3, "run_time": 25, "enabled": True}
                ]
                
                success = await manager.create_weekly_schedule(
                    device_id=device_id,
                    name="Weekend Watering",
                    stations=weekly_stations,
                    days=[5, 6],  # Saturday and Sunday
                    start_time="08:00"
                )
                
                if success:
                    print("✅ WebSocket command sent successfully")
                else:
                    print("❌ WebSocket command failed - this may be expected if schedules are not supported via API")
                
                # Request schedules via WebSocket
                print("\n📅 Requesting schedules via WebSocket...")
                await manager.list_schedules(device_id)
                
                print("\n✅ Schedule management examples completed!")
                
    except BhyveAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
    except BhyveConnectionError as e:
        print(f"❌ Connection failed: {e}")
    except BhyveError as e:
        print(f"❌ Bhyve error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    import os
    asyncio.run(main())
