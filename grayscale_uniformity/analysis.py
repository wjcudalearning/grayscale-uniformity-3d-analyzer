"""均勻度統計核心：區塊降採樣 (Pooling) 與均勻度指標計算。"""
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class UniformityResult:
    original_shape: Tuple[int, int]
    sampled_shape: Tuple[int, int]
    block_size: int
    mean: float
    std: float
    min_val: float
    max_val: float
    cv_uniformity: float          # (1 - std / mean) * 100
    range_uniformity: float       # (1 - (max - min) / (max + min)) * 100
    min_max_ratio: float          # min / max * 100
    block_means: np.ndarray


class Pooler:
    """向量化區塊平均 (mean pooling)，高記憶體效率。"""

    @staticmethod
    def pool(gray_img: np.ndarray, block_size: int = 2) -> np.ndarray:
        if block_size < 1:
            block_size = 1
        h, w = gray_img.shape
        h_trim = (h // block_size) * block_size
        w_trim = (w // block_size) * block_size
        if h_trim == 0 or w_trim == 0:
            return gray_img.copy()
        trimmed = gray_img[:h_trim, :w_trim]
        if block_size == 1:
            return trimmed
        reshaped = trimmed.reshape(h_trim // block_size, block_size,
                                   w_trim // block_size, block_size)
        return reshaped.mean(axis=(1, 3))


class UniformityAnalyzer:
    """依區塊大小計算灰階均勻度統計。"""

    def __init__(self, block_size: int = 2):
        self.block_size = block_size

    def analyze(self, gray_img: np.ndarray) -> UniformityResult:
        block_means = Pooler.pool(gray_img, self.block_size)

        mean_val = float(np.mean(block_means))
        std_val = float(np.std(block_means))
        min_val = float(np.min(block_means))
        max_val = float(np.max(block_means))

        if mean_val > 1e-6:
            cv_u = max(0.0, (1.0 - (std_val / mean_val)) * 100.0)
        else:
            cv_u = 100.0 if std_val < 1e-6 else 0.0

        if (max_val + min_val) > 1e-6:
            range_u = max(0.0, (1.0 - (max_val - min_val) / (max_val + min_val)) * 100.0)
        else:
            range_u = 100.0

        if max_val > 1e-6:
            min_max_ratio = (min_val / max_val) * 100.0
        else:
            min_max_ratio = 100.0 if min_val == 0 else 0.0

        return UniformityResult(
            original_shape=gray_img.shape,
            sampled_shape=block_means.shape,
            block_size=self.block_size,
            mean=mean_val, std=std_val, min_val=min_val, max_val=max_val,
            cv_uniformity=cv_u, range_uniformity=range_u,
            min_max_ratio=min_max_ratio, block_means=block_means,
        )


# ----- 模組層便利函式 (向後相容) -----
def compute_block_means(gray_img: np.ndarray, block_size: int = 2) -> np.ndarray:
    return Pooler.pool(gray_img, block_size)


def analyze_uniformity(gray_img: np.ndarray, block_size: int = 2) -> UniformityResult:
    return UniformityAnalyzer(block_size).analyze(gray_img)
