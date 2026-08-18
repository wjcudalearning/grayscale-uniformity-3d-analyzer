"""背景分析執行緒：計算均勻度並產生圖表 HTML，不阻塞介面。"""
import numpy as np
from PySide6.QtCore import QThread, Signal

from ..analysis import UniformityAnalyzer
from ..charts import ChartBuilder


class AnalysisWorker(QThread):
    """在背景執行緒執行 分析 + 圖表產生。

    以遞增的 req_id 供主視窗辨識/忽略過期結果 (協作式取消)。
    """
    finished = Signal(int, object, str)   # req_id, UniformityResult, html_content
    error = Signal(int, str)              # req_id, error message

    def __init__(self, req_id: int, gray_img: np.ndarray, block_size: int,
                 chart_type: str, colorscale: str, theme: str,
                 max_scatter_points: int, plotlyjs_mode):
        super().__init__()
        self.req_id = req_id
        self.gray_img = gray_img
        self.block_size = block_size
        self.chart_type = chart_type
        self.colorscale = colorscale
        self.theme = theme
        self.max_scatter_points = max_scatter_points
        self.plotlyjs_mode = plotlyjs_mode

    def run(self):
        try:
            result = UniformityAnalyzer(self.block_size).analyze(self.gray_img)
            html = ChartBuilder(self.colorscale, self.theme, self.max_scatter_points).build_html(
                result.block_means, self.chart_type, include_plotlyjs=self.plotlyjs_mode)
            self.finished.emit(self.req_id, result, html)
        except Exception as e:
            self.error.emit(self.req_id, str(e))
