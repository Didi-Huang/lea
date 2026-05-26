"""LabExp-Assistant — 实验室助手 GUI 主入口。

基于 PySide6，UI 从 Qt Designer .ui 文件加载。
支持中/英/日三语实时切换。
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.i18n import *  # noqa: F401, F403
from src.main_window import LabExpAssistant  # noqa: F401

PROJECT_ROOT: Path = Path(__file__).resolve().parent


def main() -> None:
    """应用入口。"""
    load_translations()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 加载 QSS 样式表
    qss_path = PROJECT_ROOT / "ui" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text("utf-8"))

    window = LabExpAssistant()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
