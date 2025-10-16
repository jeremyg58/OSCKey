#!/usr/bin/env python3
"""
OSC to Keyboard Shortcut Bridge for macOS with Web UI
Receives OSC messages and triggers keyboard shortcuts
"""

from pythonosc import dispatcher, osc_server
from pynput.keyboard import Controller, Key
from flask import Flask, render_template_string, request, jsonify, send_file
import threading
import time
import logging
import json
import os
import socket
import subprocess
import webbrowser
from collections import deque
try:
    import rumps
    RUMPS_AVAILABLE = True
except ImportError:
    RUMPS_AVAILABLE = False

# In-memory log storage (stores last 500 log entries)
log_buffer = deque(maxlen=500)

class BufferHandler(logging.Handler):
    """Custom logging handler that stores logs in memory"""
    def emit(self, record):
        log_entry = {
            'timestamp': self.format(record),
            'level': record.levelname,
            'message': record.getMessage()
        }
        log_buffer.append(log_entry)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add buffer handler to store logs
buffer_handler = BufferHandler()
buffer_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(buffer_handler)

# Initialize keyboard controller
keyboard = Controller()

# Configuration file path
CONFIG_FILE = "osc_keyboard_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "osc_port": 5005,
    "osc_ip": "0.0.0.0",
    "custom_shortcuts": {
        "/key/save": {
            "modifiers": ["command"],
            "key": "s",
            "description": "Save"
        },
        "/key/copy": {
            "modifiers": ["command"],
            "key": "c",
            "description": "Copy"
        },
        "/key/paste": {
            "modifiers": ["command"],
            "key": "v",
            "description": "Paste"
        },
        "/key/undo": {
            "modifiers": ["command"],
            "key": "z",
            "description": "Undo"
        },
        "/key/redo": {
            "modifiers": ["command", "shift"],
            "key": "z",
            "description": "Redo"
        }
    }
}

# Global variables
config = DEFAULT_CONFIG.copy()
osc_server_instance = None
osc_thread = None

# Modifier key mapping
MODIFIERS = {
    'command': Key.cmd,
    'cmd': Key.cmd,
    'option': Key.alt,
    'opt': Key.alt,
    'alt': Key.alt,
    'control': Key.ctrl,
    'ctrl': Key.ctrl,
    'shift': Key.shift,
}

# Special key mapping
SPECIAL_KEYS = {
    'space': Key.space,
    'enter': Key.enter,
    'return': Key.enter,
    'tab': Key.tab,
    'backspace': Key.backspace,
    'delete': Key.delete,
    'esc': Key.esc,
    'escape': Key.esc,
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    'home': Key.home,
    'end': Key.end,
    'pageup': Key.page_up,
    'pagedown': Key.page_down,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
}

# Key codes for AppleScript (macOS virtual key codes)
APPLESCRIPT_KEY_CODES = {
    'left': 123,
    'right': 124,
    'down': 125,
    'up': 126,
}


def press_key_with_applescript(modifiers, key):
    """
    Press key using AppleScript for better compatibility with apps like Magnet
    """
    try:
        # Build modifier string
        modifier_parts = []
        for mod in modifiers:
            mod_lower = mod.lower()
            if mod_lower in ['command', 'cmd']:
                modifier_parts.append('command down')
            elif mod_lower in ['option', 'opt', 'alt']:
                modifier_parts.append('option down')
            elif mod_lower in ['control', 'ctrl']:
                modifier_parts.append('control down')
            elif mod_lower in ['shift']:
                modifier_parts.append('shift down')

        modifier_str = ', '.join(modifier_parts) if modifier_parts else ''

        # Get key code if it's an arrow key
        key_lower = key.lower()
        if key_lower in APPLESCRIPT_KEY_CODES:
            key_code = APPLESCRIPT_KEY_CODES[key_lower]
            if modifier_str:
                applescript = f'tell application "System Events" to key code {key_code} using {{{modifier_str}}}'
            else:
                applescript = f'tell application "System Events" to key code {key_code}'
        else:
            # For regular keys, use keystroke
            if modifier_str:
                applescript = f'tell application "System Events" to keystroke "{key}" using {{{modifier_str}}}'
            else:
                applescript = f'tell application "System Events" to keystroke "{key}"'

        # Execute AppleScript
        result = subprocess.run(['osascript', '-e', applescript],
                              capture_output=True, text=True, timeout=2)

        if result.returncode != 0:
            logger.error(f"AppleScript error: {result.stderr}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error with AppleScript: {e}")
        return False


