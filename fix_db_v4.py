import mysql.connector
import json

try:
    from backend.config.settings import DATABASE_CONFIG
except ImportError:
    DATABASE_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': 'YOUR_PASSWORD', 'database': 'grid_forecast_system', 'charset': 'utf8mb4'
    }


def fix_database_v4():
    print("🚀 开始执行 V4 数据库升级 (用户画像完善)...")
    conn = None
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 1. 扩充 sys_user 表
        print("🛠️ 正在升级 sys_user 表结构...")
        alter_statements = [
            "ADD COLUMN gender VARCHAR(10) DEFAULT '未知'",
            "ADD COLUMN employee_id VARCHAR(50) COMMENT '工号'",
            "ADD COLUMN address VARCHAR(255) COMMENT '联系地址'",
            "ADD COLUMN avatar VARCHAR(255) DEFAULT 'default_avatar.png'",
            "ADD COLUMN last_login_ip VARCHAR(50)",
            "ADD COLUMN preferences JSON COMMENT '系统偏好设置'",
            "ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE COMMENT '双因素认证'"
        ]

        for stmt in alter_statements:
            try:
                cursor.execute(f"ALTER TABLE sys_user {stmt}")
            except mysql.connector.errors.ProgrammingError:
                pass  # 忽略已存在的字段错误

        # 2. 确保有演示用的访问日志表
        print("🛠️ 检查日志表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sys_access_log (
                log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT,
                ip_address VARCHAR(50),
                action VARCHAR(50),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. 注入一些演示日志
        print("💉 注入演示日志数据...")
        cursor.execute(
            "INSERT INTO sys_access_log (user_id, ip_address, action, status) VALUES (1, '192.168.1.101', 'LOGIN', 'SUCCESS')")
        cursor.execute(
            "INSERT INTO sys_access_log (user_id, ip_address, action, status) VALUES (1, '10.0.0.5', 'UPDATE_PROFILE', 'SUCCESS')")

        conn.commit()
        print("✅ V4 数据库升级完成！")

    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    fix_database_v4()