import os
import sys
import mysql.connector
from PIL import Image, ImageDraw, ImageFont

# 导入配置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from backend.config.settings import DATABASE_CONFIG
    from backend.common import UPLOAD_DIR  # 复用 common 里的路径配置
except ImportError:
    print("⚠️ 无法导入配置，使用默认值")
    DATABASE_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': 'YOUR_PASSWORD',  # ⚠️ 如果密码错误请修改这里
        'database': 'grid_forecast_system', 'charset': 'utf8mb4'
    }
    UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')


def fix_avatars():
    print("🚑 开始修复头像缺失与路径错误问题...")

    # 1. 确保 uploads 文件夹存在
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        print(f"📁 创建目录: {UPLOAD_DIR}")

    # 2. 检查并生成默认头像文件
    default_avatar_path = os.path.join(UPLOAD_DIR, "default_avatar.png")
    if not os.path.exists(default_avatar_path):
        print("🎨 正在生成默认头像 (default_avatar.png)...")
        try:
            # 生成一个 200x200 的灰色图片，中间写个 "User"
            img = Image.new('RGB', (200, 200), color=(112, 128, 144))  # SlateGray
            d = ImageDraw.Draw(img)
            # 画个简单的圆或者文字
            d.ellipse([50, 50, 150, 150], fill=(200, 200, 200))
            img.save(default_avatar_path)
            print("✅ 默认头像已生成！")
        except Exception as e:
            print(f"⚠️ 无法生成图片 (需要 pip install pillow): {e}")
    else:
        print("✅ 默认头像文件已存在。")

    # 3. 修复数据库里的路径
    print("🔧 正在修正数据库中的头像路径...")
    conn = None
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 将所有 'default_avatar.png' (不带路径) 修正为 '/uploads/default_avatar.png'
        sql_fix_path = """
            UPDATE sys_user 
            SET avatar = '/uploads/default_avatar.png' 
            WHERE avatar = 'default_avatar.png' 
               OR avatar IS NULL 
               OR avatar = ''
               OR avatar = '/default_avatar.png'
        """
        cursor.execute(sql_fix_path)
        print(f"   ✅ 已修正 {cursor.rowcount} 个用户的头像路径")

        conn.commit()
        print("🎉 修复完成！现在刷新网页，404 错误应该消失了。")

    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    fix_avatars()