def load_config():
    """Load configuration from file"""
    global config
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
                logger.info("Configuration loaded from file")
        else:
            save_config()
            logger.info("Created default configuration file")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        config = DEFAULT_CONFIG.copy()


def save_config():
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved")
    except Exception as e:
        logger.error(f"Error saving config: {e}")


def press_key_combo(modifiers=None, key=None):
    """
    Press a keyboard shortcut with optional modifiers
    
    Args:
        modifiers: List of modifier keys (e.g., ['command', 'shift'])
        key: The main key to press (e.g., 's', 'enter')
    """
    if modifiers is None:
        modifiers = []
    
    # Convert modifier names to Key objects
    modifier_keys = []
    for mod in modifiers:
        mod_lower = mod.lower()
        if mod_lower in MODIFIERS:
            modifier_keys.append(MODIFIERS[mod_lower])
        else:
            logger.warning(f"Unknown modifier: {mod}")
    
    # Get the main key
    main_key = None
    if key:
        key_lower = key.lower()
        if key_lower in SPECIAL_KEYS:
            main_key = SPECIAL_KEYS[key_lower]
        else:
            # Regular character key
            main_key = key
    
    # Press the key combination
    try:
        # Build readable key combo string
        if key:
            combo_str = '+'.join([m.capitalize() for m in modifiers] + [key.upper()])
        else:
            combo_str = '+'.join([m.capitalize() for m in modifiers])

        logger.info(f"PRESSING: /key/[{combo_str}]")

        # Use AppleScript for arrow keys with modifiers (for Magnet compatibility)
        key_lower = key.lower() if key else None
        if key_lower in APPLESCRIPT_KEY_CODES and modifiers:
            logger.info(f"Using AppleScript method for better app compatibility")
            success = press_key_with_applescript(modifiers, key)
            if success:
                logger.info(f"SUCCESS: /key/[{combo_str}]")
            else:
                logger.error(f"AppleScript method failed for /key/[{combo_str}]")
            return

        # Use pynput for everything else
        # Press all modifiers
        for mod_key in modifier_keys:
            keyboard.press(mod_key)

        time.sleep(0.01)

        # Press and release the main key
        if main_key:
            keyboard.press(main_key)
            keyboard.release(main_key)

        time.sleep(0.01)

        # Release all modifiers in reverse order
        for mod_key in reversed(modifier_keys):
            keyboard.release(mod_key)

        logger.info(f"SUCCESS: /key/[{combo_str}]")

    except Exception as e:
        logger.error(f"ERROR pressing key combo: {e}")


