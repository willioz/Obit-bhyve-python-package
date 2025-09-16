#!/usr/bin/env python3
"""
Bhyve MQTT Gateway - Connects Bhyve devices to MQTT broker
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from orbit_bhyve.client import BhyveClient as BhyveWebSocketClient
from orbit_bhyve.mqtt_client import BhyveMQTTClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BhyveMQTTGateway:
    """Gateway that connects Bhyve devices to MQTT broker"""
    
    def __init__(self):
        self.bhyve_client = None
        self.mqtt_client = None
        self.running = False
        
    async def start(self):
        """Start the gateway"""
        logger.info("🚀 Starting Bhyve MQTT Gateway...")
        
        # Get credentials
        username = os.getenv("BHYVE_USERNAME")
        password = os.getenv("BHYVE_PASSWORD")
        mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        
        if not username or not password:
            logger.error("❌ Bhyve credentials not found in .env file")
            return False
            
        try:
            # Initialize Bhyve client
            logger.info("🔑 Connecting to Bhyve API...")
            self.bhyve_client = BhyveWebSocketClient(username=username, password=password)
            await self.bhyve_client.authenticate()
            logger.info("✅ Bhyve authentication successful")
            
            # Connect to WebSocket for real-time updates
            await self.bhyve_client.connect()
            logger.info("✅ Bhyve WebSocket connected")
            
            # Initialize MQTT client
            logger.info("🔌 Connecting to MQTT broker...")
            self.mqtt_client = BhyveMQTTClient(
                mqtt_broker=mqtt_broker,
                mqtt_port=mqtt_port
            )
            await self.mqtt_client.connect()
            logger.info("✅ MQTT broker connected")
            
            # Set up event handlers
            self._setup_event_handlers()
            
            # Get initial device data
            await self._publish_initial_data()
            
            self.running = True
            logger.info("🎉 Gateway started successfully!")
            logger.info(f"📱 Found {len(self.bhyve_client.devices)} devices")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start gateway: {e}")
            return False
    
    def _setup_event_handlers(self):
        """Set up event handlers for real-time updates"""
        
        def handle_device_update(data):
            """Handle device status updates"""
            try:
                device_id = data.get("device_id")
                if device_id and device_id in self.bhyve_client.devices:
                    device = self.bhyve_client.devices[device_id]
                    
                    # Publish device status to MQTT
                    device_data = {
                        "id": device.id,
                        "name": device.name,
                        "type": device.type,
                        "status": device.status,
                        "watering_status": device.watering_status,
                        "is_watering": device.is_watering,
                        "run_mode": device.run_mode,
                        "battery_level": device.battery_level,
                        "signal_strength": device.signal_strength,
                        "last_seen": device.last_seen,
                        "is_connected": device.is_connected,
                        "firmware_version": device.firmware_version,
                        "hardware_version": device.hardware_version,
                        "num_stations": device.num_stations,
                        "zones": device.zones,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Publish to MQTT
                    asyncio.create_task(self._publish_device_data(device_data))
                    
            except Exception as e:
                logger.error(f"Error handling device update: {e}")
        
        # Register event handlers
        self.bhyve_client.on_event("device_status", handle_device_update)
        self.bhyve_client.on_event("watering_in_progress_notification", handle_device_update)
        self.bhyve_client.on_event("watering_complete", handle_device_update)
        self.bhyve_client.on_event("device_idle", handle_device_update)
        self.bhyve_client.on_event("change_mode", handle_device_update)
    
    async def _publish_initial_data(self):
        """Publish initial device data to MQTT"""
        try:
            # Get devices from Bhyve API
            devices_data = await self.bhyve_client.get_devices()
            
            if devices_data:
                logger.info(f"📱 Publishing data for {len(devices_data)} devices...")
                
                for device_data in devices_data:
                    await self._publish_device_data(device_data)
                    
                # Publish devices list
                await self.mqtt_client.publish_devices_list(devices_data)
                
            else:
                logger.warning("⚠️ No devices found")
                
        except Exception as e:
            logger.error(f"Error publishing initial data: {e}")
    
    async def _publish_device_data(self, device_data):
        """Publish device data to MQTT topics"""
        try:
            device_id = device_data.get("id")
            if not device_id:
                return
                
            # Publish device details
            await self.mqtt_client.publish_device_details(device_id, device_data)
            
            # Publish device status
            status_data = {
                "device_id": device_id,
                "status": device_data.get("status", {}),
                "watering_status": device_data.get("watering_status", {}),
                "is_watering": device_data.get("is_watering", False),
                "run_mode": device_data.get("run_mode", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            await self.mqtt_client.publish_device_status(device_id, status_data)
            
            # Publish zone information
            zones = device_data.get("zones", [])
            for i, zone in enumerate(zones):
                await self.mqtt_client.publish_zone_info(device_id, i, zone)
                
        except Exception as e:
            logger.error(f"Error publishing device data: {e}")
    
    async def stop(self):
        """Stop the gateway"""
        logger.info("🛑 Stopping Bhyve MQTT Gateway...")
        self.running = False
        
        if self.bhyve_client:
            await self.bhyve_client.disconnect()
            
        if self.mqtt_client:
            await self.mqtt_client.disconnect()
            
        logger.info("✅ Gateway stopped")
    
    async def run(self):
        """Run the gateway main loop"""
        if not await self.start():
            return
            
        try:
            logger.info("🔄 Gateway running... Press Ctrl+C to stop")
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        finally:
            await self.stop()

async def main():
    """Main function"""
    gateway = BhyveMQTTGateway()
    await gateway.run()

if __name__ == "__main__":
    asyncio.run(main())
