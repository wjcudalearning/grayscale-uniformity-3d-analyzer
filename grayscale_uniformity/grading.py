"""均勻度分級：以「偏離平均 ±X%」為不均勻度定義，對照警戒線 (3/5/10/20%) 評級。"""
import re
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List

# 均勻度分級警戒線 (%)
DEFAULT_THRESHOLDS: List[float] = [3.0, 5.0, 10.0, 20.0]

# 各等級的標籤與色彩 (門檻% -> (標籤, 色碼))；None 代表超過最大門檻 = 不合格
GRADE_STYLE = {
    3.0:  ("優 (Excellent)", "#059669"),
    5.0:  ("良 (Good)", "#2563eb"),
    10.0: ("尚可 (Acceptable)", "#d97706"),
    20.0: ("偏差 (Marginal)", "#ea580c"),
    None: ("不合格 (Fail)", "#dc2626"),
}

# 分區圖用的離散色階 (由嚴到寬)
ZONE_COLORS = ["#059669", "#2563eb", "#d97706", "#ea580c", "#dc2626"]


@dataclass
class UniformityGrade:
    thresholds: List[float]
    deviation_pct: np.ndarray        # 每個區塊相對平均值的偏差百分比
    max_dev_pct: float
    p99_dev_pct: float               # 第 99 百分位偏差 (評級依據，抗少量熱點)
    pass_rates: Dict[float, float]   # 門檻 -> 容差內區塊比例 (%)
    grade_threshold: Optional[float]
    grade_label: str
    grade_color: str


class UniformityGrader:
    """依偏離平均百分比評定均勻度等級。"""

    def __init__(self, thresholds: Optional[List[float]] = None, pass_percentile: float = 99.0):
        self.thresholds = sorted(float(t) for t in (thresholds or DEFAULT_THRESHOLDS))
        self.pass_percentile = pass_percentile

    def grade(self, block_means: np.ndarray, mean_val: float) -> UniformityGrade:
        if mean_val > 1e-6:
            dev = np.abs(block_means - mean_val) / mean_val * 100.0
        else:
            dev = np.zeros_like(block_means)

        max_dev = float(np.max(dev)) if dev.size else 0.0
        p99 = float(np.percentile(dev, self.pass_percentile)) if dev.size else 0.0
        pass_rates = {t: float(np.mean(dev <= t) * 100.0) for t in self.thresholds}

        grade_t: Optional[float] = None
        for t in self.thresholds:
            if p99 <= t:
                grade_t = t
                break
        label, color = GRADE_STYLE.get(grade_t, GRADE_STYLE[None])

        return UniformityGrade(
            thresholds=self.thresholds, deviation_pct=dev,
            max_dev_pct=max_dev, p99_dev_pct=p99, pass_rates=pass_rates,
            grade_threshold=grade_t, grade_label=label, grade_color=color,
        )


def grade_uniformity(block_means, mean_val, thresholds=None) -> UniformityGrade:
    return UniformityGrader(thresholds).grade(block_means, mean_val)


def parse_thresholds(text: str, fallback: Optional[List[float]] = None) -> List[float]:
    """將使用者輸入 (逗號 / 空白 / 頓號分隔) 解析為排序、去重、正值的門檻清單。
    無有效值時回傳 fallback (預設 DEFAULT_THRESHOLDS)。"""
    fallback = list(fallback if fallback is not None else DEFAULT_THRESHOLDS)
    if not text:
        return fallback
    values = []
    for tok in re.split(r"[,\s、;]+", str(text).strip()):
        if not tok:
            continue
        try:
            v = float(tok)
        except ValueError:
            continue
        if v > 0:
            values.append(round(v, 4))
    values = sorted(set(values))
    return values if values else fallback
