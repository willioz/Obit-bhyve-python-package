#!/usr/bin/env python3
"""
Orbit Bhyve Package CLI Entry Point
"""

import asyncio
import sys
import argparse
from .gateway import BhyveMQTTGateway

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Orbit Bhyve MQTT Gateway')
    parser.add_argument('--mode', choices=['gateway', 'dashboard'], default='gateway',
                       help='Run mode: gateway (default) or dashboard')
    parser.add_argument('--broker', default='localhost',
                       help='MQTT broker address (default: localhost)')
    parser.add_argument('--port', type=int, default=1883,
                       help='MQTT broker port (default: 1883)')
    
    args = parser.parse_args()
    
    if args.mode == 'gateway':
        print("🚀 Starting Bhyve MQTT Gateway...")
        gateway = BhyveMQTTGateway()
        asyncio.run(gateway.run())
    elif args.mode == 'dashboard':
        print("🌐 Starting Bhyve Web Dashboard...")
        from .examples.mqtt_dashboard import main as dashboard_main
        dashboard_main()

if __name__ == '__main__':
    main()
