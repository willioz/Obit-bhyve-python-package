#!/usr/bin/env python3
"""
MQTT-based Bhyve Dashboard

A Flask web dashboard that uses MQTT for both monitoring and control of Bhyve devices.
This dashboard connects to an MQTT broker and provides real-time device monitoring
and control capabilities.
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any

from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

from orbit_bhyve.mqtt_client import BhyveMQTTClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Global MQTT client
mqtt_client = None
mqtt_connected = False
devices_data = {}

def create_mqtt_client():
    """Create and configure MQTT client."""
    global mqtt_client
    
    # MQTT configuration from environment variables
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    
    logger.info(f"Creating MQTT client for {mqtt_broker}:{mqtt_port}")
    
    mqtt_client = BhyveMQTTClient(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        use_tls=False
    )
    
    # Set up event handlers
    def on_device_status(device_id, status):
        logger.info(f"Device {device_id} status update: {status}")
        devices_data[device_id] = devices_data.get(device_id, {})
        devices_data[device_id].update(status)
    
    def on_device_details(device_id, details):
        logger.info(f"Device {device_id} details update")
        devices_data[device_id] = details
    
    def on_watering_started(device_id, message):
        logger.info(f"Device {device_id} started watering: {message}")
        devices_data[device_id] = devices_data.get(device_id, {})
        devices_data[device_id]['watering_status'] = {
            'status': 'watering_in_progress',
            'current_station': message.get('current_station'),
            'run_time': message.get('run_time'),
            'started_at': message.get('started_watering_station_at')
        }
    
    def on_watering_completed(device_id, message):
        logger.info(f"Device {device_id} completed watering")
        if device_id in devices_data and 'watering_status' in devices_data[device_id]:
            devices_data[device_id]['watering_status']['status'] = 'idle'
    
    def on_mode_changed(device_id, message):
        logger.info(f"Device {device_id} mode changed to: {message.get('mode')}")
        devices_data[device_id] = devices_data.get(device_id, {})
        devices_data[device_id]['mode'] = message.get('mode')
    
    def on_devices_list(device_ids):
        logger.info(f"Received devices list: {device_ids}")
    
    # Register event handlers
    mqtt_client.on_event('device_status', on_device_status)
    mqtt_client.on_event('device_details', on_device_details)
    mqtt_client.on_event('watering_started', on_watering_started)
    mqtt_client.on_event('watering_completed', on_watering_completed)
    mqtt_client.on_event('mode_changed', on_mode_changed)
    mqtt_client.on_event('devices_list', on_devices_list)

async def maintain_mqtt_connection():
    """Maintain MQTT connection in background."""
    global mqtt_connected
    
    while True:
        try:
            if not mqtt_connected:
                logger.info("Connecting to MQTT broker...")
                connected = await mqtt_client.connect()
                if connected:
                    mqtt_connected = True
                    logger.info("✅ Connected to MQTT broker")
                    
                    # Request device refresh
                    mqtt_client.refresh_devices()
                else:
                    logger.error("❌ Failed to connect to MQTT broker")
                    await asyncio.sleep(10)
            else:
                # Check if still connected
                if not mqtt_client.connected:
                    mqtt_connected = False
                    logger.warning("MQTT connection lost, will reconnect...")
                else:
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in MQTT connection loop: {e}")
            mqtt_connected = False
            await asyncio.sleep(10)

def start_mqtt_loop():
    """Start MQTT event loop in background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(maintain_mqtt_connection())

# Flask routes
@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('mqtt_dashboard.html')

