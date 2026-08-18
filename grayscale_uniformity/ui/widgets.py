"""可重用的 GUI 元件與樣式常數。"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class MetricCard(QFrame):
    """統計指標卡：標題 + 大字數值，左側著色邊框。"""

    def __init__(self, title: str, init_val: str, accent_color: str, tint_color: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {tint_color};
                border: 1px solid #eceef1;
                border-left: 4px solid {accent_color};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 10)
        layout.setSpacing(3)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 600; letter-spacing: 0.3px;")
        layout.addWidget(lbl_t)

        self.value_label = QLabel(init_val)
        self.value_label.setObjectName("metric_value")
        self.value_label.setStyleSheet(f"color: {accent_color}; font-size: 24px; font-weight: 700;")
        layout.addWidget(self.value_label)

    def set_value(self, text: str):
        self.value_label.setText(text)


def field_label_qss() -> str:
    return "color: #6b7280; font-size: 12px; font-weight: 600; padding: 2px 0;"


#: 主視窗淺色簡約樣式表
APP_QSS = """
    QMainWindow { background-color: #f4f5f7; }
    QWidget { color: #1f2430; font-family: "Segoe UI", "Microsoft JhengHei", sans-serif; font-size: 13px; }
    QLabel { background: transparent; }
    QGroupBox {
        background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
        margin-top: 18px; padding: 16px 14px 12px 14px; font-weight: 600; font-size: 13px;
    }
    QGroupBox::title {
        subcontrol-origin: margin; subcontrol-position: top left;
        padding: 2px 8px; left: 12px; color: #4b5563; background: transparent;
    }
    QPushButton {
        background-color: #ffffff; color: #374151; border: 1px solid #d1d5db;
        border-radius: 8px; padding: 9px 14px; font-size: 13px; font-weight: 500;
    }
    QPushButton:hover { background-color: #f9fafb; border-color: #9ca3af; }
    QPushButton:pressed { background-color: #f3f4f6; }
    QPushButton:disabled { background-color: #f3f4f6; color: #b0b6bf; border-color: #e5e7eb; }
    QPushButton#primary {
        background-color: #2563eb; color: #ffffff; border: 1px solid #2563eb; font-weight: 600;
    }
    QPushButton#primary:hover { background-color: #1d4ed8; border-color: #1d4ed8; }
    QPushButton#primary:pressed { background-color: #1e40af; }
    QPushButton#primary:disabled { background-color: #bfdbfe; color: #eff6ff; border-color: #bfdbfe; }
    QComboBox {
        background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 8px;
        padding: 7px 10px; color: #1f2430; font-size: 13px;
    }
    QComboBox:hover { border-color: #9ca3af; }
    QComboBox:focus { border-color: #2563eb; }
    QLineEdit {
        background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 8px;
        padding: 7px 10px; color: #1f2430; font-size: 13px;
    }
    QLineEdit:hover { border-color: #9ca3af; }
    QLineEdit:focus { border-color: #2563eb; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView {
        background-color: #ffffff; color: #1f2430; selection-background-color: #2563eb;
        selection-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; outline: none; padding: 4px;
    }
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { border: none; background: transparent; width: 10px; margin: 2px; }
    QScrollBar::handle:vertical { background: #cbd0d8; min-height: 24px; border-radius: 5px; }
    QScrollBar::handle:vertical:hover { background: #aab0ba; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QProgressBar { background-color: #e5e7eb; border: none; border-radius: 3px; }
    QProgressBar::chunk { background-color: #2563eb; border-radius: 3px; }
"""
