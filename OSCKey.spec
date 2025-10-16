# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['osckey.py'],
    pathex=[],
    binaries=[],
    datas=[('OSCKeyIcon.png', '.'), ('OSCKeyIcon.icns', '.')],
    hiddenimports=['rumps'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OSCKey',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OSCKey',
)

app = BUNDLE(
    coll,
    name='OSCKey.app',
    icon='OSCKeyIcon.icns',
    bundle_identifier='com.jeremyg58.osckey',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSAppleEventsUsageDescription': 'OSCKey needs to send keyboard events.',
        'NSSystemAdministrationUsageDescription': 'OSCKey needs accessibility permissions to control keyboard.',
    },
)
