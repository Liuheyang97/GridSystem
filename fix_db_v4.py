import mysql.connector
import sys
import os

# 尝试导入配置
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from backend.config.settings import DATABASE_CONFIG
except ImportError:
    print("⚠️ 无法自动导入配置，使用默认配置 (请确认密码是否正确)")
    DATABASE_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': 'YOUR_PASSWORD',  # ⚠️ 如果报错，请手动修改这里的密码
        'database': 'grid_forecast_system', 'charset': 'utf8mb4'
    }


def reset_all_2fa():
    print("🔄 正在暴力清除所有用户的 2FA 设置...")
    conn = None
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 1. 清空 mfa_secret (密钥) 和 mfa_enabled (开关状态)
        # 2. 同时强制修复 preferences 为 NULL 的情况，防止黑屏
        sql_reset = "UPDATE sys_user SET mfa_secret = NULL, mfa_enabled = 0"
        cursor.execute(sql_reset)
        rows_2fa = cursor.rowcount

        print(f"✅ 2FA 重置成功！影响用户数: {rows_2fa}")

        # 3. 顺便修复可能导致黑屏的脏数据 (preferences)
        print("🧹 正在清理脏数据 (修复黑屏隐患)...")
        # 如果 preferences 是空的，给它设为默认值
        import json
        default_pref = json.dumps({"alert_method": "site"})
        cursor.execute("UPDATE sys_user SET preferences=%s WHERE preferences IS NULL OR preferences=''",
                       (default_pref,))

        conn.commit()
        print("🎉 数据库清理完毕！现在所有人都回到了初始状态（无 2FA）。")

    except Exception as e:
        print(f"❌ 操作失败: {e}")
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    reset_all_2fa()