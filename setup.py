#!/usr/bin/env python3
"""
Orbit Bhyve Package Setup Script
"""

import os
import subprocess
import sys

def main():
    """Setup the Orbit Bhyve package"""
    print("🌱 Orbit Bhyve Package Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("📝 Creating .env file from template...")
        if os.path.exists('env.example'):
            with open('env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ Created .env file - please edit with your credentials")
        else:
            print("❌ No env.example file found")
            return False
    else:
        print("✅ .env file already exists")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False
    
    # Install package in development mode
    print("\n🔧 Installing package in development mode...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], check=True)
        print("✅ Package installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install package")
        return False
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your Bhyve credentials")
    print("2. Run: python -m orbit_bhyve")
    print("3. Open browser to: http://localhost:5001")
    
    return True

if __name__ == '__main__':
    main()