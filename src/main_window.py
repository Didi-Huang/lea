"""LabExpAssistant main window class."""

import json
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.convertor import BtpConvertor
from src.i18n import (
    DPI_DEFAULT,
    DPI_MAX,
    DPI_MIN,
    TAB_ORDER,
    _current_lang,
    load_translations,
    set_language,
    tr,
)
from src.pdf_editor import PdfPageEditor
from src.project_builder import ProjectBuilder


class LabExpAssistant(QMainWindow):
    """实验室助手主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self._load_ui()
        self._init_convertor_controls()
        self._init_pdf_editor_controls()  # PDF 页面编辑器（来自 UI 文件）
        self._init_data_controls()  # Data 标签页控件
        self._init_settings_controls()  # Settings 标签页控件
        self._init_cache_cleaner_controls()  # Cache Cleaner 标签页控件
        self._init_project_controls()  # Project 标签页控件
        self._init_snippets_controls()  # Snippets 标签页控件
        self._connect_signals()
        self._load_settings()  # 从 user_data/config.json 加载设置
        self._apply_language(_current_lang)  # 应用初始语言
        self._connect_language_signals()  # 连接语言切换信号

    # ── Project 页控件 ────────────────────────────────

    def _init_project_controls(self) -> None:
        """初始化 Project 标签页的控件引用。"""
        self.edit_experiment_name = self.findChild(QLineEdit, "edit_experiment_name")
        self.edit_parent_folder = self.findChild(QLineEdit, "edit_parent_folder")
        self.parent_folder_path_btn = self.findChild(QPushButton, "parent_folder_path_btn")
        self.combo_project_template = self.findChild(QComboBox, "combo_project_template")
        self.check_generate_gitignore = self.findChild(QCheckBox, "check_generate_gitignore")
        self.check_init_repo = self.findChild(QCheckBox, "check_init_repo")
        self.btn_project_create = self.findChild(QPushButton, "btn_project_create")
        self.text_log = self.findChild(QTextBrowser, "text_log")

    # ── Snippets 页控件 ──────────────────────────────

    def _init_snippets_controls(self) -> None:
        """初始化 Snippets 标签页控件并加载代码片段。"""
        self.combo_snippets_category = self.findChild(QComboBox, "combo_snippets_category")
        self.list_snippets = self.findChild(QListWidget, "list_snippets")
        self.edit_snippets_preview = self.findChild(QPlainTextEdit, "edit_snippets_preview")
        self.btn_snippets_copy = self.findChild(QPushButton, "btn_snippets_copy")
        self.btn_snippets_insert = self.findChild(QPushButton, "btn_snippets_insert")
        self._snippets_data: list = []

        # 分割器默认比例（列表 30% / 预览 70%）
        splitter = self.findChild(QSplitter, "splitter_snippets")
        if splitter:
            splitter.setSizes([200, 500])

        self._load_snippets_from_disk()

    def _load_snippets_from_disk(self) -> None:
        """从 user_data/snippets/ 加载 JSON 片段文件。"""
        snippets_dir = PROJECT_ROOT / "user_data" / "snippets"
        self._snippets_data = []
        if not snippets_dir.exists():
            return
        for f in sorted(snippets_dir.glob("*.json")):
            try:
                self._snippets_data.append(json.loads(f.read_text("utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        self._refresh_snippets_list()

    def _refresh_snippets_list(self) -> None:
        """根据分类过滤刷新列表。"""
        if not self.list_snippets:
            return
        self.list_snippets.clear()
        category = (
            self.combo_snippets_category.currentText() if self.combo_snippets_category else "All"
        )
        for item in self._snippets_data:
            if category == "All" or item.get("category", "") == category:
                self.list_snippets.addItem(item.get("title", "Untitled"))

    def _on_snippet_selected(self) -> None:
        """列表选中项变化时更新预览。"""
        if not self.list_snippets or not self.edit_snippets_preview:
            return
        row = self.list_snippets.currentRow()
        if 0 <= row < len(self._displayed_indices()):
            idx = self._displayed_indices()[row]
            self.edit_snippets_preview.setPlainText(self._snippets_data[idx].get("code", ""))

    def _displayed_indices(self) -> list:
        """返回当前过滤条件下显示的片段在 _snippets_data 中的索引。"""
        category = (
            self.combo_snippets_category.currentText() if self.combo_snippets_category else "All"
        )
        return [
            i
            for i, item in enumerate(self._snippets_data)
            if category == "All" or item.get("category", "") == category
        ]

    def _snippets_copy(self) -> None:
        """复制当前代码到剪贴板。"""
        code = self.edit_snippets_preview.toPlainText() if self.edit_snippets_preview else ""
        if code:
            QApplication.clipboard().setText(code)

    def _snippets_insert(self) -> None:
        """复制代码到剪贴板（同 copy，用于快速复制到项目）。"""
        self._snippets_copy()

    # ── UI 加载 ────────────────────────────────────────
    # ── UI 加载 ────────────────────────────────────────

    def _load_ui(self) -> None:
        """加载 .ui 文件并设置主窗口。"""
        loader = QUiLoader()
        ui_path = PROJECT_ROOT / "ui" / "main_window.ui"
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
        # 设置合理的最小尺寸和默认尺寸
        self.setMinimumSize(680, 500)
        self.resize(max(size.width(), 750), max(size.height(), 580))
        self.setWindowTitle(tr("app.title"))

        # 标签页按钮平分水平空间（动态计算 + resize 事件）
        self._update_tab_widths()

    def resizeEvent(self, event) -> None:
        """窗口大小变化时重新计算标签页宽度。"""
        super().resizeEvent(event)
        self._update_tab_widths()

    def _update_tab_widths(self) -> None:
        """让 N 个标签页按钮均分 QTabWidget 水平宽度。"""
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        if not tab_widget or tab_widget.count() == 0:
            return
        n = tab_widget.count()
        tab_bar = tab_widget.tabBar()
        available = tab_widget.viewportSizeHint().width()
        if available <= 0:
            available = tab_widget.width() - 4
        per_tab = max(80, (available - (n + 1) * 2) // n)
        tab_bar.setStyleSheet(f"QTabBar::tab {{ min-width: {per_tab}px; max-width: {per_tab + 4}px; }}")

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

        # 存储 UI 文件中的原始控件，用于翻译
        self._widget_box_convert_beamer = self.findChild(QGroupBox, "box_convert_beamer_to_ppt")
        self._widget_btp_io_box = self.findChild(QGroupBox, "box_btp_io")
        self._widget_btp_log_box = self.findChild(QGroupBox, "box_btp_log")
        self._widget_label_btp_source = self.findChild(QLabel, "label_btp_io_source")
        self._widget_label_btp_output = self.findChild(QLabel, "label_btp_io_output_folder")
        self._widget_label_btp_format = self.findChild(QLabel, "label_btp_io_output_format")
        self._widget_label_btp_custom = self.findChild(QLabel, "label_btp_custom_name")

        # 工具提示
        self.btn_btp_io_source.setToolTip(tr("convertor.tooltip_source"))
        self.btn_btp_io_output_folder.setToolTip(tr("convertor.tooltip_output"))
        self.btn_btp_convert.setToolTip(tr("convertor.tooltip_convert"))

        # DPI 和进度条（UI 文件定义）
        self.spin_btp_dpi = self.findChild(QSpinBox, "spin_btp_dpi")
        self.progress_btp = self.findChild(QProgressBar, "progress_btp")
        self._lbl_btp_dpi = self.findChild(QLabel, "label_btp_dpi")

    def _init_btp_extra_controls(self) -> None:
        """（已废弃：DPI 和进度条现在由 UI 文件定义。）"""
        pass

    # ── PDF 页面编辑器控件 ─────────────────────────────

    def _init_pdf_editor_controls(self) -> None:
        """初始化 PDF 页面编辑器控件引用（由 UI 文件定义）。"""
        self.group_pdf_edit = self.findChild(QGroupBox, "group_pdf_edit")
        self.btn_pdf_edit_source = self.findChild(QPushButton, "btn_pdf_edit_source")
        self.lbl_pdf_edit_info = self.findChild(QLabel, "lbl_pdf_edit_info")
        self.btn_pdf_edit_info = self.findChild(QPushButton, "btn_pdf_edit_info")
        self.radio_pdf_delete = self.findChild(QRadioButton, "radio_pdf_delete")
        self.radio_pdf_extract = self.findChild(QRadioButton, "radio_pdf_extract")
        self.lbl_pdf_edit_range = self.findChild(QLabel, "lbl_pdf_edit_range")
        self.edit_pdf_edit_range = self.findChild(QLineEdit, "edit_pdf_edit_range")
        self.btn_pdf_edit_output = self.findChild(QPushButton, "btn_pdf_edit_output")
        self.edit_pdf_edit_output = self.findChild(QLineEdit, "edit_pdf_edit_output")
        self.btn_pdf_edit_execute = self.findChild(QPushButton, "btn_pdf_edit_execute")
        self.tb_pdf_edit_log = self.findChild(QTextBrowser, "tb_pdf_edit_log")

        if self.btn_pdf_edit_info:
            self.btn_pdf_edit_info.setEnabled(False)
        if self.btn_pdf_edit_execute:
            self.btn_pdf_edit_execute.setEnabled(False)
        if self.radio_pdf_delete:
            self.radio_pdf_delete.setChecked(True)

        # 保存内部状态
        self._pdf_source_path: str = ""

    # ── Data 页控件 ────────────────────────────────────

    def _init_data_controls(self) -> None:
        """初始化 Data 标签页的控件引用。"""
        # 数据源
        self.edit_data_source = self.findChild(QLineEdit, "edit_data_source")
        self.btn_data_source = self.findChild(QPushButton, "btn_data_source")
        self.combo_data_encoding = self.findChild(QComboBox, "combo_data_encoding")
        self.combo_data_separator = self.findChild(QComboBox, "combo_data_separator")
        self.spin_data_header = self.findChild(QSpinBox, "spin_data_header")
        self.btn_data_load = self.findChild(QPushButton, "btn_data_load")

        # 预览
        self.table_data_preview = self.findChild(QTableView, "table_data_preview")
        self.lbl_data_stats = self.findChild(QLabel, "lbl_data_stats")

        # 分析
        self.combo_data_xcol = self.findChild(QComboBox, "combo_data_xcol")
        self.combo_data_ycol = self.findChild(QComboBox, "combo_data_ycol")
        self.btn_data_scatter = self.findChild(QPushButton, "btn_data_scatter")
        self.btn_data_hist = self.findChild(QPushButton, "btn_data_hist")
        self.btn_data_linear = self.findChild(QPushButton, "btn_data_linear")
        self.widget_data_plot = self.findChild(QWidget, "widget_data_plot")
        self.lbl_data_fit_result = self.findChild(QLabel, "lbl_data_fit_result")
        self.btn_data_save_png = self.findChild(QPushButton, "btn_data_save_png")
        self.btn_data_copy_latex = self.findChild(QPushButton, "btn_data_copy_latex")

        # 初始禁用分析按钮（数据未加载时不可用）
        self.btn_data_scatter.setEnabled(False)
        self.btn_data_hist.setEnabled(False)
        self.btn_data_linear.setEnabled(False)

        # 表格交替行颜色
        self.table_data_preview.setAlternatingRowColors(True)

        # 工具提示
        self.btn_data_load.setToolTip(tr("data.tooltip_load"))
        self.btn_data_scatter.setToolTip(tr("data.tooltip_scatter"))
        self.btn_data_linear.setToolTip(tr("data.tooltip_linear"))

        # 存储 UI 文件中的控件引用，用于翻译
        self._group_data_source = self.findChild(QGroupBox, "group_data_source")
        self._label_data_source = self.findChild(QLabel, "label_data_source")
        self._label_data_encoding = self.findChild(QLabel, "label_data_encoding")
        self._label_data_separator = self.findChild(QLabel, "label_data_separator")
        self._label_data_header = self.findChild(QLabel, "label_data_header")
        self._group_data_preview = self.findChild(QGroupBox, "group_data_preview")
        self._group_data_analysis = self.findChild(QGroupBox, "group_data_analysis")
        self._label_data_xcol = self.findChild(QLabel, "label_data_xcol")
        self._label_data_ycol = self.findChild(QLabel, "label_data_ycol")

    # ── Settings 页控件 ────────────────────────────────

    def _init_settings_controls(self) -> None:
        """初始化 Settings 标签页的控件引用。"""
        # 语言
        self.radio_settings_lang_zh = self.findChild(QRadioButton, "radio_settings_lang_zh")
        self.radio_settings_lang_ja = self.findChild(QRadioButton, "radio_settings_lang_ja")
        self.radio_settings_lang_en = self.findChild(QRadioButton, "radio_settings_lang_en")

        # 个人信息
        self.edit_settings_name = self.findChild(QLineEdit, "edit_settings_name")
        self.edit_settings_student_id = self.findChild(QLineEdit, "edit_settings_student_id")

        # 外观 —— 用普通 QComboBox 替换 QFontComboBox 以避免独立弹窗问题
        self._init_font_combo()

        self.spin_settings_font_size = self.findChild(QSpinBox, "spin_settings_font_size")

    def _init_font_combo(self) -> None:
        """用普通 QComboBox 替换 UI 文件中的 QFontComboBox。

        原因：PySide6 的 QFontComboBox 在部分平台/主题下会弹出独立对话框
        而非下拉列表，且不会自动关闭。
        """
        from PySide6.QtGui import QFontDatabase

        old_combo = self.findChild(QFontComboBox, "combo_settings_font")
        if old_combo is None:
            return

        # 找到旧 combo 在布局中的位置
        parent_layout = None
        index = -1
        parent_widget = old_combo.parentWidget()
        if parent_widget:
            parent_layout = parent_widget.layout()
        if parent_layout is None:
            # 尝试从 form layout 中查找
            for child in self.findChildren(QWidget):
                lay = child.layout()
                if lay:
                    idx = lay.indexOf(old_combo)
                    if idx >= 0:
                        parent_layout = lay
                        index = idx
                        break

        # 创建新 combo 并填入系统字体（逐项设置字体以保留预览效果）
        from PySide6.QtCore import Qt as QtCore

        new_combo = QComboBox()
        new_combo.setObjectName("combo_settings_font")
        font_db = QFontDatabase()
        for family in font_db.families():
            new_combo.addItem(family)
            new_combo.setItemData(
                new_combo.count() - 1,
                QFontDatabase.font(family, "", 10),
                QtCore.FontRole,
            )

        # 替换
        if parent_layout is not None and index >= 0:
            parent_layout.replaceWidget(old_combo, new_combo)
        old_combo.hide()
        old_combo.deleteLater()

        self.combo_settings_font = new_combo

        # 默认值
        self.spin_settings_default_dpi = self.findChild(QSpinBox, "spin_settings_default_dpi")
        self.combo_settings_default_format = self.findChild(
            QComboBox, "combo_settings_default_format"
        )

        # 按钮
        self.btn_settings_reset = self.findChild(QPushButton, "btn_settings_reset")
        self.btn_settings_save = self.findChild(QPushButton, "btn_settings_save")
        self.btn_settings_cancel = self.findChild(QPushButton, "btn_settings_cancel")

        # 存储 UI 文件中的控件引用，用于翻译
        self._group_settings_lang = self.findChild(QGroupBox, "group_settings_lang")
        self._group_settings_personal = self.findChild(QGroupBox, "group_settings_personal")
        self._label_settings_name = self.findChild(QLabel, "label_settings_name")
        self._label_settings_student_id = self.findChild(QLabel, "label_settings_student_id")
        self._group_settings_appearance = self.findChild(QGroupBox, "group_settings_appearance")
        self._label_settings_font = self.findChild(QLabel, "label_settings_font")
        self._label_settings_font_size = self.findChild(QLabel, "label_settings_font_size")
        self._group_settings_defaults = self.findChild(QGroupBox, "group_settings_defaults")
        self._label_settings_default_dpi = self.findChild(QLabel, "label_settings_default_dpi")
        self._label_settings_default_format = self.findChild(
            QLabel, "label_settings_default_format"
        )

    # ── 语言切换 ─────────────────────────────────────

    def _init_cache_cleaner_controls(self) -> None:
        """初始化 Cache Cleaner 标签页的控件引用。"""
        # LaTeX 区域
        self.group_cache_latex = self.findChild(QGroupBox, "group_cache_latex")
        self.label_cache_latex_output = self.findChild(QLabel, "label_cache_latex_output")
        self.edit_cache_latex_output = self.findChild(QLineEdit, "edit_cache_latex_output")
        self.btn_cache_latex_clear_output = self.findChild(
            QPushButton, "btn_cache_latex_clear_output"
        )
        self.label_cache_latex_aux = self.findChild(QLabel, "label_cache_latex_aux")
        self.edit_cache_latex_aux = self.findChild(QLineEdit, "edit_cache_latex_aux")
        self.check_cache_latex_files_only = self.findChild(
            QCheckBox, "check_cache_latex_files_only"
        )
        self.btn_cache_latex_delete_aux = self.findChild(QPushButton, "btn_cache_latex_delete_aux")
        self.btn_auto_clear_latex = self.findChild(QPushButton, "btn_auto_clear_latex")
        # Python 区域
        self.group_cache_python = self.findChild(QGroupBox, "group_cache_python")
        self.check_cache_python_pycache = self.findChild(QCheckBox, "check_cache_python_pycache")
        self.check_cache_python_pyc = self.findChild(QCheckBox, "check_cache_python_pyc")
        self.btn_auto_clear_python = self.findChild(QPushButton, "btn_auto_clear_python")

    # ── 语言切换 ─────────────────────────────────────

    def _connect_language_signals(self) -> None:
        """连接语言切换单选按钮的信号（在初始语言应用之后）。"""
        self.radio_settings_lang_zh.toggled.connect(self._on_language_changed)
        self.radio_settings_lang_ja.toggled.connect(self._on_language_changed)
        self.radio_settings_lang_en.toggled.connect(self._on_language_changed)

    def _on_language_changed(self, checked: bool) -> None:
        """语言单选按钮切换时重新应用界面语言。"""
        if not checked:
            return
        lang = self._get_selected_language()
        set_language(lang)
        self._apply_language(lang)

    def _apply_language(self, lang: str) -> None:
        """将界面所有文本切换为指定语言。

        覆盖 UI 文件中的静态控件、程序化创建的控件以及标签页标题。
        """
        # ── 窗口标题 ──────────────────────────────────
        self.setWindowTitle(tr("app.title"))

        # ── 标签页标题 ────────────────────────────────
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        if tab_widget:
            for i, key in enumerate(TAB_ORDER):
                if i < tab_widget.count():
                    tab_widget.setTabText(i, tr(key))

        # ── Project 标签页 ─────────────────────────────
        _set_if(self.findChild(QLabel, "label_experiment_name"), "setText", tr("project.exp_name"))
        _set_if(
            self.findChild(QLabel, "label_parent_folder"), "setText", tr("project.parent_folder")
        )
        _set_if(
            self.findChild(QLabel, "label_project_template"),
            "setText",
            tr("project.template_label"),
        )
        _set_if(
            self.findChild(QPushButton, "parent_folder_path_btn"), "setText", tr("project.browse")
        )
        _set_if(
            self.findChild(QCheckBox, "check_generate_gitignore"),
            "setText",
            tr("project.gen_gitignore"),
        )
        _set_if(self.findChild(QCheckBox, "check_init_repo"), "setText", tr("project.init_repo"))
        _set_if(self.findChild(QPushButton, "btn_project_create"), "setText", tr("project.create"))
        _set_if(self.findChild(QGroupBox, "group_log"), "setTitle", tr("project.log"))

        # ── Convertor 标签页（UI 文件控件） ─────────────
        _set_if(self._widget_box_convert_beamer, "setTitle", tr("convertor.beamer_to_ppt"))
        _set_if(self._widget_btp_io_box, "setTitle", tr("convertor.source_pdf").rstrip(":"))
        _set_if(self._widget_btp_log_box, "setTitle", tr("convertor.log"))
        _set_if(self._widget_label_btp_source, "setText", tr("convertor.source_pdf"))
        _set_if(self._widget_label_btp_output, "setText", tr("convertor.output_folder"))
        _set_if(self._widget_label_btp_format, "setText", tr("convertor.output_format"))
        _set_if(self._widget_label_btp_custom, "setText", tr("convertor.custom_filename"))
        _set_if(self.btn_btp_convert, "setText", tr("convertor.convert"))
        _set_if(self.btn_btp_io_source, "setText", tr("struct.browse"))
        _set_if(self.btn_btp_io_output_folder, "setText", tr("struct.browse"))

        # Convertor 程序化控件
        _set_if(self._lbl_btp_dpi, "setText", tr("convertor.dpi_label"))

        # ── PDF 编辑器 ────────────────────────────────
        _set_if(self.group_pdf_edit, "setTitle", tr("pdf_editor.title"))
        _set_if(self.btn_pdf_edit_source, "setText", tr("pdf_editor.select_pdf"))
        _set_if(self.lbl_pdf_edit_info, "setText", tr("pdf_editor.no_file"))
        _set_if(self.btn_pdf_edit_info, "setText", tr("pdf_editor.get_info"))
        _set_if(self.radio_pdf_delete, "setText", tr("pdf_editor.delete_pages"))
        _set_if(self.radio_pdf_extract, "setText", tr("pdf_editor.extract_pages"))
        _set_if(self.lbl_pdf_edit_range, "setText", tr("pdf_editor.page_range"))
        _set_if(
            self.edit_pdf_edit_range, "setPlaceholderText", tr("pdf_editor.page_range_placeholder")
        )
        _set_if(self.btn_pdf_edit_output, "setText", tr("pdf_editor.output_path"))
        _set_if(
            self.edit_pdf_edit_output, "setPlaceholderText", tr("pdf_editor.output_placeholder")
        )
        _set_if(self.btn_pdf_edit_execute, "setText", tr("pdf_editor.execute"))

        # ── Data 标签页 ───────────────────────────────
        _set_if(self._group_data_source, "setTitle", tr("data.source"))
        _set_if(self._label_data_source, "setText", tr("data.file"))
        _set_if(self.btn_data_source, "setText", tr("data.browse"))
        _set_if(self._label_data_encoding, "setText", tr("data.encoding"))
        _set_if(self._label_data_separator, "setText", tr("data.separator"))
        _set_if(self._label_data_header, "setText", tr("data.header_row"))
        _set_if(self.btn_data_load, "setText", tr("data.load"))
        _set_if(self._group_data_preview, "setTitle", tr("data.preview"))
        _set_if(self.lbl_data_stats, "setText", tr("data.not_loaded"))
        _set_if(self._group_data_analysis, "setTitle", tr("data.analysis"))
        _set_if(self._label_data_xcol, "setText", tr("data.x_axis"))
        _set_if(self._label_data_ycol, "setText", tr("data.y_axis"))
        _set_if(self.btn_data_scatter, "setText", tr("data.scatter"))
        _set_if(self.btn_data_hist, "setText", tr("data.hist"))
        _set_if(self.btn_data_linear, "setText", tr("data.linear"))
        _set_if(self.lbl_data_fit_result, "setText", tr("data.fit_placeholder"))
        _set_if(self.btn_data_save_png, "setText", tr("data.save_png"))
        _set_if(self.btn_data_copy_latex, "setText", tr("data.copy_latex"))

        # ── Settings 标签页 ───────────────────────────
        _set_if(self._group_settings_lang, "setTitle", tr("settings.language"))
        _set_if(self.radio_settings_lang_zh, "setText", tr("settings.lang_zh"))
        _set_if(self.radio_settings_lang_en, "setText", tr("settings.lang_en"))
        _set_if(self.radio_settings_lang_ja, "setText", tr("settings.lang_ja"))
        _set_if(self._group_settings_personal, "setTitle", tr("settings.personal_info"))
        _set_if(self._label_settings_name, "setText", tr("settings.name"))
        _set_if(self.edit_settings_name, "setPlaceholderText", tr("settings.name_placeholder"))
        _set_if(self._label_settings_student_id, "setText", tr("settings.student_id"))
        _set_if(
            self.edit_settings_student_id,
            "setPlaceholderText",
            tr("settings.student_id_placeholder"),
        )
        _set_if(self._group_settings_appearance, "setTitle", tr("settings.appearance"))
        _set_if(self._label_settings_font, "setText", tr("settings.font"))
        _set_if(self._label_settings_font_size, "setText", tr("settings.font_size"))
        _set_if(self._group_settings_defaults, "setTitle", tr("settings.defaults"))
        _set_if(self._label_settings_default_dpi, "setText", tr("settings.default_dpi"))
        _set_if(self._label_settings_default_format, "setText", tr("settings.default_format"))
        _set_if(self.btn_settings_reset, "setText", tr("settings.reset"))
        _set_if(self.btn_settings_save, "setText", tr("settings.save"))
        _set_if(self.btn_settings_cancel, "setText", tr("settings.cancel"))

        # ── Cache Cleaner 标签页 ───────────────────────
        _set_if(self.group_cache_latex, "setTitle", tr("cache_cleaner.latex"))
        _set_if(self.label_cache_latex_output, "setText", tr("cache_cleaner.output_location"))
        _set_if(self.btn_cache_latex_clear_output, "setText", tr("cache_cleaner.clear"))
        _set_if(self.label_cache_latex_aux, "setText", tr("cache_cleaner.aux_path"))
        _set_if(self.check_cache_latex_files_only, "setText", tr("cache_cleaner.files_only"))
        _set_if(self.btn_cache_latex_delete_aux, "setText", tr("cache_cleaner.delete_aux"))
        _set_if(self.btn_auto_clear_latex, "setText", tr("cache_cleaner.auto_clear"))
        _set_if(self.group_cache_python, "setTitle", tr("cache_cleaner.python"))
        _set_if(self.check_cache_python_pycache, "setText", tr("cache_cleaner.clear_pycache"))
        _set_if(self.check_cache_python_pyc, "setText", tr("cache_cleaner.clear_pyc"))
        _set_if(self.btn_auto_clear_python, "setText", tr("cache_cleaner.auto_clear"))

    # ── 设置加载 / 保存 ─────────────────────────────────

    @property
    def _config_path(self) -> Path:
        """返回 user_data/config.json 的路径。"""
        return PROJECT_ROOT / "user_data" / "config.json"

    def _load_settings(self) -> None:
        """从 user_data/config.json 加载设置到界面控件。"""
        if not self._config_path.exists():
            return
        try:
            config: dict = json.loads(self._config_path.read_text("utf-8"))

            # 语言
            lang = config.get("language", "zh_CN")
            set_language(lang)
            if lang == "ja":
                self.radio_settings_lang_ja.setChecked(True)
            elif lang == "en":
                self.radio_settings_lang_en.setChecked(True)
            else:
                self.radio_settings_lang_zh.setChecked(True)

            # 个人信息
            self.edit_settings_name.setText(config.get("name", ""))
            self.edit_settings_student_id.setText(config.get("student_id", ""))

            # 外观
            font_family = config.get("font_family", "")
            if font_family:
                self.combo_settings_font.setCurrentText(font_family)
            font_size = config.get("font_size", 10)
            self.spin_settings_font_size.setValue(font_size)
            self._apply_appearance()

            # 默认值
            default_dpi = config.get("default_dpi", DPI_DEFAULT)
            self.spin_settings_default_dpi.setValue(default_dpi)
            # 同步 Convertor 标签页的 DPI
            if hasattr(self, "spin_btp_dpi"):
                self.spin_btp_dpi.setValue(default_dpi)

            default_format = config.get("default_format", "PDF to PPTX")
            idx = self.combo_settings_default_format.findText(default_format)
            if idx >= 0:
                self.combo_settings_default_format.setCurrentIndex(idx)

            # 恢复窗口几何和最后标签页
            geo_b64 = config.get("window_geometry", "")
            if geo_b64:
                import base64

                from PySide6.QtCore import QByteArray

                self.restoreGeometry(QByteArray.fromBase64(base64.b64decode(geo_b64)))
            last_tab = config.get("last_tab_index", 0)
            tab_widget = self.findChild(QTabWidget, "tabWidget")
            if tab_widget and 0 <= last_tab < tab_widget.count():
                tab_widget.setCurrentIndex(last_tab)

        except (json.JSONDecodeError, OSError):
            pass  # 文件损坏就忽略，使用默认值

    def _save_settings(self) -> None:
        """保存当前设置到 user_data/config.json。

        如果 user_data/ 目录不存在，弹窗询问是否创建。
        """
        user_data_dir = PROJECT_ROOT / "user_data"
        if not user_data_dir.exists():
            reply = QMessageBox.question(
                self,
                tr("settings.dir_not_found_title"),
                tr("settings.dir_not_found_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                user_data_dir.mkdir(parents=True, exist_ok=True)
            else:
                return

        # 保存窗口几何
        import base64

        geo_bytes = self.saveGeometry().toBase64().data()
        geo_b64 = base64.b64encode(geo_bytes).decode("ascii")

        # 当前标签页
        tab_widget = self.findChild(QTabWidget, "tabWidget")
        last_tab = tab_widget.currentIndex() if tab_widget else 0

        config: dict = {
            "language": self._get_selected_language(),
            "name": self.edit_settings_name.text().strip(),
            "student_id": self.edit_settings_student_id.text().strip(),
            "font_family": self.combo_settings_font.currentText(),
            "font_size": self.spin_settings_font_size.value(),
            "default_dpi": self.spin_settings_default_dpi.value(),
            "default_format": self.combo_settings_default_format.currentText(),
            "window_geometry": geo_b64,
            "last_tab_index": last_tab,
        }
        self._config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), "utf-8")
        # 应用外观
        self._apply_appearance()
        # 同时保存语言到全局并重新应用
        set_language(self._get_selected_language())
        self._apply_language(_current_lang)

    def _get_selected_language(self) -> str:
        """返回当前选中的语言标识。"""
        if self.radio_settings_lang_ja.isChecked():
            return "ja"
        elif self.radio_settings_lang_en.isChecked():
            return "en"
        return "zh_CN"

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

        # Data 标签页
        self.btn_data_source.clicked.connect(self._data_browse_source)
        self.btn_data_load.clicked.connect(self._data_load_csv)
        self.btn_data_scatter.clicked.connect(self._data_scatter)
        self.btn_data_hist.clicked.connect(self._data_hist)
        self.btn_data_linear.clicked.connect(self._data_linear)
        self.btn_data_save_png.clicked.connect(self._data_save_png)
        self.btn_data_copy_latex.clicked.connect(self._data_copy_latex)

        # Cache Cleaner 标签页
        self.btn_cache_latex_clear_output.clicked.connect(self._cache_clear_latex_output)
        self.btn_cache_latex_delete_aux.clicked.connect(self._cache_delete_aux)
        self.btn_auto_clear_latex.clicked.connect(self._cache_auto_clear_latex)
        self.btn_auto_clear_python.clicked.connect(self._cache_auto_clear_python)

        # Snippets 标签页
        self.combo_snippets_category.currentTextChanged.connect(self._refresh_snippets_list)
        self.list_snippets.currentRowChanged.connect(self._on_snippet_selected)
        self.btn_snippets_copy.clicked.connect(self._snippets_copy)
        self.btn_snippets_insert.clicked.connect(self._snippets_insert)

        # Project 标签页
        self.parent_folder_path_btn.clicked.connect(self._project_browse_folder)
        self.btn_project_create.clicked.connect(self._project_create)

        # Settings 标签页
        self.btn_settings_save.clicked.connect(self._save_settings)
        self.btn_settings_cancel.clicked.connect(self._load_settings)
        self.btn_settings_reset.clicked.connect(self._settings_reset)
        # 外观实时应用
        self.combo_settings_font.currentTextChanged.connect(self._on_appearance_changed)
        self.spin_settings_font_size.valueChanged.connect(self._on_appearance_changed)

    # ── Convertor 槽函数 ──────────────────────────────

    def _browse_source(self) -> None:
        """浏览选择源 PDF 文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.select_pdf"), "", "PDF Files (*.pdf)"
        )
        if path:
            self.edit_btp_io_source.setText(path)

    def _browse_output_folder(self) -> None:
        """浏览选择输出文件夹。"""
        path = QFileDialog.getExistingDirectory(self, tr("dialog.select_output_folder"))
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
            QMessageBox.warning(self, tr("dialog.warning"), tr("convertor.no_source"))
            return

        output_folder = self.edit_btp_io_output_folder.text().strip()
        if not output_folder:
            QMessageBox.warning(self, tr("dialog.warning"), tr("convertor.no_output"))
            return

        fmt = self.combo_btp_io_output_format.currentText()
        use_custom = self.cb_btp_custom_name.isChecked()
        custom_name = self.edit_btp_custom_name.text().strip() if use_custom else ""

        dpi = self.spin_btp_dpi.value()

        self.tb_btp_log.clear()
        self.tb_btp_log.append(f"{tr('convertor.starting')}{source}")
        self.tb_btp_log.append(f"DPI: {dpi}, {tr('convertor.output_format')[:-1]}: {fmt}")

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
            self.tb_btp_log.append(tr("convertor.done"))
            self.tb_btp_log.append(f"{tr('convertor.output_file')}{result['output_path']}")
        else:
            self.tb_btp_log.append(f"{tr('convertor.failed')}{result['error']}")
            QMessageBox.critical(self, tr("dialog.error"), result["error"])

    # ── PDF 编辑器槽函数 ──────────────────────────────

    def _pdf_browse_source(self) -> None:
        """选择要编辑的 PDF 源文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog.select_pdf"), "", "PDF Files (*.pdf)"
        )
        if path:
            self._pdf_source_path = path
            self.lbl_pdf_edit_info.setText(f"{tr('pdf_editor.selected')}{Path(path).name}")
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
            page_word = tr("pdf_editor.pages_info")
            self.lbl_pdf_edit_info.setText(
                f"{Path(self._pdf_source_path).name} — {info.total_pages}{page_word}{size_str}"
            )
            self.tb_pdf_edit_log.append(f"PDF info: {info.total_pages}{page_word}{size_str}")
        except Exception as exc:
            self.tb_pdf_edit_log.append(f"{tr('pdf_editor.cannot_read')}{exc}")

    def _pdf_browse_output(self) -> None:
        """浏览选择 PDF 输出路径。"""
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog.save_pdf"), "", "PDF Files (*.pdf)")
        if path:
            self.edit_pdf_edit_output.setText(path)

    def _pdf_on_input_changed(self) -> None:
        """页面范围输入变化时启用/禁用执行按钮。"""
        has_range = bool(self.edit_pdf_edit_range.text().strip())
        self.btn_pdf_edit_execute.setEnabled(bool(self._pdf_source_path) and has_range)

    def _pdf_execute(self) -> None:
        """执行 PDF 页面删除或提取。"""
        if not self._pdf_source_path:
            QMessageBox.warning(self, tr("dialog.warning"), tr("pdf_editor.no_file_selected"))
            return

        range_text = self.edit_pdf_edit_range.text().strip()
        if not range_text:
            QMessageBox.warning(self, tr("dialog.warning"), tr("pdf_editor.no_range"))
            return

        output_path = self.edit_pdf_edit_output.text().strip()
        if not output_path:
            QMessageBox.warning(self, tr("dialog.warning"), tr("pdf_editor.no_output"))
            return

        # 获取总页数用于校验
        try:
            info = PdfPageEditor.get_info(self._pdf_source_path)
            total_pages = info.total_pages
        except Exception as exc:
            QMessageBox.critical(self, tr("dialog.error"), f"{tr('pdf_editor.cannot_read')}{exc}")
            return

        # 解析页面范围
        try:
            pages = PdfPageEditor.parse_page_spec(range_text, total_pages)
        except ValueError as exc:
            QMessageBox.warning(self, tr("dialog.info"), str(exc))
            return

        self.tb_pdf_edit_log.clear()
        self.tb_pdf_edit_log.append(
            f"{tr('pdf_editor.total_pages')}{total_pages}"
            f"{tr('pdf_editor.target_pages')}{len(pages)}{tr('pdf_editor.pages_info')}"
        )

        is_delete = self.radio_pdf_delete.isChecked()
        if is_delete:
            self.tb_pdf_edit_log.append(f"{tr('pdf_editor.op_delete')}{range_text}")
            result = PdfPageEditor.delete_pages(
                source=self._pdf_source_path,
                pages_to_delete=pages,
                output_path=output_path,
            )
        else:
            self.tb_pdf_edit_log.append(f"{tr('pdf_editor.op_extract')}{range_text}")
            result = PdfPageEditor.extract_pages(
                source=self._pdf_source_path,
                pages_to_extract=pages,
                output_path=output_path,
            )

        if result.success:
            page_word = tr("pdf_editor.pages_info")
            self.tb_pdf_edit_log.append(
                f"{tr('pdf_editor.done')}{result.output_path} ({result.page_count}{page_word})"
            )
        else:
            self.tb_pdf_edit_log.append(f"{tr('pdf_editor.failed')}{result.error}")
            QMessageBox.critical(self, tr("dialog.error"), result.error)

    # ── Data 标签页槽函数 ──────────────────────────────

    def _embed_plot(self, fig) -> None:
        """将 matplotlib Figure 嵌入 widget_data_plot。"""
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        # 清除旧内容
        layout = self.widget_data_plot.layout()
        if layout is None:
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(self.widget_data_plot)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        canvas.draw()

    def _data_browse_source(self) -> None:
        """浏览选择 CSV 数据文件。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("dialog.select_csv"),
            "",
            "CSV Files (*.csv);;TSV Files (*.tsv);;All Files (*)",
        )
        if path:
            self.edit_data_source.setText(path)

    def _data_load_csv(self) -> None:
        """加载 CSV 数据并显示预览。"""
        source = self.edit_data_source.text().strip()
        if not source:
            QMessageBox.warning(self, tr("dialog.info"), tr("data.no_file"))
            return

        from pathlib import Path

        import pandas as pd

        if not Path(source).exists():
            QMessageBox.warning(self, tr("dialog.error"), tr("data.file_not_found"))
            return

        encoding = self.combo_data_encoding.currentText()
        sep_text = self.combo_data_separator.currentText()
        sep = "\t" if sep_text == "\\t" else sep_text
        header_row = self.spin_data_header.value()

        try:
            df = pd.read_csv(
                source, encoding=encoding, sep=sep, header=None if header_row == 0 else header_row
            )
        except Exception as exc:
            QMessageBox.critical(self, tr("dialog.error"), f"{tr('data.load_failed')}{exc}")
            return

        self._data_df = df

        # 填充 QTableView
        model = QStandardItemModel(df.shape[0], df.shape[1])
        if header_row == 0:
            model.setHorizontalHeaderLabels([str(c) for c in df.columns])
        else:
            model.setHorizontalHeaderLabels([f"Col{i+1}" for i in range(df.shape[1])])
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                val = df.iat[row, col]
                item = QStandardItem(str(val) if not pd.isna(val) else "")
                model.setItem(row, col, item)
        self._data_model = model
        self.table_data_preview.setModel(model)

        # 更新统计
        self.lbl_data_stats.setText(
            f"{df.shape[0]} {tr('data.rows')}, {df.shape[1]} {tr('data.columns')}"
        )

        # 填充列选择下拉框
        cols = [str(c) for c in df.columns]
        self.combo_data_xcol.clear()
        self.combo_data_ycol.clear()
        self.combo_data_xcol.addItems(cols)
        self.combo_data_ycol.addItems(cols)
        if len(cols) >= 2:
            self.combo_data_ycol.setCurrentIndex(1)

        # 启用分析按钮
        self.btn_data_scatter.setEnabled(True)
        self.btn_data_hist.setEnabled(True)
        self.btn_data_linear.setEnabled(True)

        # 状态栏消息
        self.statusBar().showMessage(
            f"{tr('data.loaded')} {Path(source).name} — "
            f"{df.shape[0]} {tr('data.rows')}, {df.shape[1]} {tr('data.columns')}"
        )

    def _data_scatter(self) -> None:
        """绘制散点图。"""
        if not hasattr(self, "_data_df") or self._data_df is None:
            return
        import matplotlib

        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        xcol = self.combo_data_xcol.currentText()
        ycol = self.combo_data_ycol.currentText()
        df = self._data_df

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.scatter(df[xcol], df[ycol], s=20, alpha=0.7, edgecolors="k", linewidths=0.3)
        ax.set_xlabel(xcol)
        ax.set_ylabel(ycol)
        ax.set_title(f"{ycol} vs {xcol}")
        fig.tight_layout()

        # 替换 plot widget 内容
        self._embed_plot(fig)

    def _data_hist(self) -> None:
        """绘制直方图。"""
        if not hasattr(self, "_data_df") or self._data_df is None:
            return
        import matplotlib

        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        xcol = self.combo_data_xcol.currentText()
        df = self._data_df

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.hist(df[xcol].dropna(), bins=20, edgecolor="k", alpha=0.7)
        ax.set_xlabel(xcol)
        ax.set_ylabel(tr("data.frequency"))
        fig.tight_layout()

        self._embed_plot(fig)

    def _data_linear(self) -> None:
        """执行线性拟合。"""
        if not hasattr(self, "_data_df") or self._data_df is None:
            return
        import matplotlib
        import numpy as np

        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        from scipy.optimize import curve_fit

        xcol = self.combo_data_xcol.currentText()
        ycol = self.combo_data_ycol.currentText()
        df = self._data_df

        x = df[xcol].dropna().values.astype(float)
        y = df[ycol].dropna().values.astype(float)
        # 确保等长
        mask = ~(np.isnan(x) | np.isnan(y))
        x, y = x[mask], y[mask]

        if len(x) < 2:
            QMessageBox.warning(self, tr("dialog.info"), tr("data.insufficient_data"))
            return

        def linear(x, a, b):
            return a * x + b

        popt, pcov = curve_fit(linear, x, y)
        a, b = popt
        a_err = np.sqrt(pcov[0, 0])
        b_err = np.sqrt(pcov[1, 1])

        # R^2
        y_pred = linear(x, *popt)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # 绘图
        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.scatter(x, y, s=20, alpha=0.7, edgecolors="k", linewidths=0.3, label="Data")
        xfit = np.linspace(x.min(), x.max(), 100)
        ax.plot(xfit, linear(xfit, *popt), "r-", label="Fit")
        ax.set_xlabel(xcol)
        ax.set_ylabel(ycol)
        ax.legend(fontsize=8)
        fig.tight_layout()

        self._embed_plot(fig)

        # 显示拟合结果
        self.lbl_data_fit_result.setText(
            f"y = ({a:.4f} ± {a_err:.4f})x + ({b:.4f} ± {b_err:.4f})\n" f"R² = {r2:.4f}"
        )

    def _data_save_png(self) -> None:
        """保存当前图表为 PNG。"""
        # 检查 plot widget 中是否有 canvas
        layout = self.widget_data_plot.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and hasattr(widget, "figure"):
                path, _ = QFileDialog.getSaveFileName(
                    self, tr("data.save_png_dialog"), "plot.png", "PNG (*.png)"
                )
                if path:
                    widget.figure.savefig(path, dpi=150, bbox_inches="tight")
                    QMessageBox.information(
                        self, tr("dialog.done"), f"{tr('data.saved_to')} {path}"
                    )
                return

    def _data_copy_latex(self) -> None:
        """复制拟合结果为 LaTeX 公式。"""
        text = self.lbl_data_fit_result.text() if self.lbl_data_fit_result else ""
        if text and "y =" in text:
            QApplication.clipboard().setText(text)
            self.lbl_data_fit_result.setStyleSheet("color: green;")
            from PySide6.QtCore import QTimer

            QTimer.singleShot(1500, lambda: self.lbl_data_fit_result.setStyleSheet(""))

    # ── Cache Cleaner 槽函数 ──────────────────────────

    def _cache_clear_latex_output(self) -> None:
        """清理 LaTeX 输出目录下 PDF 文件。"""
        output_dir = (
            self.edit_cache_latex_output.text().strip()
            if self.edit_cache_latex_output
            else "outputs/"
        )
        self._cache_delete_files(output_dir, ["*.pdf"], tr("cache_cleaner.cleared_output"))

    def _cache_delete_aux(self) -> None:
        """清理 LaTeX 辅助文件。"""
        aux_dir = (
            self.edit_cache_latex_aux.text().strip()
            if self.edit_cache_latex_aux
            else "outputs/.latextmp/"
        )
        files_only = (
            self.check_cache_latex_files_only.isChecked()
            if self.check_cache_latex_files_only
            else False
        )
        patterns = [
            "*.aux",
            "*.log",
            "*.toc",
            "*.out",
            "*.nav",
            "*.snm",
            "*.bbl",
            "*.blg",
            "*.fdb_latexmk",
            "*.fls",
            "*.synctex.gz",
        ]
        self._cache_delete_files(
            aux_dir, patterns, tr("cache_cleaner.cleared_aux"), files_only=files_only
        )

    def _cache_auto_clear_latex(self) -> None:
        """一键清理 LaTeX 输出 + 辅助文件。"""
        self._cache_clear_latex_output()
        self._cache_delete_aux()

    def _cache_auto_clear_python(self) -> None:
        """清理 Python 缓存。"""
        import shutil
        from pathlib import Path

        base = Path.cwd()
        cleared = 0

        if self.check_cache_python_pycache and self.check_cache_python_pycache.isChecked():
            for pycache in base.rglob("__pycache__"):
                try:
                    shutil.rmtree(pycache)
                    cleared += 1
                except OSError:
                    pass

        if self.check_cache_python_pyc and self.check_cache_python_pyc.isChecked():
            for pyc in list(base.rglob("*.pyc")) + list(base.rglob("*.pyo")):
                try:
                    pyc.unlink()
                    cleared += 1
                except OSError:
                    pass

        QMessageBox.information(
            self,
            tr("dialog.done"),
            f"{tr('cache_cleaner.cleared_python')} {cleared} {tr('cache_cleaner.items')}",
        )

    def _cache_delete_files(
        self, dir_path: str, patterns: list, msg: str, files_only: bool = False
    ) -> None:
        """通用文件清理函数。"""
        import shutil
        from pathlib import Path

        target = Path(dir_path)
        if not target.exists():
            QMessageBox.warning(
                self, tr("dialog.warning"), f"{tr('cache_cleaner.dir_not_found')}: {dir_path}"
            )
            return

        deleted = 0
        for pattern in patterns:
            for f in target.glob(pattern):
                try:
                    if files_only and f.is_dir():
                        continue
                    if f.is_file() or f.is_symlink():
                        f.unlink()
                        deleted += 1
                    elif f.is_dir():
                        shutil.rmtree(f)
                        deleted += 1
                except OSError:
                    pass

        QMessageBox.information(
            self, tr("dialog.done"), f"{msg} {deleted} {tr('cache_cleaner.items')}"
        )

    # ── Settings 标签页槽函数 ──────────────────────────

    # ── Project 标签页槽函数 ──────────────────────────

    def _project_browse_folder(self) -> None:
        """浏览选择项目父目录。"""
        path = QFileDialog.getExistingDirectory(self, tr("dialog.select_output_folder"))
        if path:
            self.edit_parent_folder.setText(path)

    def _project_create(self) -> None:
        """执行项目结构创建。"""
        exp_name = self.edit_experiment_name.text().strip() if self.edit_experiment_name else ""
        if not exp_name:
            QMessageBox.warning(self, tr("dialog.warning"), tr("project.warning.no_name"))
            return

        parent = self.edit_parent_folder.text().strip() if self.edit_parent_folder else ""
        if not parent:
            QMessageBox.warning(self, tr("dialog.warning"), tr("project.warning.no_path"))
            return

        template_key = (
            self.combo_project_template.currentText() if self.combo_project_template else "Default"
        )
        gen_git = (
            self.check_generate_gitignore.isChecked() if self.check_generate_gitignore else False
        )
        init_g = self.check_init_repo.isChecked() if self.check_init_repo else False

        if self.text_log:
            self.text_log.clear()
            self.text_log.append(f"{tr('project.creating')} {exp_name}")
            self.text_log.append(f"{tr('project.template')} {template_key}")

        builder = ProjectBuilder(
            experiment_name=exp_name,
            target_parent=parent,
            template_key=template_key,
            generate_gitignore=gen_git,
            init_repo=init_g,
            overwrite=False,
        )
        result = builder.run()

        if self.text_log:
            if result.success:
                self.text_log.append(f"{tr('project.done')} {result.project_path}")
                self.text_log.append(f"{tr('project.files_created')} {len(result.files_created)}")
                for f in result.files_created:
                    self.text_log.append(f"  {f}")
            else:
                self.text_log.append(f"{tr('project.failed')} {result.error}")
                QMessageBox.critical(self, tr("dialog.error"), result.error or "Unknown error")

    def _on_appearance_changed(self, *args) -> None:
        """字体或字号变化时实时应用外观。"""
        self._apply_appearance()

    def _apply_appearance(self) -> None:
        """将字体族和字号应用到整个应用。"""
        from PySide6.QtGui import QFont

        family = self.combo_settings_font.currentText() if self.combo_settings_font else ""
        size = self.spin_settings_font_size.value() if self.spin_settings_font_size else 10
        if family:
            font = QFont(family, size)
            QApplication.setFont(font)

    def _settings_reset(self) -> None:
        """恢复设置默认值。"""
        reply = QMessageBox.question(
            self,
            tr("settings.confirm_reset"),
            tr("settings.confirm_reset_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.radio_settings_lang_zh.setChecked(True)
            self.edit_settings_name.clear()
            self.edit_settings_student_id.clear()
            self.spin_settings_font_size.setValue(10)
            self.spin_settings_default_dpi.setValue(DPI_DEFAULT)
            self.combo_settings_default_format.setCurrentIndex(0)

    # ── 入口 ──────────────────────────────────────────────


def _set_if(widget, method: str, value: str) -> None:
    """安全调用 widget 的 setter 方法（widget 可能为 None）。"""
    if widget is not None:
        getattr(widget, method)(value)
