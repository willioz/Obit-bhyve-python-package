#!/usr/bin/env python3
"""
Simple Orbit Bhyve Web Dashboard

A simplified Flask web interface that connects to Bhyve on-demand.
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

def get_credentials():
    """Get credentials from environment variables."""
    username = os.getenv("BHYVE_USERNAME")
    password = os.getenv("BHYVE_PASSWORD")
    
    if not username or not password:
        return None, None
    
    return username, password

async def connect_to_bhyve():
    """Connect to Bhyve WebSocket and load devices."""
    global bhyve_client, devices, device_data, last_update, connection_status
    
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
        # Check if WebSocket is still connected
        if not bhyve_client.connected:
            return jsonify({'success': False, 'error': 'WebSocket connection lost. Please reconnect.'}), 400
        
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            bhyve_client.start_watering(device_id, station, duration)
        )
        loop.close()
        
        if result:
            return jsonify({'success': True, 'message': f'Started watering station {station}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to start watering'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<device_id>/stop_watering', methods=['POST'])
def api_stop_watering(device_id):
    """API endpoint to stop all watering on a device."""
    if not bhyve_client or connection_status != "connected":
        return jsonify({'success': False, 'error': 'Not connected to Bhyve'}), 400
    
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            bhyve_client.stop_watering(device_id)
        )
        loop.close()
        
        if result:
            return jsonify({'success': True, 'message': 'Stopped all watering'})
        else:
            return jsonify({'success': False, 'error': 'Failed to stop watering'})
            
    except Exception as e:
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
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            bhyve_client.set_device_mode(device_id, mode)
        )
        loop.close()
        
        if result:
            return jsonify({'success': True, 'message': f'Set device mode to {mode}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to set device mode'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🌱 Starting Simple Orbit Bhyve Web Dashboard...")
    print("📱 Open your browser to: http://localhost:5000")
    print("🔧 Make sure BHYVE_USERNAME and BHYVE_PASSWORD are set in your .env file")
    print("🔌 Click 'Connect' button to establish connection")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
