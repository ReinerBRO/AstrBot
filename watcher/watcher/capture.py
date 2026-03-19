from io import BytesIO

from PIL import Image, ImageGrab

try:
    from mss import mss
except Exception:
    mss = None


def get_available_monitors() -> list[dict]:
    """获取所有可用显示器的信息"""
    try:
        if mss is not None:
            with mss() as sct:
                monitors = []
                # monitors[0] 是虚拟的全屏幕，从 monitors[1] 开始是实际显示器
                for i in range(1, len(sct.monitors)):
                    mon = sct.monitors[i]
                    monitors.append(
                        {
                            "index": i,
                            "width": mon["width"],
                            "height": mon["height"],
                            "left": mon["left"],
                            "top": mon["top"],
                        }
                    )
                return monitors
        # 如果没有 mss，返回单个默认显示器
        return [{"index": 1, "width": 1920, "height": 1080, "left": 0, "top": 0}]
    except Exception:
        return [{"index": 1, "width": 1920, "height": 1080, "left": 0, "top": 0}]


def capture_monitor(monitor_index: int = 1) -> Image.Image:
    """捕获指定显示器的截图"""
    try:
        if mss is not None:
            with mss() as sct:
                # 确保索引有效
                if monitor_index < 1 or monitor_index >= len(sct.monitors):
                    monitor_index = 1
                monitor = sct.monitors[monitor_index]
                shot = sct.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.rgb)

        image = ImageGrab.grab()
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except Exception as exc:
        raise RuntimeError(
            "截图失败。请检查屏幕录制权限，或安装 mss: pip install mss"
        ) from exc


def capture_screen(monitor_index: int = 1) -> Image.Image:
    """捕获屏幕截图（兼容旧接口）"""
    return capture_monitor(monitor_index)


def to_jpeg_bytes(
    image: Image.Image, quality: int = 70, resize_width: int = 0
) -> bytes:
    if resize_width and image.width > resize_width:
        ratio = resize_width / image.width
        new_size = (resize_width, int(image.height * ratio))
        image = image.resize(new_size)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()
