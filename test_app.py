import os
import unittest
import numpy as np
from PIL import Image

# 測試前先解除限制
Image.MAX_IMAGE_PIXELS = None

from grayscale_uniformity import (
    load_grayscale_image,
    compute_block_means,
    analyze_uniformity,
    create_plotly_html,
    create_report_html,
    grade_uniformity,
    parse_thresholds,
    DEFAULT_THRESHOLDS,
)


class TestUniformityAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_img_path = "d:/3D scatter/test_sample.png"
        arr = np.linspace(50, 200, 200 * 200, dtype=np.uint8).reshape((200, 200))
        Image.fromarray(arr).save(self.test_img_path)

    def tearDown(self):
        if os.path.exists(self.test_img_path):
            try:
                os.remove(self.test_img_path)
            except Exception:
                pass

    def test_load_grayscale_image(self):
        """測試圖片載入與灰階轉換"""
        gray = load_grayscale_image(self.test_img_path)
        self.assertEqual(gray.shape, (200, 200))
        self.assertTrue(np.issubdtype(gray.dtype, np.floating))

    def test_load_and_pooling_2x2(self):
        """測試 2x2 (每 4 個像素 1 個 mean) 區塊平均"""
        data = np.array([
            [10, 20, 30, 40],
            [10, 20, 30, 40],
            [50, 50, 10, 10],
            [50, 50, 10, 10],
        ], dtype=np.float32)
        pooled = compute_block_means(data, block_size=2)
        self.assertEqual(pooled.shape, (2, 2))
        self.assertAlmostEqual(pooled[0, 0], 15.0)
        self.assertAlmostEqual(pooled[0, 1], 35.0)
        self.assertAlmostEqual(pooled[1, 0], 50.0)
        self.assertAlmostEqual(pooled[1, 1], 10.0)

    def test_perfect_uniformity(self):
        """測試完全均勻影像之均勻度應為 100%"""
        constant_img = np.full((100, 100), 128.0, dtype=np.float32)
        result = analyze_uniformity(constant_img, block_size=2)
        self.assertAlmostEqual(result.mean, 128.0)
        self.assertAlmostEqual(result.std, 0.0)
        self.assertAlmostEqual(result.cv_uniformity, 100.0)
        self.assertAlmostEqual(result.range_uniformity, 100.0)
        self.assertAlmostEqual(result.min_max_ratio, 100.0)

    def test_large_image_handling(self):
        """測試超大型陣列 (PIL 限制全開) 運算效能"""
        large_arr = np.random.randint(0, 255, size=(2000, 2000)).astype(np.float32)
        result = analyze_uniformity(large_arr, block_size=2)
        self.assertEqual(result.sampled_shape, (1000, 1000))
        self.assertTrue(0 <= result.cv_uniformity <= 100)

    def test_plotly_html_generation(self):
        """測試 Plotly HTML 各種圖表生成"""
        grid = np.random.uniform(50, 200, size=(50, 50)).astype(np.float32)
        for ct in ["scatter3d", "surface", "heatmap", "histogram", "profile"]:
            html = create_plotly_html(grid, chart_type=ct)
            self.assertIn("plotly", html.lower())

    def test_grade_uniformity(self):
        """測試偏離平均分級：完全均勻 => 優，通過率 100%"""
        uniform = np.full((60, 60), 100.0, dtype=np.float32)
        g = grade_uniformity(uniform, 100.0)
        self.assertEqual(g.grade_threshold, 3.0)
        self.assertAlmostEqual(g.max_dev_pct, 0.0)
        for t in g.thresholds:
            self.assertAlmostEqual(g.pass_rates[t], 100.0)

        # 已知偏差：一半 +10%、一半 -10% => 最大偏差 10%，±3/5% 通過率 0%
        arr = np.full((10, 10), 100.0, dtype=np.float32)
        arr[:5, :] = 110.0
        arr[5:, :] = 90.0
        g2 = grade_uniformity(arr, float(arr.mean()))
        self.assertAlmostEqual(g2.max_dev_pct, 10.0, places=4)
        self.assertAlmostEqual(g2.pass_rates[3.0], 0.0)
        self.assertAlmostEqual(g2.pass_rates[10.0], 100.0)

    def test_parse_thresholds(self):
        """測試警戒線門檻字串解析：排序去重、過濾非法值、回退預設"""
        self.assertEqual(parse_thresholds("3, 5, 10, 20"), [3.0, 5.0, 10.0, 20.0])
        self.assertEqual(parse_thresholds("20 5、5  3"), [3.0, 5.0, 20.0])  # 空白/頓號分隔+去重
        self.assertEqual(parse_thresholds("2,4,8"), [2.0, 4.0, 8.0])        # 自訂值
        self.assertEqual(parse_thresholds(""), DEFAULT_THRESHOLDS)          # 空 -> 預設
        self.assertEqual(parse_thresholds("abc, -1, 0"), DEFAULT_THRESHOLDS)  # 全非法 -> 預設

    def test_report_with_custom_thresholds(self):
        """測試自訂門檻可反映於報表分級"""
        grid = np.random.uniform(90, 110, size=(40, 40)).astype(np.float32)
        result = analyze_uniformity(grid, block_size=1)
        html = create_report_html(result, thresholds=[2, 8], image_name="c.png", timestamp="t")
        self.assertIn("±2%", html)
        self.assertIn("±8%", html)

    def test_report_html_generation(self):
        """測試完整 HTML 報表生成含所有區段"""
        grid = np.random.uniform(80, 200, size=(80, 100)).astype(np.float32)
        result = analyze_uniformity(grid, block_size=1)
        html = create_report_html(result, image_name="unittest.png", timestamp="2026-01-01 00:00:00")
        for token in ["空間熱力圖", "均勻度分區圖", "灰階直方圖", "中央剖面線",
                      "徑向亮度衰減", "3D 曲面", "警戒線", "plotly"]:
            self.assertIn(token.lower(), html.lower())


if __name__ == "__main__":
    unittest.main()
