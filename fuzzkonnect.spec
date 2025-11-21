# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Fuzzkonnect
This configures how the executable is built
"""

block_cipher = None

# Collect all data files (templates, static files, etc.)
datas = [
    ('templates', 'templates'),
    ('matcher.py', '.'),
    ('app.py', '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'flask',
    'werkzeug',
    'jinja2',
    'pandas',
    'numpy',
    'scipy',
    'scipy.optimize',
    'scipy.spatial',
    'fuzzywuzzy',
    'rapidfuzz',
    'sentence_transformers',
    'transformers',
    'torch',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Fuzzkonnect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one (e.g., 'icon.ico' for Windows)
)
