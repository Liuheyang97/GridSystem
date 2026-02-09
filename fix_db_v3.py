import mysql.connector
import json
import sys
import os

# 导入配置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from backend.config.settings import DATABASE_CONFIG
except ImportError:
    print("⚠️ 使用默认配置")
    DATABASE_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': 'YOUR_PASSWORD',  # ⚠️ 如果密码不是默认的，请修改这里
        'database': 'grid_forecast_system', 'charset': 'utf8mb4'
    }


def fix_corruption():
    print("🚑 开始修复黑屏数据与 2FA 状态...")
    conn = None
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 1. 暴力修复 preferences (解决黑屏核心)
        # 把所有看起来像 {"0": "{"... 这种坏掉的数据全部重置
        print("🧹 清洗损坏的偏好设置...")
        default_pref = json.dumps({"alert_method": "site"})

        # 查找坏数据：以 {"0": 开头的通常是 Python 字典被误转字符串的结果
        sql_fix_pref = """
            UPDATE sys_user 
            SET preferences = %s 
            WHERE preferences LIKE '%%"0":%%' OR preferences IS NULL
        """
        cursor.execute(sql_fix_pref, (default_pref,))
        print(f"   ✅ 已重置 {cursor.rowcount} 条损坏的用户配置")

        # 2. 同步 2FA 状态
        # 你的数据库里 superadmin 有密钥(mfa_secret)，但开关(mfa_enabled)是 0
        print("🔧 同步 2FA 开关状态...")
        cursor.execute("""
            UPDATE sys_user 
            SET mfa_enabled = 1 
            WHERE mfa_secret IS NOT NULL AND mfa_secret != '' AND length(mfa_secret) > 10
        """)
        print(f"   ✅ 已强制开启 {cursor.rowcount} 个用户的 2FA 开关")

        conn.commit()
        print("🎉 修复完成！黑屏问题应该已解决。")

    except Exception as e:
        print(f"❌ 修复失败: {e}")
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    fix_corruption()