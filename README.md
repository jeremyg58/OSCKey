# OSCKey

A macOS application that receives OSC (Open Sound Control) messages and triggers keyboard shortcuts. Perfect for integrating lighting consoles, DAWs, and other OSC-enabled software with your Mac's keyboard shortcuts.

## Features

- **OSC to Keyboard Bridge**: Receive OSC messages and trigger keyboard shortcuts
- **Web Configuration Interface**: Easy-to-use web UI for managing shortcuts
- **Custom Shortcuts**: Define your own OSC addresses mapped to key combinations
- **Real-time Log Viewer**: Monitor OSC messages and key presses with filtering
- **Magnet Integration**: Special AppleScript integration for window management apps
- **Modifier Key Support**: Command, Option, Control, and Shift
- **Special Keys**: Arrows, function keys, and more

## Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jeremyg58/OSCKey.git
   cd OSCKey
   ```

2. **Install dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python3 osckey.py
   ```

   On first run, macOS will prompt you to grant **Accessibility permissions**. Click "Open System Settings" and enable the permission. If the dialog doesn't appear automatically, you can grant permissions manually:
   - Open **System Settings** → **Privacy & Security** → **Accessibility**
   - Add your **Terminal** or **Python** application and enable it

4. **Open the web interface**:
   - Navigate to http://localhost:5000
   - Configure your shortcuts

## Usage

### Basic OSC Messages

Send OSC messages to port **5005** (configurable via web UI):

- **Single key**: `/key s` → Press 's'
- **With modifiers**: `/key command s` → Cmd+S (Save)
- **Multiple modifiers**: `/key command shift z` → Cmd+Shift+Z (Redo)
- **Arrow keys**: `/key/left` → Left Arrow
- **With modifiers**: `/key control option right` → Ctrl+Opt+Right

### Supported Modifiers

- `command` or `cmd`
- `option` or `opt` or `alt`
- `control` or `ctrl`
- `shift`

### Special Keys

`space`, `enter`, `tab`, `backspace`, `delete`, `esc`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `f1`-`f12`

### Custom Shortcuts

Use the web interface to create custom shortcuts:

1. Open http://localhost:5000
2. Go to "Add New Shortcut"
3. Enter OSC address (e.g., `/key/windowright`)
4. Select modifiers
5. Enter key
6. Click "Add Shortcut"

Now you can trigger it with a simple OSC message: `/key/windowright`

## Configuration

### Web UI

- **URL**: http://localhost:5000
- **Configuration Tab**: Manage OSC server settings and custom shortcuts
- **Logs Tab**: Real-time log viewer with OSC message filtering

### Configuration File

Settings are saved to `osc_keyboard_config.json`:

```json
{
  "osc_port": 5005,
  "osc_ip": "0.0.0.0",
  "custom_shortcuts": {
    "/key/save": {
      "modifiers": ["command"],
      "key": "s",
      "description": "Save"
    }
  }
}
```

## Integration Examples

### ETC Eos Consoles

```
[Macro] OSC String: /key/windowright
```

### TouchOSC

1. Add a button
2. Set OSC message: `/key command s`
3. Set destination: Your Mac's IP, port 5005

### Max/MSP

```
[udpsend 127.0.0.1 5005]
|
[/key command s(
```

### Python

```python
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 5005)
client.send_message("/key", "command s")
```

## Magnet Integration

OSCKey has special compatibility for [Magnet](https://magnet.crowdcafe.com/) and similar window management apps. Arrow key combinations with modifiers automatically use AppleScript for maximum compatibility.

Example shortcuts for Magnet:
- `/key/windowleft` → Control+Option+Left (Move window left)
- `/key/windowright` → Control+Option+Right (Move window right)

## Running as a Service

### Launch Agent (Auto-start on login)

1. Create `~/Library/LaunchAgents/com.osckey.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.osckey</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/OSCKey/osckey.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/osckey.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/osckey-error.log</string>
</dict>
</plist>
```

2. Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.osckey.plist
```

## Troubleshooting

### Keys not working

The application automatically checks for accessibility permissions on startup. If keyboard control isn't working:

1. Check the console output for permission warnings
2. Manually verify **Accessibility permissions** in System Settings → Privacy & Security → Accessibility
3. Restart the application after granting permissions
4. Check the logs tab in the web UI for errors

### Port already in use

Change the port in the web UI or edit `osc_keyboard_config.json`

### OSC messages not received

1. Verify the application is running on the correct IP/port
2. Check firewall settings
3. Use the logs tab to see if messages are arriving

## Requirements

- macOS 10.14 or later
- Python 3.7+
- Dependencies listed in `requirements.txt`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please use the [GitHub Issues](https://github.com/yourusername/OSCKey/issues) page.
