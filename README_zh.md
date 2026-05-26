中文 | [日本語](./README_ja.md) | [English](./README.md)

<div align="center">

# LEA — Lab Experiment Assistant（实验助手）

**面向物理/化学实验全流程的桌面 GUI 工具**

项目初始化 → 数据分析 → 可视化 → 格式转换 → 缓存清理

</div>

> [!NOTE]
> `user_data/` 目录已在 `.gitignore` 中，不会被 Git 追踪。
> 请自行创建该目录并放入必要的用户数据文件。

## 功能

### Project — 一键创建项目骨架
从模板（Default / Scientific / Custom）生成标准实验目录结构。
可选生成 `.gitignore` 和初始化 git 仓库。

### Data — CSV 数据分析与可视化 **[核心]**
- 加载 CSV 文件，支持自定义编码、分隔符、表头行
- 表格预览数据
- **散点图** 和 **直方图**（matplotlib 嵌入式图形）
- **线性拟合**：通过 `scipy.optimize.curve_fit` 输出斜率/截距的不确定度和 R²
- 拟合结果复制为 LaTeX 公式 / 导出为 PNG

### Convertor — Beamer PDF 转 PPTX
- 将 PDF 每页按可调 DPI（100–400）渲染为高分辨率 PNG 嵌入 `.pptx`
- **PDF 页面编辑器**：按页码范围删除、提取或拆分（支持 `1,3,5-8,10-` 格式）

### Cache Cleaner — 缓存清理
- LaTeX：清理输出 PDF 和辅助文件（`.aux`、`.log`、`.toc`、`.out` 等）
- Python：递归删除 `__pycache__/`、`*.pyc`、`*.pyo`

### Settings — 设置
- **实时语言切换** — 中文 / English / 日本語（181 条翻译键）
- 字体与字号、默认 DPI / 输出格式、模板所需学号

## 安装

```bash
# 克隆仓库
git clone https://github.com/Didi-Huang/lea.git
cd lea

# 创建虚拟环境并安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install PySide6 pymupdf python-pptx pandas matplotlib scipy numpy
```

## 使用

```bash
python main.py
```

1. **Project** 标签页 — 输入实验名称 → 选择父目录和模板 → 点击「创建」
2. **Data** 标签页 — 浏览 CSV → 「加载」→ 选择 X/Y 列 → 「散点图」/「直方图」/「线性拟合」
3. **Convertor** 标签页 — 选择源 PDF、输出文件夹、DPI → 点击「转换」
4. **Cache Cleaner** — 点击 LaTeX 或 Python 的「自动清理」
5. **Settings** — 切换语言、保存偏好设置

## 项目结构

```
lea/
├── main.py                  # PySide6 GUI 入口
├── src/
│   ├── convertor.py         # Beamer PDF → PPTX 转换
│   ├── pdf_editor.py        # PDF 页面删除 / 提取 / 拆分
│   └── project_builder.py   # 实验目录结构生成
├── ui/
│   └── main_window.ui       # Qt Designer 界面布局
├── locales/
│   ├── en.json / zh_CN.json / ja.json   # 国际化（各 181 键）
├── templates/
│   ├── structures/          # 项目目录模板 (JSON)
│   ├── gitignore/           # .gitignore 模板
│   └── readme/              # README 模板
├── fonts/                   # HarmonyOS Sans 字体文件
└── user_data/               # 用户设置、历史记录、自定义模板（已 gitignore）
```

## 依赖

| 包 | 用途 |
|---|------|
| PySide6 | GUI 框架 |
| PyMuPDF (`fitz`) | PDF 渲染与页面操作 |
| python-pptx | PPTX 生成 |
| pandas | CSV 数据加载 |
| matplotlib | 绘图（散点图、直方图、拟合曲线） |
| scipy | 曲线拟合 |
| numpy | 数值数组 |

## 许可证

MIT
