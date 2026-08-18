"""卡片式 HTML 均勻度分析報表 (多圖表 + 3/5/10/20% 警戒線分級)。"""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from typing import Optional, List

from .analysis import UniformityResult
from .grading import UniformityGrader, ZONE_COLORS
from .charts import auto_value_range, downsample_for_view


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ReportBuilder:
    """組裝完整的離線 HTML 分析報表 (內嵌 plotly.js 一次)。"""

    def __init__(self, colorscale: str = "Viridis", thresholds: Optional[List[float]] = None):
        self.colorscale = colorscale
        self.grader = UniformityGrader(thresholds)

    # -- 單一圖表輸出為可嵌入 div (不含 plotly.js) --
    @staticmethod
    def _fig_div(fig: go.Figure, height: int = 400) -> str:
        fig.update_layout(
            autosize=True, height=height, margin=dict(l=12, r=12, b=12, t=36),
            paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
            font=dict(color="#374151", family="Segoe UI, Microsoft JhengHei, sans-serif"))
        return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                           config={"responsive": True, "displayModeBar": True,
                                   "modeBarButtonsToRemove": ["toImage", "lasso2d", "select2d"]})

    @staticmethod
    def _axes(fig, xt, yt, y_reversed=False):
        fig.update_xaxes(title_text=xt, gridcolor="#e5e7eb", color="#374151", zeroline=False)
        fig.update_yaxes(title_text=yt, gridcolor="#e5e7eb", color="#374151", zeroline=False,
                         autorange="reversed" if y_reversed else True)

    def build(self, result: UniformityResult, image_name: str = "", timestamp: str = "") -> str:
        from plotly.offline import get_plotlyjs

        bm = result.block_means
        mean_val = result.mean
        grade = self.grader.grade(bm, mean_val)
        thr = grade.thresholds
        vmin, vmax = auto_value_range(bm)
        h, w = bm.shape

        # 1. 空間熱力圖
        hm, _ = downsample_for_view(bm)
        fig_hm = go.Figure(go.Heatmap(z=hm, colorscale=self.colorscale, zmin=vmin, zmax=vmax,
                                      colorbar=dict(title="灰階值"),
                                      hovertemplate="X: %{x}<br>Y: %{y}<br>灰階值: %{z:.2f}<extra></extra>"))
        self._axes(fig_hm, "X (欄/寬度)", "Y (列/高度)", y_reversed=True)
        # 鎖定 1:1 長寬比，避免狹長影像被拉伸變形 (letterbox 置中)
        fig_hm.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain")
        div_hm = self._fig_div(fig_hm, 420)

        # 2. 均勻度分區圖 (偏差 zone map)
        dev_view, _ = downsample_for_view(grade.deviation_pct)
        zmax_zone = max(25.0, thr[-1] * 1.25)
        zone_scale, prev = [], 0.0
        for i, t in enumerate(thr + [zmax_zone]):
            c = ZONE_COLORS[min(i, len(ZONE_COLORS) - 1)]
            zone_scale.append([prev / zmax_zone, c])
            zone_scale.append([min(t, zmax_zone) / zmax_zone, c])
            prev = t
        fig_zone = go.Figure(go.Heatmap(z=dev_view, colorscale=zone_scale, zmin=0, zmax=zmax_zone,
                                        colorbar=dict(title="偏差 %", tickvals=[0] + thr),
                                        hovertemplate="X: %{x}<br>Y: %{y}<br>偏差: %{z:.2f}%<extra></extra>"))
        self._axes(fig_zone, "X (欄/寬度)", "Y (列/高度)", y_reversed=True)
        fig_zone.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain")
        div_zone = self._fig_div(fig_zone, 420)

        # 3. 直方圖 + 警戒線 (伺服器端分箱，避免超大影像把數千萬原始值塞進 HTML)
        counts, edges = np.histogram(bm, bins=72, range=(vmin, vmax))
        centers = (edges[:-1] + edges[1:]) / 2.0
        fig_hist = go.Figure(go.Bar(x=centers, y=counts, width=(edges[1] - edges[0]),
                                    marker=dict(color="#93c5fd"),
                                    hovertemplate="灰階值: %{x:.1f}<br>數量: %{y}<extra></extra>"))
        fig_hist.add_vline(x=mean_val, line=dict(color="#111827", width=2),
                           annotation_text="平均", annotation_position="top")
        for t, c in zip(thr, ZONE_COLORS):
            fig_hist.add_vline(x=mean_val * (1 + t / 100.0), line=dict(color=c, width=1.2, dash="dash"),
                               annotation_text=f"±{t:g}%", annotation_position="top",
                               annotation_font=dict(color=c, size=10))
            fig_hist.add_vline(x=mean_val * (1 - t / 100.0), line=dict(color=c, width=1.2, dash="dash"))
        self._axes(fig_hist, "灰階值", "數量 (區塊數)")
        fig_hist.update_layout(bargap=0.04)
        div_hist = self._fig_div(fig_hist, 380)

        # 4. 中央剖面線 + 容差帶
        fig_prof = go.Figure()
        fig_prof.add_trace(go.Scatter(x=np.arange(w), y=bm[h // 2, :], mode="lines",
                                      name="中央橫向 (Row)", line=dict(color="#2563eb", width=2)))
        fig_prof.add_trace(go.Scatter(x=np.arange(h), y=bm[:, w // 2], mode="lines",
                                      name="中央縱向 (Col)", line=dict(color="#059669", width=2)))
        fig_prof.add_hline(y=mean_val, line=dict(color="#111827", width=1.5))
        for t, c in zip(thr, ZONE_COLORS):
            for sign in (1, -1):
                fig_prof.add_hline(y=mean_val * (1 + sign * t / 100.0),
                                   line=dict(color=c, width=1, dash="dash"))
        self._axes(fig_prof, "位置 (採樣區塊索引)", "灰階值")
        fig_prof.update_layout(legend=dict(orientation="h", y=1.12, x=0))
        div_prof = self._fig_div(fig_prof, 380)

        # 5. 徑向亮度衰減 (以降採樣資料計算，避免超大影像配置數千萬元素的座標網格)
        rad_src, _ = downsample_for_view(bm, 250000)
        rh, rw = rad_src.shape
        yy, xx = np.mgrid[0:rh, 0:rw]
        cy, cx = (rh - 1) / 2.0, (rw - 1) / 2.0
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        rmax = float(r.max()) if r.size else 1.0
        rn = (r / rmax if rmax > 0 else r).ravel()
        nb = 48
        idx = np.clip((rn * nb).astype(int), 0, nb - 1)
        radial_mean = np.bincount(idx, weights=rad_src.ravel(), minlength=nb) / \
            np.maximum(np.bincount(idx, minlength=nb), 1)
        radial_x = (np.arange(nb) + 0.5) / nb * 100.0
        fig_rad = go.Figure()
        fig_rad.add_trace(go.Scatter(x=radial_x, y=radial_mean, mode="lines+markers",
                                     line=dict(color="#7c3aed", width=2), marker=dict(size=4),
                                     name="徑向平均"))
        fig_rad.add_hline(y=mean_val, line=dict(color="#111827", width=1.5))
        for t, c in zip(thr, ZONE_COLORS):
            for sign in (1, -1):
                fig_rad.add_hline(y=mean_val * (1 + sign * t / 100.0),
                                  line=dict(color=c, width=1, dash="dash"))
        self._axes(fig_rad, "距中心距離 (% 最大半徑)", "灰階平均值")
        div_rad = self._fig_div(fig_rad, 380)

        # 6. 3D 曲面總覽
        sf, step = downsample_for_view(bm, 90000)
        fig_surf = go.Figure(go.Surface(z=sf, x=np.arange(0, w, step), y=np.arange(0, h, step),
                                        colorscale=self.colorscale, cmin=vmin, cmax=vmax,
                                        colorbar=dict(title="灰階值")))
        fig_surf.update_layout(scene=dict(
            xaxis=dict(title="X", color="#374151"),
            yaxis=dict(title="Y", color="#374151", autorange="reversed"),
            zaxis=dict(title="灰階值", range=[vmin, vmax], color="#374151"),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))))
        div_surf = self._fig_div(fig_surf, 460)

        return self._assemble(result, grade, image_name, timestamp,
                              [div_hm, div_zone, div_hist, div_prof, div_rad, div_surf],
                              get_plotlyjs())

    def _assemble(self, result, grade, image_name, timestamp, divs, plotly_js) -> str:
        thr = grade.thresholds
        pass_rows = "".join(
            f'<tr><td>±{t:g}%</td><td class="mono">{grade.pass_rates[t]:.2f}%</td>'
            f'<td><div class="bar"><span style="width:{min(grade.pass_rates[t],100):.1f}%;'
            f'background:{c}"></span></div></td></tr>'
            for t, c in zip(thr, ZONE_COLORS))

        stat_cards = f"""
          <div class="stat"><div class="k">平均亮度 (Mean)</div><div class="v">{result.mean:.2f}</div></div>
          <div class="stat"><div class="k">標準差 (Std)</div><div class="v">{result.std:.2f}</div></div>
          <div class="stat"><div class="k">變異係數均勻度</div><div class="v">{result.cv_uniformity:.2f}%</div></div>
          <div class="stat"><div class="k">極值對比均勻度</div><div class="v">{result.range_uniformity:.2f}%</div></div>
          <div class="stat"><div class="k">最大偏差</div><div class="v">{grade.max_dev_pct:.2f}%</div></div>
          <div class="stat"><div class="k">P99 偏差 (評級依據)</div><div class="v">{grade.p99_dev_pct:.2f}%</div></div>
          <div class="stat"><div class="k">極值 (Min / Max)</div><div class="v">{result.min_val:.1f} / {result.max_val:.1f}</div></div>
          <div class="stat"><div class="k">採樣網格</div><div class="v">{result.sampled_shape[1]}×{result.sampled_shape[0]}</div></div>
        """

        titles = [
            ("① 空間熱力圖", "整體亮度分佈 (俯視)"),
            ("② 均勻度分區圖", "偏離平均之偏差落在各警戒區間"),
            ("③ 灰階直方圖", "分佈集中度，虛線為 ±警戒線"),
            ("④ 中央剖面線", "中央橫/縱向切面 + 容差帶"),
            ("⑤ 徑向亮度衰減", "由中心向外的平均亮度趨勢 (暗角判讀)"),
            ("⑥ 3D 曲面總覽", "整體起伏立體檢視"),
        ]
        charts_html = "".join(
            f'<section class="card chart"><h2>{t}<span class="sub">{s}</span></h2>{d}</section>'
            for (t, s), d in zip(titles, divs))

        thr_desc = "、".join(f"±{t:g}%" for t in thr)
        css = _REPORT_CSS

        return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>灰階均勻度分析報表</title>
{css}
<script type="text/javascript">{plotly_js}</script>
</head><body>
<div class="wrap">
  <header class="top">
    <h1>灰階均勻度分析報表</h1>
    <div class="meta">
      影像檔案：{_esc(image_name or "(未命名影像)")}<br>
      原始解析度：{result.original_shape[1]}×{result.original_shape[0]}　|
      採樣區塊：{result.block_size}×{result.block_size}　|　採樣網格：{result.sampled_shape[1]}×{result.sampled_shape[0]}<br>
      產生時間：{_esc(timestamp)}　|　警戒線：{thr_desc}（偏離平均定義）
    </div>
  </header>

  <div class="grade-hero">
    <div class="badge" style="background:{grade.grade_color}">{_esc(grade.grade_label)}</div>
    <div class="desc">
      判定等級 <b>{_esc(grade.grade_label)}</b><br>
      最大偏差 <b>{grade.max_dev_pct:.2f}%</b>　·　P99 偏差 <b>{grade.p99_dev_pct:.2f}%</b>（用以抗少量熱點/壞點）<br>
      評級方式：以第 99 百分位偏差對照警戒線分級。
    </div>
  </div>

  <div class="stats">{stat_cards}</div>

  <div class="passtable">
    <h2>各警戒線通過率（區塊落在容差內比例）</h2>
    <table>
      <thead><tr><th>警戒線</th><th>通過率</th><th style="width:45%">分佈</th></tr></thead>
      <tbody>{pass_rows}</tbody>
    </table>
  </div>

  <div class="grid">{charts_html}</div>

  <footer>由 灰階均勻度 3D 視覺化分析工具 產生　·　不均勻度定義：|區塊值 − 平均| / 平均 × 100%</footer>
