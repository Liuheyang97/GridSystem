import mysql.connector
import sys

try:
    from backend.config.settings import DATABASE_CONFIG
except:
    DATABASE_CONFIG = {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'YOUR_PASSWORD',
                       'database': 'grid_forecast_system', 'charset': 'utf8mb4'}


def upgrade_db():
    print("🚀 V9.6 数据库升级中...")
    conn = mysql.connector.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    # 补全 sys_user 字段
    cols = [
        ("gender", "VARCHAR(10)"),
        ("employee_id", "VARCHAR(50)"),
        ("address", "VARCHAR(255)"),
        ("department", "VARCHAR(100)"),  # 新增
        ("avatar", "TEXT"),
        ("preferences", "JSON"),
        ("mfa_enabled", "BOOLEAN DEFAULT 0")
    ]
    for col, definition in cols:
        try:
            cur.execute(f"ALTER TABLE sys_user ADD COLUMN {col} {definition}")
            print(f"✅ 添加字段: {col}")
        except:
            pass

    conn.commit()
    conn.close()
    print("✨ 数据库就绪！请启动 main.py")


if __name__ == "__main__":
    upgrade_db()