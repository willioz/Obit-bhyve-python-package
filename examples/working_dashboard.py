#!/usr/bin/env python3
"""
Working Orbit Bhyve Web Dashboard

A Flask web interface that maintains a persistent WebSocket connection.
"""

import asyncio
import json
import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from orbit_bhyve import BhyveClient, BhyveDevice
from orbit_bhyve.exceptions import BhyveError, BhyveConnectionError, BhyveAuthenticationError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'bhyve-dashboard-secret-key'

# Global variables
bhyve_client = None
devices = {}
device_data = {}
last_update = None
connection_status = "disconnected"
websocket_task = None

def get_credentials():
    """Get credentials from environment variables."""
    username = os.getenv("BHYVE_USERNAME")
    password = os.getenv("BHYVE_PASSWORD")
    
    if not username or not password:
        return None, None
    
    return username, password

async def maintain_websocket_connection():
    """Maintain the WebSocket connection and handle messages."""
    global bhyve_client, devices, device_data, last_update, connection_status
    
    while True:
        try:
            if not bhyve_client or not bhyve_client.connected:
                print("🔌 WebSocket disconnected, attempting to reconnect...")
                await asyncio.sleep(5)
                continue
            
            # Keep the connection alive by sending a ping
            await bhyve_client.websocket.ping()
            await asyncio.sleep(30)  # Ping every 30 seconds
            
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            connection_status = "disconnected"
            await asyncio.sleep(5)

async def connect_to_bhyve():
    """Connect to Bhyve WebSocket and load devices."""
    global bhyve_client, devices, device_data, last_update, connection_status, websocket_task
    
    username, password = get_credentials()
    if not username or not password:
        connection_status = "no_credentials"
        return False
    
    try:
        print(f"🔐 Connecting with username: {username}")
        bhyve_client = BhyveClient(username=username, password=password)
        
        # Authenticate
        print("🔑 Authenticating...")
        await bhyve_client.authenticate()
        connection_status = "authenticated"
        print("✅ Authentication successful")
        
        # Connect to WebSocket
        print("🌐 Connecting to WebSocket...")
        await bhyve_client.connect()
        connection_status = "connected"
        print("✅ WebSocket connection successful")
        
        # Set up event handlers
        def on_watering_update(data):
            global device_data, last_update
            device_id = data.get('device_id')
            if device_id and device_id in devices:
                device_data[device_id] = devices[device_id].get_device_info()
                last_update = datetime.now()
                print(f"🔄 Updated device {device_id}")
        
        bhyve_client.on_event("watering_in_progress_notification", on_watering_update)
        bhyve_client.on_event("device_idle", on_watering_update)
        bhyve_client.on_event("change_mode", on_watering_update)
        
        # Load devices
        print("📱 Loading devices...")
        devices_data = await bhyve_client.get_devices()
        devices = {}
        device_data = {}
        
        for device_info in devices_data:
            device = BhyveDevice(device_info, bhyve_client)
            devices[device.id] = device
            device_data[device.id] = device.get_device_info()
            print(f"  - {device.name} ({device.id})")
        
        last_update = datetime.now()
        print(f"✅ Connected to Bhyve and loaded {len(devices)} devices")
        
        # Start the WebSocket maintenance task
        websocket_task = asyncio.create_task(maintain_websocket_connection())
        
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Bhyve: {e}")
        import traceback
        traceback.print_exc()
        connection_status = f"error: {str(e)}"
        return False

