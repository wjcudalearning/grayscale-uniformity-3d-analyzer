# 專案待辦清單 (TODO) - 灰階均勻度 3D 視覺化分析工具

## 1. 環境與依賴配置
- [x] 建立 `requirements.txt`
- [x] 於 venv 確認安裝相依套件 (`PySide6`, `numpy`, `opencv-python`, `Pillow`, `plotly`)

## 2. 核心演算法與資料處理模組 (`analyzer.py`)
- [x] 影像讀取與自動轉灰階處理 (已全開 PIL 記憶體限制 `Image.MAX_IMAGE_PIXELS = None`，支援大圖與中文路徑)
- [x] 每 4 個像素 (2x2) 或自訂網格取 mean 的降採樣 (Pooling) 演算法
- [x] 均勻度指標計算：
  - [x] 灰階平均值 (Mean)、標準差 (Std)、最小值 (Min)、最大值 (Max)
  - [x] 變異係數均勻度 $U_{\text{CV}} = (1 - \sigma / \mu) \times 100\%$
  - [x] 極值對比均勻度 $U_{\text{range}} = (1 - \frac{\text{Max} - \text{Min}}{\text{Max} + \text{Min}}) \times 100\%$
  - [x] 最低/最高比例均勻度 $(\text{Min} / \text{Max}) \times 100\%$
- [x] Plotly 3D Scatter 圖表生成邏輯（X: 欄座標, Y: 列座標, Z: 灰階值, 色彩對應亮度）
- [x] 支援 3D Surface / 2D Heatmap 模式切換與多種色溫色表

## 3. GUI 介面開發 (`main_window.py` / `main.py`)
- [x] 建立 PySide6 主視窗佈局 (現代化深色主題、高質感卡片佈局)
- [x] 檔案選擇器與原始影像縮圖即時預覽
- [x] 採樣網格大小設定下拉選單 (預設 2x2 [4px], 1x1, 4x4, 8x8, 16x16)
- [x] 統計數據面板 (卡片式呈現均勻度百分比、平均值、標準差、極值等)
- [x] 嵌入 `QWebEngineView` 呈現 Plotly 3D 互動圖表 (支援旋轉、縮放、懸停數值)
- [x] 背景執行緒 (`QThread`) 異步計算與渲染，大圖處理不卡介面
- [x] 內建「生成測試漸層圖」方便快速測試
- [x] 支援匯出 CSV 分析報告與獨立 HTML 互動圖表

## 4. 整合與測試
- [x] 撰寫單元測試 (`test_app.py`) 驗證演算法、超大圖支援、均勻度指標與圖表生成
- [x] 測試全數通過 (5/5 OK)

## 5. 待優化項目 (Optimization Backlog)

### 5.1 已知問題與修正
- [x] **3D 圖表空白問題**：`QWebEngineView.setHtml()` 有約 2MB 內容上限，但內嵌 plotly.js 的完整 HTML 達 5MB 以上導致靜默失敗、圖表空白 → 已改為寫入暫存檔並以 `file://` URL 載入（`main_window.py`）
- [x] **縮圖記憶體風險**：改用 `np.ascontiguousarray(...)` + `QImage(...).copy()`，由 QImage 自持緩衝，避免區域 numpy 陣列被回收導致縮圖損毀
- [x] **plotly.js 重複內嵌**：App 內圖表改用 `include_plotlyjs='directory'`，plotly.min.js 於啟動時寫入暫存夾一次共用；每次重繪 HTML 由 5MB 降至約 300KB（匯出檔仍用完整內嵌保持獨立離線）

### 5.2 效能優化
- [x] **參數變更防抖 (Debounce)**：下拉選單變更改走 250ms `QTimer` 防抖，快速連續切換只執行最後一次重算
- [x] **`worker.terminate()` 風險**：移除強制終止，改用遞增請求編號的協作式取消（過期結果自動忽略），並保留 worker 參照避免 GC
- [x] **16-bit / 浮點影像處理**：`create_plotly_html` 新增 `_auto_value_range`，8-bit 維持 0–255，16-bit/浮點依實際最大值動態設定 cmin/cmax 與軸範圍
- [x] **大圖散點降採樣策略**：新增「渲染品質」下拉（效能／平衡／品質，2 萬～8 萬點），控制 `max_scatter_points`

### 5.3 功能與體驗
- [x] **GUI 淺色簡約重構**：白底卡片、單一藍色主色、主/次按鈕層次、統計卡片著色左邊框、關閉暗色殘留樣式；3D 圖表預設同步淺色
- [x] **匯出報告加入原始檔名/時間戳記**，並支援匯出降採樣後的區塊均值矩陣 (CSV / NPY)
- [x] **色表明暗主題切換**：新增「圖表主題」下拉（淺色／深色），套用於檢視與匯出
- [x] **拖放 (Drag & Drop) 載入影像**：主視窗支援拖入影像檔直接載入分析
- [x] **統計面板加入直方圖 / 剖面線**：新增「灰階直方圖」與「中央剖面線」兩種視覺化模式輔助判讀分布
- [ ] **錯誤處理**：非影像檔或損毀檔案的更友善提示與復原（部分完成：拖放不支援副檔名已提示，仍可再強化損毀檔復原）

## 6. 完整 HTML 分析報表 + 分級
- [x] **卡片式多圖表 HTML 報表** (`report.py` / `ReportBuilder`)：等級摘要卡、空間熱力圖、均勻度分區圖、直方圖(含警戒線)、中央剖面線(含容差帶)、徑向亮度衰減、3D 曲面總覽；內嵌 plotly.js 一次、獨立離線可用
- [x] **均勻度警戒線分級** (`grading.py` / `UniformityGrader`)：以「偏離平均 ±X%」定義不均勻度，警戒線 3/5/10/20%，以 P99 偏差評級 (優/良/尚可/偏差/不合格)，並計算各警戒線通過率
- [x] GUI 新增「📊 匯出完整分析報表 (HTML)」按鈕

## 7. OOP 模組化重構
- [x] 由扁平 `analyzer.py` / `main_window.py` 拆分為 `grayscale_uniformity` 套件：
  `image_io` (ImageLoader)、`analysis` (UniformityAnalyzer/Pooler)、`grading` (UniformityGrader)、
  `charts` (ChartBuilder)、`report` (ReportBuilder)、`ui/{main_window,worker,widgets}`
- [x] 各模組保留模組層便利函式維持向後相容；單元測試擴充至 7 項並全數通過

## 8. 後續可再優化 (Nice-to-have)
- [ ] 錯誤處理：損毀影像檔的復原提示 (拖放副檔名已提示)
- [ ] 主圖表區與縮圖使用相同 colormap 一致化預覽
- [ ] 大圖載入亦移至背景執行緒（目前 `ImageLoader.load` 在主執行緒）
- [ ] 記憶使用者上次選用的參數（QSettings）
- [x] 報表警戒線門檻可由 GUI 自訂（`edit_thresholds` 欄位 + `parse_thresholds`，預設 3/5/10/20）
