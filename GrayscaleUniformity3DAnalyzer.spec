# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定：單一 Windows EXE (含 PySide6 QtWebEngine 與 Plotly 資料)。

建置：
    venv\\Scripts\\pyinstaller GrayscaleUniformity3DAnalyzer.spec --noconfirm
產出：
    dist/GrayscaleUniformity3DAnalyzer.exe
"""
from PyInstaller.utils.hooks import collect_all

# Plotly 需要打包其 package_data (get_plotlyjs 讀取 plotly.min.js) 與子模組
datas, binaries, hiddenimports = [], [], []
for _pkg in ("plotly",):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['grayscale_uniformity'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'IPython'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GrayscaleUniformity3DAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # GUI 應用程式，不顯示終端機視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
