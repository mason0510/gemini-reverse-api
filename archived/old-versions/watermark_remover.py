"""
Gemini Watermark Remover - Python Implementation
功能: 去除Gemini生成的图片水印
关键词: gemini, watermark, removal, alpha, reverse-blending
"""
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Optional
from pathlib import Path
import io

# 常量定义
ALPHA_THRESHOLD = 0.002  # 忽略极小Alpha值（噪声）
MAX_ALPHA = 0.99         # 避免除零
LOGO_VALUE = 255         # 白色水印颜色值


class WatermarkRemover:
    """Gemini水印去除器"""

    def __init__(self, asset_dir: Path = None):
        """
        初始化水印去除器

        Args:
            asset_dir: 资产文件目录，包含bg_48.png和bg_96.png
        """
        self.asset_dir = asset_dir or Path(__file__).parent
        self._alpha_maps = {}

    def detect_watermark_config(self, image_width: int, image_height: int) -> Dict[str, int]:
        """
        根据图片尺寸检测水印配置

        Gemini水印规则:
        - 宽高均>1024: 使用96×96水印，边距64px
        - 其他: 使用48×48水印，边距32px
        """
        if image_width > 1024 and image_height > 1024:
            return {
                "logoSize": 96,
                "marginRight": 64,
                "marginBottom": 64
            }
        else:
            return {
                "logoSize": 48,
                "marginRight": 32,
                "marginBottom": 32
            }

    def calculate_watermark_position(self, image_width: int, image_height: int, config: Dict) -> Dict[str, int]:
        """计算水印在图片中的位置"""
        logo_size = config["logoSize"]
        margin_right = config["marginRight"]
        margin_bottom = config["marginBottom"]

        return {
            "x": image_width - margin_right - logo_size,
            "y": image_height - margin_bottom - logo_size,
            "width": logo_size,
            "height": logo_size
        }

    def load_alpha_map(self, size: int) -> np.ndarray:
        """
        从资产文件加载Alpha映射

        Args:
            size: 水印尺寸（48或96）

        Returns:
            Float32Array，值范围[0.0, 1.0]
        """
        if size in self._alpha_maps:
            return self._alpha_maps[size]

        bg_path = self.asset_dir / f"bg_{size}.png"
        if not bg_path.exists():
            raise FileNotFoundError(f"Alpha map asset not found: {bg_path}")

        bg_img = Image.open(bg_path).convert("RGBA")
        bg_array = np.array(bg_img)

        alpha_map = np.zeros((size, size), dtype=np.float32)

        for i in range(size):
            for j in range(size):
                r, g, b, _ = bg_array[i, j]
                max_channel = max(r, g, b)
                alpha_map[i, j] = max_channel / 255.0

        self._alpha_maps[size] = alpha_map
        return alpha_map

    def remove_watermark(self, image_array: np.ndarray) -> np.ndarray:
        """
        从图片中去除水印（原地修改）

        算法原理:
        Gemini添加水印: watermarked = α × logo + (1 - α) × original
        反向求解: original = (watermarked - α × logo) / (1 - α)

        Args:
            image_array: PIL图片数组，会被原地修改

        Returns:
            处理后的图片数组
        """
        height, width = image_array.shape[:2]

        # 检测水印配置
        config = self.detect_watermark_config(width, height)
        position = self.calculate_watermark_position(width, height, config)

        # 获取Alpha映射
        alpha_map = self.load_alpha_map(config["logoSize"])

        # 处理水印区域的每个像素
        x, y, wm_width, wm_height = position["x"], position["y"], position["width"], position["height"]

        for row in range(wm_height):
            for col in range(wm_width):
                img_y, img_x = y + row, x + col

                # 边界检查
                if img_y >= height or img_x >= width:
                    continue

                alpha = alpha_map[row, col]

                # 跳过极小Alpha值
                if alpha < ALPHA_THRESHOLD:
                    continue

                # 限制Alpha值避免除零
                alpha = min(alpha, MAX_ALPHA)
                one_minus_alpha = 1.0 - alpha

                # 对RGB三个通道应用反向Alpha混合
                for c in range(3):
                    watermarked = image_array[img_y, img_x, c]
                    original = (watermarked - alpha * LOGO_VALUE) / one_minus_alpha
                    image_array[img_y, img_x, c] = np.clip(np.round(original), 0, 255)

        return image_array

    def remove_from_bytes(self, image_bytes: bytes) -> bytes:
        """
        从字节流中去除水印

        Args:
            image_bytes: 图片字节流

        Returns:
            处理后的图片字节流（PNG格式）
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(img)

            processed_array = self.remove_watermark(image_array)
            processed_img = Image.fromarray(processed_array)

            output = io.BytesIO()
            processed_img.save(output, format="PNG")
            return output.getvalue()

        except Exception as e:
            print(f"Watermark removal failed: {e}")
            return image_bytes  # 失败时返回原图

    def remove_from_base64(self, base64_data: str) -> str:
        """
        从Base64数据中去除水印

        Args:
            base64_data: Base64编码的图片数据

        Returns:
            处理后的Base64数据（PNG格式）
        """
        import base64 as b64

        # 移除data URL前缀
        if base64_data.startswith("data:"):
            base64_data = base64_data.split(",", 1)[1]

        image_bytes = b64.b64decode(base64_data)
        processed_bytes = self.remove_from_bytes(image_bytes)
        return f"data:image/png;base64,{b64.b64encode(processed_bytes).decode()}"

    def get_watermark_info(self, image_width: int, image_height: int) -> Dict:
        """获取水印信息（用于显示）"""
        config = self.detect_watermark_config(image_width, image_height)
        position = self.calculate_watermark_position(image_width, image_height, config)

        return {
            "size": config["logoSize"],
            "position": position,
            "config": config
        }


# 全局单例
_remover_instance = None


def get_watermark_remover() -> WatermarkRemover:
    """获取全局水印去除器单例"""
    global _remover_instance
    if _remover_instance is None:
        _remover_instance = WatermarkRemover()
    return _remover_instance
