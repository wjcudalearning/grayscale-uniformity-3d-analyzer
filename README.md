# 灰階均勻度 3D 視覺化分析工具

> Grayscale Uniformity 3D Analyzer — 一款以 PySide6 + Plotly 打造的桌面工具，用於量測與視覺化影像（光場 / 背光 / 面板 / 感測器）的灰階均勻度，並依警戒線自動分級、產生卡片式 HTML 分析報表。

淺色簡約介面，載入影像後即時計算均勻度指標並以互動式 3D 圖表呈現。支援超大影像、16-bit / 浮點格式與含中文路徑的檔案。

---

## ✨ 功能特色

- **多種視覺化模式**：3D 散點圖、3D 曲面圖、2D 熱力圖、灰階直方圖、中央剖面線，皆可即時切換、旋轉、縮放、懸停查值。
- **均勻度指標**：變異係數均勻度（CV）、極值對比均勻度（Range）、最小/最大比例，以及平均值、標準差、極值等統計。
- **警戒線分級**：以「偏離平均 ±X%」為不均勻度定義，內建 **3% / 5% / 10% / 20%** 警戒線（可於 GUI 自訂門檻），依第 99 百分位偏差自動評級（優 / 良 / 尚可 / 偏差 / 不合格），並計算各警戒線通過率。
- **完整 HTML 分析報表**：一鍵匯出卡片式報表，含等級摘要、空間熱力圖、均勻度分區圖、直方圖（附警戒線）、中央剖面線、徑向亮度衰減（暗角判讀）與 3D 曲面總覽；內嵌 plotly.js，單檔離線可看。
- **效能優化**：區塊降採樣（Pooling）、背景執行緒計算、參數防抖、散點密度品質分級、共用 plotly.js 快速重繪。
- **資料匯出**：CSV 統計報告、區塊均值矩陣（CSV / NumPy `.npy`）、單圖互動 HTML。
- **便利操作**：拖放載入影像、原圖縮圖預覽、內建測試漸層圖。

---

## 🚀 安裝與執行

需求：Python 3.9+（Windows / macOS / Linux）

```bash
# 1. 建立虛擬環境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 啟動應用程式
python main.py
```

執行單元測試：

```bash
python -m unittest test_app -v
```

### 免安裝執行檔 (Windows)

不想安裝 Python 的使用者，可至 [Releases](https://github.com/wjcudalearning/grayscale-uniformity-3d-analyzer/releases) 下載打包好的單一 `.exe` 直接執行。

自行打包：

```bash
pip install pyinstaller
pyinstaller GrayscaleUniformity3DAnalyzer.spec --noconfirm
# 產出 dist/GrayscaleUniformity3DAnalyzer.exe
```

---

## 🖱️ 使用方式

1. 點「📂 開啟影像檔案」或直接把影像**拖入視窗**（也可按「🎨 生成測試漸層圖」快速體驗）。
2. 於左側調整**區塊採樣大小**、**視覺化模式**、**配色**、**渲染品質**與**圖表主題**，右側圖表即時更新。
3. 查看左側均勻度統計卡片。
4. 按「📊 匯出完整分析報表 (HTML)」產生含警戒線分級的多圖表報表；或用「💾 匯出數據」輸出 CSV / 矩陣 / 單圖 HTML。

---

## 📊 均勻度與分級定義

| 指標 | 公式 |
|---|---|
| 變異係數均勻度 (CV) | `(1 − σ / μ) × 100%` |
| 極值對比均勻度 (Range) | `(1 − (Max − Min) / (Max + Min)) × 100%` |
| 最小/最大比例 | `Min / Max × 100%` |
| **不均勻度（分級用）** | `\|區塊值 − 平均\| / 平均 × 100%` |

分級以每個區塊的偏離平均百分比之 **第 99 百分位（P99）** 對照警戒線判定，避免少數熱點 / 壞點主導評級：

| P99 偏差 | 等級 |
|---|---|
| ≤ 3% | 優 (Excellent) |
| ≤ 5% | 良 (Good) |
| ≤ 10% | 尚可 (Acceptable) |
| ≤ 20% | 偏差 (Marginal) |
| > 20% | 不合格 (Fail) |

---

## 🧩 專案結構

```
grayscale_uniformity/         # 核心套件
├── image_io.py               # ImageLoader：影像載入與灰階轉換
├── analysis.py               # UniformityAnalyzer / Pooler：降採樣與均勻度指標
├── grading.py                # UniformityGrader：偏離平均警戒線分級
├── charts.py                 # ChartBuilder：單一 Plotly 圖表
├── report.py                 # ReportBuilder：卡片式多圖表 HTML 報表
└── ui/
    ├── main_window.py        # 主視窗
    ├── worker.py             # 背景分析執行緒
    └── widgets.py            # 可重用元件與樣式
main.py                       # 應用程式進入點
test_app.py                   # 單元測試
```

每個核心模組同時提供類別（OOP）與模組層便利函式，方便以程式方式呼叫：

```python
from grayscale_uniformity import ImageLoader, UniformityAnalyzer, UniformityGrader, ReportBuilder

gray = ImageLoader.load("panel.png")
result = UniformityAnalyzer(block_size=2).analyze(gray)
grade = UniformityGrader().grade(result.block_means, result.mean)
print(grade.grade_label, grade.pass_rates)

html = ReportBuilder(colorscale="Viridis").build(result, image_name="panel.png")
open("report.html", "w", encoding="utf-8").write(html)
```

---

## 🛠️ 技術棧

PySide6 · Plotly · NumPy · OpenCV · Pillow

## 📄 授權

MIT License，詳見 [LICENSE](LICENSE)。