def sync_connect():
    """Synchronous wrapper for connection."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(connect_to_bhyve())
    finally:
        loop.close()

def sync_watering_command(device_id, station, duration):
    """Synchronous wrapper for watering command."""
    if not bhyve_client or not bhyve_client.connected:
        return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            bhyve_client.start_watering(device_id, station, duration)
        )
    finally:
        loop.close()

def sync_stop_watering(device_id):
    """Synchronous wrapper for stop watering command."""
    if not bhyve_client or not bhyve_client.connected:
        return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            bhyve_client.stop_watering(device_id)
        )
    finally:
        loop.close()

def sync_set_mode(device_id, mode):
    """Synchronous wrapper for set mode command."""
    if not bhyve_client or not bhyve_client.connected:
        return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            bhyve_client.set_device_mode(device_id, mode)
        )
    finally:
        loop.close()

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html', 
                         devices=device_data, 
                         connection_status=connection_status,
                         last_update=last_update)

@app.route('/api/devices')
def api_devices():
    """API endpoint to get device data."""
    return jsonify({
        'devices': device_data,
        'connection_status': connection_status,
        'last_update': last_update.isoformat() if last_update else None
    })

@app.route('/api/connect', methods=['POST'])
def api_connect():
    """API endpoint to connect to Bhyve."""
    global connection_status
    
    if connection_status == "connected":
        return jsonify({'success': True, 'message': 'Already connected'})
    
    try:
        success = sync_connect()
        if success:
            return jsonify({'success': True, 'message': 'Connected successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to connect'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/device/<device_id>/start_watering', methods=['POST'])
def api_start_watering(device_id):
    """API endpoint to start watering a station."""
    if not bhyve_client or connection_status != "connected":
        return jsonify({'success': False, 'error': 'Not connected to Bhyve'}), 400
    
    data = request.get_json()
    station = data.get('station')
    duration = data.get('duration', 300)  # Default 5 minutes
    
    if not station:
        return jsonify({'success': False, 'error': 'Station number required'}), 400
    
    try:
        print(f"🌊 Starting watering: Device {device_id}, Station {station}, Duration {duration}s")
        result = sync_watering_command(device_id, station, duration)
        
        if result:
            print(f"✅ Watering command sent successfully")
            return jsonify({'success': True, 'message': f'Started watering station {station}'})
        else:
            print(f"❌ Watering command failed")
            return jsonify({'success': False, 'error': 'Failed to start watering'})
            
    except Exception as e:
        print(f"❌ Error starting watering: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<device_id>/stop_watering', methods=['POST'])
def api_stop_watering(device_id):
    """API endpoint to stop all watering on a device."""
    if not bhyve_client or connection_status != "connected":
        return jsonify({'success': False, 'error': 'Not connected to Bhyve'}), 400
    
    try:
        print(f"🛑 Stopping watering: Device {device_id}")
        result = sync_stop_watering(device_id)
        
        if result:
            print(f"✅ Stop watering command sent successfully")
            return jsonify({'success': True, 'message': 'Stopped all watering'})
        else:
            print(f"❌ Stop watering command failed")
            return jsonify({'success': False, 'error': 'Failed to stop watering'})
            
    except Exception as e:
        print(f"❌ Error stopping watering: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<device_id>/set_mode', methods=['POST'])
def api_set_mode(device_id):
    """API endpoint to set device mode."""
    if not bhyve_client or connection_status != "connected":
        return jsonify({'success': False, 'error': 'Not connected to Bhyve'}), 400
    
    data = request.get_json()
    mode = data.get('mode')
    
    if not mode or mode not in ['auto', 'manual', 'off']:
        return jsonify({'success': False, 'error': 'Invalid mode. Must be auto, manual, or off'}), 400
    
    try:
        print(f"🔧 Setting mode: Device {device_id}, Mode {mode}")
        result = sync_set_mode(device_id, mode)
        
        if result:
            print(f"✅ Mode change command sent successfully")
            return jsonify({'success': True, 'message': f'Set device mode to {mode}'})
        else:
            print(f"❌ Mode change command failed")
            return jsonify({'success': False, 'error': 'Failed to set device mode'})
            
    except Exception as e:
        print(f"❌ Error setting mode: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🌱 Starting Working Orbit Bhyve Web Dashboard...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🔧 Make sure BHYVE_USERNAME and BHYVE_PASSWORD are set in your .env file")
    print("🔌 Click 'Connect' button to establish connection")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
