"""使用者偏好設定 (QSettings) 與 QtWebEngine GPU 旗標。

注意：QtWebEngine 的硬體加速旗標必須在 QApplication / QtWebEngine 初始化「之前」
設定，無法於執行期即時切換，故 GPU 開關採「儲存偏好 + 重啟生效」。
"""
from PySide6.QtCore import QSettings

ORG = "Lab"
APP = "GrayscaleUniformity3DAnalyzer"


def settings() -> QSettings:
    return QSettings(ORG, APP)


def get_gpu_enabled() -> bool:
    """讀取是否啟用硬體 GPU 加速 (預設 True)。"""
    v = settings().value("display/gpu_enabled", True)
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def set_gpu_enabled(value: bool) -> None:
    settings().setValue("display/gpu_enabled", bool(value))
    settings().sync()


def chromium_flags(gpu_enabled: bool) -> str:
    """回傳對應的 QTWEBENGINE_CHROMIUM_FLAGS 字串。"""
    if gpu_enabled:
        # 忽略 GPU 封鎖清單、開啟 GPU 光柵化與零拷貝，盡量走硬體加速
        return "--ignore-gpu-blocklist --enable-gpu-rasterization --enable-zero-copy"
    # 強制軟體渲染 (SwiftShader)，供除錯或無 GPU 環境
    return "--disable-gpu --disable-gpu-compositing --disable-gpu-rasterization"
