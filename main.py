"""LabExp-Assistant — 实验室助手 GUI 主入口。

基于 PySide6，UI 从 Qt Designer .ui 文件加载。
"""
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QMainWindow,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.convertor import BtpConvertor
from src.pdf_editor import PdfPageEditor

# ── 常量 ──────────────────────────────────────────────
LOCALES_DIR: Path = Path(__file__).resolve().parent / "locales"
DPI_MIN: int = 100
DPI_MAX: int = 400
DPI_DEFAULT: int = 250


# ── 翻译支持（暂未启用） ─────────────────────────────
_translations: dict = {}
_current_lang: str = "en"


def load_translations() -> None:
    """加载所有语言包。"""
    for lang in ("en", "zh_CN", "ja"):
        path = LOCALES_DIR / f"{lang}.json"
        if path.exists():
            _translations.setdefault(lang, {}).update(
                json.loads(path.read_text("utf-8"))
            )


def tr(key: str) -> str:
    """国际化翻译（占位）。"""
    return _translations.get(_current_lang, {}).get(key, key)


# ── 主窗口 ────────────────────────────────────────────
class LabExpAssistant(QMainWindow):
    """实验室助手主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self._load_ui()
        self._init_convertor_controls()
        self._init_btp_extra_controls()   # DPI + 进度条
        self._init_pdf_editor_controls()  # PDF 页面编辑器
        self._connect_signals()

    # ── UI 加载 ────────────────────────────────────────

    def _load_ui(self) -> None:
        """加载 .ui 文件并设置主窗口。"""
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "ui" / "main_window.ui"
        ui_file = QFile(str(ui_path))
        ui_file.open(QIODevice.ReadOnly)
        ui_widget = loader.load(ui_file)
        ui_file.close()

        if ui_widget.centralWidget():
            self.setCentralWidget(ui_widget.centralWidget())
        else:
            self.setCentralWidget(ui_widget)

        size = ui_widget.size()
        ui_widget.deleteLater()
        self.resize(size)
        self.setWindowTitle("Lab Exp Assistant")

        # 默认选中 Convertor 标签页
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        if tab_widget:
            tab_widget.setCurrentIndex(3)

    # ── Convertor 页控件 ────────────────────────────────

    def _init_convertor_controls(self) -> None:
        """初始化 Convertor 标签页的已有控件引用。"""
        self.edit_btp_io_source = self.findChild(QLineEdit, "edit_btp_io_source")
        self.btn_btp_io_source = self.findChild(QPushButton, "btn_btp_io_source")

        self.edit_btp_io_output_folder = self.findChild(QLineEdit, "edit_btp_io_output_folder")
        self.btn_btp_io_output_folder = self.findChild(QPushButton, "btn_btp_io_output_folder")

        self.combo_btp_io_output_format = self.findChild(QComboBox, "combo_btp_io_output_format")

        self.cb_btp_custom_name = self.findChild(QCheckBox, "cb_btp_custom_name")
        self.edit_btp_custom_name = self.findChild(QLineEdit, "edit_btp_custom_name")
        self.lbl_btp_custom_ext = self.findChild(QLabel, "lbl_btp_custom_ext")

        self.btn_btp_convert = self.findChild(QPushButton, "btn_btp_convert")
        self.tb_btp_log = self.findChild(QTextBrowser, "tb_btp_log")

        # 自定义名输入框默认禁用
        self.edit_btp_custom_name.setEnabled(False)
        self.lbl_btp_custom_ext.setEnabled(False)

    def _init_btp_extra_controls(self) -> None:
        """在已有布局中程序化添加 DPI 调节和进度条。

        将 DPI 行插入到 box_btp_io 布局中（自定义名与转换按钮之间），
        将进度条插入到 box_btp_log 布局中（日志框上方）。
        """
        # ── DPI SpinBox ─────────────────────────────
        io_box = self.findChild(QGroupBox, "box_btp_io")
        if io_box is None:
            return
        io_layout = io_box.layout()  # verticalLayout_2
        if io_layout is None:
            return

        dpi_layout = QHBoxLayout()
        dpi_label = QLabel("DPI:")
        dpi_label.setMinimumWidth(60)
        dpi_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.spin_btp_dpi = QSpinBox()
        self.spin_btp_dpi.setRange(DPI_MIN, DPI_MAX)
        self.spin_btp_dpi.setValue(DPI_DEFAULT)
        self.spin_btp_dpi.setSuffix(" DPI")
        dpi_layout.addWidget(dpi_label)
        dpi_layout.addWidget(self.spin_btp_dpi, 1)
        dpi_layout.addStretch(6)

        # 插入到 convert 按钮之前（最后一项前）
        convert_idx = io_layout.count() - 1
        io_layout.insertLayout(convert_idx, dpi_layout)

        # ── Progress Bar ────────────────────────────
        log_box = self.findChild(QGroupBox, "box_btp_log")
        if log_box is None:
            return
        log_layout = log_box.layout()  # verticalLayout_3
        if log_layout is None:
            return

        self.progress_btp = QProgressBar()
        self.progress_btp.setVisible(False)
        log_layout.insertWidget(0, self.progress_btp)

    # ── PDF 页面编辑器控件 ─────────────────────────────

    def _init_pdf_editor_controls(self) -> None:
        """在 Convertor 标签页底部添加 PDF 页面编辑器区域。"""
        tab_convertor = self.findChild(QWidget, "tab_convertor")
        if tab_convertor is None:
            return
        tab_layout = tab_convertor.layout()  # verticalLayout_5
        if tab_layout is None:
            return

        # ── 主 GroupBox ─────────────────────────────
        self.group_pdf_edit = QGroupBox("PDF 页面编辑器")
        pdf_layout = QVBoxLayout(self.group_pdf_edit)

        # 第 1 行：源文件
        row1 = QHBoxLayout()
        self.btn_pdf_edit_source = QPushButton("选择 PDF...")
        self.lbl_pdf_edit_info = QLabel("未选择文件")
        self.btn_pdf_edit_info = QPushButton("获取信息")
        self.btn_pdf_edit_info.setEnabled(False)
        row1.addWidget(self.btn_pdf_edit_source)
        row1.addWidget(self.lbl_pdf_edit_info, 1)
        row1.addWidget(self.btn_pdf_edit_info)
        pdf_layout.addLayout(row1)

        # 第 2 行：操作模式 + 页面范围
        row2 = QHBoxLayout()
        self.radio_pdf_delete = QRadioButton("删除页面")
        self.radio_pdf_delete.setChecked(True)
        self.radio_pdf_extract = QRadioButton("提取页面")
        self.lbl_pdf_edit_range = QLabel("页面范围:")
        self.edit_pdf_edit_range = QLineEdit()
        self.edit_pdf_edit_range.setPlaceholderText("例: 1,3,5-8,10-")
        row2.addWidget(self.radio_pdf_delete)
        row2.addWidget(self.radio_pdf_extract)
        row2.addWidget(self.lbl_pdf_edit_range)
        row2.addWidget(self.edit_pdf_edit_range, 1)
        pdf_layout.addLayout(row2)

        # 第 3 行：输出路径
        row3 = QHBoxLayout()
        self.btn_pdf_edit_output = QPushButton("输出路径...")
        self.edit_pdf_edit_output = QLineEdit()
        self.edit_pdf_edit_output.setPlaceholderText("输出文件路径（自动填入）")
        row3.addWidget(self.btn_pdf_edit_output)
        row3.addWidget(self.edit_pdf_edit_output, 1)
        pdf_layout.addLayout(row3)

        # 第 4 行：执行按钮
        row4 = QHBoxLayout()
        self.btn_pdf_edit_execute = QPushButton("执行")
        self.btn_pdf_edit_execute.setEnabled(False)
        row4.addStretch()
        row4.addWidget(self.btn_pdf_edit_execute)
        pdf_layout.addLayout(row4)

        # 日志
        self.tb_pdf_edit_log = QTextBrowser()
        self.tb_pdf_edit_log.setMaximumHeight(120)
        pdf_layout.addWidget(self.tb_pdf_edit_log)

        # 插入到标签页底部
        tab_layout.addWidget(self.group_pdf_edit)

        # 保存内部状态
        self._pdf_source_path: str = ""

    # ── 信号槽连接 ─────────────────────────────────────

    def _connect_signals(self) -> None:
        """连接所有信号槽。"""
        # Convertor
        self.btn_btp_io_source.clicked.connect(self._browse_source)
        self.btn_btp_io_output_folder.clicked.connect(self._browse_output_folder)
        self.cb_btp_custom_name.toggled.connect(self._on_custom_name_toggled)
        self.btn_btp_convert.clicked.connect(self._on_convert)

        # PDF 编辑器
        self.btn_pdf_edit_source.clicked.connect(self._pdf_browse_source)
        self.btn_pdf_edit_info.clicked.connect(self._pdf_get_info)
        self.btn_pdf_edit_output.clicked.connect(self._pdf_browse_output)
        self.btn_pdf_edit_execute.clicked.connect(self._pdf_execute)
        self.edit_pdf_edit_range.textChanged.connect(self._pdf_on_input_changed)

    # ── Convertor 槽函数 ──────────────────────────────

    def _browse_source(self) -> None:
        """浏览选择源 PDF 文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF Files (*.pdf)"
        )
        if path:
            self.edit_btp_io_source.setText(path)

    def _browse_output_folder(self) -> None:
        """浏览选择输出文件夹。"""
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.edit_btp_io_output_folder.setText(path)

    def _on_custom_name_toggled(self, checked: bool) -> None:
        """自定义文件名复选框切换。"""
        self.edit_btp_custom_name.setEnabled(checked)
        self.lbl_btp_custom_ext.setEnabled(checked)

    def _on_convert(self) -> None:
        """执行 Beamer PDF → PPTX 转换。"""
        source = self.edit_btp_io_source.text().strip()
        if not source:
            QMessageBox.warning(self, "Warning", "请选择源文件")
            return

        output_folder = self.edit_btp_io_output_folder.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Warning", "请选择输出文件夹")
            return

        fmt = self.combo_btp_io_output_format.currentText()
        use_custom = self.cb_btp_custom_name.isChecked()
        custom_name = self.edit_btp_custom_name.text().strip() if use_custom else ""

        dpi = self.spin_btp_dpi.value()

        self.tb_btp_log.clear()
        self.tb_btp_log.append(f"开始转换: {source}")
        self.tb_btp_log.append(f"DPI: {dpi}, 格式: {fmt}")

        # 准备进度条
        self.progress_btp.setVisible(True)
        self.progress_btp.setValue(0)
        self.btn_btp_convert.setEnabled(False)

        def on_progress(current: int, total: int) -> None:
            """更新进度条，并刷新 UI 防止冻结。"""
            self.progress_btp.setMaximum(total)
            self.progress_btp.setValue(current)
            QApplication.processEvents()

        converter = BtpConvertor(
            source=source,
            output_folder=output_folder,
            output_format=fmt,
            custom_name=custom_name,
            dpi=dpi,
            progress_callback=on_progress,
        )
        result = converter.run()

        self.btn_btp_convert.setEnabled(True)
        self.progress_btp.setVisible(False)

        if result["success"]:
            self.tb_btp_log.append("转换完成！")
            self.tb_btp_log.append(f"输出文件: {result['output_path']}")
        else:
            self.tb_btp_log.append(f"转换失败: {result['error']}")
            QMessageBox.critical(self, "错误", result["error"])

    # ── PDF 编辑器槽函数 ──────────────────────────────

    def _pdf_browse_source(self) -> None:
        """选择要编辑的 PDF 源文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF Files (*.pdf)"
        )
        if path:
            self._pdf_source_path = path
            self.lbl_pdf_edit_info.setText(f"已选择: {Path(path).name}")
            self.btn_pdf_edit_info.setEnabled(True)
            self.btn_pdf_edit_execute.setEnabled(True)
            # 自动猜输出路径
            guessed = Path(path).parent / f"{Path(path).stem}_edited.pdf"
            self.edit_pdf_edit_output.setText(str(guessed))
            self._pdf_get_info()

    def _pdf_get_info(self) -> None:
        """获取并显示 PDF 信息。"""
        if not self._pdf_source_path:
            return
        try:
            info = PdfPageEditor.get_info(self._pdf_source_path)
            size_str = ""
            if info.width_points and info.height_points:
                size_str = f" ({info.width_points:.0f}x{info.height_points:.0f} pt)"
            self.lbl_pdf_edit_info.setText(
                f"{Path(self._pdf_source_path).name} — {info.total_pages} 页{size_str}"
            )
            self.tb_pdf_edit_log.append(
                f"PDF 信息: {info.total_pages} 页{size_str}"
            )
        except Exception as exc:
            self.tb_pdf_edit_log.append(f"获取信息失败: {exc}")

    def _pdf_browse_output(self) -> None:
        """浏览选择 PDF 输出路径。"""
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self.edit_pdf_edit_output.setText(path)

    def _pdf_on_input_changed(self) -> None:
        """页面范围输入变化时启用/禁用执行按钮。"""
        has_range = bool(self.edit_pdf_edit_range.text().strip())
        self.btn_pdf_edit_execute.setEnabled(
            bool(self._pdf_source_path) and has_range
        )

    def _pdf_execute(self) -> None:
        """执行 PDF 页面删除或提取。"""
        if not self._pdf_source_path:
            QMessageBox.warning(self, "Warning", "请先选择 PDF 文件")
            return

        range_text = self.edit_pdf_edit_range.text().strip()
        if not range_text:
            QMessageBox.warning(self, "Warning", "请输入页面范围")
            return

        output_path = self.edit_pdf_edit_output.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Warning", "请指定输出路径")
            return

        # 获取总页数用于校验
        try:
            info = PdfPageEditor.get_info(self._pdf_source_path)
            total_pages = info.total_pages
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"无法读取 PDF 信息: {exc}")
            return

        # 解析页面范围
        try:
            pages = PdfPageEditor.parse_page_spec(range_text, total_pages)
        except ValueError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            return

        self.tb_pdf_edit_log.clear()
        self.tb_pdf_edit_log.append(
            f"总页数: {total_pages}, 目标页面: {len(pages)} 页"
        )

        is_delete = self.radio_pdf_delete.isChecked()
        if is_delete:
            self.tb_pdf_edit_log.append(f"操作: 删除页面 {range_text}")
            result = PdfPageEditor.delete_pages(
                source=self._pdf_source_path,
                pages_to_delete=pages,
                output_path=output_path,
            )
        else:
            self.tb_pdf_edit_log.append(f"操作: 提取页面 {range_text}")
            result = PdfPageEditor.extract_pages(
                source=self._pdf_source_path,
                pages_to_extract=pages,
                output_path=output_path,
            )

        if result.success:
            self.tb_pdf_edit_log.append(
                f"完成! 输出: {result.output_path} ({result.page_count} 页)"
            )
        else:
            self.tb_pdf_edit_log.append(f"失败: {result.error}")
            QMessageBox.critical(self, "错误", result.error)


# ── 入口 ──────────────────────────────────────────────
def main() -> None:
    """应用入口。"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LabExpAssistant()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
