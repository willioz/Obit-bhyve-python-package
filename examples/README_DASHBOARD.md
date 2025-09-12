# 🌱 Orbit Bhyve Web Dashboard

A beautiful, real-time web interface for monitoring and controlling your Orbit Bhyve irrigation devices.

## Features

- **Real-time Monitoring** - Live device status and watering progress
- **Manual Control** - Start/stop watering on any station
- **Mode Control** - Set device modes (Auto, Manual, Off)
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Auto-refresh** - Updates every 5 seconds automatically
- **WebSocket Integration** - Real-time communication with Bhyve devices

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Credentials**
   Create a `.env` file in the project root:
   ```bash
   BHYVE_USERNAME=your@email.com
   BHYVE_PASSWORD=yourpassword
   ```

3. **Start the Dashboard**
   ```bash
   python start_dashboard.py
   ```

4. **Open Your Browser**
   Navigate to: http://localhost:5000

## Usage

### Device Monitoring
- View all your Bhyve devices in real-time
- See device status (Online/Offline)
- Monitor watering progress and remaining time
- Check device mode and configuration

### Manual Control
- **Start Watering**: Select a station and duration, then click "Start Watering"
- **Stop Watering**: Click "Stop All" to stop all watering on a device
- **Change Mode**: Use the mode buttons (Auto, Manual, Off) to change device behavior

### Real-time Updates
- The dashboard automatically refreshes every 5 seconds
- WebSocket events provide instant updates when watering starts/stops
- Connection status is shown in the top status bar

## API Endpoints

The dashboard also provides REST API endpoints for integration:

- `GET /api/devices` - Get all device data
- `POST /api/device/{id}/start_watering` - Start watering a station
- `POST /api/device/{id}/stop_watering` - Stop all watering
- `POST /api/device/{id}/set_mode` - Set device mode
- `GET /api/refresh` - Refresh device data

## Troubleshooting

### Connection Issues
- Ensure your `.env` file has correct credentials
- Check your internet connection
- Verify your Bhyve account is active

### Device Not Showing
- Make sure the device is online in the Bhyve mobile app
- Check that the device is connected to WiFi
- Try refreshing the page

### Watering Not Starting
- Ensure the device is in Manual mode
- Check that the selected station is valid
- Verify the device is online

## Customization

The dashboard is built with Flask and can be easily customized:

- **Templates**: Modify `examples/templates/dashboard.html`
- **Styling**: Update the CSS in the HTML template
- **Functionality**: Extend `examples/web_dashboard.py`

## Security Notes

- The dashboard runs on `0.0.0.0:5000` by default (accessible from any network)
- For production use, consider:
  - Running behind a reverse proxy (nginx)
  - Adding authentication
  - Using HTTPS
  - Restricting access to specific IP addresses

## Requirements

- Python 3.7+
- Flask 2.0+
- Orbit Bhyve account
- Network access to Bhyve devices

## Support

If you encounter issues:
1. Check the console output for error messages
2. Verify your credentials and network connection
3. Ensure all dependencies are installed
4. Check the Bhyve mobile app to confirm device status
