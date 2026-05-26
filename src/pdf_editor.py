"""PDF 页面编辑器 — 删除 / 提取 / 拆分指定页面。

基于 PyMuPDF (fitz) 实现，不依赖外部工具（如 pdftk、qpdf）。
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PdfInfo:
    """PDF 文件基本信息。"""
    total_pages: int
    width_points: float | None = None
    height_points: float | None = None


@dataclass
class EditResult:
    """页面编辑操作结果。"""
    success: bool
    output_path: str | None = None
    page_count: int = 0
    error: str | None = None


class PdfPageEditor:
    """PDF 页面编辑工具。

    提供删除页面、提取页面、按范围拆分的功能。
    所有方法都基于 PyMuPDF 的 select/delete_page 实现。
    """

    @staticmethod
    def get_info(path: str) -> PdfInfo:
        """获取 PDF 基本信息：总页数、页面尺寸。

        Args:
            path: PDF 文件路径。

        Returns:
            PdfInfo 包含总页数和首页尺寸（points）。
        """
        import fitz
        doc = fitz.open(path)
        total = doc.page_count
        info = PdfInfo(total_pages=total)
        if total > 0:
            rect = doc[0].rect
            info.width_points = rect.width
            info.height_points = rect.height
        doc.close()
        return info

    @staticmethod
    def parse_page_spec(spec: str, total_pages: int) -> list[int]:
        """解析页面范围字符串，返回 1-based 页码列表。

        支持的格式:
          - 单页:         "3"          → [3]
          - 范围:         "5-8"        → [5,6,7,8]
          - 逗号组合:     "1,3,5-7"    → [1,3,5,6,7]
          - 末尾省略:     "5-"         → [5,6,...,total]
          - 开头省略:     "-3"         → [1,2,3]

        Args:
            spec: 页面范围字符串。
            total_pages: PDF 总页数，用于解析省略号范围。

        Returns:
            排序去重后的 1-based 页码列表。

        Raises:
            ValueError: 格式无法解析或页码超出范围。
        """
        result: set[int] = set()
        # 按逗号拆分
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        if not parts:
            raise ValueError("页面范围不能为空")

        for part in parts:
            # 匹配 "start-end" 或 "start-" 或 "-end" 或 单数字
            m = re.fullmatch(r"(\d+)?\s*-\s*(\d+)?", part)
            if m:
                start_str, end_str = m.group(1), m.group(2)
                if start_str and not end_str:
                    # "5-"
                    start = int(start_str)
                    end = total_pages
                elif not start_str and end_str:
                    # "-3"
                    start = 1
                    end = int(end_str)
                elif start_str and end_str:
                    # "5-8"
                    start, end = int(start_str), int(end_str)
                else:
                    raise ValueError(f"无法解析范围: {part!r}")

                if start < 1 or end > total_pages or start > end:
                    raise ValueError(
                        f"页码范围 {start}-{end} 超出 PDF 总页数 (1-{total_pages})"
                    )
                result.update(range(start, end + 1))
            else:
                # 单数字
                try:
                    page = int(part)
                except ValueError:
                    raise ValueError(f"无法解析页码: {part!r}")
                if page < 1 or page > total_pages:
                    raise ValueError(
                        f"页码 {page} 超出范围 (1-{total_pages})"
                    )
                result.add(page)

        return sorted(result)

    @staticmethod
    def delete_pages(
        source: str,
        pages_to_delete: list[int],
        output_path: str,
    ) -> EditResult:
        """删除指定页面，输出新 PDF。

        原 PDF 不被修改，生成一个不含目标页面的新文件。

        Args:
            source: 源 PDF 路径。
            pages_to_delete: 要删除的 1-based 页码列表。
            output_path: 输出 PDF 路径。

        Returns:
            EditResult 包含操作结果。
        """
        import fitz
        try:
            source_path = Path(source)
            if not source_path.exists():
                return EditResult(success=False, error=f"文件不存在: {source}")

            doc = fitz.open(str(source_path))
            total = doc.page_count

            # 校验
            for p in pages_to_delete:
                if p < 1 or p > total:
                    doc.close()
                    return EditResult(
                        success=False,
                        error=f"页码 {p} 超出范围 (1-{total})",
                    )

            # 选择保留的页面（0-based）
            delete_set = {p - 1 for p in pages_to_delete}  # 转 0-based
            keep_indices = [i for i in range(total) if i not in delete_set]

            if len(keep_indices) == 0:
                doc.close()
                return EditResult(success=False, error="删除后 PDF 为空")

            doc.select(keep_indices)
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path_obj))
            doc.close()

            removed = total - len(keep_indices)
            logger.info("PDF 页面删除完成: %d → %d 页 (删除 %d 页)",
                         total, len(keep_indices), removed)

            return EditResult(
                success=True,
                output_path=str(output_path_obj),
                page_count=len(keep_indices),
            )

        except Exception:
            logger.exception("PDF 页面删除失败")
            return EditResult(success=False, error="删除失败，请查看日志")

    @staticmethod
    def extract_pages(
        source: str,
        pages_to_extract: list[int],
        output_path: str,
    ) -> EditResult:
        """提取指定页面，生成新 PDF。

        Args:
            source: 源 PDF 路径。
            pages_to_extract: 要提取的 1-based 页码列表。
            output_path: 输出 PDF 路径。

        Returns:
            EditResult 包含操作结果。
        """
        import fitz
        try:
            source_path = Path(source)
            if not source_path.exists():
                return EditResult(success=False, error=f"文件不存在: {source}")

            doc = fitz.open(str(source_path))
            total = doc.page_count

            for p in pages_to_extract:
                if p < 1 or p > total:
                    doc.close()
                    return EditResult(
                        success=False,
                        error=f"页码 {p} 超出范围 (1-{total})",
                    )

            # 0-based indices
            select_indices = [p - 1 for p in pages_to_extract]
            doc.select(select_indices)
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path_obj))
            doc.close()

            logger.info("PDF 页面提取完成: 提取 %d 页 → %s",
                         len(select_indices), output_path)

            return EditResult(
                success=True,
                output_path=str(output_path_obj),
                page_count=len(select_indices),
            )

        except Exception:
            logger.exception("PDF 页面提取失败")
            return EditResult(success=False, error="提取失败，请查看日志")
