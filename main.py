"""應用程式進入點：灰階均勻度 3D 視覺化分析工具。"""
import os
import sys
from PIL import Image

# 完全解除 PIL 圖片大小與記憶體限制 (支援超大圖)
Image.MAX_IMAGE_PIXELS = None

# 依使用者偏好設定 QtWebEngine 的 GPU 旗標 —— 必須在匯入 QtWebEngine / 建立
# QApplication 之前完成，否則不生效。
from grayscale_uniformity.config import get_gpu_enabled, chromium_flags
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + " " + chromium_flags(get_gpu_enabled())
).strip()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from grayscale_uniformity.ui import MainWindow


def main():
    # 支援高 DPI 螢幕清晰渲染
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Grayscale Uniformity 3D Analyzer")
    app.setOrganizationName("Lab")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
