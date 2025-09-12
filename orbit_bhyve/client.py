"""
WebSocket-based client for Orbit Bhyve irrigation controllers.

This module provides real-time communication with Orbit Bhyve devices
using WebSocket connections for both monitoring and control.
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import threading
import time

from .exceptions import (
    BhyveAuthenticationError,
    BhyveConnectionError,
    BhyveAPIError,
)


class BhyveClient:
    """
    WebSocket-based client for Orbit Bhyve irrigation controllers.
    
    This client provides real-time communication with Bhyve devices
    using WebSocket connections for both monitoring and control.
    """
    
    BASE_URL = "https://api.orbitbhyve.com"
    WS_URL = "wss://api.orbitbhyve.com/v1/events"
    
    def __init__(self, username: str = None, password: str = None, token: str = None):
        """
        Initialize the WebSocket client.
        
        Args:
            username: Bhyve account username/email
            password: Bhyve account password
            token: Pre-obtained orbit session token
        """
        self.username = username
        self.password = password
        self.token = token
        self.user_id = None
        self.device_id = None
        self.websocket = None
        self.connected = False
        self.event_handlers = {}
        self.devices = {}
        self.loop = None
        self.thread = None
        self.logger = logging.getLogger(__name__)
        
    async def authenticate(self) -> bool:
        """
        Authenticate with the Bhyve API.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            BhyveAuthenticationError: If authentication fails
            BhyveConnectionError: If there's a connection issue
        """
        if not self.username or not self.password:
            raise BhyveAuthenticationError(
                "Username and password are required for authentication"
            )

        try:
            import requests
            
            # Use the correct API endpoint and payload structure
            auth_data = {
                "session": {
                    "email": self.username,
                    "password": self.password
                }
            }

            response = requests.post(
                f"{self.BASE_URL}/v1/session", json=auth_data, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("orbit_session_token")
                self.user_id = data.get("user_id")
                
                if self.token:
                    return True
                else:
                    raise BhyveAuthenticationError(
                        "No orbit_session_token received from authentication"
                    )
            else:
                raise BhyveAuthenticationError(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )

        except Exception as e:
            raise BhyveConnectionError(
                f"Connection error during authentication: {str(e)}"
            )

    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.token:
            raise BhyveAuthenticationError("Not authenticated. Call authenticate() first.")

        try:
            self.websocket = await websockets.connect(self.WS_URL)
            self.connected = True
            
            # Send authentication message
            auth_message = {
                "event": "app_connection",
                "orbit_session_token": self.token
            }
            
            await self.websocket.send(json.dumps(auth_message))
            self.logger.info("Connected to WebSocket and sent authentication")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except Exception as e:
            self.connected = False
            raise BhyveConnectionError(f"Failed to connect to WebSocket: {str(e)}")

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            self.logger.info("Disconnected from WebSocket")

    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"Received non-JSON message: {message}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error in message listener: {e}")
            self.connected = False

    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        event_type = data.get("event")
        
        # Update device data based on message type
        device_id = data.get("device_id")
        if device_id and device_id in self.devices:
            device_data = self.devices[device_id]
            # Check if it's a BhyveDevice object or just a dict
            if hasattr(device_data, '_update_from_websocket'):
                device_data._update_from_websocket(data)
            else:
                # If it's just a dict, we can't update it directly
                # This happens when we store raw device data instead of BhyveDevice objects
                self.logger.debug(f"Received message for device {device_id}, but device is not a BhyveDevice object")
        
        # Call event handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
        
        # Log the message
        self.logger.debug(f"Received: {json.dumps(data, indent=2)}")

    def on_event(self, event_type: str, handler: Callable):
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle (e.g., 'watering_in_progress_notification')
            handler: Function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices associated with the account.
        
        Returns:
            List of device dictionaries
        """
        if not self.token or not self.user_id:
            raise BhyveAuthenticationError("Not authenticated. Call authenticate() first.")

        try:
            import requests
            
            response = requests.get(
                f"{self.BASE_URL}/v1/devices?user_id={self.user_id}",
                headers={"orbit-session-token": self.token},
                timeout=30
            )

            if response.status_code == 200:
                devices_data = response.json()
                self.devices = {device["id"]: device for device in devices_data}
                return devices_data
            else:
                raise BhyveAPIError(
                    f"Failed to get devices: {response.status_code} - {response.text}"
                )

        except Exception as e:
            raise BhyveConnectionError(f"Connection error getting devices: {str(e)}")

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a command to the WebSocket server.
        
        Args:
            command: Command dictionary to send
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.connected or not self.websocket:
            raise BhyveConnectionError("Not connected to WebSocket")
        
        try:
            await self.websocket.send(json.dumps(command))
            self.logger.info(f"Sent command: {json.dumps(command, indent=2)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return False

    async def start_watering(self, device_id: str, station: int, duration_seconds: int = 300) -> bool:
        """
        Start watering a specific station.
        
        Args:
            device_id: ID of the device
            station: Station number (1-12)
            duration_seconds: Duration in seconds to water
            
        Returns:
            True if command sent successfully, False otherwise
        """
        from datetime import datetime
        
        command = {
            "event": "change_mode",
            "device_id": device_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "mode": "manual",
            "stations": [
                {
                    "station": station,
                    "run_time": duration_seconds / 60.0  # Convert to minutes
                }
            ]
        }
        
        return await self.send_command(command)

    async def stop_watering(self, device_id: str) -> bool:
        """
        Stop all watering on a device.
        
        Args:
            device_id: ID of the device
            
        Returns:
            True if command sent successfully, False otherwise
        """
        from datetime import datetime
        
        # First, stop watering by setting manual mode with empty stations
        stop_command = {
            "event": "change_mode",
            "device_id": device_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "mode": "manual",
            "stations": []
        }
        
        # Send the stop command
        result = await self.send_command(stop_command)
        
        # Then return to auto mode
        auto_command = {
            "event": "change_mode",
            "device_id": device_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "mode": "auto"
        }
        
        # Send the auto mode command
        auto_result = await self.send_command(auto_command)
        
        return result and auto_result

    async def set_device_mode(self, device_id: str, mode: str) -> bool:
        """
        Set device run mode.
        
        Args:
            device_id: ID of the device
            mode: Run mode ('auto', 'manual', 'off')
            
        Returns:
            True if command sent successfully, False otherwise
        """
        command = {
            "event": "change_mode",
            "device_id": device_id,
            "mode": mode,
            "program": None,
            "stations": []
        }
        
        return await self.send_command(command)

    async def get_schedules(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get all schedules for a device via WebSocket.
        
        Note: This method sends a WebSocket command to request schedules.
        The actual schedule data will be received via WebSocket events.
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of schedule dictionaries (may be empty if no schedules exist)
            
        Raises:
            BhyveAuthenticationError: If not authenticated
            BhyveConnectionError: If not connected to WebSocket
        """
        if not self.token or not self.user_id:
            raise BhyveAuthenticationError("Not authenticated. Call authenticate() first.")
        
        if not self.connected or not self.websocket:
            raise BhyveConnectionError("Not connected to WebSocket. Call connect() first.")

        try:
            # Send WebSocket command to get schedules
            command = {
                "event": "program_list",
                "device_id": device_id
            }
            
            success = await self.send_command(command)
            if success:
                # Note: The actual schedule data will be received via WebSocket events
                # This method returns an empty list as a placeholder
                # In a real implementation, you would store the received schedules
                # and return them from a cache or state management system
                self.logger.info(f"Requested schedules for device {device_id}")
                return []
            else:
                self.logger.error(f"Failed to request schedules for device {device_id}")
                return []

        except Exception as e:
            raise BhyveConnectionError(f"Error requesting schedules: {str(e)}")

    async def create_schedule(self, device_id: str, schedule_data: Dict[str, Any]) -> bool:
        """
        Create a new schedule for a device.
        
        Args:
            device_id: ID of the device
            schedule_data: Schedule configuration dictionary
            
        Returns:
            True if schedule created successfully, False otherwise
        """
        command = {
            "event": "program_save",
            "device_id": device_id,
            "program": schedule_data
        }
        
        return await self.send_command(command)

    async def update_schedule(self, device_id: str, program_id: str, schedule_data: Dict[str, Any]) -> bool:
        """
        Update an existing schedule.
        
        Args:
            device_id: ID of the device
            program_id: ID of the program to update
            schedule_data: Updated schedule configuration
            
        Returns:
            True if schedule updated successfully, False otherwise
        """
        # Include the program_id in the schedule data
        schedule_data["id"] = program_id
        
        command = {
            "event": "program_save",
            "device_id": device_id,
            "program": schedule_data
        }
        
        return await self.send_command(command)

    async def delete_schedule(self, device_id: str, program_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            device_id: ID of the device
            program_id: ID of the program to delete
            
        Returns:
            True if schedule deleted successfully, False otherwise
        """
        command = {
            "event": "program_delete",
            "device_id": device_id,
            "program_id": program_id
        }
        
        return await self.send_command(command)

    async def enable_schedule(self, device_id: str, program_id: str) -> bool:
        """
        Enable a schedule.
        
        Args:
            device_id: ID of the device
            program_id: ID of the program to enable
            
        Returns:
            True if schedule enabled successfully, False otherwise
        """
        command = {
            "event": "program_enable",
            "device_id": device_id,
            "program_id": program_id
        }
        
        return await self.send_command(command)

    async def disable_schedule(self, device_id: str, program_id: str) -> bool:
        """
        Disable a schedule.
        
        Args:
            device_id: ID of the device
            program_id: ID of the program to disable
            
        Returns:
            True if schedule disabled successfully, False otherwise
        """
        command = {
            "event": "program_disable",
            "device_id": device_id,
            "program_id": program_id
        }
        
        return await self.send_command(command)

    def run_sync(self, coro):
        """Run an async coroutine in a sync context."""
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        return self.loop.run_until_complete(coro)

    def start_background_loop(self):
        """Start the event loop in a background thread."""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def _run_loop(self):
        """Run the event loop in a background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def close(self):
        """Close the client and clean up resources."""
        await self.disconnect()
        if self.loop and not self.loop.is_closed():
            self.loop.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.loop and not self.loop.is_closed():
            self.loop.run_until_complete(self.close())