def handle_keypress(address, *args):
    """Handle incoming OSC messages for keypresses"""
    # Build the key combo string for logging
    def build_key_path(mods, k):
        """Build /key/[KeyCombo] format"""
        if k:
            combo = '+'.join([m.capitalize() for m in mods] + [k.upper()])
        else:
            combo = '+'.join([m.capitalize() for m in mods])
        return f"/key/[{combo}]"

    # Check custom shortcuts first
    if address in config["custom_shortcuts"]:
        shortcut = config["custom_shortcuts"][address]
        shortcut_desc = shortcut.get("description", "")
        mods = shortcut.get("modifiers", [])
        k = shortcut.get("key")
        key_path = build_key_path(mods, k)

        if shortcut_desc:
            logger.info(f"OSC RECEIVED: {address} -> {key_path} ({shortcut_desc})")
        else:
            logger.info(f"OSC RECEIVED: {address} -> {key_path}")
        press_key_combo(mods, k)
        return

    # If no args provided, try to extract key from address (e.g., /key/down -> "down")
    if not args and address.startswith('/key/'):
        key_from_address = address[5:].strip()  # Remove '/key/' prefix and clean whitespace
        if key_from_address:
            args = [key_from_address]
        else:
            logger.warning(f"OSC RECEIVED: {address} -> No arguments provided")
            return
    elif not args:
        logger.warning(f"OSC RECEIVED: {address} -> No arguments provided")
        return

    # If first arg is a string with spaces, split it
    if len(args) == 1 and isinstance(args[0], str) and ' ' in args[0]:
        args = args[0].split()

    # Separate modifiers from the main key
    modifiers = []
    key = None

    for arg in args:
        arg_str = str(arg).strip()  # Clean whitespace
        arg_lower = arg_str.lower()
        if arg_lower in MODIFIERS:
            modifiers.append(arg_str)
        else:
            key = arg_str
            break

    # Log and execute the keypress
    if key or modifiers:
        key_path = build_key_path(modifiers, key)
        logger.info(f"OSC RECEIVED: {address} -> {key_path}")
        press_key_combo(modifiers, key)
    else:
        logger.warning(f"OSC RECEIVED: {address} -> No valid key or modifier found")


def handle_unmatched_osc(address, *args):
    """Handle OSC messages that don't match /key patterns"""
    if args:
        args_str = ', '.join([f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args])
    else:
        args_str = "(none)"
    logger.warning(f"OSC UNMATCHED: {address} | Args: [{args_str}]")
    logger.warning(f"   Hint: Expected address format is /key or /key/... (e.g., /key/save)")


def start_osc_server():
    """Start the OSC server"""
    global osc_server_instance

    try:
        # Setup OSC dispatcher
        disp = dispatcher.Dispatcher()
        disp.map("/key", handle_keypress)
        disp.map("/key/*", handle_keypress)
        # Catch-all for unmatched messages
        disp.set_default_handler(handle_unmatched_osc)

        # Start OSC server
        osc_ip = config.get("osc_ip", "127.0.0.1")
        osc_port = config.get("osc_port", 5005)

        osc_server_instance = osc_server.ThreadingOSCUDPServer((osc_ip, osc_port), disp)

        # Enable socket reuse to prevent "Address already in use" errors
        osc_server_instance.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logger.info(f"OSC Server started on {osc_ip}:{osc_port}")
        osc_server_instance.serve_forever()

    except Exception as e:
        logger.error(f"Error starting OSC server: {e}")


def restart_osc_server():
    """Restart the OSC server with new configuration"""
    global osc_server_instance, osc_thread

    try:
        # Stop existing server
        if osc_server_instance:
            logger.info("Stopping OSC server...")
            osc_server_instance.shutdown()
            osc_server_instance.server_close()  # Explicitly close the socket
            if osc_thread:
                osc_thread.join(timeout=3)

        # Give the OS time to release the port
        time.sleep(0.5)

        # Clear the old instance
        osc_server_instance = None

        # Start new server
        osc_thread = threading.Thread(target=start_osc_server, daemon=True)
        osc_thread.start()

        # Wait a moment to ensure server starts
        time.sleep(0.5)

        logger.info("OSC server restarted")
        return True

    except Exception as e:
        logger.error(f"Error restarting OSC server: {e}")
        return False


