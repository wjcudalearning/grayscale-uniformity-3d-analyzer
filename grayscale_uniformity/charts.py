"""Plotly 圖表產生：3D 散點 / 曲面 / 熱力圖 / 直方圖 / 剖面線。"""
import numpy as np
import plotly.graph_objects as go
from typing import Any, Tuple


def auto_value_range(block_means: np.ndarray) -> Tuple[float, float]:
    """依實際資料自動判定色彩/軸值域：8-bit 固定 0–255 以保有絕對亮度語意，
    16-bit / 浮點來源則採 0–實際最大值，避免對比被壓縮。"""
    if block_means.size == 0:
        return 0.0, 255.0
    data_max = float(np.nanmax(block_means))
    return (0.0, 255.0) if data_max <= 255.0 else (0.0, data_max)


def downsample_for_view(arr: np.ndarray, max_cells: int = 160000) -> Tuple[np.ndarray, int]:
    """降採樣矩陣至 max_cells 以下，回傳 (矩陣, 步長)。"""
    total = arr.shape[0] * arr.shape[1]
    if total <= max_cells:
        return arr, 1
    step = int(np.ceil(np.sqrt(total / max_cells)))
    return arr[::step, ::step], step


class ChartBuilder:
    """依設定 (配色/主題/散點上限) 產生單一 Plotly 圖表的完整 HTML。"""

    def __init__(self, colorscale: str = "Viridis", theme: str = "dark",
                 max_scatter_points: int = 40000):
        self.colorscale = colorscale
        self.theme = theme
        self.max_scatter_points = max_scatter_points

    def _palette(self):
        dark = self.theme == "dark"
        return {
            "bg": "#1e1e24" if dark else "#ffffff",
            "paper": "#1e1e24" if dark else "#ffffff",
            "font": "#e0e0e0" if dark else "#202020",
            "grid": "#33333e" if dark else "#e5e5e5",
        }

    def build_html(self, block_means: np.ndarray, chart_type: str = "scatter3d",
                   include_plotlyjs: Any = True) -> str:
        h, w = block_means.shape
        total = h * w
        vmin, vmax = auto_value_range(block_means)
        p = self._palette()
        bg, paper, font, grid = p["bg"], p["paper"], p["font"], p["grid"]
        cbar = lambda: dict(title=dict(text="灰階值", font=dict(color=font)),
                            tickfont=dict(color=font))
        fig = go.Figure()

        if chart_type == "scatter3d":
            step = 1
            if total > self.max_scatter_points:
                step = int(np.ceil(np.sqrt(total / self.max_scatter_points)))
            xx, yy = np.meshgrid(np.arange(0, w, step), np.arange(0, h, step))
            zz = block_means[0:h:step, 0:w:step]
            fig.add_trace(go.Scatter3d(
                x=xx.flatten(), y=yy.flatten(), z=zz.flatten(), mode="markers",
                marker=dict(size=2.5 if step == 1 else 3.5, color=zz.flatten(),
                            colorscale=self.colorscale, cmin=vmin, cmax=vmax,
                            colorbar=cbar(), opacity=0.88),
                hovertemplate="X (寬): %{x}<br>Y (高): %{y}<br>灰階值: %{z:.2f}<extra></extra>"))

        elif chart_type == "surface":
            step = 1
            if total > 90000:
                step = int(np.ceil(np.sqrt(total / 90000)))
            fig.add_trace(go.Surface(
                x=np.arange(0, w, step), y=np.arange(0, h, step),
                z=block_means[::step, ::step], colorscale=self.colorscale,
                cmin=vmin, cmax=vmax, colorbar=cbar(),
                hovertemplate="X (寬): %{x}<br>Y (高): %{y}<br>灰階值: %{z:.2f}<extra></extra>"))

        elif chart_type == "heatmap":
            fig.add_trace(go.Heatmap(
                z=block_means, colorscale=self.colorscale, zmin=vmin, zmax=vmax,
                colorbar=cbar(),
                hovertemplate="X (寬): %{x}<br>Y (高): %{y}<br>灰階值: %{z:.2f}<extra></extra>"))

        elif chart_type == "histogram":
            fig.add_trace(go.Histogram(
                x=block_means.flatten(), nbinsx=64,
                marker=dict(color="#3b82f6", line=dict(color=paper, width=0.5)),
                hovertemplate="灰階值區間: %{x}<br>數量: %{y}<extra></extra>"))

        elif chart_type == "profile":
            mid_row = block_means[h // 2, :]
            mid_col = block_means[:, w // 2]
            fig.add_trace(go.Scatter(x=np.arange(w), y=mid_row, mode="lines",
                          name="中央橫向剖面 (Row)", line=dict(color="#3b82f6", width=2),
                          hovertemplate="X: %{x}<br>灰階值: %{y:.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=np.arange(h), y=mid_col, mode="lines",
                          name="中央縱向剖面 (Col)", line=dict(color="#10b981", width=2),
                          hovertemplate="Y: %{x}<br>灰階值: %{y:.2f}<extra></extra>"))

        self._apply_layout(fig, chart_type, vmin, vmax, p)

        html = fig.to_html(include_plotlyjs=include_plotlyjs, full_html=True,
                           config={"responsive": True, "displayModeBar": True,
                                   "modeBarButtonsToRemove": ["toImage"]})
        style = ("<style>html,body{margin:0;padding:0;width:100%;height:100%;"
                 f"overflow:hidden;background-color:{bg};}}"
                 ".plotly-graph-div{width:100% !important;height:100% !important;}</style>")
        return html.replace("<head>", f"<head>{style}")

    def _apply_layout(self, fig, chart_type, vmin, vmax, p):
        font, grid, bg, paper = p["font"], p["grid"], p["bg"], p["paper"]
        fam = "Segoe UI, Microsoft JhengHei, sans-serif"
        common = dict(margin=dict(l=10, r=10, b=10, t=30), paper_bgcolor=paper,
                      font=dict(color=font, family=fam))
        if chart_type in ("scatter3d", "surface"):
            fig.update_layout(scene=dict(
                xaxis=dict(title="X (欄/寬度)", backgroundcolor=bg, gridcolor=grid, color=font),
                yaxis=dict(title="Y (列/高度)", backgroundcolor=bg, gridcolor=grid, color=font,
                           autorange="reversed"),
                zaxis=dict(title="灰階值", range=[vmin, vmax], backgroundcolor=bg,
                           gridcolor=grid, color=font),
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))), **common)
        elif chart_type == "histogram":
            fig.update_layout(plot_bgcolor=bg, bargap=0.05,
                xaxis=dict(title="灰階值", range=[vmin, vmax], gridcolor=grid, color=font),
                yaxis=dict(title="數量 (區塊數)", gridcolor=grid, color=font), **common)
        elif chart_type == "profile":
            fig.update_layout(plot_bgcolor=bg,
                legend=dict(font=dict(color=font), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(title="位置 (採樣區塊索引)", gridcolor=grid, color=font),
                yaxis=dict(title="灰階值", range=[vmin, vmax], gridcolor=grid, color=font), **common)
        else:  # heatmap
            fig.update_layout(plot_bgcolor=bg,
                xaxis=dict(title="X (欄/寬度)", gridcolor=grid, color=font),
                yaxis=dict(title="Y (列/高度)", gridcolor=grid, color=font,
                           autorange="reversed"), **common)


def create_plotly_html(block_means, chart_type="scatter3d", max_scatter_points=40000,
                       colorscale="Viridis", theme="dark", include_plotlyjs=True) -> str:
    """模組層便利函式 (向後相容)。"""
    return ChartBuilder(colorscale, theme, max_scatter_points).build_html(
        block_means, chart_type, include_plotlyjs)