</div>
</body></html>"""


_REPORT_CSS = """
    <style>
      * { box-sizing: border-box; }
      body { margin:0; background:#f4f5f7; color:#1f2430;
             font-family:"Segoe UI","Microsoft JhengHei",sans-serif; }
      .wrap { max-width:1280px; margin:0 auto; padding:28px 22px 60px; }
      header.top { margin-bottom:22px; }
      header.top h1 { font-size:22px; margin:0 0 6px; font-weight:700; }
      header.top .meta { color:#6b7280; font-size:13px; line-height:1.7; }
      .grade-hero { display:flex; align-items:center; gap:20px; flex-wrap:wrap;
             background:#fff; border:1px solid #e5e7eb; border-radius:14px;
             padding:20px 24px; margin-bottom:18px; }
      .badge { color:#fff; font-weight:700; font-size:20px; padding:14px 22px;
               border-radius:12px; white-space:nowrap; }
      .grade-hero .desc { font-size:13px; color:#4b5563; line-height:1.7; }
      .grade-hero .desc b { color:#1f2430; }
      .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
               gap:12px; margin-bottom:18px; }
      .stat { background:#fff; border:1px solid #e5e7eb; border-left:4px solid #2563eb;
              border-radius:10px; padding:10px 14px; }
      .stat .k { font-size:11px; color:#6b7280; font-weight:600; }
      .stat .v { font-size:19px; font-weight:700; color:#111827; margin-top:2px; }
      .passtable { background:#fff; border:1px solid #e5e7eb; border-radius:12px;
                   padding:16px 18px; margin-bottom:18px; }
      .passtable h2 { font-size:15px; margin:0 0 10px; }
      table { width:100%; border-collapse:collapse; font-size:13px; }
      th,td { text-align:left; padding:7px 8px; border-bottom:1px solid #f1f2f4; }
      th { color:#6b7280; font-weight:600; }
      td.mono { font-variant-numeric:tabular-nums; font-weight:600; }
      .bar { background:#eef0f3; border-radius:6px; height:9px; width:100%; overflow:hidden; }
      .bar span { display:block; height:100%; border-radius:6px; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(520px,1fr)); gap:16px; }
      .card { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:14px 16px 6px; }
      .card h2 { font-size:15px; margin:0 0 4px; display:flex; align-items:baseline; gap:10px; }
      .card h2 .sub { font-size:12px; color:#9ca3af; font-weight:400; }
      .card .plotly-graph-div { width:100% !important; }
      footer { margin-top:30px; color:#9ca3af; font-size:12px; text-align:center; }
      @media (max-width:560px){ .grid{grid-template-columns:1fr;} }
    </style>
    """


def create_report_html(result, colorscale="Viridis", thresholds=None,
                       image_name="", timestamp="") -> str:
    """模組層便利函式 (向後相容)。"""
    return ReportBuilder(colorscale, thresholds).build(result, image_name, timestamp)
