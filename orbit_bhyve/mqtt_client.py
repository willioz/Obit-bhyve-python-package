"""
MQTT client for Orbit Bhyve devices based on JavaScript implementation analysis.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import paho.mqtt.client as mqtt
from .exceptions import BhyveError, BhyveConnectionError, BhyveAuthenticationError


class BhyveMQTTClient:
    """
    MQTT client for Orbit Bhyve devices.
    
    This client connects to an MQTT broker and provides device control
    functionality based on the JavaScript implementation analysis.
    """
    
    # Topic structure based on JavaScript constants
    TOPICS = {
        'prefix': 'bhyve',
        'online': 'bhyve/online',
        'alive': 'bhyve/alive',
        'devices': 'bhyve/devices',
        'device': 'bhyve/device',
        'message': 'bhyve/message',
        'device_refresh': 'bhyve/device/refresh',
    }
    
    def __init__(self, 
                 mqtt_broker: str,
                 mqtt_port: int = 1883,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 client_id: Optional[str] = None,
                 use_tls: bool = False):
        """
        Initialize MQTT client.
        
        Args:
            mqtt_broker: MQTT broker address
            mqtt_port: MQTT broker port
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
            client_id: MQTT client ID (auto-generated if None)
            use_tls: Whether to use TLS encryption
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.client_id = client_id or f"bhyve-mqtt_{int(time.time())}"
        self.use_tls = use_tls
        
        self.connected = False
        self.devices = {}
        self.event_handlers = {}
        self.logger = logging.getLogger(__name__)
        
        # MQTT client
        self.mqtt_client = None
        self._setup_mqtt_client()
    
    def _setup_mqtt_client(self):
        """Setup MQTT client with event handlers."""
        self.mqtt_client = mqtt.Client(self.client_id)
        
        # Set authentication if provided
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Set up TLS if needed
        if self.use_tls:
            self.mqtt_client.tls_set()
        
        # Set up event handlers
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_log = self._on_log
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            self.connected = True
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to device topics
            self._subscribe_to_topics()
            
            # Publish online status
            self._publish_online()
        else:
            self.logger.error(f"Failed to connect to MQTT broker. Result code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        self.connected = False
        self.logger.warning(f"Disconnected from MQTT broker. Result code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Parse message based on topic
            if topic.startswith(f"{self.TOPICS['device']}/"):
                self._handle_device_message(topic, payload)
            elif topic == self.TOPICS['devices']:
                self._handle_devices_list(payload)
            else:
                self.logger.debug(f"Unhandled topic: {topic}")
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")
    
    def _on_log(self, client, userdata, level, buf):
        """Handle MQTT client logging."""
        self.logger.debug(f"MQTT: {buf}")
    
    def _subscribe_to_topics(self):
        """Subscribe to relevant MQTT topics."""
        topics_to_subscribe = [
            self.TOPICS['devices'],
            self.TOPICS['device_refresh'],
            f"{self.TOPICS['device']}/+/status",
            f"{self.TOPICS['device']}/+/details",
            f"{self.TOPICS['device']}/+/message",
        ]
        
        for topic in topics_to_subscribe:
            self.mqtt_client.subscribe(topic)
            self.logger.debug(f"Subscribed to topic: {topic}")
    
    def _publish_online(self):
        """Publish online status."""
        if self.connected:
            self.mqtt_client.publish(self.TOPICS['alive'], datetime.utcnow().isoformat())
            self.mqtt_client.publish(self.TOPICS['online'], 'true', qos=0, retain=True)
    
    def _handle_device_message(self, topic: str, payload: str):
        """Handle device-specific messages."""
        try:
            # Extract device ID from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                device_id = topic_parts[2]
                
                if topic.endswith('/status'):
                    # Device status update
                    status_data = json.loads(payload) if payload else {}
                    if device_id not in self.devices:
                        self.devices[device_id] = {}
                    self.devices[device_id].update(status_data)
                    self._trigger_event('device_status', device_id, status_data)
                    
                elif topic.endswith('/details'):
                    # Device details update
                    device_data = json.loads(payload)
                    self.devices[device_id] = device_data
                    self._trigger_event('device_details', device_id, device_data)
                    
                elif topic.endswith('/message'):
                    # Device message (real-time updates)
                    message_data = json.loads(payload)
                    self._handle_realtime_message(device_id, message_data)
                    self._trigger_event('device_message', device_id, message_data)
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON from topic {topic}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling device message: {e}")
    
    def _handle_realtime_message(self, device_id: str, message_data: dict):
        """Handle real-time device messages and update device status."""
        try:
            event_type = message_data.get('event')
            
            if event_type == 'watering_in_progress_notification':
                # Update watering status
                if device_id not in self.devices:
                    self.devices[device_id] = {}
                
                self.devices[device_id]['watering_status'] = {
                    'status': 'watering_in_progress',
                    'current_station': message_data.get('current_station'),
                    'run_time': message_data.get('run_time'),
                    'total_run_time_sec': message_data.get('total_run_time_sec'),
                    'started_watering_station_at': message_data.get('started_watering_station_at')
                }
                self._trigger_event('watering_started', device_id, message_data)
                
            elif event_type == 'watering_complete':
                # Clear watering status
                if device_id in self.devices and 'watering_status' in self.devices[device_id]:
                    self.devices[device_id]['watering_status']['status'] = 'idle'
                self._trigger_event('watering_completed', device_id, message_data)
                
            elif event_type == 'change_mode':
                # Update device mode
                if device_id not in self.devices:
                    self.devices[device_id] = {}
                self.devices[device_id]['mode'] = message_data.get('mode')
                self._trigger_event('mode_changed', device_id, message_data)
                
        except Exception as e:
            self.logger.error(f"Error handling real-time message: {e}")
    
    def _handle_devices_list(self, payload: str):
        """Handle devices list message."""
        try:
            device_ids = json.loads(payload)
            self.logger.info(f"Received devices list: {device_ids}")
            self._trigger_event('devices_list', device_ids)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing devices list: {e}")
    
    def _trigger_event(self, event_type: str, *args):
        """Trigger event handlers."""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type](*args)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    async def connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            for _ in range(10):  # Wait up to 10 seconds
                if self.connected:
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.connected = False
    
    def on_event(self, event_type: str, handler: Callable):
        """
        Register event handler.
        
        Args:
            event_type: Type of event ('device_status', 'device_details', 'device_message', 'devices_list')
            handler: Function to call when event occurs
        """
        self.event_handlers[event_type] = handler
    
    def start_watering(self, device_id: str, station: int, duration_minutes: float) -> bool:
        """
        Start watering a specific station.
        
        Args:
            device_id: Device ID
            station: Station number
            duration_minutes: Duration in minutes
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to MQTT broker")
            return False
        
        try:
            # Construct command based on JavaScript implementation
            command = {
                "event": "change_mode",
                "device_id": device_id,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "mode": "manual",
                "stations": [{"station": station, "run_time": duration_minutes}]
            }
            
            # Publish to device control topic
            topic = f"{self.TOPICS['device']}/{device_id}/zone/{station}/set"
            payload = json.dumps({"state": "ON", "time": duration_minutes})
            
            result = self.mqtt_client.publish(topic, payload)
            self.logger.info(f"Sent watering command to {topic}: {payload}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"Error sending watering command: {e}")
            return False
    
    def stop_watering(self, device_id: str) -> bool:
        """
        Stop watering on a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to MQTT broker")
            return False
        
        try:
            # Construct stop command based on JavaScript implementation
            command = {
                "event": "change_mode",
                "device_id": device_id,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "mode": "manual",
                "stations": []
            }
            
            # Publish to device control topic (empty stations = stop)
            topic = f"{self.TOPICS['device']}/{device_id}/zone/1/set"  # Use station 1 as default
            payload = json.dumps({"state": "OFF"})
            
            result = self.mqtt_client.publish(topic, payload)
            self.logger.info(f"Sent stop watering command to {topic}: {payload}")
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"Error sending stop watering command: {e}")
            return False
    
    def refresh_devices(self) -> bool:
        """
        Request device refresh.
        
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.connected:
            self.logger.error("Not connected to MQTT broker")
            return False
        
        try:
            result = self.mqtt_client.publish(self.TOPICS['device_refresh'], "")
            self.logger.info("Sent device refresh request")
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"Error sending device refresh: {e}")
            return False
    
    def get_devices(self) -> Dict[str, Any]:
        """
        Get current device data.
        
        Returns:
            Dictionary of device data
        """
        return self.devices.copy()
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get status of a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device status data
        """
        return self.devices.get(device_id, {})
    
    def is_device_watering(self, device_id: str) -> bool:
        """
        Check if a device is currently watering.
        
        Args:
            device_id: Device ID
            
        Returns:
            True if device is watering, False otherwise
        """
        device = self.devices.get(device_id, {})
        watering_status = device.get('watering_status', {})
        return watering_status.get('status') == 'watering_in_progress'
    
    def get_device_mode(self, device_id: str) -> str:
        """
        Get the current mode of a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device mode ('auto', 'manual', etc.)
        """
        device = self.devices.get(device_id, {})
        return device.get('mode', 'unknown')
    
    def get_watering_station(self, device_id: str) -> Optional[int]:
        """
        Get the currently watering station.
        
        Args:
            device_id: Device ID
            
        Returns:
            Station number if watering, None otherwise
        """
        device = self.devices.get(device_id, {})
        watering_status = device.get('watering_status', {})
        if watering_status.get('status') == 'watering_in_progress':
            return watering_status.get('current_station')
        return None
