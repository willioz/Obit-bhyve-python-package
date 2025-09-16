"""
MQTT client for Orbit Bhyve devices based on JavaScript implementation analysis.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import paho.mqtt.client as mqtt
import jsonschema
from jsonschema import validate, ValidationError
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
    
    # Command validation schema based on JavaScript implementation
    COMMAND_SCHEMA = {
        "type": "object",
        "properties": {
            "time": {
                "type": "number",
                "minimum": 1,
                "maximum": 999
            },
            "state": {
                "type": "string",
                "enum": ["ON", "OFF", "on", "off"]
            }
        },
        "if": {
            "properties": {
                "state": {
                    "enum": ["ON", "on"]
                }
            },
            "required": ["state"]
        },
        "then": {
            "required": ["time"]
        },
        "required": ["state"],
        "additionalProperties": False
    }
    
    DEFAULT_CONFIG = {
        'keepalive': 10,  # seconds
        'connect_timeout': 120,  # seconds
        'reconnect_period': 5,  # seconds
        'max_retries': 10,
        'clean_session': True,
        'will_qos': 0,
        'will_retain': True
    }
    
    # Environment variable configuration mapping
    ENV_CONFIG_MAP = {
        'BHYVE_MQTT_BROKER': 'mqtt_broker',
        'BHYVE_MQTT_PORT': 'mqtt_port',
        'BHYVE_MQTT_USERNAME': 'mqtt_username',
        'BHYVE_MQTT_PASSWORD': 'mqtt_password',
        'BHYVE_MQTT_CLIENT_ID': 'client_id',
        'BHYVE_MQTT_USE_TLS': 'use_tls',
        'BHYVE_MQTT_KEEPALIVE': 'keepalive',
        'BHYVE_MQTT_CONNECT_TIMEOUT': 'connect_timeout',
        'BHYVE_MQTT_RECONNECT_PERIOD': 'reconnect_period',
        'BHYVE_MQTT_MAX_RETRIES': 'max_retries',
        'BHYVE_MQTT_CLEAN_SESSION': 'clean_session',
        'BHYVE_MQTT_WILL_QOS': 'will_qos',
        'BHYVE_MQTT_WILL_RETAIN': 'will_retain',
        'BHYVE_LOG_LEVEL': 'log_level'
    }
    
    def __init__(self, 
                 mqtt_broker: Optional[str] = None,
                 mqtt_port: Optional[int] = None,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 client_id: Optional[str] = None,
                 use_tls: Optional[bool] = None,
                 keepalive: Optional[int] = None,
                 connect_timeout: Optional[int] = None,
                 reconnect_period: Optional[int] = None,
                 max_retries: Optional[int] = None,
                 clean_session: Optional[bool] = None):
        """
        Initialize MQTT client with advanced configuration.
        Configuration can be provided via parameters or environment variables.
        Parameters override environment variables.
        
        Environment Variables:
            BHYVE_MQTT_BROKER: MQTT broker address
            BHYVE_MQTT_PORT: MQTT broker port (default: 1883)
            BHYVE_MQTT_USERNAME: MQTT username
            BHYVE_MQTT_PASSWORD: MQTT password
            BHYVE_MQTT_CLIENT_ID: MQTT client ID
            BHYVE_MQTT_USE_TLS: Whether to use TLS encryption (true/false)
            BHYVE_MQTT_KEEPALIVE: Keepalive interval in seconds (default: 10)
            BHYVE_MQTT_CONNECT_TIMEOUT: Connection timeout in seconds (default: 120)
            BHYVE_MQTT_RECONNECT_PERIOD: Reconnection period in seconds (default: 5)
            BHYVE_MQTT_MAX_RETRIES: Maximum reconnection attempts (default: 10)
            BHYVE_MQTT_CLEAN_SESSION: Whether to use clean session (true/false, default: true)
            BHYVE_MQTT_WILL_QOS: Will message QoS level (default: 0)
            BHYVE_MQTT_WILL_RETAIN: Whether will message is retained (true/false, default: true)
            BHYVE_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Args:
            mqtt_broker: MQTT broker address (overrides BHYVE_MQTT_BROKER)
            mqtt_port: MQTT broker port (overrides BHYVE_MQTT_PORT)
            mqtt_username: MQTT username (overrides BHYVE_MQTT_USERNAME)
            mqtt_password: MQTT password (overrides BHYVE_MQTT_PASSWORD)
            client_id: MQTT client ID (overrides BHYVE_MQTT_CLIENT_ID)
            use_tls: Whether to use TLS encryption (overrides BHYVE_MQTT_USE_TLS)
            keepalive: Keepalive interval in seconds (overrides BHYVE_MQTT_KEEPALIVE)
            connect_timeout: Connection timeout in seconds (overrides BHYVE_MQTT_CONNECT_TIMEOUT)
            reconnect_period: Reconnection period in seconds (overrides BHYVE_MQTT_RECONNECT_PERIOD)
            max_retries: Maximum reconnection attempts (overrides BHYVE_MQTT_MAX_RETRIES)
            clean_session: Whether to use clean session (overrides BHYVE_MQTT_CLEAN_SESSION)
        """
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment variables first
        env_config = self._load_env_config()
        
        # Override with provided parameters
        self.mqtt_broker = mqtt_broker or env_config.get('mqtt_broker')
        self.mqtt_port = mqtt_port if mqtt_port is not None else env_config.get('mqtt_port', 1883)
        self.mqtt_username = mqtt_username or env_config.get('mqtt_username')
        self.mqtt_password = mqtt_password or env_config.get('mqtt_password')
        self.client_id = client_id or env_config.get('client_id') or f"bhyve-mqtt_{int(time.time())}"
        self.use_tls = use_tls if use_tls is not None else env_config.get('use_tls', False)
        
        # Validate required parameters
        if not self.mqtt_broker:
            raise ValueError("MQTT broker address is required. Set BHYVE_MQTT_BROKER environment variable or provide mqtt_broker parameter.")
        
        # Advanced MQTT configuration
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Override config with environment variables first
        if 'keepalive' in env_config:
            self.config['keepalive'] = env_config['keepalive']
        if 'connect_timeout' in env_config:
            self.config['connect_timeout'] = env_config['connect_timeout']
        if 'reconnect_period' in env_config:
            self.config['reconnect_period'] = env_config['reconnect_period']
        if 'max_retries' in env_config:
            self.config['max_retries'] = env_config['max_retries']
        if 'clean_session' in env_config:
            self.config['clean_session'] = env_config['clean_session']
        if 'will_qos' in env_config:
            self.config['will_qos'] = env_config['will_qos']
        if 'will_retain' in env_config:
            self.config['will_retain'] = env_config['will_retain']
        
        # Override with provided parameters (highest priority)
        if keepalive is not None:
            self.config['keepalive'] = keepalive
        if connect_timeout is not None:
            self.config['connect_timeout'] = connect_timeout
        if reconnect_period is not None:
            self.config['reconnect_period'] = reconnect_period
        if max_retries is not None:
            self.config['max_retries'] = max_retries
        if clean_session is not None:
            self.config['clean_session'] = clean_session
        
        self.connected = False
        self.devices = {}
        self.event_handlers = {}
        
        # Retry tracking
        self._retry_count = 0
        self._last_connect_attempt = 0
        
        # Topic subscription tracking (matching JavaScript implementation)
        self._subscribed_topics = set()
        
        # Retained message tracking
        self._retained_messages = {}
        
        # Signal handling for graceful shutdown
        self._shutdown_requested = False
        self._original_signal_handlers = {}
        self._setup_signal_handlers()
        
        # MQTT client
        self.mqtt_client = None
        self._setup_mqtt_client()
        
        # Command validation
        self._validator = jsonschema.Draft7Validator(self.COMMAND_SCHEMA)
        
        # Configure logging level from environment
        log_level = env_config.get('log_level')
        if log_level:
            self._configure_logging(log_level)
    
    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dictionary with configuration values from environment variables
        """
        config = {}
        
        for env_var, config_key in self.ENV_CONFIG_MAP.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion based on expected type
                if config_key in ['mqtt_port', 'keepalive', 'connect_timeout', 'reconnect_period', 'max_retries', 'will_qos']:
                    try:
                        config[config_key] = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                elif config_key in ['use_tls', 'clean_session', 'will_retain']:
                    config[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    config[config_key] = value
        
        return config
    
    def _configure_logging(self, log_level: str):
        """
        Configure logging level based on environment variable.
        
        Args:
            log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        level = level_map.get(log_level.upper())
        if level is not None:
            self.logger.setLevel(level)
            # Also configure the root logger if it's not already configured
            if not logging.getLogger().handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(level)
        else:
            self.logger.warning(f"Invalid log level: {log_level}. Valid levels: {list(level_map.keys())}")
    
    def _setup_mqtt_client(self):
        """Setup MQTT client with advanced configuration and event handlers."""
        self.mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, 
            self.client_id,
            clean_session=self.config['clean_session']
        )
        
        # Set authentication if provided
        if self.mqtt_username and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        # Set up TLS if needed
        if self.use_tls:
            self.mqtt_client.tls_set()
        
        # Set up Last Will and Testament (LWT)
        self.mqtt_client.will_set(
            self.TOPICS['online'],
            'false',
            qos=self.config['will_qos'],
            retain=self.config['will_retain']
        )
        
        # Set up event handlers
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_log = self._on_log
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully."""
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            self._shutdown_requested = True
            self.disconnect()
            sys.exit(0)
        
        # Store original handlers and set new ones
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                self._original_signal_handlers[sig] = signal.signal(sig, signal_handler)
            except (OSError, ValueError) as e:
                # Some signals might not be available on all platforms
                self.logger.warning(f"Could not set signal handler for {sig}: {e}")
    
    def _restore_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, original_handler in self._original_signal_handlers.items():
            try:
                signal.signal(sig, original_handler)
            except (OSError, ValueError) as e:
                self.logger.warning(f"Could not restore signal handler for {sig}: {e}")
        self._original_signal_handlers.clear()
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection with retry logic."""
        if rc == 0:
            self.connected = True
            self._retry_count = 0  # Reset retry count on successful connection
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to device topics (or resubscribe if reconnecting)
            if self._subscribed_topics:
                self._resubscribe_to_topics()
            else:
                self._subscribe_to_topics()
            
            # Publish online status
            self._publish_online()
        else:
            self._retry_count += 1
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            self.logger.error(f"Failed to connect to MQTT broker (attempt {self._retry_count}): {error_msg}")
            
            # Check if we've exceeded max retries
            if self._retry_count >= self.config['max_retries']:
                self.logger.error(f"Maximum retry attempts ({self.config['max_retries']}) exceeded. Giving up.")
                self._trigger_event('max_retries_exceeded', None, {
                    'retry_count': self._retry_count,
                    'max_retries': self.config['max_retries']
                })
    
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
            f"{self.TOPICS['device']}/+/zone/+/set",  # Zone control commands
        ]
        
        for topic in topics_to_subscribe:
            self._subscribe_to_topic(topic)
    
    def _subscribe_to_topic(self, topic: str, force: bool = False):
        """
        Subscribe to a topic with duplicate prevention.
        
        Args:
            topic: The topic to subscribe to
            force: Force subscription even if already subscribed
        """
        # Skip if already subscribed and not forced
        if not force and topic in self._subscribed_topics:
            self.logger.debug(f"Already subscribed to topic: {topic}")
            return
        
        self.logger.info(f"{'Re' if force and topic in self._subscribed_topics else ''}Subscribing to topic: {topic}")
        
        try:
            result, mid = self.mqtt_client.subscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                # Only add to tracking set on successful subscription
                self._subscribed_topics.add(topic)
                self.logger.debug(f"Successfully subscribed to topic: {topic} (mid: {mid})")
            else:
                self.logger.error(f"Failed to subscribe to topic {topic}: MQTT error {result}")
        except Exception as e:
            self.logger.error(f"Error subscribing to topic {topic}: {e}")
    
    def _resubscribe_to_topics(self):
        """Resubscribe to all previously subscribed topics."""
        self.logger.info("Resubscribing to all previously subscribed topics")
        for topic in list(self._subscribed_topics):
            self._subscribe_to_topic(topic, force=True)
    
    def subscribe_to_topic(self, topic: str):
        """
        Public method to subscribe to a topic.
        
        Args:
            topic: The topic to subscribe to
        """
        self._subscribe_to_topic(topic)
    
    def unsubscribe_from_topic(self, topic: str):
        """
        Unsubscribe from a topic.
        
        Args:
            topic: The topic to unsubscribe from
        """
        try:
            result, mid = self.mqtt_client.unsubscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self._subscribed_topics.discard(topic)
                self.logger.info(f"Unsubscribed from topic: {topic} (mid: {mid})")
            else:
                self.logger.error(f"Failed to unsubscribe from topic {topic}: MQTT error {result}")
        except Exception as e:
            self.logger.error(f"Error unsubscribing from topic {topic}: {e}")
    
    def get_subscribed_topics(self) -> set:
        """
        Get the set of currently subscribed topics.
        
        Returns:
            Set of subscribed topic strings
        """
        return self._subscribed_topics.copy()
    
    def is_subscribed_to_topic(self, topic: str) -> bool:
        """
        Check if currently subscribed to a topic.
        
        Args:
            topic: The topic to check
            
        Returns:
            True if subscribed, False otherwise
        """
        return topic in self._subscribed_topics
    
    def subscribe_to_device_topics(self, device_id: str):
        """
        Subscribe to all topics for a specific device.
        
        Args:
            device_id: The device ID to subscribe to
        """
        device_topics = [
            f"{self.TOPICS['device']}/{device_id}/status",
            f"{self.TOPICS['device']}/{device_id}/details",
            f"{self.TOPICS['device']}/{device_id}/message",
            f"{self.TOPICS['device']}/{device_id}/refresh",
        ]
        
        for topic in device_topics:
            self._subscribe_to_topic(topic)
    
    def subscribe_to_device_zone_topics(self, device_id: str, zones: List[int]):
        """
        Subscribe to zone control topics for a specific device.
        
        Args:
            device_id: The device ID
            zones: List of zone/station numbers
        """
        for zone in zones:
            topic = f"{self.TOPICS['device']}/{device_id}/zone/{zone}/set"
            self._subscribe_to_topic(topic)
    
    def unsubscribe_from_device_topics(self, device_id: str):
        """
        Unsubscribe from all topics for a specific device.
        
        Args:
            device_id: The device ID to unsubscribe from
        """
        device_topics = [
            f"{self.TOPICS['device']}/{device_id}/status",
            f"{self.TOPICS['device']}/{device_id}/details",
            f"{self.TOPICS['device']}/{device_id}/message",
            f"{self.TOPICS['device']}/{device_id}/refresh",
        ]
        
        for topic in device_topics:
            self.unsubscribe_from_topic(topic)
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """
        Get subscription statistics.
        
        Returns:
            Dictionary containing subscription statistics
        """
        return {
            'total_subscriptions': len(self._subscribed_topics),
            'subscribed_topics': sorted(list(self._subscribed_topics)),
            'device_topics': [t for t in self._subscribed_topics if '/device/' in t],
            'zone_control_topics': [t for t in self._subscribed_topics if '/zone/' in t and '/set' in t],
            'system_topics': [t for t in self._subscribed_topics if t in [self.TOPICS['devices'], self.TOPICS['device_refresh']]]
        }
    
    def _publish_online(self):
        """Publish online status."""
        if self.connected:
            self.mqtt_client.publish(self.TOPICS['alive'], datetime.utcnow().isoformat())
            self.mqtt_client.publish(self.TOPICS['online'], 'true', qos=0, retain=True)
    
    def publish_device_status(self, device_id: str, status_data: Dict[str, Any], retain: bool = False):
        """
        Publish device status to MQTT.
        
        Args:
            device_id: Device ID
            status_data: Status data to publish
            retain: Whether to retain the message
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        topic = f"{self.TOPICS['device']}/{device_id}/status"
        payload = json.dumps(status_data) if status_data else ""
        
        return self.publish_with_retention(topic, payload, retain=retain)
    
    def publish_device_details(self, device_id: str, device_data: Dict[str, Any], retain: bool = True):
        """
        Publish device details to MQTT.
        
        Args:
            device_id: Device ID
            device_data: Complete device data
            retain: Whether to retain the message (default: True)
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        topic = f"{self.TOPICS['device']}/{device_id}/details"
        payload = json.dumps(device_data)
        
        return self.publish_with_retention(topic, payload, retain=retain)
    
    def publish_zone_info(self, device_id: str, zone_number: int, zone_data: Dict[str, Any], retain: bool = False):
        """
        Publish zone information to MQTT.
        
        Args:
            device_id: Device ID
            zone_number: Zone/station number
            zone_data: Zone data to publish
            retain: Whether to retain the message
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        topic = f"{self.TOPICS['device']}/{device_id}/zone/{zone_number}"
        payload = json.dumps(zone_data)
        
        return self.publish_with_retention(topic, payload, retain=retain)
    
    def publish_device_message(self, device_id: str, message_data: Dict[str, Any]):
        """
        Publish device message to MQTT.
        
        Args:
            device_id: Device ID
            message_data: Message data to publish
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        topic = f"{self.TOPICS['device']}/{device_id}/message"
        payload = json.dumps(message_data)
        
        return self.publish_with_retention(topic, payload, retain=False)
    
    def publish_devices_list(self, device_ids: List[str]):
        """
        Publish list of all device IDs.
        
        Args:
            device_ids: List of device IDs
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        topic = self.TOPICS['devices']
        payload = json.dumps(device_ids)
        
        return self.publish_with_retention(topic, payload, retain=False)
    
    def publish_device_data(self, device_id: str, device_data: Dict[str, Any]):
        """
        Publish complete device data including status, details, and zones.
        This matches the JavaScript implementation's device publishing logic.
        
        Args:
            device_id: Device ID
            device_data: Complete device data dictionary
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        try:
            # Extract components from device data
            status = device_data.get('status', {})
            zones = device_data.get('zones', {})
            
            # Publish device status (watering status only)
            watering_status = status.get('watering_status')
            if watering_status:
                status_payload = json.dumps(watering_status)
            else:
                status_payload = ""
            
            self.publish_device_status(device_id, status_payload)
            
            # Publish device details (retained)
            self.publish_device_details(device_id, device_data, retain=True)
            
            # Publish zone information for each zone
            if zones:
                for zone_number, zone_data in zones.items():
                    if isinstance(zone_number, str) and zone_number.isdigit():
                        zone_num = int(zone_number)
                        self.publish_zone_info(device_id, zone_num, zone_data)
                    else:
                        self.logger.warning(f"Invalid zone number for device {device_id}: {zone_number}")
            else:
                self.logger.warning(f"No zones data for device {device_id}")
            
            self.logger.info(f"Published complete device data for {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing device data for {device_id}: {e}")
            return False
    
    def publish_all_devices(self, devices_data: Dict[str, Dict[str, Any]]):
        """
        Publish data for all devices and the devices list.
        This matches the JavaScript implementation's devices publishing logic.
        
        Args:
            devices_data: Dictionary of device_id -> device_data
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        try:
            device_ids = []
            
            # Publish each device's data
            for device_id, device_data in devices_data.items():
                if not device_id:
                    self.logger.warning("Skipping device without ID")
                    continue
                
                device_ids.append(device_id)
                self.publish_device_data(device_id, device_data)
            
            # Publish devices list
            self.publish_devices_list(device_ids)
            
            self.logger.info(f"Published data for {len(device_ids)} devices")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing all devices data: {e}")
            return False
    
    def publish_with_retention(self, topic: str, payload: str, retain: bool = True, qos: int = 0):
        """
        Publish a message with retention control.
        
        Args:
            topic: MQTT topic
            payload: Message payload
            retain: Whether to retain the message
            qos: Quality of Service level
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return False
        
        try:
            result = self.mqtt_client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Track retained messages
                if retain:
                    self._retained_messages[topic] = {
                        'payload': payload,
                        'timestamp': time.time(),
                        'qos': qos
                    }
                else:
                    # Remove from retained messages if explicitly not retained
                    self._retained_messages.pop(topic, None)
                
                self.logger.debug(f"Published to {topic} (retain={retain}, qos={qos})")
                return True
            else:
                self.logger.error(f"Failed to publish to {topic}: MQTT error {result.rc}")
                return False
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def clear_retained_message(self, topic: str):
        """
        Clear a retained message by publishing an empty payload.
        
        Args:
            topic: Topic to clear
            
        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.connected:
            self.logger.warning("Cannot clear retained message - not connected to MQTT broker")
            return False
        
        try:
            result = self.mqtt_client.publish(topic, "", qos=0, retain=True)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Remove from tracking
                self._retained_messages.pop(topic, None)
                self.logger.info(f"Cleared retained message for topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to clear retained message for {topic}: MQTT error {result.rc}")
                return False
        except Exception as e:
            self.logger.error(f"Error clearing retained message for {topic}: {e}")
            return False
    
    def get_retained_messages(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all currently tracked retained messages.
        
        Returns:
            Dictionary of topic -> message info
        """
        return self._retained_messages.copy()
    
    def is_topic_retained(self, topic: str) -> bool:
        """
        Check if a topic has a retained message.
        
        Args:
            topic: Topic to check
            
        Returns:
            True if topic has retained message, False otherwise
        """
        return topic in self._retained_messages
    
    def get_retained_message_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a retained message.
        
        Args:
            topic: Topic to get info for
            
        Returns:
            Message info dict or None if not retained
        """
        return self._retained_messages.get(topic)
    
    def publish_device_state_persistent(self, device_id: str, device_data: Dict[str, Any]):
        """
        Publish device state with persistent retention for offline clients.
        This ensures new clients get the latest device state immediately.
        
        Args:
            device_id: Device ID
            device_data: Complete device data
        """
        if not self.connected:
            self.logger.warning("Cannot publish persistent state - not connected to MQTT broker")
            return False
        
        try:
            # Publish device details with retention
            details_topic = f"{self.TOPICS['device']}/{device_id}/details"
            details_payload = json.dumps(device_data)
            self.publish_with_retention(details_topic, details_payload, retain=True, qos=1)
            
            # Publish zone information with retention
            zones = device_data.get('zones', {})
            for zone_number, zone_data in zones.items():
                if isinstance(zone_number, str) and zone_number.isdigit():
                    zone_topic = f"{self.TOPICS['device']}/{device_id}/zone/{zone_number}"
                    zone_payload = json.dumps(zone_data)
                    self.publish_with_retention(zone_topic, zone_payload, retain=True, qos=1)
            
            # Publish online status with retention
            self.publish_with_retention(self.TOPICS['online'], 'true', retain=True, qos=1)
            
            self.logger.info(f"Published persistent state for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing persistent state for {device_id}: {e}")
            return False
    
    def cleanup_retained_messages(self, device_id: str):
        """
        Clean up retained messages for a specific device.
        This is useful when a device is removed or goes offline.
        
        Args:
            device_id: Device ID to clean up
        """
        if not self.connected:
            self.logger.warning("Cannot cleanup retained messages - not connected to MQTT broker")
            return False
        
        try:
            # Topics to clean up for the device
            topics_to_clean = [
                f"{self.TOPICS['device']}/{device_id}/details",
                f"{self.TOPICS['device']}/{device_id}/status",
            ]
            
            # Clean up zone topics (we don't know how many zones, so we'll clean known ones)
            for topic in list(self._retained_messages.keys()):
                if f"/device/{device_id}/zone/" in topic:
                    topics_to_clean.append(topic)
            
            # Clear each topic
            for topic in topics_to_clean:
                self.clear_retained_message(topic)
            
            self.logger.info(f"Cleaned up retained messages for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up retained messages for {device_id}: {e}")
            return False
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if a shutdown signal has been received.
        
        Returns:
            True if shutdown was requested, False otherwise
        """
        return self._shutdown_requested
    
    def request_shutdown(self):
        """
        Manually request a graceful shutdown.
        This can be called programmatically to initiate shutdown.
        """
        self.logger.info("Manual shutdown requested")
        self._shutdown_requested = True
    
    def get_signal_handlers_info(self) -> Dict[str, Any]:
        """
        Get information about signal handlers.
        
        Returns:
            Dictionary with signal handler information
        """
        return {
            'shutdown_requested': self._shutdown_requested,
            'registered_signals': list(self._original_signal_handlers.keys()),
            'signal_names': [signal.Signals(sig).name for sig in self._original_signal_handlers.keys()]
        }
    
    def get_env_config(self) -> Dict[str, Any]:
        """
        Get current environment variable configuration.
        
        Returns:
            Dictionary with current environment variable values
        """
        return self._load_env_config()
    
    def get_env_config_info(self) -> Dict[str, Any]:
        """
        Get detailed information about environment variable configuration.
        
        Returns:
            Dictionary with environment variable information
        """
        env_config = self._load_env_config()
        return {
            'available_env_vars': list(self.ENV_CONFIG_MAP.keys()),
            'env_config_map': self.ENV_CONFIG_MAP,
            'current_env_values': env_config,
            'default_config': self.DEFAULT_CONFIG,
            'current_config': self.config
        }
    
    def validate_env_config(self) -> Dict[str, Any]:
        """
        Validate current environment variable configuration.
        
        Returns:
            Dictionary with validation results
        """
        env_config = self._load_env_config()
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'invalid_values': []
        }
        
        # Check required configuration
        if not env_config.get('mqtt_broker'):
            validation_result['missing_required'].append('BHYVE_MQTT_BROKER')
            validation_result['valid'] = False
        
        # Validate integer values
        int_fields = ['mqtt_port', 'keepalive', 'connect_timeout', 'reconnect_period', 'max_retries', 'will_qos']
        for field in int_fields:
            if field in env_config:
                try:
                    int(env_config[field])
                except (ValueError, TypeError):
                    validation_result['invalid_values'].append(f"{self.ENV_CONFIG_MAP.get(field, field)}: {env_config[field]}")
                    validation_result['valid'] = False
        
        # Validate boolean values
        bool_fields = ['use_tls', 'clean_session', 'will_retain']
        for field in bool_fields:
            if field in env_config:
                if not isinstance(env_config[field], bool):
                    validation_result['warnings'].append(f"{self.ENV_CONFIG_MAP.get(field, field)}: {env_config[field]} (converted to boolean)")
        
        # Validate log level
        if 'log_level' in env_config:
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if env_config['log_level'].upper() not in valid_levels:
                validation_result['invalid_values'].append(f"BHYVE_LOG_LEVEL: {env_config['log_level']} (valid: {valid_levels})")
                validation_result['valid'] = False
        
        return validation_result
    
    def _handle_device_message(self, topic: str, payload: str):
        """Handle device-specific messages."""
        try:
            # Extract device ID from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3:
                device_id = topic_parts[2]
                
                # Handle zone control commands (e.g., bhyve/device/{id}/zone/{station}/set)
                if '/zone/' in topic and topic.endswith('/set'):
                    self._handle_zone_control_command(topic, payload)
                    
                elif topic.endswith('/status'):
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
    
    def _handle_zone_control_command(self, topic: str, payload: str):
        """Handle zone control commands with validation."""
        try:
            # Parse topic to extract device ID and station
            # Format: bhyve/device/{device_id}/zone/{station}/set
            topic_parts = topic.split('/')
            if len(topic_parts) < 6:
                raise ValueError(f"Invalid zone control topic format: {topic}")
            
            device_id = topic_parts[2]
            station_str = topic_parts[4]
            
            # Validate device ID
            if not device_id or device_id.strip() == '':
                raise ValueError('Invalid device ID in topic')
            
            # Validate station number
            try:
                station = int(station_str)
                if station < 0:
                    raise ValueError(f"Invalid station number: {station}")
            except ValueError:
                raise ValueError(f"Invalid station number: {station_str}")
            
            # Validate and parse command
            command = self.validate_command(payload)
            
            # Construct WebSocket message
            ws_message = self.construct_watering_message(device_id, station, command)
            
            # Log the command
            self.logger.info(f"Zone control command: Device {device_id}, Station {station}, Command {command}")
            self.logger.debug(f"WebSocket message: {json.dumps(ws_message, indent=2)}")
            
            # Trigger event for external handling (e.g., WebSocket forwarding)
            self._trigger_event('zone_control_command', device_id, {
                'station': station,
                'command': command,
                'ws_message': ws_message
            })
            
        except ValueError as e:
            self.logger.error(f"Zone control command validation failed: {e}")
            self._trigger_event('command_validation_error', topic, str(e))
        except Exception as e:
            self.logger.error(f"Error handling zone control command: {e}")
            self._trigger_event('command_error', topic, str(e))
    
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
        # Check if shutdown was requested
        if self._shutdown_requested:
            self.logger.info("Shutdown requested, skipping connection attempt")
            return False
            
        try:
            current_time = time.time()
            
            # Check if we should attempt reconnection based on retry logic
            if self._retry_count > 0:
                time_since_last_attempt = current_time - self._last_connect_attempt
                if time_since_last_attempt < self.config['reconnect_period']:
                    self.logger.debug(f"Waiting {self.config['reconnect_period'] - time_since_last_attempt:.1f}s before retry")
                    return False
            
            self._last_connect_attempt = current_time
            
            # Connect with advanced configuration
            self.mqtt_client.connect(
                self.mqtt_broker, 
                self.mqtt_port, 
                keepalive=self.config['keepalive']
            )
            
            # Start the network loop
            self.mqtt_client.loop_start()
            
            # Wait for connection to be established
            timeout_seconds = min(self.config['connect_timeout'], 10)  # Cap at 10 seconds for async
            for _ in range(timeout_seconds):
                if self.connected:
                    self._retry_count = 0  # Reset retry count on successful connection
                    self.logger.info(f"Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
                    self.logger.debug(f"Configuration: keepalive={self.config['keepalive']}s, "
                                    f"timeout={self.config['connect_timeout']}s, "
                                    f"clean_session={self.config['clean_session']}")
                    return True
                await asyncio.sleep(1)
            
            self._retry_count += 1
            self.logger.warning(f"Connection attempt {self._retry_count} failed (timeout)")
            return False
            
        except Exception as e:
            self._retry_count += 1
            self.logger.error(f"Failed to connect to MQTT broker (attempt {self._retry_count}): {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.connected = False
        
        # Restore original signal handlers
        self._restore_signal_handlers()
    
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
    
    def validate_command(self, message: str) -> Dict[str, Any]:
        """
        Validate command message against schema.
        
        Args:
            message: JSON string or dict to validate
            
        Returns:
            Validated command object
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Parse message to dict if it's a string
            if isinstance(message, str):
                command = json.loads(message)
            elif isinstance(message, dict):
                command = message
            else:
                raise ValueError("Message must be a JSON string or dict")
            
            # Validate command against schema
            self._validator.validate(command)
            
            # Normalize state to uppercase for consistency
            if 'state' in command:
                command['state'] = command['state'].upper()
            
            return command
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except ValidationError as e:
            errors = []
            for error in self._validator.iter_errors(command):
                errors.append(f"{'.'.join(str(p) for p in error.absolute_path) if error.absolute_path else 'root'}: {error.message}")
            raise ValueError(f"Command validation failed: {'; '.join(errors)}")
        except Exception as e:
            raise ValueError(f"Validation error: {e}")
    
    def construct_watering_message(self, device_id: str, station: int, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construct watering command message for WebSocket.
        
        Args:
            device_id: Device ID
            station: Station number
            command: Validated command dict
            
        Returns:
            WebSocket message dict
        """
        return {
            "event": "change_mode",
            "device_id": device_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "mode": "manual",
            "stations": [
                {
                    "station": station,
                    "run_time": command["time"]
                }
            ] if command["state"] == "ON" else []
        }
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current MQTT client configuration.
        
        Returns:
            Dictionary containing current configuration
        """
        return {
            'broker': self.mqtt_broker,
            'port': self.mqtt_port,
            'client_id': self.client_id,
            'use_tls': self.use_tls,
            'connected': self.connected,
            'retry_count': self._retry_count,
            'config': self.config.copy()
        }
    
    def get_retry_status(self) -> Dict[str, Any]:
        """
        Get current retry status and configuration.
        
        Returns:
            Dictionary containing retry information
        """
        return {
            'retry_count': self._retry_count,
            'max_retries': self.config['max_retries'],
            'reconnect_period': self.config['reconnect_period'],
            'last_connect_attempt': self._last_connect_attempt,
            'can_retry': self._retry_count < self.config['max_retries'],
            'time_until_next_retry': max(0, self.config['reconnect_period'] - (time.time() - self._last_connect_attempt))
        }
