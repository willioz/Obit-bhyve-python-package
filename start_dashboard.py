#!/usr/bin/env python3
"""
Orbit Bhyve Web Dashboard Startup Script

This script starts the web dashboard for monitoring and controlling Bhyve devices.
Make sure you have set BHYVE_USERNAME and BHYVE_PASSWORD in your .env file.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_credentials():
    """Check if credentials are available."""
    username = os.getenv("BHYVE_USERNAME")
    password = os.getenv("BHYVE_PASSWORD")
    
    if not username or not password:
        print("❌ Error: BHYVE_USERNAME and BHYVE_PASSWORD must be set in your .env file")
        print("\n📝 Create a .env file with:")
        print("BHYVE_USERNAME=your@email.com")
        print("BHYVE_PASSWORD=yourpassword")
        return False
    
    return True

def main():
    """Main function to start the dashboard."""
    print("🌱 Orbit Bhyve Web Dashboard")
    print("=" * 40)
    
    if not check_credentials():
        sys.exit(1)
    
    print("✅ Credentials found")
    print("🚀 Starting web dashboard...")
    print("\n📱 Open your browser to: http://localhost:5000")
    print("🔧 Press Ctrl+C to stop the dashboard")
    print("-" * 40)
    
    try:
        # Import and run the working dashboard
        from examples.working_dashboard import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
