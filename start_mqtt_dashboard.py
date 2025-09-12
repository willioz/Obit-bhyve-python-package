#!/usr/bin/env python3
"""
Start the MQTT-based Bhyve Dashboard
"""

import sys
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    # Check for MQTT configuration
    mqtt_broker = os.getenv("MQTT_BROKER")
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    
    if not mqtt_broker:
        print("❌ Please set MQTT_BROKER environment variable in your .env file.")
        print("   Example: MQTT_BROKER=localhost")
        sys.exit(1)
    
    print("🌱 Orbit Bhyve MQTT Dashboard")
    print("=" * 40)
    print("✅ MQTT broker configured")
    print(f"   Broker: {mqtt_broker}")
    print(f"   Username: {mqtt_username or 'None'}")
    print(f"   Password: {'***' if mqtt_password else 'None'}")
    print("🚀 Starting MQTT dashboard...")
    print("\n📱 Open your browser to: http://localhost:5001")
    print("🔧 Press Ctrl+C to stop the dashboard")
    print("-" * 40)

    try:
        from examples.mqtt_dashboard import app
        app.run(debug=False, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
