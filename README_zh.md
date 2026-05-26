<div align="center">

<span style="font-size: 3em;"><strong>LEA ---- Lab Experiment Assistant</strong></span>

<span style="font-size: 1.8em;"><strong>实验助手</strong></span>

<span style="font-size: 1.5em;">中文 | [日本語](./README_ja.md) | [English](./README.md)</span>

</div>


# 功能
- 实验项目初始化
  - 生成实验项目的基本目录结构和必要文件
  - 生成常见于实验无关需忽视的文件列表（如`.DS_Store`、`.code-workspace`, 本项目生成的用户文件等）

> [!NOTE]
> `user_data/` 目录已在 `.gitignore` 中，不会被 Git 追踪。
> 请自行创建该目录并放入必要的数据文件。

- 生成实验报告模板
  - 根据预设的模板生成实验报告的初始版本
- 清理LaTeX编译生成的临时文件
  - 删除LaTeX编译过程中产生的辅助文件（如`.aux`、`.log`、`.toc`等）

- 报告文件格式转换
  - Beamer 生成文件转换为 Power Point 等可格式

- 缓存文件清理
  - 清理LaTeX编译生成的临时文件
  - 清理Python运行生成的临时文件
  - 清理LaTeX输出目录（可选）


