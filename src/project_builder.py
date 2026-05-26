"""Project Builder — 实验项目目录结构一键创建。

从 templates/structures/*.json 读取结构模板，
创建对应目录和文件，可选生成 .gitignore 和初始化 git 仓库。
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TEMPLATES_DIR: Path = Path(__file__).resolve().parent.parent / "templates"
STRUCTURES_DIR: Path = TEMPLATES_DIR / "structures"
GITIGNORE_DIR: Path = TEMPLATES_DIR / "gitignore"

TEMPLATE_MAP: dict[str, str] = {
    "Default": "default.json",
    "Scientific": "scientific.json",
    "Custom": "custom.json",
}


@dataclass
class BuildResult:
    """创建结果。"""

    success: bool
    project_path: str | None = None
    files_created: list[str] = field(default_factory=list)
    error: str | None = None


class ProjectBuilder:
    """实验项目目录结构创建器。

    从 JSON 模板读取目录结构，在目标路径下创建整个实验项目骨架。
    支持变量替换（如 {experiment_name}）。

    Attributes:
        experiment_name: 实验名称，用于变量替换。
        target_parent: 目标父目录路径。
        template_key: 模板标识（Default/Scientific/Custom）。
        generate_gitignore: 是否生成 .gitignore。
        init_repo: 是否初始化 git 仓库。
        overwrite: 是否覆盖已存在目录。
    """

    def __init__(
        self,
        experiment_name: str,
        target_parent: str,
        template_key: str = "Default",
        generate_gitignore: bool = False,
        init_repo: bool = False,
        overwrite: bool = False,
    ):
        self.experiment_name = experiment_name
        self.target_parent = Path(target_parent)
        self.template_key = template_key
        self.generate_gitignore = generate_gitignore
        self.init_repo = init_repo
        self.overwrite = overwrite

    def run(self) -> BuildResult:
        """执行创建流程。"""
        try:
            return self._build()
        except Exception as exc:
            logger.exception("项目创建异常")
            return BuildResult(success=False, error=str(exc))

    # ── 内部实现 ─────────────────────────────────────────

    def _build(self) -> BuildResult:
        """创建核心逻辑。"""
        project_path = self.target_parent / self.experiment_name

        # 检查目录是否已存在
        if project_path.exists():
            if not self.overwrite:
                return BuildResult(
                    success=False,
                    error=f"目录已存在: {project_path}",
                )
            logger.warning("覆盖已存在目录: %s", project_path)

        # 加载模板
        template = self._load_template()
        if template is None:
            return BuildResult(
                success=False,
                error=f"找不到模板: {self.template_key}",
            )

        structure: dict[str, Any] = template.get("structure", {})
        files_created: list[str] = []

        # 创建目录结构
        self._create_node(project_path, structure, files_created, "")

        # 生成 .gitignore
        if self.generate_gitignore:
            self._write_gitignore(project_path, files_created)

        # 初始化 git 仓库
        if self.init_repo:
            self._init_git(project_path)

        return BuildResult(
            success=True,
            project_path=str(project_path),
            files_created=files_created,
        )

    def _load_template(self) -> dict[str, Any] | None:
        """加载结构模板 JSON。"""
        filename = TEMPLATE_MAP.get(self.template_key)
        if filename is None:
            return None

        # Custom 模板从 user_data 加载
        if self.template_key == "Custom":
            custom_path = (
                Path(__file__).resolve().parent.parent
                / "user_data"
                / "custom_templates"
                / "structure.json"
            )
            if custom_path.exists():
                return json.loads(custom_path.read_text("utf-8"))

        path = STRUCTURES_DIR / filename
        if not path.exists():
            return None

        return json.loads(path.read_text("utf-8"))

    def _create_node(
        self,
        base: Path,
        node: dict[str, Any],
        files_created: list[str],
        prefix: str,
    ) -> None:
        """递归创建目录和文件。

        JSON 结构中：
        - key 为目录名/文件名
        - value 为 None → 创建空目录
        - value 为 str → 创建文件（内容为 value）
        - value 为 dict → 递归创建子目录
        """
        for name, content in node.items():
            # 变量替换
            resolved_name = name.replace("{experiment_name}", self.experiment_name)
            rel_path = f"{prefix}{resolved_name}"

            if content is None:
                # 空目录
                dir_path = base / resolved_name
                dir_path.mkdir(parents=True, exist_ok=True)
                files_created.append(f"{rel_path}/")
            elif isinstance(content, str):
                # 文件
                file_path = base / resolved_name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                files_created.append(rel_path)
                resolved_content = content.replace("{experiment_name}", self.experiment_name)
                file_path.write_text(resolved_content, "utf-8")
            elif isinstance(content, dict):
                # 子目录
                subdir = base / resolved_name
                subdir.mkdir(parents=True, exist_ok=True)
                files_created.append(f"{rel_path}/")
                self._create_node(subdir, content, files_created, f"{rel_path}/")

    def _write_gitignore(self, project_path: Path, files_created: list[str]) -> None:
        """生成 .gitignore 文件。"""
        # 优先用 Python 模板
        tmpl_path = GITIGNORE_DIR / "python.tmpl"
        if not tmpl_path.exists():
            tmpl_path = GITIGNORE_DIR / "default.tmpl"

        if tmpl_path.exists():
            content = tmpl_path.read_text("utf-8")
            # 可选的学号变量替换（从 settings 读取，此处用空字符串）
            content = content.replace("{{ student_id }}", "")
            (project_path / ".gitignore").write_text(content, "utf-8")
            files_created.append(".gitignore")

    @staticmethod
    def _init_git(project_path: Path) -> None:
        """初始化 git 仓库。"""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(project_path),
                capture_output=True,
                check=True,
            )
            logger.info("git init: %s", project_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("git init 失败: %s", exc)
