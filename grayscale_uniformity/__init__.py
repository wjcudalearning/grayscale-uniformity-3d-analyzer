"""灰階均勻度 3D 視覺化分析工具 — 核心套件。

模組分工：
  image_io  — ImageLoader：影像載入與灰階轉換
  analysis  — UniformityAnalyzer / UniformityResult：區塊降採樣與均勻度指標
  grading   — UniformityGrader / UniformityGrade：偏離平均警戒線分級
  charts    — ChartBuilder：單一 Plotly 圖表
  report    — ReportBuilder：卡片式多圖表 HTML 報表
  ui        — PySide6 GUI
"""
from .image_io import ImageLoader, load_grayscale_image
from .analysis import (
    UniformityResult, UniformityAnalyzer, Pooler,
    compute_block_means, analyze_uniformity,
)
from .grading import (
    UniformityGrade, UniformityGrader, grade_uniformity, parse_thresholds,
    DEFAULT_THRESHOLDS, GRADE_STYLE, ZONE_COLORS,
)
from .charts import ChartBuilder, create_plotly_html, auto_value_range, downsample_for_view
from .report import ReportBuilder, create_report_html

__version__ = "1.1.0"

__all__ = [
    "ImageLoader", "load_grayscale_image",
    "UniformityResult", "UniformityAnalyzer", "Pooler",
    "compute_block_means", "analyze_uniformity",
    "UniformityGrade", "UniformityGrader", "grade_uniformity", "parse_thresholds",
    "DEFAULT_THRESHOLDS", "GRADE_STYLE", "ZONE_COLORS",
    "ChartBuilder", "create_plotly_html", "auto_value_range", "downsample_for_view",
    "ReportBuilder", "create_report_html",
]
