"""
Orbit Bhyve Python Package

A Python package for controlling and managing Orbit Bhyve irrigation controllers.
This package provides an easy-to-use interface for interacting with Bhyve devices
through their WebSocket API for real-time control and monitoring.

Author: William Chevrier
Version: 0.2.0
License: MIT
"""

from .client import BhyveClient
from .device import BhyveDevice
from .exceptions import BhyveError, BhyveConnectionError, BhyveAuthenticationError

__version__ = "0.2.0"
__author__ = "William Chevrier"
__email__ = "williamchevrier@sablierechevrier.com"
__license__ = "MIT"

__all__ = [
    "BhyveClient",
    "BhyveDevice", 
    "BhyveError",
    "BhyveConnectionError",
    "BhyveAuthenticationError",
]
