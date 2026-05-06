"""PDF → PPT / PPTX 转换逻辑（占位）"""
from pathlib import Path

class BtpConvertor:
    def __init__(self, source: str, output_folder: str,
                 output_format: str, custom_name: str = ""):
        self.source = Path(source)
        self.output_folder = Path(output_folder)
        self.output_format = output_format      # "PDF to PPTX" 或 "PDF to PPT"
        self.custom_name = custom_name

    def run(self) -> dict:
        """
        模拟转换过程，返回结果字典。
        后续替换为真正的 PDF 解析 + python-pptx 生成逻辑。
        """
        try:
            # 模拟耗时
            import time
            time.sleep(1)

            # 确定输出文件名
            if self.custom_name:
                ext = ".pptx" if "PPTX" in self.output_format else ".ppt"
                out_name = self.custom_name + ext
            else:
                stem = self.source.stem
                ext = ".pptx" if "PPTX" in self.output_format else ".ppt"
                out_name = f"{stem}_converted{ext}"

            output_path = self.output_folder / out_name

            # 模拟输出文件（实际写入空文件测试）
            output_path.touch(exist_ok=True)

            return {"success": True, "output_path": str(output_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}