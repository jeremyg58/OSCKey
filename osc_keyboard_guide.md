# OSCKey - Complete Usage Guide

A Python application that receives OSC (Open Sound Control) messages and triggers keyboard shortcuts on macOS.

---

## Table of Contents
1. [Installation](#installation)
2. [Initial Setup](#initial-setup)
3. [Running the Application](#running-the-application)
4. [OSC Message Format](#osc-message-format)
5. [Examples](#examples)
6. [Testing with OSC Clients](#testing-with-osc-clients)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

---

## Installation

### Prerequisites
- macOS (tested on macOS 10.14+)
- Python 3.7 or higher
- pip (Python package installer)

### Install Required Packages

Open Terminal and run:

```bash
pip3 install python-osc pynput flask
```

Or if you prefer using a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv osckey-env

# Activate it
source osckey-env/bin/activate

# Install packages
pip install python-osc pynput flask
```

---

## Initial Setup

### 1. Save the Script

Save the `osckey.py` file to a location on your Mac, for example:
```
~/Documents/osckey/osckey.py
```

### 2. Make it Executable (Optional)

```bash
chmod +x osckey.py
```

### 3. Grant Accessibility Permissions

**CRITICAL:** macOS requires accessibility permissions for keyboard control.

1. Run the script for the first time:
   ```bash
   python3 osckey.py
   ```

2. macOS will display a security prompt or the script will fail with a permissions error

3. Go to **System Settings** (or System Preferences):
   - Navigate to **Privacy & Security** → **Accessibility**
   - Click the lock icon to make changes
   - Add **Terminal** (or your Python executable) to the list
   - Enable the checkbox

4. Restart the script

**Note:** If using an IDE like VSCode or PyCharm, you may need to add that application instead of Terminal.

---

## Running the Application

### Basic Usage

```bash
cd ~/Documents/osckey
python3 osckey.py
```

Once running, you'll see:
- **Web UI:** Open `http://localhost:5000` in your browser for configuration
- **OSC Server:** Listening on the configured IP and port (default: 127.0.0.1:5005)

### Using the Web Configuration Interface

The web interface allows you to:

1. **Change OSC Settings:**
   - Modify the listen IP address
   - Change the OSC port
   - Restart the OSC server with new settings

2. **Manage Custom Shortcuts:**
   - View all configured shortcuts
   - Add new custom OSC addresses
   - Delete existing shortcuts
   - Configure modifier combinations (Command, Option, Control, Shift)

**To access the web UI:**
1. Start the application
2. Open your browser to `http://localhost:5000`
3. Make changes and they'll be saved automatically to `osckey_config.json`

### Running in Background

To keep it running in the background:

```bash
nohup python3 osckey.py > osckey.log 2>&1 &
```

To stop the background process:
```bash
ps aux | grep osckey.py
kill [PID]
```

### Configuration

By default, the application listens on:
- **IP Address:** `127.0.0.1` (localhost only)
- **Port:** `5005`

To change these, edit the script:
```python
OSC_IP = "0.0.0.0"  # Listen on all interfaces
OSC_PORT = 8000     # Different port
```

---

## OSC Message Format

### Basic Structure

All messages are sent to OSC address patterns starting with `/key`

### Single Key Press

**Format:** `/key [key]`

```
/key s          → Press 's'
/key a          → Press 'a'
/key 5          → Press '5'
```

### Special Keys

**Format:** `/key [special_key]`

```
/key space      → Spacebar
/key enter      → Enter/Return
/key tab        → Tab
/key backspace  → Backspace
/key delete     → Delete
/key esc        → Escape
/key up         → Up Arrow
/key down       → Down Arrow
/key left       → Left Arrow
/key right      → Right Arrow
/key home       → Home
/key end        → End
/key pageup     → Page Up
/key pagedown   → Page Down
/key f1         → F1
/key f2         → F2
...
/key f12        → F12
```

### Keyboard Shortcuts with Modifiers

**Format:** `/key [modifier1] [modifier2] ... [key]`

**Supported Modifiers:**
- `command` or `cmd`
- `option` or `opt` or `alt`
- `control` or `ctrl`
- `shift`

```
/key command s                    → Cmd+S (Save)
/key command shift z              → Cmd+Shift+Z (Redo)
/key control option left          → Ctrl+Opt+Left Arrow
/key shift command option f5      → Shift+Cmd+Opt+F5
```

### Pre-Mapped Shortcuts

Convenient shortcuts with dedicated OSC addresses:

```
/key/save       → Cmd+S
/key/copy       → Cmd+C
/key/paste      → Cmd+V
/key/undo       → Cmd+Z
/key/redo       → Cmd+Shift+Z
```

---

## Examples

### Common Shortcuts

| Action | OSC Message |
|--------|-------------|
| Save | `/key command s` |
| Copy | `/key command c` |
| Paste | `/key command v` |
| Cut | `/key command x` |
| Select All | `/key command a` |
| Find | `/key command f` |
| New Tab | `/key command t` |
| Close Window | `/key command w` |
| Quit App | `/key command q` |
| Undo | `/key command z` |
| Redo | `/key command shift z` |
| Bold Text | `/key command b` |
| Italic Text | `/key command i` |

### Application-Specific Examples

**Logic Pro X:**
```
/key space              → Play/Stop
/key r                  → Record
/key command k          → Open Key Commands
```

**Ableton Live:**
```
/key space              → Play/Stop
/key f9                 → Record
/key command e          → Export Audio
```

**Final Cut Pro:**
```
/key space              → Play/Stop
/key e                  → Extend Edit
/key command b          → Blade Tool
```

### Text Editing

```
/key option left        → Move word left
/key option right       → Move word right
/key command left       → Move to line start
/key command right      → Move to line end
/key option backspace   → Delete word
```

---

## Testing with OSC Clients

### Using TouchOSC (iOS/Android)

1. Install TouchOSC on your device
2. Connect to the same network as your Mac
3. Set destination:
   - Host: Your Mac's IP address (or `127.0.0.1` if testing locally)
   - Port: `5005`
4. Create buttons with OSC messages like `/key command s`

### Using Max/MSP

```
[udpsend 127.0.0.1 5005]
|
[prepend send]
|
[/key command s(
```

### Using Pure Data

```
[send /key command s(
|
[packOSC]
|
[udpsend 127.0.0.1 5005]
```

### Using Python (for testing)

```python
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 5005)

# Send single key
client.send_message("/key", "s")

# Send shortcut
client.send_message("/key", "command s")

# Or send as list
client.send_message("/key", ["command", "shift", "z"])

# Use pre-mapped
client.send_message("/key/save", [])
```

### Using oscsend (Command Line)

Install oscsend:
```bash
brew install liblo
```

Send messages:
```bash
oscsend localhost 5005 /key s s "s"
oscsend localhost 5005 /key s "command s"
oscsend localhost 5005 /key/save
```

---

## Troubleshooting

### Keys Not Working

**Check Accessibility Permissions:**
1. System Settings → Privacy & Security → Accessibility
2. Ensure Terminal (or your Python app) is enabled
3. Try removing and re-adding the permission

**Try Restarting the Script:**
```bash
# Stop the script (Ctrl+C)
# Start it again
python3 osc_keyboard_bridge.py
```

### OSC Messages Not Being Received

**Check Port Availability:**
```bash
lsof -i :5005
```

If the port is in use, either:
- Kill the process using it
- Change the port in the script

**Verify Network Connection:**
- If sending from another device, ensure both are on the same network
- Check firewall settings (System Settings → Network → Firewall)

**Test with Python Client:**
```python
from pythonosc import udp_client
client = udp_client.SimpleUDPClient("127.0.0.1", 5005)
client.send_message("/key", "space")
```

### ModuleNotFoundError

```bash
# Reinstall dependencies
pip3 install --upgrade python-osc pynput flask
```

### "Operation not permitted" Error

This means accessibility permissions are not granted. See [Initial Setup](#initial-setup).

---

## Advanced Usage

### Configuration File

Settings are saved to `osckey_config.json` in the same directory as the script. You can edit this file directly if needed:

```json
{
  "osc_port": 5005,
  "osc_ip": "127.0.0.1",
  "custom_shortcuts": {
    "/key/save": {
      "modifiers": ["command"],
      "key": "s",
      "description": "Save"
    }
  }
}
```

Changes to this file require restarting the application or using the web UI to reload.

### Running as a Launch Agent (Auto-start on Login)

Create `~/Library/LaunchAgents/com.osckey.plist`:

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
        <string>/Users/YOUR_USERNAME/Documents/osckey/osckey.py</string>
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

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.osckey.plist
```

### Adding Custom Pre-Mapped Shortcuts

**Method 1: Using the Web UI (Recommended)**
1. Open `http://localhost:5000`
2. Scroll to "Add New Shortcut"
3. Fill in the OSC address, modifiers, key, and description
4. Click "Add Shortcut"

**Method 2: Edit the configuration file directly**

Edit `osckey_config.json`:

```json
{
  "custom_shortcuts": {
    "/key/screenshot": {
      "modifiers": ["command", "shift"],
      "key": "3",
      "description": "Take screenshot"
    },
    "/key/spotlight": {
      "modifiers": ["command"],
      "key": "space",
      "description": "Open Spotlight"
    }
  }
}
```

Then restart the application.

**Method 3: Edit the Python code**

Edit the `handle_keypress` function:

```python
def handle_keypress(address, *args):
    # Add your custom shortcuts here
    if address == "/key/screenshot":
        press_key_combo(['command', 'shift'], '3')
        return
    elif address == "/key/spotlight":
        press_key_combo(['command'], 'space')
        return
    elif address == "/key/mission_control":
        press_key_combo(['control'], 'up')
        return
    # ... rest of function
```

### Multiple OSC Addresses

You can create organized OSC namespaces:

```python
# In the main() function, add more mappings:
disp.map("/app/logic/*", handle_logic_shortcuts)
disp.map("/app/ableton/*", handle_ableton_shortcuts)
disp.map("/text/*", handle_text_editing)
```

### Logging to File

```python
# Modify the logging setup:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('osckey.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
```

---

## Tips & Best Practices

1. **Start Simple:** Test with basic key presses before complex shortcuts
2. **Check Logs:** Monitor the console output to see what OSC messages are received
3. **App-Specific Testing:** Different apps may respond differently to programmatic keypresses
4. **Timing:** Some apps need slight delays between rapid keystrokes
5. **Security:** Only expose to trusted networks if listening on `0.0.0.0`

---

## Support & Customization

This script is designed to be easily customizable. Common modifications:

- Change default port/IP in the `main()` function
- Add pre-mapped shortcuts in `handle_keypress()`
- Adjust timing with `time.sleep()` values
- Add custom key mappings to `SPECIAL_KEYS` dictionary

For questions or issues, check the console logs for detailed error messages.