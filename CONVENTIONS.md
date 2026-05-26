# LabExp-Assistant 编码约定

## 项目定位

GUI 桌面工具应用，非数据分析项目。用 PySide6 构建界面，后台用 PyMuPDF / python-pptx 等库处理 PDF 和 PPTX 文件。

## 1. 模块职责

```
src/           — 核心逻辑模块（无 UI 依赖）
ui/            — Qt Designer .ui 文件
templates/     — 实验项目模板
locales/       — 国际化资源
fonts/         — 字体文件
user_data/     — 用户数据（gitignore 中，不提交）
```

- **一个模块一个类**，类承载状态 + 多个方法。
- 纯工具函数用 `@staticmethod` 或独立函数。
- **UI 层不写业务逻辑**，业务逻辑层不直接引用 Qt 控件。
- 耗时操作（PDF 渲染、PPTX 生成）不在 UI 线程执行。

## 2. 编码规范

### 2.1 类型注解

- 函数参数和返回值必须写 type hints。
- 函数内部局部变量不写。
- 不使用 `Protocol`、`TypedDict` 等高级注解。

```python
def render_page(
    pdf_path: str,
    dpi: int = 200,
) -> bytes | None:
    ...
```

### 2.2 路径

统一 `pathlib.Path`，不用 `os.path`。

```python
from pathlib import Path
output_dir = Path("../output/")
output_dir.mkdir(parents=True, exist_ok=True)
```

### 2.3 日志

```python
import logging
logger = logging.getLogger(__name__)
```

- 核心逻辑用 `logger.info()` / `logger.warning()` / `logger.exception()`。
- UI 层捕获后通过日志控件（`QTextBrowser`）显示给用户。
- 不用 `print()`。

### 2.4 文档字符串

Google 风格，只用 `Args` / `Returns` / `Raises`。

```python
def convert_pdf_to_pptx(
    source: str,
    output_path: str,
    dpi: int = 250,
) -> dict:
    """将 Beamer PDF 每页渲染为位图并插入 PPTX。

    Args:
        source: 源 PDF 文件路径。
        output_path: 输出 PPTX 文件路径。
        dpi: 渲染 DPI，默认 250。

    Returns:
        {"success": True, "output_path": "..."} 或
        {"success": False, "error": "错误信息"}。
    """
```

### 2.5 命名

- 变量/函数全英文，注释中文。
- 不写懒缩写：`value` 不写 `val`，`bounds` 不写 `bnds`。
- 领域标准缩写保留：PDF, DPI, PPTX, RGB。
- 范围越小名字越短：循环 `i`/`j`/`k`，参数完整词，常量 `UPPER_SNAKE`。
- 常量定义在模块顶部。

### 2.6 数据容器

用 `@dataclass` 而非手写类。

```python
from dataclasses import dataclass

@dataclass
class ConversionResult:
    success: bool
    output_path: str | None = None
    error: str | None = None
```

### 2.7 错误处理

- 可恢复的异常 catch 并报告，不可恢复的让上层处理。
- 不在 `except` 里写 `pass`。
- 向用户展示友好错误信息，向日志输出详细栈信息。

```python
try:
    doc = fitz.open(str(self.source))
except fitz.FileDataError:
    logger.exception("无法打开 PDF")
    return {"success": False, "error": "无法打开 PDF 文件，可能已损坏"}
```

## 3. 函数/方法定义顺序

1. 构造方法 `__init__`
2. 公开方法（`run`, `convert` 等）
3. 内部方法（`_helper`）
4. 静态工具方法（`@staticmethod`）

## 4. DOM 控件命名

UI 文件中的 `objectName` 命名规则：

- 前缀表类型：`edit_`（输入框）、`btn_`（按钮）、`label_`（标签）、`combo_`（下拉框）、`cb_`（复选框）、`tb_`（日志框）、`progress_`（进度条）
- 中间表所属模块：`btp_`（Beamer to PPT）、`pdf_edit_`（PDF 编辑器）
- 后缀表用途：`source`、`output`、`format`、`name`

例：`btn_btp_io_source`、`edit_pdf_edit_range`、`progress_btp`

## 5. Agent 行为规则

### 禁止

1. 不要反复读同一个文件 — 一次读入，传引用。
2. 不要重写已有函数 — 先查 `src/` 和现有代码。
3. 不要留空壳 — 不确定的功能不提交，但开发过程中逐步完善是正常的。
4. 不要过度设计边缘场景 — 工具应用聚焦主要使用路径。

### 应当

- 跨项目通用模式写入 `didi/ideas/`（引用 physics-lab 工具库）。
- 对 PDF / PPTX 这类外部文件操作做基本的损坏/空文件检查。
- 修改 UI 前先读 `.ui` 文件确认已有控件。
