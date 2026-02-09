import os
from PIL import Image, ImageDraw, ImageFont
import math

# 确保上传目录存在
UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

TARGET_PATH = os.path.join(UPLOAD_DIR, "default_avatar.png")


def create_tech_avatar():
    print("🎨 正在绘制GridMaster专属科技感默认头像...")
    # 1. 画布配置 (200x200, 深色背景)
    size = 200
    bg_color = '#0b1121'  # 与网页背景一致的深蓝
    primary_color = '#3b82f6'  # 蓝色主调
    accent_color = '#00f7ff'  # 青色高光 (发光感)

    img = Image.new('RGB', (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)

    center = size // 2

    # 2. 绘制背景网格和电路纹理
    # 画一些微妙的六边形网格背景
    for i in range(0, size, 20):
        draw.line([(i, 0), (i, size)], fill='#1e293b', width=1)
        draw.line([(0, i), (size, i)], fill='#1e293b', width=1)

    # 3. 绘制外圈能量环
    # 画几个同心圆，模拟能量场
    draw.ellipse([20, 20, 180, 180], outline=primary_color, width=2)
    draw.ellipse([30, 30, 170, 170], outline='#1e3a8a', width=1)

    # 4. 绘制抽象的用户半身像 (用几何图形表示科技感)
    # 头部 (圆形)
    head_radius = 35
    draw.ellipse([center - head_radius, 40, center + head_radius, 40 + head_radius * 2], fill=primary_color)
    # 头部高光 (增加立体感)
    draw.ellipse([center - head_radius + 10, 50, center - head_radius + 25, 65], fill=accent_color)

    # 身体 (梯形/弧形)
    body_top = 120
    draw.pieslice([40, body_top - 60, 160, body_top + 100], 180, 360, fill=primary_color)

    # 5. 添加“电路连接线” (核心科技感来源)
    # 从头部中心向下连接
    draw.line([center, 110, center, 180], fill=accent_color, width=3)
    # 向两侧分叉
    draw.line([center, 140, 60, 170], fill=accent_color, width=2)
    draw.line([center, 140, 140, 170], fill=accent_color, width=2)

    # 在连接点画上发光的小圆点
    nodes = [(center, 110), (center, 140), (center, 180), (60, 170), (140, 170)]
    for nx, ny in nodes:
        draw.ellipse([nx - 4, ny - 4, nx + 4, ny + 4], fill=accent_color)

    # 6. 保存
    img.save(TARGET_PATH, 'PNG')
    print(f"✨ 专属头像已生成并保存至: {TARGET_PATH}")
    print("快去刷新网页看看效果吧！")


if __name__ == "__main__":
    create_tech_avatar()