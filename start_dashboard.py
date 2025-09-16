#!/usr/bin/env python3
"""
Orbit Bhyve MQTT Dashboard Startup Script

This script starts the MQTT-based dashboard for monitoring and controlling Bhyve devices.
Configure your MQTT settings in the .env file.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_mqtt_config():
    """Check if MQTT configuration is available."""
    broker = os.getenv("MQTT_BROKER")
    port = os.getenv("MQTT_PORT")
    
    if not broker:
        print("❌ Error: MQTT_BROKER must be set in your .env file")
        print("\n📝 Create a .env file with:")
        print("MQTT_BROKER=localhost")
        print("MQTT_PORT=1883")
        return False
    
    return True

def main():
    """Main function to start the dashboard."""
    print("🌱 Orbit Bhyve MQTT Dashboard")
    print("=" * 40)
    
    if not check_mqtt_config():
        sys.exit(1)
    
    print("✅ MQTT configuration found")
    print("🚀 Starting MQTT dashboard...")
    print("\n📱 Open your browser to: http://localhost:5001")
    print("🔧 Press Ctrl+C to stop the dashboard")
    print("-" * 40)
    
    try:
        # Import and run the MQTT dashboard
        from examples.mqtt_dashboard import app
        app.run(debug=False, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
