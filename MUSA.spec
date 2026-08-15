# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launch_musa.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src\\musa\\assets', 'musa\\assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={'matplotlib': {'backends': 'TkAgg'}},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'keras', 'cv2', 'PySide6', 'shiboken6', 'sympy', 'IPython', 'notebook', 'grpc', 'boto3', 'botocore', 'folium', 'xarray', 'jedi', 'lxml'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MUSA',
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
    icon='src\\musa\\assets\\icon.png',
)
