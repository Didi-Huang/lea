"""Labexp-Assistant — 基于 UI 文件 + 纯 Convertor 页逻辑"""
import sys
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
)
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader

# 临时翻译支持（可删除）
# ======================
LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_translations: dict = {}
_current_lang = "en"

def load_translations():
    for lang in ("en", "zh_CN", "ja"):
        path = LOCALES_DIR / f"{lang}.json"
        if path.exists():
            _translations.setdefault(lang, {}).update(json.loads(path.read_text("utf-8")))

def tr(key: str) -> str:
    return _translations.get(_current_lang, {}).get(key, key)
# ======================

from src.convertor import BtpConvertor  # 逻辑模块

class LabExpAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        # 1) 加载 UI
        loader = QUiLoader()
        ui_file = QFile(str(Path(__file__).resolve().parent / "ui" / "main_window.ui"))
        ui_file.open(QIODevice.ReadOnly)
        self.ui = loader.load(ui_file)
        ui_file.close()

        # 将加载的 QMainWindow 的中央部件设为自己的中央部件
        if self.ui.centralWidget():
            self.setCentralWidget(self.ui.centralWidget())
        else:
            self.setCentralWidget(self.ui)

        # 复制 UI 尺寸（先存尺寸再删除临时窗口）
        size = self.ui.size()
        self.ui.deleteLater()   # 释放临时窗口
        self.resize(size)

        # 2) 初始化 Convertor 页控件引用（方便后续访问）
        self._init_convertor_controls()

        # 3) 连接信号槽
        self._connect_convertor_signals()

    # ------------------------------------------------
    #  Convertor 页控件引用 (属性名与 CSV 中的 objectName 相同)
    # ------------------------------------------------
    def _init_convertor_controls(self):
        # 直接通过 findChild 获取控件，缓存为属性
        self.label_btp_io_source = self.findChild(QWidget, "label_btp_io_source")
        self.edit_btp_io_source = self.findChild(QWidget, "edit_btp_io_source")
        self.btn_btp_io_source = self.findChild(QWidget, "btn_btp_io_source")

        self.label_btp_io_output_folder = self.findChild(QWidget, "label_btp_io_output_folder")
        self.edit_btp_io_output_folder = self.findChild(QWidget, "edit_btp_io_output_folder")
        self.btn_btp_io_output_folder = self.findChild(QWidget, "btn_btp_io_output_folder")

        self.label_btp_io_output_format = self.findChild(QWidget, "label_btp_io_output_format")
        self.combo_btp_io_output_format = self.findChild(QWidget, "combo_btp_io_output_format")

        self.label_btp_custom_name = self.findChild(QWidget, "label_btp_custom_name")
        self.cb_btp_custom_name = self.findChild(QWidget, "cb_btp_custom_name")
        self.edit_btp_custom_name = self.findChild(QWidget, "edit_btp_custom_name")
        self.lbl_btp_custom_ext = self.findChild(QWidget, "lbl_btp_custom_ext")

        self.btn_btp_convert = self.findChild(QWidget, "btn_btp_convert")
        self.tb_btp_log = self.findChild(QWidget, "tb_btp_log")

        # 初始化状态：自定义文件名输入框默认禁用
        self.edit_btp_custom_name.setEnabled(False)
        self.lbl_btp_custom_ext.setEnabled(False)

    # ------------------------------------------------
    #  Convertor 页信号槽连接
    # ------------------------------------------------
    def _connect_convertor_signals(self):
        # 1) 源文件浏览
        self.btn_btp_io_source.clicked.connect(self._browse_source)

        # 2) 输出文件夹浏览
        self.btn_btp_io_output_folder.clicked.connect(self._browse_output_folder)

        # 3) 自定义文件名复选框（UI 中已有 connection，但这里再确保一次）
        self.cb_btp_custom_name.toggled.connect(self._on_custom_name_toggled)

        # 4) 转换按钮
        self.btn_btp_convert.clicked.connect(self._on_convert)

    # ------------------------------------------------
    #  Convertor 页槽函数
    # ------------------------------------------------
    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF Files (*.pdf)"
        )
        if path:
            self.edit_btp_io_source.setText(path)

    def _browse_output_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.edit_btp_io_output_folder.setText(path)

    def _on_custom_name_toggled(self, checked):
        self.edit_btp_custom_name.setEnabled(checked)
        self.lbl_btp_custom_ext.setEnabled(checked)

    def _on_convert(self):
        # 收集参数
        source = self.edit_btp_io_source.text().strip()
        if not source:
            QMessageBox.warning(self, "Warning", "请选择源文件")
            return

        output_folder = self.edit_btp_io_output_folder.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "Warning", "请选择输出文件夹")
            return

        fmt = self.combo_btp_io_output_format.currentText()  # "PDF to PPTX" / "PDF to PPT"
        use_custom = self.cb_btp_custom_name.isChecked()
        custom_name = self.edit_btp_custom_name.text().strip() if use_custom else ""

        # 调用转换逻辑（目前为模拟）
        self.tb_btp_log.clear()
        self.tb_btp_log.append("开始转换...")

        converter = BtpConvertor(
            source, output_folder, fmt, custom_name
        )
        result = converter.run()   # 返回 True/False + 消息

        if result["success"]:
            self.tb_btp_log.append("转换完成！")
            self.tb_btp_log.append(f"输出文件: {result['output_path']}")
        else:
            self.tb_btp_log.append(f"转换失败: {result['error']}")
            QMessageBox.critical(self, "错误", result['error'])


def main():
    # load_translations()  # 暂时不需要，若需要取消注释并在 locales 下放对应 json
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LabExpAssistant()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()