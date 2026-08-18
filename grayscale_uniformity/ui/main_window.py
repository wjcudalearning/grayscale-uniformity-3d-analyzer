"""主視窗：載入影像、設定參數、即時 3D 視覺化與報表匯出。"""
import os
import tempfile
from datetime import datetime
import numpy as np
from PySide6.QtCore import Qt, Slot, QUrl, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QGroupBox, QFrame,
    QProgressBar, QMessageBox, QSplitter, QScrollArea
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..image_io import ImageLoader
from ..analysis import UniformityResult
from ..charts import create_plotly_html
from ..report import create_report_html
from ..grading import parse_thresholds, DEFAULT_THRESHOLDS
from .worker import AnalysisWorker
from .widgets import MetricCard, field_label_qss, APP_QSS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("影像灰階均勻度 3D 視覺化分析工具")
        self.resize(1300, 850)
        self.setMinimumSize(950, 650)

        self.current_image_path = None
        self.current_gray_img = None
        self.current_result: UniformityResult = None
        self.worker = None
        self._req_counter = 0      # 遞增請求編號，用以忽略過期的背景結果 (取代危險的 terminate())
        self._active_req = 0
        self._workers = []         # 保留執行中 worker 參照，避免被 GC

        # 每次分析的暫存輸出資料夾 (圖表 HTML 與共用 plotly.min.js 置於同處)
        self._tmp_dir = tempfile.mkdtemp(prefix="grayscale3d_")
        self._chart_tmp_path = os.path.join(self._tmp_dir, "chart.html")
        self._prepare_shared_plotlyjs()

        # 參數變更防抖計時器：快速切換下拉選單時只在停頓後觸發一次重算
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(250)
        self._debounce_timer.timeout.connect(self._run_analysis)

        self.setAcceptDrops(True)  # 支援拖放影像檔載入

        self._setup_ui()
        self.setStyleSheet(APP_QSS)

    def _prepare_shared_plotlyjs(self):
        """將 plotly.min.js 寫入暫存資料夾一次，供 App 內圖表以 'directory' 模式共用引用，
        避免每次分析都內嵌 5MB+ 的函式庫拖慢重繪。失敗則回退為完整內嵌。"""
        self._plotlyjs_mode = True
        try:
            from plotly.offline import get_plotlyjs
            js_path = os.path.join(self._tmp_dir, "plotly.min.js")
            if not os.path.exists(js_path):
                with open(js_path, "w", encoding="utf-8") as f:
                    f.write(get_plotlyjs())
            self._plotlyjs_mode = "directory"
        except Exception:
            self._plotlyjs_mode = True

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ------------------ 左側控制面板 ------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(12)

        # 1. 檔案載入區
        file_group = QGroupBox("檔案操作")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(8)

        self.btn_open = QPushButton("📂 開啟影像檔案...")
        self.btn_open.setObjectName("primary")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_file_dialog)
        file_layout.addWidget(self.btn_open)

        self.btn_test_pattern = QPushButton("🎨 生成測試漸層圖")
        self.btn_test_pattern.setCursor(Qt.PointingHandCursor)
        self.btn_test_pattern.clicked.connect(self._generate_test_pattern)
        file_layout.addWidget(self.btn_test_pattern)

        self.lbl_file_info = QLabel("尚未載入影像")
        self.lbl_file_info.setWordWrap(True)
        self.lbl_file_info.setStyleSheet("color: #6b7280; font-size: 12px;")
        file_layout.addWidget(self.lbl_file_info)

        # 縮圖預覽
        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setFixedHeight(120)
        self.lbl_thumbnail.setStyleSheet(
            "background-color: #f9fafb; border: 1px dashed #cbd0d8; border-radius: 8px; color: #9ca3af; font-size: 12px;"
        )
        self.lbl_thumbnail.setText("縮圖預覽")
        file_layout.addWidget(self.lbl_thumbnail)

        scroll_layout.addWidget(file_group)

        # 2. 參數設定區
        param_group = QGroupBox("分析與視覺化設定")
        param_layout = QVBoxLayout(param_group)
        param_layout.setSpacing(8)

        lbl_block = QLabel("區塊採樣大小 (Pooling):")
        lbl_block.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_block)
        self.combo_block = QComboBox()
        self.combo_block.addItem("2x2 (每 4 個像素算 1 個 Mean)", 2)
        self.combo_block.addItem("1x1 (原始像素，無降採樣)", 1)
        self.combo_block.addItem("4x4 (每 16 個像素算 1 個 Mean)", 4)
        self.combo_block.addItem("8x8 (每 64 個像素算 1 個 Mean)", 8)
        self.combo_block.addItem("16x16 (每 256 個像素算 1 個 Mean)", 16)
        self.combo_block.currentIndexChanged.connect(self._schedule_analysis)
        param_layout.addWidget(self.combo_block)

        lbl_chart = QLabel("視覺化模式:")
        lbl_chart.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_chart)
        self.combo_chart = QComboBox()
        self.combo_chart.addItem("3D 散點圖 (Scatter3D)", "scatter3d")
        self.combo_chart.addItem("3D 曲面圖 (Surface)", "surface")
        self.combo_chart.addItem("2D 熱力圖 (Heatmap)", "heatmap")
        self.combo_chart.addItem("灰階直方圖 (Histogram)", "histogram")
        self.combo_chart.addItem("中央剖面線 (Profile)", "profile")
        self.combo_chart.currentIndexChanged.connect(self._schedule_analysis)
        param_layout.addWidget(self.combo_chart)

        lbl_color = QLabel("色溫配色 (Colormap):")
        lbl_color.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_color)
        self.combo_color = QComboBox()
        for cmap in ["Viridis", "Plasma", "Turbo", "Jet", "Greys", "Hot", "Cividis"]:
            self.combo_color.addItem(cmap, cmap)
        self.combo_color.currentIndexChanged.connect(self._schedule_analysis)
        param_layout.addWidget(self.combo_color)

        lbl_quality = QLabel("渲染品質 (散點密度):")
        lbl_quality.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_quality)
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("平衡 (約 4 萬點)", 40000)
        self.combo_quality.addItem("效能優先 (約 2 萬點)", 20000)
        self.combo_quality.addItem("品質優先 (約 8 萬點)", 80000)
        self.combo_quality.currentIndexChanged.connect(self._schedule_analysis)
        param_layout.addWidget(self.combo_quality)

        lbl_theme = QLabel("圖表主題:")
        lbl_theme.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("淺色 (Light)", "light")
        self.combo_theme.addItem("深色 (Dark)", "dark")
        self.combo_theme.currentIndexChanged.connect(self._schedule_analysis)
        param_layout.addWidget(self.combo_theme)

        # 報表警戒線門檻 (%)，逗號分隔；供完整 HTML 報表分級使用
        lbl_thr = QLabel("報表警戒線門檻 (%，逗號分隔):")
        lbl_thr.setStyleSheet(field_label_qss())
        param_layout.addWidget(lbl_thr)
        self.edit_thresholds = QLineEdit(", ".join(f"{t:g}" for t in DEFAULT_THRESHOLDS))
        self.edit_thresholds.setPlaceholderText("例如 3, 5, 10, 20")
        self.edit_thresholds.setToolTip("僅影響「完整分析報表」的警戒線與分級；以「偏離平均 ±X%」定義")
        param_layout.addWidget(self.edit_thresholds)

        scroll_layout.addWidget(param_group)

        # 3. 均勻度統計指標區
        stats_group = QGroupBox("灰階均勻度統計")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(8)

        self.card_cv_uniformity = MetricCard("變異係數均勻度", "-- %", "#059669", "#f0fdf9")
        stats_layout.addWidget(self.card_cv_uniformity)

        self.card_range_uniformity = MetricCard("極值對比均勻度", "-- %", "#2563eb", "#eff6ff")
        stats_layout.addWidget(self.card_range_uniformity)

        self.lbl_stat_mean = QLabel("平均亮度 (Mean): --")
        self.lbl_stat_std = QLabel("標準差 (Std): --")
        self.lbl_stat_min_max = QLabel("極值 (Min / Max): -- / --")
        self.lbl_stat_ratio = QLabel("最小/最大比例: -- %")
        self.lbl_stat_points = QLabel("分析資料點數: --")

        for lbl in [self.lbl_stat_mean, self.lbl_stat_std, self.lbl_stat_min_max,
                    self.lbl_stat_ratio, self.lbl_stat_points]:
            lbl.setStyleSheet("color: #4b5563; font-size: 13px; padding: 3px 2px; border-bottom: 1px solid #f1f2f4;")
            stats_layout.addWidget(lbl)

        scroll_layout.addWidget(stats_group)

        # 4. 匯出按鈕
        self.btn_report = QPushButton("📊 匯出完整分析報表 (HTML)")
        self.btn_report.setObjectName("primary")
        self.btn_report.setCursor(Qt.PointingHandCursor)
        self.btn_report.clicked.connect(self._export_full_report)
        self.btn_report.setEnabled(False)
        scroll_layout.addWidget(self.btn_report)

        self.btn_export = QPushButton("💾 匯出數據 (CSV / 矩陣 / 單圖 HTML)")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export_report)
        self.btn_export.setEnabled(False)
        scroll_layout.addWidget(self.btn_export)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        splitter.addWidget(left_panel)
        splitter.setStretchFactor(0, 0)

        # ------------------ 右側視覺化 Web 視圖 ------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.setHtml(self._get_placeholder_html())
        right_layout.addWidget(self.web_view)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 920])

    def _get_placeholder_html(self) -> str:
        return """
        <!DOCTYPE html><html><head><style>
            body { margin:0; padding:0; height:100vh; display:flex; flex-direction:column;
                   justify-content:center; align-items:center; background-color:#ffffff;
                   color:#6b7280; font-family:'Segoe UI', Microsoft JhengHei, sans-serif; }
            .icon { font-size:54px; margin-bottom:12px; opacity:0.85; }
            .text { font-size:18px; font-weight:600; color:#374151; }
            .sub { font-size:13px; color:#9ca3af; margin-top:8px; }
        </style></head><body>
            <div class="icon">📊</div>
            <div class="text">請開啟圖片或生成測試圖進行灰階均勻度分析</div>
            <div class="sub">支援 2x2 區塊均值 · 3D 散點/曲面 · 熱力圖 · 直方圖 · 剖面線</div>
        </body></html>
        """

    # ------------------ 檔案載入 ------------------
    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇影像檔案", "",
            "影像檔案 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有檔案 (*.*)")
        if file_path:
            self._load_image(file_path)

    def _load_image(self, file_path: str):
        try:
            self.current_gray_img = ImageLoader.load(file_path)
            self.current_image_path = file_path
            h, w = self.current_gray_img.shape
            file_name = os.path.basename(file_path)
            self.lbl_file_info.setText(f"📄 {file_name}\n解析度: {w} × {h} ({w*h:,} 像素)")
            self._update_thumbnail(self.current_gray_img)
            self._run_analysis()   # 載入新圖立即分析，不需防抖
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"讀取圖片失敗: {str(e)}")

    def _generate_test_pattern(self):
        """生成合成漸層測試影像 (模擬中央均勻與四周漸暗的光場)"""
        h, w = 300, 400
        y, x = np.ogrid[:h, :w]
        center_y, center_x = h / 2.0, w / 2.0
        dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        pattern = 210.0 - 60.0 * (dist / max_dist) ** 1.8
        pattern = np.clip(pattern + np.random.normal(0, 3, (h, w)), 0, 255).astype(np.float32)

        self.current_gray_img = pattern
        self.current_image_path = "測試光場模擬圖 (Synthetic Pattern)"
        self.lbl_file_info.setText(f"🎨 測試光場模擬圖\n解析度: {w} × {h} ({w*h:,} 像素)")
        self._update_thumbnail(pattern)
        self._run_analysis()

    def _update_thumbnail(self, gray_data: np.ndarray):
        # 以 .copy() 建立由 QImage 自持的連續緩衝，避免區域 numpy 陣列被回收造成縮圖損毀
        norm_img = np.ascontiguousarray(np.clip(gray_data, 0, 255).astype(np.uint8))
        h, w = norm_img.shape
        q_img = QImage(norm_img.data, w, h, w, QImage.Format_Grayscale8).copy()
        scaled = QPixmap.fromImage(q_img).scaled(
            self.lbl_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_thumbnail.setPixmap(scaled)

    # ------------------ 分析流程 ------------------
    def _schedule_analysis(self):
        """參數變更時排程一次防抖分析 (250ms 內連續變更只執行最後一次)"""
        if self.current_gray_img is None:
            return
        self._debounce_timer.start()

    def _run_analysis(self):
        if self.current_gray_img is None:
            return
        self._debounce_timer.stop()

        self.progress_bar.show()
        self.btn_open.setEnabled(False)
        self.btn_test_pattern.setEnabled(False)

        # 協作式取消：遞增請求編號，過期 worker 結果會被忽略 (不使用危險的 terminate())
        self._req_counter += 1
        self._active_req = self._req_counter
        self._workers = [w for w in self._workers if w.isRunning()]

        worker = AnalysisWorker(
            self._active_req, self.current_gray_img, self.combo_block.currentData(),
            self.combo_chart.currentData(), self.combo_color.currentData(),
            self.combo_theme.currentData(), self.combo_quality.currentData(),
            self._plotlyjs_mode)
        worker.finished.connect(self._on_analysis_finished)
        worker.error.connect(self._on_analysis_error)
        worker.finished.connect(lambda *_: self._cleanup_worker(worker))
        worker.error.connect(lambda *_: self._cleanup_worker(worker))
        self._workers.append(worker)
        self.worker = worker
        worker.start()

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    @Slot(int, object, str)
    def _on_analysis_finished(self, req_id: int, result: UniformityResult, html_content: str):
        if req_id != self._active_req:
            return  # 忽略過期結果 (使用者已切換參數)
        self.progress_bar.hide()
        self.btn_open.setEnabled(True)
        self.btn_test_pattern.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_report.setEnabled(True)
        self.current_result = result

        self.card_cv_uniformity.set_value(f"{result.cv_uniformity:.2f} %")
        self.card_range_uniformity.set_value(f"{result.range_uniformity:.2f} %")
        self.lbl_stat_mean.setText(f"平均亮度 (Mean): {result.mean:.2f}")
        self.lbl_stat_std.setText(f"標準差 (Std): {result.std:.2f}")
        self.lbl_stat_min_max.setText(f"極值 (Min / Max): {result.min_val:.1f} / {result.max_val:.1f}")
        self.lbl_stat_ratio.setText(f"最小/最大比例: {result.min_max_ratio:.2f} %")
        sw, sh = result.sampled_shape[1], result.sampled_shape[0]
        self.lbl_stat_points.setText(f"分析採樣點: {sw} × {sh} ({sw*sh:,} 個區塊均值)")

        self._load_chart_html(html_content)

    def _load_chart_html(self, html_content: str):
        # 透過暫存檔以 file:// 載入，避開 QWebEngineView.setHtml 的 ~2MB 內容上限
        try:
            with open(self._chart_tmp_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.web_view.load(QUrl.fromLocalFile(self._chart_tmp_path))
        except Exception:
            self.web_view.setHtml(html_content)

    @Slot(int, str)
    def _on_analysis_error(self, req_id: int, err_msg: str):
        if req_id != self._active_req:
            return
        self.progress_bar.hide()
        self.btn_open.setEnabled(True)
        self.btn_test_pattern.setEnabled(True)
        QMessageBox.critical(self, "分析錯誤", f"計算過程中發生錯誤:\n{err_msg}")

    # ------------------ 拖放載入影像 ------------------
    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() and any(u.isLocalFile() for u in mime.urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if ImageLoader.is_supported(path):
                    self._load_image(path)
                    event.acceptProposedAction()
                else:
                    ext = os.path.splitext(path)[1].lower()
                    QMessageBox.warning(self, "不支援的檔案", f"無法載入此類型檔案: {ext or '未知'}")
                return
        event.ignore()

    # ------------------ 匯出 ------------------
    def _export_full_report(self):
        """匯出多圖表卡片式 HTML 均勻度分析報表 (含 3/5/10/20% 警戒線分級)"""
        if self.current_result is None:
            return
        base = os.path.splitext(os.path.basename(str(self.current_image_path or "uniformity")))[0]
        file_path, _ = QFileDialog.getSaveFileName(
            self, "匯出完整分析報表", f"{base}_report.html", "HTML 分析報表 (*.html)")
        if not file_path:
            return
        if not file_path.lower().endswith(".html"):
            file_path += ".html"
        # 解析使用者自訂警戒線門檻 (無效則回退預設)，並回填正規化後的值
        thresholds = parse_thresholds(self.edit_thresholds.text(), DEFAULT_THRESHOLDS)
        self.edit_thresholds.setText(", ".join(f"{t:g}" for t in thresholds))
        try:
            html = create_report_html(
                self.current_result, colorscale=self.combo_color.currentData(),
                thresholds=thresholds,
                image_name=str(self.current_image_path or ""),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "成功", f"完整分析報表已儲存至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"無法產生報表: {str(e)}")

    def _export_report(self):
        if self.current_result is None:
            return
        base = os.path.splitext(os.path.basename(str(self.current_image_path or "uniformity")))[0]
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "匯出均勻度分析報告", f"{base}_report.csv",
            "CSV 統計報告 (*.csv);;HTML 互動圖表 (*.html);;"
            "區塊均值矩陣 CSV (*.csv);;區塊均值矩陣 NumPy (*.npy)")
        if not file_path:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        r = self.current_result
        ext = os.path.splitext(file_path)[1].lower()
        is_matrix = "矩陣" in (selected_filter or "")

        try:
            if ext == ".html":
                html = create_plotly_html(
                    r.block_means, chart_type=self.combo_chart.currentData(),
                    colorscale=self.combo_color.currentData(),
                    theme=self.combo_theme.currentData(),
                    include_plotlyjs=True)  # 匯出檔需獨立離線可用
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html)
            elif ext == ".npy":
                np.save(file_path, r.block_means)
            elif is_matrix and ext == ".csv":
                np.savetxt(file_path, r.block_means, fmt="%.4f", delimiter=",",
                           header=f"Block-mean matrix ({r.sampled_shape[0]}x{r.sampled_shape[1]}) "
                                  f"from {self.current_image_path} @ {timestamp}")
            else:
                with open(file_path, "w", encoding="utf-8-sig") as f:
                    f.write("項目,數值\n")
                    f.write(f"匯出時間,{timestamp}\n")
                    f.write(f"原始影像檔案,{self.current_image_path}\n")
                    f.write(f"原始解析度,{r.original_shape[1]}x{r.original_shape[0]}\n")
                    f.write(f"採樣區塊大小,{r.block_size}x{r.block_size}\n")
                    f.write(f"採樣後網格,{r.sampled_shape[1]}x{r.sampled_shape[0]}\n")
                    f.write(f"變異係數均勻度 (CV Uniformity),{r.cv_uniformity:.4f}%\n")
                    f.write(f"極值對比均勻度 (Range Uniformity),{r.range_uniformity:.4f}%\n")
                    f.write(f"平均亮度 (Mean),{r.mean:.4f}\n")
                    f.write(f"標準差 (Std),{r.std:.4f}\n")
                    f.write(f"最小值 (Min),{r.min_val:.4f}\n")
                    f.write(f"最大值 (Max),{r.max_val:.4f}\n")
                    f.write(f"最小最大值比例,{r.min_max_ratio:.4f}%\n")

            QMessageBox.information(self, "成功", f"報告已成功儲存至:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"無法儲存報告: {str(e)}")

    def closeEvent(self, event):
        # 結束前使殘留結果失效、等待背景執行緒並清理暫存資料夾
        self._active_req = -1
        for w in list(self._workers):
            if w.isRunning():
                w.wait(3000)
        try:
            import shutil
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        except Exception:
            pass
        super().closeEvent(event)
