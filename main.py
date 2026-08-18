"""應用程式進入點：灰階均勻度 3D 視覺化分析工具。"""
import sys
from PIL import Image

# 完全解除 PIL 圖片大小與記憶體限制 (支援超大圖)
Image.MAX_IMAGE_PIXELS = None

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
