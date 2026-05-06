"""
Labexp-Assistant
实验代码助手 —— PySide6 版本
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox,
    QFormLayout, QMessageBox, QFileDialog, QTabWidget, QCheckBox,
    QComboBox, QStatusBar,
)
from PySide6.QtCore import Qt, QThread, Signal

from PySide6.QtGui import QFont, QFontDatabase

# =========================
# 路径配置
# =========================
BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"
LOCALES_DIR = BASE_DIR / "locales"
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_FILE = Path.home() / ".labexp_assistant_config.json"

# =========================
# 多语言支持
# =========================

LANGUAGES = {
    "zh_CN": "中文",
    "en": "English",
    "ja": "日本語",
}

_translations: dict[str, dict[str, str]] = {}
_current_lang = "zh_CN"


def load_translations():
    """加载所有语言文件"""
    global _translations
    for lang_code in LANGUAGES:
        path = LOCALES_DIR / f"{lang_code}.json"
        if path.exists():
            _translations[lang_code] = json.loads(path.read_text(encoding="utf-8"))
        else:
            _translations[lang_code] = {}


def tr(key: str) -> str:
    """翻译函数：根据当前语言返回对应文本，找不到则返回 key 本身"""
    return _translations.get(_current_lang, {}).get(key, key)


def set_language(lang_code: str):
    """切换当前语言"""
    global _current_lang
    if lang_code in _translations:
        _current_lang = lang_code


# =========================
# 模板管理
# =========================

def render_template(text: str, **kwargs) -> str:
    """简单的模板渲染：将 {{ var }} 替换为 kwargs 中的值"""
    def replacer(match):
        var_name = match.group(1).strip()
        return str(kwargs.get(var_name, match.group(0)))
    return re.sub(r'\{\{\s*(\w+)\s*\}\}', replacer, text)


def load_template_text(category: str, name: str) -> str | None:
    """从 templates/{category}/{name}.tmpl 加载文本模板"""
    path = TEMPLATES_DIR / category / f"{name}.tmpl"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def load_structure_json(name: str) -> dict | None:
    """从 templates/structures/{name}.json 加载结构定义"""
    path = TEMPLATES_DIR / "structures" / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def list_templates(category: str, extension: str = ".tmpl") -> list[str]:
    """列出 templates/{category}/ 下所有模板文件（不含扩展名）"""
    dir_path = TEMPLATES_DIR / category
    if not dir_path.exists():
        return []
    return sorted(p.stem for p in dir_path.glob(f"*{extension}"))


def list_structure_templates() -> list[str]:
    """列出可用的结构模板"""
    dir_path = TEMPLATES_DIR / "structures"
    if not dir_path.exists():
        return []
    return sorted(p.stem for p in dir_path.glob("*.json"))


# =========================
# 字体加载
# =========================

def load_fonts() -> str | None:
    """加载 fonts/ 目录下的字体，返回字体族名（取第一个加载的字体系列）"""
    if not FONTS_DIR.exists():
        return None

    font_family = None
    for ttf_path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(ttf_path))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families and font_family is None:
                font_family = families[0]
    return font_family


# =========================
# 后台工作线程
# =========================

class CreateStructureThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, exp_name: str, base_dir: str, overwrite: bool, structure: dict):
        super().__init__()
        self.exp_name = exp_name
        self.base_dir = base_dir
        self.overwrite = overwrite
        self.structure = structure

    def run(self):
        base = Path(self.base_dir).resolve() / self.exp_name
        if base.exists():
            if not self.overwrite:
                self.finished_signal.emit(False, tr("struct.exists") + str(base))
                return
        try:
            self._create_tree(base, self.structure, self.exp_name)
            self.finished_signal.emit(True, tr("struct.finished") + str(base))
        except Exception as e:
            self.finished_signal.emit(False, tr("struct.failed") + str(e))

    def _create_tree(self, current: Path, structure: dict, exp_name: str):
        for name, content in structure.items():
            path = current / name
            if content is None:
                path.mkdir(parents=True, exist_ok=True)
                self.log_signal.emit(f"  [DIR]  {name}/")
            elif isinstance(content, dict):
                path.mkdir(parents=True, exist_ok=True)
                self.log_signal.emit(f"  [DIR]  {name}/")
                self._create_tree(path, content, exp_name)
            elif isinstance(content, str):
                # JSON 结构模板使用 {experiment_name}（Python str.format）
                text = content.format(experiment_name=exp_name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                self.log_signal.emit(f"  [FILE] {name}")


class GitignoreThread(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, target_dir: str, student_id: str, overwrite: bool, template_name: str):
        super().__init__()
        self.target_dir = target_dir
        self.student_id = student_id
        self.overwrite = overwrite
        self.template_name = template_name

    def run(self):
        target = Path(self.target_dir).resolve()
        gitignore_path = target / ".gitignore"

        if gitignore_path.exists() and not self.overwrite:
            self.finished_signal.emit(False, tr("git.exists"))
            return

        template_text = load_template_text("gitignore", self.template_name)
        if template_text is None:
            self.finished_signal.emit(False, tr("git.template_not_found") + self.template_name)
            return

        content = render_template(template_text, student_id=self.student_id)
        gitignore_path.write_text(content, encoding="utf-8")
        self.finished_signal.emit(True, tr("git.finished") + self.student_id + ")")


class ReadmeThread(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, exp_name: str, target_dir: str, template_name: str, student_id: str = ""):
        super().__init__()
        self.exp_name = exp_name
        self.target_dir = target_dir
        self.template_name = template_name
        self.student_id = student_id

    def run(self):
        try:
            target = Path(self.target_dir).resolve()
            readme_path = target / "README.md"

            template_text = load_template_text("readme", self.template_name)
            if template_text is None:
                # 回退到简单模板
                template_text = "# {{ experiment_name }}\n\n## 实验基本信息\n"

            content = render_template(
                template_text,
                experiment_name=self.exp_name,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                student_id=self.student_id,
                operator="",
            )
            readme_path.write_text(content, encoding="utf-8")
            self.finished_signal.emit(True, tr("readme.finished") + str(readme_path))
        except Exception as e:
            self.finished_signal.emit(False, tr("readme.failed") + str(e))


# =========================
# 辅助：配置读写
# =========================

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}

def save_config(student_id: str, language: str = "zh_CN"):
    config = {"student_id": student_id, "language": language}
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# 主窗口
# =========================

class LabExpAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.student_id = self.config.get("student_id", "1224038")

        # 应用配置中的语言
        saved_lang = self.config.get("language", "zh_CN")
        set_language(saved_lang)

        self.init_ui()
        self.apply_font()
        self.load_settings()

    def apply_font(self):
        """使用加载的字体（如果可用）"""
        font_family = load_fonts()
        if font_family:
            font = QFont(font_family, 10)
            QApplication.setFont(font)

    def init_ui(self):
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(700, 550)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ---- 标题 ----
        title = QLabel("Labexp-Assistant")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.subtitle = QLabel(tr("app.subtitle"))
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        # ---- 语言切换 ----
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_label = QLabel(tr("lang.label"))
        lang_layout.addWidget(self.lang_label)
        self.lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        # 设置为当前语言
        idx = self.lang_combo.findData(_current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # ---- 标签页 ----
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 页1: 创建结构
        tab_structure = QWidget()
        self.tabs.addTab(tab_structure, tr("tab.structure"))
        self.setup_tab_structure(tab_structure)

        # 页2: .gitignore
        tab_gitignore = QWidget()
        self.tabs.addTab(tab_gitignore, tr("tab.gitignore"))
        self.setup_tab_gitignore(tab_gitignore)

        # 页3: README
        tab_readme = QWidget()
        self.tabs.addTab(tab_readme, tr("tab.readme"))
        self.setup_tab_readme(tab_readme)

        # 页4: 设置
        tab_settings = QWidget()
        self.tabs.addTab(tab_settings, tr("tab.settings"))
        self.setup_tab_settings(tab_settings)

        # ---- 状态栏 ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("app.status.ready"))

    def _on_language_changed(self, index):
        """切换语言"""
        lang_code = self.lang_combo.itemData(index)
        if lang_code and lang_code != _current_lang:
            set_language(lang_code)
            self._refresh_ui()
            # 保存语言偏好
            save_config(self.student_id, lang_code)

    def _refresh_ui(self):
        """刷新所有界面文字"""
        self.setWindowTitle(tr("app.title"))
        self.subtitle.setText(tr("app.subtitle"))
        self.status_bar.showMessage(tr("app.status.ready"))

        # 刷新标签页标题
        self.tabs.setTabText(0, tr("tab.structure"))
        self.tabs.setTabText(1, tr("tab.gitignore"))
        self.tabs.setTabText(2, tr("tab.readme"))
        self.tabs.setTabText(3, tr("tab.settings"))

        # Tab 1: 结构
        self.struct_name_label.setText(tr("struct.exp_name"))
        self.struct_name_edit.setPlaceholderText(tr("struct.exp_name.placeholder"))
        self.struct_template_label.setText(tr("struct.template"))
        self.struct_path_label.setText(tr("struct.target_path"))
        self.struct_path_edit.setPlaceholderText(tr("struct.target_path.placeholder"))
        self.struct_browse_btn.setText(tr("struct.browse"))
        self.struct_overwrite_cb.setText(tr("struct.overwrite"))
        self.struct_create_btn.setText(tr("struct.create"))
        self.struct_log_label.setText(tr("struct.log_label"))

        # Tab 2: .gitignore
        self.git_template_label.setText(tr("git.template"))
        self.git_sid_label.setText(tr("git.student_id"))
        self.git_sid_edit.setPlaceholderText(tr("git.student_id.placeholder"))
        self.git_path_label.setText(tr("git.target_path"))
        self.git_path_edit.setPlaceholderText(tr("git.target_path.placeholder"))
        self.git_browse_btn.setText(tr("git.browse"))
        self.git_overwrite_cb.setText(tr("git.overwrite"))
        self.git_preview_group.setTitle(tr("git.preview"))
        self.git_generate_btn.setText(tr("git.generate"))

        # Tab 3: README
        self.readme_template_label.setText(tr("readme.template"))
        self.readme_name_label.setText(tr("readme.exp_name"))
        self.readme_name_edit.setPlaceholderText(tr("readme.exp_name.placeholder"))
        self.readme_path_label.setText(tr("readme.target_path"))
        self.readme_browse_btn.setText(tr("readme.browse"))
        self.readme_create_btn.setText(tr("readme.create"))

        # Tab 4: 设置
        self.settings_sid_label.setText(tr("settings.student_id"))
        self.settings_sid_edit.setPlaceholderText(tr("settings.student_id.placeholder"))
        self.settings_save_btn.setText(tr("settings.save"))

        # 语言标签
        self.lang_label.setText(tr("lang.label"))

    # -------- 标签页: 创建结构 --------
    def setup_tab_structure(self, parent):
        layout = QVBoxLayout(parent)

        form = QFormLayout()
        self.struct_name_edit = QLineEdit()
        self.struct_name_edit.setPlaceholderText(tr("struct.exp_name.placeholder"))
        self.struct_name_label = QLabel(tr("struct.exp_name"))
        form.addRow(self.struct_name_label, self.struct_name_edit)

        # 模板选择
        self.struct_template_label = QLabel(tr("struct.template"))
        self.struct_template_combo = QComboBox()
        self._populate_struct_templates()
        self.struct_template_combo.currentIndexChanged.connect(self._on_struct_template_changed)
        form.addRow(self.struct_template_label, self.struct_template_combo)

        self.struct_path_edit = QLineEdit(str(Path.cwd()))
        self.struct_path_edit.setPlaceholderText(tr("struct.target_path.placeholder"))
        self.struct_browse_btn = QPushButton(tr("struct.browse"))
        self.struct_browse_btn.clicked.connect(self._browse_struct_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.struct_path_edit)
        path_layout.addWidget(self.struct_browse_btn)
        self.struct_path_label = QLabel(tr("struct.target_path"))
        form.addRow(self.struct_path_label, path_layout)

        self.struct_overwrite_cb = QCheckBox(tr("struct.overwrite"))
        form.addRow("", self.struct_overwrite_cb)

        layout.addLayout(form)

        self.struct_create_btn = QPushButton(tr("struct.create"))
        self.struct_create_btn.clicked.connect(self._create_structure)
        layout.addWidget(self.struct_create_btn)

        # 日志输出
        self.struct_log_label = QLabel(tr("struct.log_label"))
        self.struct_log = QTextEdit()
        self.struct_log.setReadOnly(True)
        self.struct_log.setMaximumHeight(200)
        layout.addWidget(self.struct_log_label)
        layout.addWidget(self.struct_log)

        layout.addStretch()

    def _populate_struct_templates(self):
        """填充结构模板下拉框"""
        self.struct_template_combo.clear()
        names = list_structure_templates()
        for name in names:
            # 加载描述
            data = load_structure_json(name)
            display_name = data.get("name", name) if data else name
            self.struct_template_combo.addItem(display_name, name)

    def _on_struct_template_changed(self, index):
        """结构模板切换时在日志区显示描述"""
        name = self.struct_template_combo.itemData(index)
        if name:
            data = load_structure_json(name)
            if data and data.get("description"):
                self.struct_log.setPlainText(
                    f"[{data.get('name', name)}]\n{data['description']}"
                )

    def _browse_struct_path(self):
        path = QFileDialog.getExistingDirectory(self, tr("struct.browse"))
        if path:
            self.struct_path_edit.setText(path)

    def _create_structure(self):
        name = self.struct_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("dialog.warning"), tr("struct.warning.no_name"))
            return
        base_dir = self.struct_path_edit.text().strip()
        overwrite = self.struct_overwrite_cb.isChecked()

        # 获取选中的结构模板
        template_name = self.struct_template_combo.currentData()
        structure = load_structure_json(template_name)
        if structure is None:
            QMessageBox.warning(self, tr("dialog.warning"), tr("struct.template_not_found") + template_name)
            return

        self.struct_log.clear()
        self.status_bar.showMessage(tr("struct.status.creating"))

        self.struct_thread = CreateStructureThread(
            name, base_dir, overwrite, structure.get("structure", structure)
        )
        self.struct_thread.log_signal.connect(self.struct_log.append)
        self.struct_thread.finished_signal.connect(self._on_struct_finished)
        self.struct_thread.start()

    def _on_struct_finished(self, success, msg):
        self.struct_log.append(msg)
        self.status_bar.showMessage(msg)
        if success:
            QMessageBox.information(self, tr("dialog.done"), msg)

    # -------- 标签页: .gitignore --------
    def setup_tab_gitignore(self, parent):
        layout = QVBoxLayout(parent)

        form = QFormLayout()

        # 模板选择
        self.git_template_label = QLabel(tr("git.template"))
        self.git_template_combo = QComboBox()
        self._populate_gitignore_templates()
        self.git_template_combo.currentIndexChanged.connect(self._update_git_preview)
        form.addRow(self.git_template_label, self.git_template_combo)

        self.git_sid_edit = QLineEdit(self.student_id)
        self.git_sid_edit.setPlaceholderText(tr("git.student_id.placeholder"))
        self.git_sid_label = QLabel(tr("git.student_id"))
        form.addRow(self.git_sid_label, self.git_sid_edit)

        self.git_path_edit = QLineEdit(str(Path.cwd()))
        self.git_path_edit.setPlaceholderText(tr("git.target_path.placeholder"))
        self.git_browse_btn = QPushButton(tr("git.browse"))
        self.git_browse_btn.clicked.connect(lambda: self._browse_git_path())
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.git_path_edit)
        path_layout.addWidget(self.git_browse_btn)
        self.git_path_label = QLabel(tr("git.target_path"))
        form.addRow(self.git_path_label, path_layout)

        self.git_overwrite_cb = QCheckBox(tr("git.overwrite"))
        form.addRow("", self.git_overwrite_cb)

        layout.addLayout(form)

        # 预览
        self.git_preview_group = QGroupBox(tr("git.preview"))
        preview_layout = QVBoxLayout(self.git_preview_group)
        self.git_preview = QTextEdit()
        self.git_preview.setReadOnly(True)
        self.git_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.git_preview)
        layout.addWidget(self.git_preview_group)

        self.git_generate_btn = QPushButton(tr("git.generate"))
        self.git_generate_btn.clicked.connect(self._generate_gitignore)
        layout.addWidget(self.git_generate_btn)

        self.git_log = QLabel("")
        layout.addWidget(self.git_log)

        layout.addStretch()

        # 实时预览
        self.git_sid_edit.textChanged.connect(self._update_git_preview)
        self._update_git_preview()

    def _populate_gitignore_templates(self):
        """填充 .gitignore 模板下拉框"""
        self.git_template_combo.clear()
        names = list_templates("gitignore")
        for name in names:
            display_name = name.replace("_", " ").title()
            self.git_template_combo.addItem(display_name, name)

    def _browse_git_path(self):
        path = QFileDialog.getExistingDirectory(self, tr("git.browse"))
        if path:
            self.git_path_edit.setText(path)

    def _update_git_preview(self):
        sid = self.git_sid_edit.text().strip() or "1224038"
        template_name = self.git_template_combo.currentData() or "default"
        template_text = load_template_text("gitignore", template_name)
        if template_text:
            self.git_preview.setPlainText(render_template(template_text, student_id=sid))

    def _generate_gitignore(self):
        sid = self.git_sid_edit.text().strip()
        if not sid:
            QMessageBox.warning(self, tr("dialog.warning"), tr("git.warning.no_id"))
            return
        target = self.git_path_edit.text().strip()
        overwrite = self.git_overwrite_cb.isChecked()
        template_name = self.git_template_combo.currentData() or "default"

        self.status_bar.showMessage(tr("git.status.generating"))
        self.git_thread = GitignoreThread(target, sid, overwrite, template_name)
        self.git_thread.finished_signal.connect(self._on_gitignore_finished)
        self.git_thread.start()

    def _on_gitignore_finished(self, success, msg):
        self.git_log.setText(msg)
        self.status_bar.showMessage(msg)
        if success:
            QMessageBox.information(self, tr("dialog.done"), msg)

    # -------- 标签页: README --------
    def setup_tab_readme(self, parent):
        layout = QVBoxLayout(parent)

        form = QFormLayout()

        # 模板选择
        self.readme_template_label = QLabel(tr("readme.template"))
        self.readme_template_combo = QComboBox()
        self._populate_readme_templates()
        self.readme_template_combo.currentIndexChanged.connect(self._update_readme_preview)
        form.addRow(self.readme_template_label, self.readme_template_combo)

        self.readme_name_edit = QLineEdit()
        self.readme_name_edit.setPlaceholderText(tr("readme.exp_name.placeholder"))
        self.readme_name_label = QLabel(tr("readme.exp_name"))
        form.addRow(self.readme_name_label, self.readme_name_edit)

        self.readme_path_edit = QLineEdit(str(Path.cwd()))
        self.readme_browse_btn = QPushButton(tr("readme.browse"))
        self.readme_browse_btn.clicked.connect(lambda: self._browse_readme_path())
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.readme_path_edit)
        path_layout.addWidget(self.readme_browse_btn)
        self.readme_path_label = QLabel(tr("readme.target_path"))
        form.addRow(self.readme_path_label, path_layout)

        layout.addLayout(form)

        # 预览
        self.readme_preview_group = QGroupBox(tr("readme.preview"))
        preview_layout = QVBoxLayout(self.readme_preview_group)
        self.readme_preview = QTextEdit()
        self.readme_preview.setReadOnly(True)
        self.readme_preview.setMaximumHeight(150)
        preview_layout.addWidget(self.readme_preview)
        layout.addWidget(self.readme_preview_group)

        self.readme_create_btn = QPushButton(tr("readme.create"))
        self.readme_create_btn.clicked.connect(self._create_readme)
        layout.addWidget(self.readme_create_btn)

        self.readme_log = QLabel("")
        layout.addWidget(self.readme_log)
        layout.addStretch()

        # 预览联动
        self.readme_name_edit.textChanged.connect(self._update_readme_preview)
        self._update_readme_preview()

    def _populate_readme_templates(self):
        """填充 README 模板下拉框"""
        self.readme_template_combo.clear()
        names = list_templates("readme")
        for name in names:
            display_name = name.replace("_", " ").title()
            self.readme_template_combo.addItem(display_name, name)

    def _update_readme_preview(self):
        """实时预览 README 内容"""
        exp_name = self.readme_name_edit.text().strip() or tr("readme.preview_placeholder")
        template_name = self.readme_template_combo.currentData() or "default"
        template_text = load_template_text("readme", template_name)
        if template_text:
            content = render_template(
                template_text,
                experiment_name=exp_name,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                student_id=self.student_id,
                operator="",
            )
            self.readme_preview.setPlainText(content)

    def _browse_readme_path(self):
        path = QFileDialog.getExistingDirectory(self, tr("readme.browse"))
        if path:
            self.readme_path_edit.setText(path)

    def _create_readme(self):
        name = self.readme_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("dialog.warning"), tr("readme.warning.no_name"))
            return
        target = self.readme_path_edit.text().strip()
        template_name = self.readme_template_combo.currentData() or "default"

        self.status_bar.showMessage(tr("readme.status.updating"))
        self.readme_thread = ReadmeThread(name, target, template_name, self.student_id)
        self.readme_thread.finished_signal.connect(self._on_readme_finished)
        self.readme_thread.start()

    def _on_readme_finished(self, success, msg):
        self.readme_log.setText(msg)
        self.status_bar.showMessage(msg)
        if success:
            QMessageBox.information(self, tr("dialog.done"), msg)

    # -------- 标签页: 设置 --------
    def setup_tab_settings(self, parent):
        layout = QVBoxLayout(parent)

        form = QFormLayout()
        self.settings_sid_edit = QLineEdit(self.student_id)
        self.settings_sid_edit.setPlaceholderText(tr("settings.student_id.placeholder"))
        self.settings_sid_label = QLabel(tr("settings.student_id"))
        form.addRow(self.settings_sid_label, self.settings_sid_edit)

        layout.addLayout(form)

        self.settings_save_btn = QPushButton(tr("settings.save"))
        self.settings_save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self.settings_save_btn)

        self.settings_log = QLabel("")
        layout.addWidget(self.settings_log)

        layout.addStretch()

    def _save_settings(self):
        sid = self.settings_sid_edit.text().strip()
        if not sid:
            QMessageBox.warning(self, tr("dialog.warning"), tr("settings.warning.no_id"))
            return
        self.student_id = sid
        save_config(sid, _current_lang)
        # 同步到 .gitignore 标签页
        self.git_sid_edit.setText(sid)
        self.settings_log.setText(tr("settings.saved") + sid)
        self.status_bar.showMessage(tr("settings.saved") + sid)

    def load_settings(self):
        # 加载后同步到各标签页
        self.git_sid_edit.setText(self.student_id)


# =========================
# 入口
# =========================

def main():
    # 先加载翻译
    load_translations()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LabExpAssistant()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