@app.route('/api/devices')
def api_devices():
    """Get current device data."""
    global devices_data, mqtt_connected
    
    # Format devices for frontend
    formatted_devices = {}
    for device_id, device_data in devices_data.items():
        formatted_devices[device_id] = {
            'id': device_id,
            'name': device_data.get('name', f'Device {device_id[:8]}'),
            'mode': device_data.get('mode', 'unknown'),
            'is_watering': mqtt_client.is_device_watering(device_id) if mqtt_client else False,
            'watering_station': mqtt_client.get_watering_station(device_id) if mqtt_client else None,
            'watering_status': device_data.get('watering_status', {}),
            'zones': device_data.get('zones', {}),
            'status': device_data.get('status', {})
        }
    
    return jsonify({
        'devices': formatted_devices,
        'mqtt_connected': mqtt_connected,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/connect', methods=['POST'])
def api_connect():
    """Connect to MQTT broker."""
    global mqtt_connected
    
    if mqtt_connected:
        return jsonify({'success': True, 'message': 'Already connected'})
    
    try:
        # Start MQTT connection in background
        if not mqtt_client:
            create_mqtt_client()
        
        # Start MQTT loop in background thread
        mqtt_thread = threading.Thread(target=start_mqtt_loop, daemon=True)
        mqtt_thread.start()
        
        # Wait a moment for connection
        time.sleep(2)
        
        return jsonify({'success': True, 'message': 'MQTT connection initiated'})
    except Exception as e:
        logger.error(f"Error connecting to MQTT: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/device/<device_id>/start_watering', methods=['POST'])
def api_start_watering(device_id):
    """Start watering on a device."""
    global mqtt_client
    
    if not mqtt_client or not mqtt_connected:
        return jsonify({'success': False, 'message': 'MQTT not connected'}), 500
    
    try:
        data = request.get_json()
        station = data.get('station', 1)
        duration = data.get('duration', 300)  # Default 5 minutes
        
        logger.info(f"Starting watering: Device {device_id}, Station {station}, Duration {duration}s")
        
        success = mqtt_client.start_watering(device_id, station, duration / 60.0)  # Convert to minutes
        
        if success:
            return jsonify({'success': True, 'message': 'Watering command sent'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send watering command'}), 500
            
    except Exception as e:
        logger.error(f"Error starting watering: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/device/<device_id>/stop_watering', methods=['POST'])
def api_stop_watering(device_id):
    """Stop watering on a device."""
    global mqtt_client
    
    if not mqtt_client or not mqtt_connected:
        return jsonify({'success': False, 'message': 'MQTT not connected'}), 500
    
    try:
        logger.info(f"Stopping watering: Device {device_id}")
        
        success = mqtt_client.stop_watering(device_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Stop watering command sent'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send stop watering command'}), 500
            
    except Exception as e:
        logger.error(f"Error stopping watering: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/device/<device_id>/set_mode', methods=['POST'])
def api_set_mode(device_id):
    """Set device mode."""
    global mqtt_client
    
    if not mqtt_client or not mqtt_connected:
        return jsonify({'success': False, 'message': 'MQTT not connected'}), 500
    
    try:
        data = request.get_json()
        mode = data.get('mode', 'auto')
        
        logger.info(f"Setting mode: Device {device_id}, Mode {mode}")
        
        # For mode changes, we'll use the WebSocket client approach
        # This would need to be implemented in the MQTT client
        return jsonify({'success': False, 'message': 'Mode change not implemented in MQTT client yet'}), 501
            
    except Exception as e:
        logger.error(f"Error setting mode: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Refresh device data."""
    global mqtt_client
    
    if not mqtt_client or not mqtt_connected:
        return jsonify({'success': False, 'message': 'MQTT not connected'}), 500
    
    try:
        success = mqtt_client.refresh_devices()
        return jsonify({'success': success, 'message': 'Refresh command sent' if success else 'Failed to send refresh command'})
    except Exception as e:
        logger.error(f"Error refreshing devices: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Create MQTT client
    create_mqtt_client()
    
    # Start MQTT connection in background
    mqtt_thread = threading.Thread(target=start_mqtt_loop, daemon=True)
    mqtt_thread.start()
    
    # Start Flask app
    logger.info("🌱 Starting MQTT-based Bhyve Dashboard")
    logger.info("📱 Open your browser to: http://localhost:5001")
    logger.info("🔧 Press Ctrl+C to stop the dashboard")
    
    app.run(debug=False, host='0.0.0.0', port=5001)
