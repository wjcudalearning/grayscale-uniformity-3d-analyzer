# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定：onedir 資料夾版 (含 PySide6 QtWebEngine 與 Plotly 資料)。

採 onedir 模式：QtWebEngine 在資料夾版較穩定 (不需執行期解壓，可正確定位
QtWebEngineProcess.exe)，適合壓成 zip 發佈。

建置：
    venv\\Scripts\\pyinstaller GrayscaleUniformity3DAnalyzer.spec --noconfirm
產出：
    dist/GrayscaleUniformity3DAnalyzer/GrayscaleUniformity3DAnalyzer.exe  (整個資料夾為執行所需)
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
    [],
    exclude_binaries=True,   # onedir：binaries/datas 交由 COLLECT 收集至資料夾
    name='GrayscaleUniformity3DAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,           # GUI 應用程式，不顯示終端機視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GrayscaleUniformity3DAnalyzer',
)
