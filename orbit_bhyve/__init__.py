"""
Orbit Bhyve Python Package

A Python package for controlling and managing Orbit Bhyve irrigation controllers.
This package provides an easy-to-use interface for interacting with Bhyve devices
via MQTT for real-time control and monitoring.

Author: William Chevrier
Version: 0.3.0
License: MIT
"""

from .mqtt_client import BhyveMQTTClient as BhyveClient
from .exceptions import BhyveError, BhyveConnectionError, BhyveAuthenticationError

__version__ = "0.3.0"
__author__ = "William Chevrier"
__email__ = "williamchevrier@sablierechevrier.com"
__license__ = "MIT"

__all__ = [
    "BhyveClient",
    "BhyveError",
    "BhyveConnectionError",
    "BhyveAuthenticationError",
]
