# -*- mode: python ; coding: utf-8 -*-
# Build standalone desktop GUI application with:
# pyinstaller buildpro_gui.spec

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('assets', 'assets'),
        ('bill logo.png', '.'),
        ('seal.png', '.'),
        ('sign.png', '.'),
    ],
    hiddenimports=[
        'webview',
        'clr_loader',
        'pythonnet',
        'bottle',
        'cffi',
        'sqlalchemy.sql.default_comparator',
        'engineio.async_drivers.threading',
        'jinja2.ext',
        'reportlab.graphics.barrier',
        'reportlab.graphics.charts',
        'reportlab.graphics.shapes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PyQt5'],
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
    name='BuildProGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
