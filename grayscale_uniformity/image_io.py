"""影像載入與灰階轉換 (支援中文路徑、超大圖、16-bit / 浮點格式)。"""
import os
import cv2
import numpy as np
from PIL import Image

# 解除 PIL 讀取超大圖片的記憶體與像素限制 (DecompressionBombError)
Image.MAX_IMAGE_PIXELS = None


class ImageLoader:
    """將任意影像檔載入為灰階 float32 陣列。"""

    #: 支援的輸入副檔名
    SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in cls.SUPPORTED_EXTS

    @staticmethod
    def load(file_path: str) -> np.ndarray:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到檔案: {file_path}")

        # 優先使用 PIL (已解除 MAX_IMAGE_PIXELS，完整相容超大圖與 16-bit)
        try:
            with Image.open(file_path) as pil_img:
                if pil_img.mode not in ("L", "I;16", "F"):
                    gray_pil = pil_img.convert("L")
                else:
                    gray_pil = pil_img
                return np.array(gray_pil, dtype=np.float32)
        except Exception:
            # Fallback：OpenCV + np.fromfile (支援中文路徑)
            raw_data = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(raw_data, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"無法解碼此圖片檔案: {file_path}")
            if img.ndim == 2:
                gray = img
            elif img.ndim == 3:
                if img.shape[2] == 4:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                elif img.shape[2] == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img[:, :, 0]
            else:
                raise ValueError("不支援的影像維度")
            return gray.astype(np.float32)


def load_grayscale_image(file_path: str) -> np.ndarray:
    """模組層便利函式 (等同 ImageLoader.load)。"""
    return ImageLoader.load(file_path)
