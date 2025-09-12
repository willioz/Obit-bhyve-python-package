#!/usr/bin/env python3
"""
Test the exact command format from JavaScript implementation
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from orbit_bhyve import BhyveClient, BhyveDevice

# Load environment variables
load_dotenv()

async def test_js_command_format():
    """Test the exact command format from JavaScript implementation."""
    username = os.getenv("BHYVE_USERNAME")
    password = os.getenv("BHYVE_PASSWORD")
    
    if not username or not password:
        print("❌ No credentials found in .env file")
        return
    
    try:
        client = BhyveClient(username=username, password=password)
        
        print("🔑 Authenticating...")
        await client.authenticate()
        print("✅ Authentication successful")
        
        print("🌐 Connecting to WebSocket...")
        await client.connect()
        print("✅ WebSocket connection successful")
        
        # Set up message logging
        def log_all_messages(data):
            print(f"📨 WebSocket Response: {json.dumps(data, indent=2)}")
        
        client.on_event("change_mode", log_all_messages)
        client.on_event("watering_in_progress_notification", log_all_messages)
        client.on_event("watering_complete", log_all_messages)
        client.on_event("device_idle", log_all_messages)
        
        # Get devices
        devices_data = await client.get_devices()
        if devices_data:
            device_id = devices_data[0]["id"]
            print(f"📱 Testing with device: {device_id}")
            
            # Test the EXACT command format from JavaScript
            print("\n🧪 Testing EXACT JavaScript command format...")
            
            # Command 1: Start watering (exact format from JavaScript)
            command1 = {
                "event": "change_mode",
                "device_id": device_id,
                "timestamp": "2025-09-12T19:30:00.000Z",
                "mode": "manual",
                "stations": [{"station": 1, "run_time": 1.0}]
            }
            
            print(f"Sending command 1: {json.dumps(command1, indent=2)}")
            await client.websocket.send(json.dumps(command1))
            
            print("⏳ Waiting 10 seconds for response...")
            await asyncio.sleep(10)
            
            # Command 2: Stop watering (exact format from JavaScript)
            command2 = {
                "event": "change_mode",
                "device_id": device_id,
                "timestamp": "2025-09-12T19:30:10.000Z",
                "mode": "manual",
                "stations": []
            }
            
            print(f"\nSending command 2: {json.dumps(command2, indent=2)}")
            await client.websocket.send(json.dumps(command2))
            
            print("⏳ Waiting 5 seconds for response...")
            await asyncio.sleep(5)
            
            # Command 3: Return to auto mode
            command3 = {
                "event": "change_mode",
                "device_id": device_id,
                "timestamp": "2025-09-12T19:30:15.000Z",
                "mode": "auto"
            }
            
            print(f"\nSending command 3: {json.dumps(command3, indent=2)}")
            await client.websocket.send(json.dumps(command3))
            
            print("⏳ Waiting 5 seconds for response...")
            await asyncio.sleep(5)
            
            print("\n✅ Test completed!")
        
        print("🔌 Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_js_command_format())