# Flask Web UI
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OSC Keyboard Bridge - Configuration</title>
    <link rel="icon" type="image/png" href="/favicon">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f7;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #1d1d1f;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            color: #6e6e73;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h2 {
            color: #1d1d1f;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #d2d2d7;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #1d1d1f;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }
        input[type="text"], input[type="number"], select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus, input[type="number"]:focus, select:focus {
            outline: none;
            border-color: #0071e3;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #0071e3;
            color: white;
        }
        .btn-primary:hover {
            background: #0077ed;
        }
        .btn-success {
            background: #34c759;
            color: white;
        }
        .btn-success:hover {
            background: #30b350;
        }
        .btn-danger {
            background: #ff3b30;
            color: white;
        }
        .btn-danger:hover {
            background: #ff453a;
        }
        .shortcut-item {
            background: #f5f5f7;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .shortcut-info {
            flex: 1;
        }
        .shortcut-address {
            font-family: 'Monaco', 'Courier New', monospace;
            color: #0071e3;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .shortcut-combo {
            color: #1d1d1f;
            font-weight: 500;
            font-size: 14px;
        }
        .shortcut-desc {
            color: #6e6e73;
            font-size: 12px;
            margin-top: 4px;
        }
        .shortcut-actions {
            display: flex;
            gap: 8px;
        }
        .status {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            margin-top: 12px;
            display: none;
        }
        .status.success {
            background: #d1f4dd;
            color: #248a3d;
            display: block;
        }
        .status.error {
            background: #ffdede;
            color: #c41e3a;
            display: block;
        }
        .modifier-selector {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .modifier-checkbox {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            background: #f5f5f7;
            border-radius: 6px;
            cursor: pointer;
            user-select: none;
        }
        .modifier-checkbox input {
            cursor: pointer;
        }
        .modifier-checkbox:hover {
            background: #e8e8ed;
        }
        .info-box {
            background: #f5f5f7;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #0071e3;
        }
        .info-box p {
            color: #1d1d1f;
            font-size: 14px;
            line-height: 1.6;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            border-bottom: 2px solid #d2d2d7;
        }
        .tab {
            padding: 12px 24px;
            background: none;
            border: none;
            color: #6e6e73;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }
        .tab:hover {
            color: #1d1d1f;
        }
        .tab.active {
            color: #0071e3;
            border-bottom-color: #0071e3;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .log-viewer {
            background: #1d1d1f;
            color: #f5f5f7;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            padding: 16px;
            border-radius: 8px;
            height: 500px;
            overflow-y: auto;
            line-height: 1.6;
        }
        .log-entry {
            margin-bottom: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .log-entry.INFO {
            color: #f5f5f7;
        }
        .log-entry.WARNING {
            color: #ffcc00;
        }
        .log-entry.ERROR {
            color: #ff3b30;
        }
        .log-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            user-select: none;
        }
        .checkbox-label input {
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>OSC Keyboard Bridge</h1>
        <p class="subtitle">Configure OSC settings and custom keyboard shortcuts</p>

        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('config')">Configuration</button>
            <button class="tab" onclick="switchTab('logs')">Logs</button>
        </div>

        <!-- Configuration Tab -->
        <div id="config-tab" class="tab-content active">
        <!-- OSC Settings -->
        <div class="section">
            <h2>OSC Server Settings</h2>
            <div class="info-box">
                <p><strong>Note:</strong> Changing these settings will restart the OSC server. Any active connections will be interrupted briefly.</p>
            </div>
            <form id="osc-settings-form">
                <div class="grid-2">
                    <div class="form-group">
                        <label>Listen IP Address</label>
                        <input type="text" id="osc-ip" value="127.0.0.1">
                        <small style="color: #6e6e73; font-size: 12px; display: block; margin-top: 4px;">
                            Use 127.0.0.1 for localhost only, or 0.0.0.0 to listen on all interfaces
                        </small>
                    </div>
                    <div class="form-group">
                        <label>Listen Port</label>
                        <input type="number" id="osc-port" value="5005" min="1024" max="65535">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">Save & Restart Server</button>
                <div id="osc-status" class="status"></div>
            </form>
        </div>
        
        <!-- Custom Shortcuts -->
        <div class="section">
            <h2>Custom Shortcuts</h2>
            <div id="shortcuts-list"></div>
            
            <h3 style="margin-top: 30px; margin-bottom: 16px; color: #1d1d1f; font-size: 18px;">Add New Shortcut</h3>
            <form id="add-shortcut-form">
                <div class="form-group">
                    <label>OSC Address</label>
                    <input type="text" id="new-address" placeholder="/key/custom" required>
                    <small style="color: #6e6e73; font-size: 12px; display: block; margin-top: 4px;">
                        Must start with /key/ (e.g., /key/custom, /key/myapp/action)
                    </small>
                </div>
                
                <div class="form-group">
                    <label>Modifiers</label>
                    <div class="modifier-selector">
                        <label class="modifier-checkbox">
                            <input type="checkbox" name="modifier" value="command"> Command
                        </label>
                        <label class="modifier-checkbox">
                            <input type="checkbox" name="modifier" value="option"> Option
                        </label>
                        <label class="modifier-checkbox">
                            <input type="checkbox" name="modifier" value="control"> Control
                        </label>
                        <label class="modifier-checkbox">
                            <input type="checkbox" name="modifier" value="shift"> Shift
                        </label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Key</label>
                    <input type="text" id="new-key" placeholder="s" required>
                    <small style="color: #6e6e73; font-size: 12px; display: block; margin-top: 4px;">
                        Single character (a-z, 0-9) or special key (space, enter, tab, etc.)
                    </small>
                </div>
                
                <div class="form-group">
                    <label>Description (optional)</label>
                    <input type="text" id="new-description" placeholder="Save file">
                </div>
                
                <button type="submit" class="btn btn-success">Add Shortcut</button>
                <div id="shortcut-status" class="status"></div>
            </form>
        </div>
        </div>
        <!-- End Configuration Tab -->

        <!-- Logs Tab -->
        <div id="logs-tab" class="tab-content">
            <div class="section">
                <h2>Application Logs</h2>
                <div class="log-controls">
                    <div style="display: flex; gap: 16px;">
                        <label class="checkbox-label">
                            <input type="checkbox" id="autoscroll" checked>
                            <span>Auto-scroll to bottom</span>
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" id="filter-osc">
                            <span>Show only OSC messages</span>
                        </label>
                    </div>
                    <button class="btn btn-primary" onclick="clearLogs()">Clear Logs</button>
                </div>
                <div id="log-viewer" class="log-viewer"></div>
            </div>
        </div>
        <!-- End Logs Tab -->
    </div>

    <script>
        // Load current configuration
        async function loadConfig() {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            document.getElementById('osc-ip').value = config.osc_ip;
            document.getElementById('osc-port').value = config.osc_port;
            
            renderShortcuts(config.custom_shortcuts);
        }
        
        // Render shortcuts list
        function renderShortcuts(shortcuts) {
            const list = document.getElementById('shortcuts-list');
            list.innerHTML = '';
            
            for (const [address, shortcut] of Object.entries(shortcuts)) {
                const div = document.createElement('div');
                div.className = 'shortcut-item';
                
                const modifierStr = shortcut.modifiers.length > 0 
                    ? shortcut.modifiers.map(m => m.charAt(0).toUpperCase() + m.slice(1)).join('+') + '+'
                    : '';
                
                div.innerHTML = `
                    <div class="shortcut-info">
                        <div class="shortcut-address">${address}</div>
                        <div class="shortcut-combo">${modifierStr}${shortcut.key.toUpperCase()}</div>
                        ${shortcut.description ? `<div class="shortcut-desc">${shortcut.description}</div>` : ''}
                    </div>
                    <div class="shortcut-actions">
                        <button class="btn btn-danger" onclick="deleteShortcut('${address}')">Delete</button>
                    </div>
                `;
                
                list.appendChild(div);
            }
        }
        
        // Save OSC settings
        document.getElementById('osc-settings-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                osc_ip: document.getElementById('osc-ip').value,
                osc_port: parseInt(document.getElementById('osc-port').value)
            };
            
            const response = await fetch('/api/config/osc', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            const status = document.getElementById('osc-status');
            
            if (result.success) {
                status.className = 'status success';
                status.textContent = 'Settings saved and server restarted successfully!';
            } else {
                status.className = 'status error';
                status.textContent = 'Error: ' + result.message;
            }
            
            setTimeout(() => status.style.display = 'none', 3000);
        });
        
        // Add new shortcut
        document.getElementById('add-shortcut-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const modifiers = Array.from(document.querySelectorAll('input[name="modifier"]:checked'))
                .map(cb => cb.value);
            
            const data = {
                address: document.getElementById('new-address').value,
                shortcut: {
                    modifiers: modifiers,
                    key: document.getElementById('new-key').value,
                    description: document.getElementById('new-description').value
                }
            };
            
            const response = await fetch('/api/shortcuts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            const status = document.getElementById('shortcut-status');
            
            if (result.success) {
                status.className = 'status success';
                status.textContent = 'Shortcut added successfully!';
                
                // Clear form
                document.getElementById('new-address').value = '';
                document.getElementById('new-key').value = '';
                document.getElementById('new-description').value = '';
                document.querySelectorAll('input[name="modifier"]').forEach(cb => cb.checked = false);
                
                // Reload shortcuts
                loadConfig();
            } else {
                status.className = 'status error';
                status.textContent = 'Error: ' + result.message;
            }
            
            setTimeout(() => status.style.display = 'none', 3000);
        });
        
        // Delete shortcut
        async function deleteShortcut(address) {
            if (!confirm(`Delete shortcut ${address}?`)) return;
            
            const response = await fetch('/api/shortcuts', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({address: address})
            });
            
            const result = await response.json();
            if (result.success) {
                loadConfig();
            }
        }
        
        // Tab switching
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');

            // Start log polling if switching to logs tab
            if (tabName === 'logs') {
                startLogPolling();
            } else {
                stopLogPolling();
            }
        }

        // Log viewer
        let logPollInterval = null;
        let lastLogCount = 0;

        async function fetchLogs() {
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();
                const logViewer = document.getElementById('log-viewer');
                const autoscroll = document.getElementById('autoscroll').checked;
                const filterOsc = document.getElementById('filter-osc').checked;

                // Only update if logs changed
                if (data.logs.length !== lastLogCount) {
                    logViewer.innerHTML = '';
                    data.logs.forEach(log => {
                        // Filter for OSC messages if checkbox is enabled
                        if (filterOsc && !log.message.includes('OSC RECEIVED')) {
                            return;
                        }

                        const div = document.createElement('div');
                        div.className = 'log-entry ' + log.level;
                        div.textContent = log.timestamp;
                        logViewer.appendChild(div);
                    });

                    lastLogCount = data.logs.length;

                    // Auto-scroll to bottom if enabled
                    if (autoscroll) {
                        logViewer.scrollTop = logViewer.scrollHeight;
                    }
                }
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        // Re-render logs when filter changes
        document.addEventListener('DOMContentLoaded', function() {
            const filterCheckbox = document.getElementById('filter-osc');
            if (filterCheckbox) {
                filterCheckbox.addEventListener('change', function() {
                    lastLogCount = 0; // Force re-render
                    fetchLogs();
                });
            }
        });

        function startLogPolling() {
            if (logPollInterval) return;
            fetchLogs(); // Fetch immediately
            logPollInterval = setInterval(fetchLogs, 1000); // Then every second
        }

        function stopLogPolling() {
            if (logPollInterval) {
                clearInterval(logPollInterval);
                logPollInterval = null;
            }
        }

        function clearLogs() {
            // Note: This only clears the display, not the server buffer
            document.getElementById('log-viewer').innerHTML = '';
            lastLogCount = 0;
        }

        // Load config on page load
        loadConfig();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/config')
def get_config():
    return jsonify(config)

@app.route('/api/config/osc', methods=['POST'])
def update_osc_config():
    try:
        data = request.json
        config['osc_ip'] = data.get('osc_ip', '127.0.0.1')
        config['osc_port'] = data.get('osc_port', 5005)
        save_config()
        
        # Restart OSC server
        success = restart_osc_server()
        
        return jsonify({
            'success': success,
            'message': 'Configuration updated' if success else 'Failed to restart server'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/shortcuts', methods=['POST'])
def add_shortcut():
    try:
        data = request.json
        address = data['address']
        
        if not address.startswith('/key/'):
            return jsonify({'success': False, 'message': 'Address must start with /key/'})
        
        config['custom_shortcuts'][address] = data['shortcut']
        save_config()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/shortcuts', methods=['DELETE'])
def delete_shortcut():
    try:
        data = request.json
        address = data['address']

        if address in config['custom_shortcuts']:
            del config['custom_shortcuts'][address]
            save_config()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Shortcut not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/logs')
def get_logs():
    """Return all logs from the buffer"""
    return jsonify({'logs': list(log_buffer)})


@app.route('/favicon')
def favicon():
    """Serve the favicon"""
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OSCKeyIcon.png")
    if os.path.exists(icon_path):
        return send_file(icon_path, mimetype='image/png')
    return '', 404


def check_accessibility_permissions():
    """Check if accessibility permissions are granted and prompt if not"""
    try:
        # Try to check if we have accessibility permissions by attempting to use pynput
        from pynput.keyboard import Controller
        test_keyboard = Controller()

        # Try a test operation - this will trigger permission prompt if not granted
        # We don't actually press anything, just test if we can
        logger.info("Checking accessibility permissions...")

        # Trigger the permission dialog by attempting keyboard access
        test_keyboard.press(Key.shift)
        test_keyboard.release(Key.shift)

        logger.info("Accessibility permissions granted")
        return True

    except Exception as e:
        logger.warning(f"Accessibility permissions check: {e}")
        logger.warning("=" * 60)
        logger.warning("ACCESSIBILITY PERMISSIONS REQUIRED")
        logger.warning("=" * 60)
        logger.warning("macOS requires accessibility permissions for keyboard control.")
        logger.warning("")
        logger.warning("A system dialog should appear asking for permission.")
        logger.warning("If not, please manually grant permissions:")
        logger.warning("")
        logger.warning("1. Open System Settings")
        logger.warning("2. Go to Privacy & Security → Accessibility")
        logger.warning("3. Add this application and enable it")
        logger.warning("")
        logger.warning("The application will continue to run, but keyboard")
        logger.warning("control will not work until permissions are granted.")
        logger.warning("=" * 60)
        return False


class OSCKeyApp(rumps.App):
    """Menu bar application"""

    def __init__(self):
        # Get the icon path
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OSCKeyIcon.png")

        # Initialize rumps app with icon
        super(OSCKeyApp, self).__init__(
            "OSCKey",
            icon=icon_path if os.path.exists(icon_path) else None,
            quit_button=None
        )

        # Load configuration
        load_config()

        # Build menu
        self.menu = [
            rumps.MenuItem(f"Listening on {config['osc_ip']}:{config['osc_port']}"),
            None,  # Separator
            rumps.MenuItem("Open Web UI", callback=self.open_web_ui),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        # Make the status item non-clickable
        self.menu["Listening on " + f"{config['osc_ip']}:{config['osc_port']}"].set_callback(None)

    def open_web_ui(self, _):
        """Open the web UI in browser"""
        webbrowser.open('http://localhost:5000')

    def quit_app(self, _):
        """Quit the application"""
        rumps.quit_application()


def main():
    """Start the application"""
    global osc_thread

    # Load configuration
    load_config()

    logger.info("=" * 60)
    logger.info("OSC KEYBOARD BRIDGE STARTING")
    logger.info("=" * 60)

    # Check accessibility permissions
    check_accessibility_permissions()

    logger.info(f"Web UI: http://localhost:5000")
    logger.info(f"OSC Server: {config['osc_ip']}:{config['osc_port']}")
    logger.info(f"Custom Shortcuts Loaded: {len(config.get('custom_shortcuts', {}))}")
    logger.info("=" * 60)

    # Start OSC server in background thread
    osc_thread = threading.Thread(target=start_osc_server, daemon=True)
    osc_thread.start()

    # Start Flask in background thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()

    # Start menu bar app (if rumps available)
    if RUMPS_AVAILABLE:
        OSCKeyApp().run()
    else:
        # Fallback: just run Flask (blocks)
        flask_thread.join()


if __name__ == "__main__":
    main()