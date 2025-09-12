"""
WebSocket-based device representation for Orbit Bhyve irrigation controllers.

This module provides real-time device monitoring and control using WebSocket data.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .exceptions import BhyveDeviceError


class BhyveDevice:
    """
    Represents a Bhyve irrigation controller device with WebSocket support.
    
    This class provides real-time monitoring and control of individual Bhyve devices
    using WebSocket data for up-to-date status information.
    """
    
    def __init__(self, device_data: Dict[str, Any], client=None):
        """
        Initialize a WebSocket-enabled Bhyve device.
        
        Args:
            device_data: Dictionary containing device information from the API
            client: BhyveWebSocketClient instance for making WebSocket calls
        """
        self._data = device_data
        self._client = client
        self._id = device_data.get("id")
        self._name = device_data.get("name", "Unknown Device")
        self._type = device_data.get("type", "unknown")
        
        # Parse the status object which contains detailed device information
        status = device_data.get("status") or {}
        self._status = status
        self._run_mode = status.get("run_mode", "unknown")
        self._watering_status = status.get("watering_status") or {}
        self._is_watering = (status.get("watering_status") or {}).get("status") == "watering_in_progress"
        
        # Extract additional device info
        self._battery_level = device_data.get("battery_level")
        self._signal_strength = device_data.get("signal_strength")
        self._last_seen = device_data.get("status_updated_at")
        self._is_connected = device_data.get("is_connected", False)
        self._firmware_version = device_data.get("firmware_version")
        self._hardware_version = device_data.get("hardware_version")
        self._num_stations = device_data.get("num_stations", 0)
        self._zones = device_data.get("zones", [])
        
        # WebSocket event data
        self._last_websocket_update = None
        self._websocket_data = {}

    def _update_from_websocket(self, data: Dict[str, Any]):
        """Update device data from WebSocket message."""
        if not data:
            return
            
        self._last_websocket_update = datetime.now(timezone.utc)
        self._websocket_data = data
        
        # Update status based on WebSocket event
        event_type = data.get("event")
        
        if event_type == "change_mode":
            self._run_mode = data.get("mode", self._run_mode)
            if data.get("stations"):
                # Update watering status for manual mode
                self._watering_status = {
                    "stations": data.get("stations", []),
                    "status": "watering_in_progress" if data.get("stations") else "idle"
                }
                self._is_watering = bool(data.get("stations"))
        
        elif event_type == "watering_in_progress_notification":
            self._watering_status = {
                "current_station": data.get("current_station"),
                "status": data.get("status"),
                "time_remaining": data.get("total_run_time_sec", 0),
                "started_at": data.get("started_watering_station_at"),
                "stations": data.get("water_event_queue", []),
                "rain_sensor_hold": data.get("rain_sensor_hold", False)
            }
            self._is_watering = data.get("status") == "watering_in_progress"
        
        elif event_type == "device_idle":
            self._is_watering = False
            self._watering_status = {"status": "idle"}
        
        elif event_type == "device_connected":
            self._is_connected = True
            self._firmware_version = data.get("fw_version", self._firmware_version)
            self._hardware_version = data.get("hw_version", self._hardware_version)
            self._num_stations = data.get("num_stations", self._num_stations)

    @property
    def id(self) -> str:
        """Get the device ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the device name."""
        return self._name

    @property
    def type(self) -> str:
        """Get the device type."""
        return self._type

    @property
    def status(self) -> Dict[str, Any]:
        """Get the device status."""
        return self._status

    @property
    def run_mode(self) -> str:
        """Get the device run mode (auto, manual, etc.)."""
        return self._run_mode

    @property
    def is_watering(self) -> bool:
        """Check if the device is currently watering."""
        return self._is_watering

    @property
    def watering_status(self) -> Dict[str, Any]:
        """Get detailed watering status information."""
        return self._watering_status

    @property
    def battery_level(self) -> Optional[int]:
        """Get the battery level percentage (if applicable)."""
        return self._battery_level

    @property
    def signal_strength(self) -> Optional[int]:
        """Get the signal strength (if applicable)."""
        return self._signal_strength

    @property
    def last_seen(self) -> Optional[datetime]:
        """Get the last seen timestamp."""
        if self._last_seen:
            try:
                return datetime.fromisoformat(self._last_seen.replace('Z', '+00:00'))
            except:
                return None
        return None

    @property
    def is_online(self) -> bool:
        """Check if the device is online."""
        return self._is_connected

    @property
    def firmware_version(self) -> Optional[str]:
        """Get the firmware version."""
        return self._firmware_version

    @property
    def hardware_version(self) -> Optional[str]:
        """Get the hardware version."""
        return self._hardware_version

    @property
    def num_stations(self) -> int:
        """Get the number of stations."""
        return self._num_stations

    @property
    def zones(self) -> List[Dict[str, Any]]:
        """Get the zones configuration."""
        return self._zones

    @property
    def last_websocket_update(self) -> Optional[datetime]:
        """Get the last WebSocket update time."""
        return self._last_websocket_update

    def get_valves(self) -> List[Dict[str, Any]]:
        """
        Get information about all valves (stations) on this device.

        Returns:
            List of valve/station information dictionaries
        """
        valves = []
        
        # Check if there are stations in the watering status
        watering_status = self._watering_status
        if "stations" in watering_status:
            for station in watering_status["stations"]:
                valve_info = {
                    "id": f"station_{station.get('station', 'unknown')}",
                    "name": f"Station {station.get('station', 'unknown')}",
                    "station": station.get("station"),
                    "run_time": station.get("run_time"),
                    "status": "active" if station.get("run_time", 0) > 0 else "inactive"
                }
                valves.append(valve_info)
        
        # If no stations in watering status, create default stations
        if not valves:
            for i in range(1, self._num_stations + 1):
                valve_info = {
                    "id": f"station_{i}",
                    "name": f"Station {i}",
                    "station": i,
                    "run_time": 0,
                    "status": "inactive"
                }
                valves.append(valve_info)
        
        return valves

    def get_current_watering_info(self) -> Dict[str, Any]:
        """
        Get current watering information for the device.
        
        Returns:
            Dictionary with current watering status information
        """
        watering_status = self._watering_status
        
        if not watering_status or watering_status.get("status") != "watering_in_progress":
            return {
                "is_watering": False,
                "current_station": None,
                "time_remaining": 0,
                "total_time": 0
            }
        
        return {
            "is_watering": True,
            "current_station": watering_status.get("current_station"),
            "time_remaining": watering_status.get("time_remaining", 0),
            "total_time": watering_status.get("time_remaining", 0),
            "started_at": watering_status.get("started_at"),
            "stations": watering_status.get("stations", []),
            "rain_sensor_hold": watering_status.get("rain_sensor_hold", False)
        }

    async def start_watering_station(self, station: int, duration_seconds: int = 300) -> bool:
        """
        Start watering a specific station.
        
        Args:
            station: Station number (1-12)
            duration_seconds: Duration in seconds to water
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.start_watering(self._id, station, duration_seconds)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to start watering station: {str(e)}")

    async def stop_watering(self) -> bool:
        """
        Stop all watering on this device.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.stop_watering(self._id)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to stop watering: {str(e)}")

    async def set_mode(self, mode: str) -> bool:
        """
        Set device run mode (auto, manual, off).
        
        Args:
            mode: Run mode ('auto', 'manual', 'off')
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.set_device_mode(self._id, mode)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to set device mode: {str(e)}")

    async def get_schedules(self) -> List[Dict[str, Any]]:
        """
        Get all schedules for this device.
        
        Returns:
            List of schedule dictionaries
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.get_schedules(self._id)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to get schedules: {str(e)}")

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> bool:
        """
        Create a new schedule for this device.
        
        Args:
            schedule_data: Schedule configuration dictionary
            
        Returns:
            True if schedule created successfully, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.create_schedule(self._id, schedule_data)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to create schedule: {str(e)}")

    async def update_schedule(self, program_id: str, schedule_data: Dict[str, Any]) -> bool:
        """
        Update an existing schedule.
        
        Args:
            program_id: ID of the program to update
            schedule_data: Updated schedule configuration
            
        Returns:
            True if schedule updated successfully, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.update_schedule(self._id, program_id, schedule_data)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to update schedule: {str(e)}")

    async def delete_schedule(self, program_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            program_id: ID of the program to delete
            
        Returns:
            True if schedule deleted successfully, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.delete_schedule(self._id, program_id)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to delete schedule: {str(e)}")

    async def enable_schedule(self, program_id: str) -> bool:
        """
        Enable a schedule.
        
        Args:
            program_id: ID of the program to enable
            
        Returns:
            True if schedule enabled successfully, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.enable_schedule(self._id, program_id)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to enable schedule: {str(e)}")

    async def disable_schedule(self, program_id: str) -> bool:
        """
        Disable a schedule.
        
        Args:
            program_id: ID of the program to disable
            
        Returns:
            True if schedule disabled successfully, False otherwise
            
        Raises:
            BhyveDeviceError: If the device is not available or client not available
        """
        if not self._client:
            raise BhyveDeviceError("No client available for WebSocket calls")
            
        try:
            return await self._client.disable_schedule(self._id, program_id)
        except Exception as e:
            raise BhyveDeviceError(f"Failed to disable schedule: {str(e)}")

    def get_device_info(self) -> Dict[str, Any]:
        """Get comprehensive device information."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "run_mode": self.run_mode,
            "is_watering": self.is_watering,
            "watering_status": self.watering_status,
            "battery_level": self.battery_level,
            "signal_strength": self.signal_strength,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": self.is_online,
            "firmware_version": self.firmware_version,
            "hardware_version": self.hardware_version,
            "num_stations": self.num_stations,
            "zones": self.zones,
            "valves": self.get_valves(),
            "current_watering": self.get_current_watering_info(),
            "last_websocket_update": self.last_websocket_update.isoformat() if self.last_websocket_update else None,
        }

    def __str__(self) -> str:
        """String representation of the device."""
        return f"BhyveWebSocketDevice(id={self.id}, name='{self.name}', type='{self.type}', mode='{self.run_mode}')"
