import mysql.connector
import json
from datetime import datetime, timedelta

try:
    from backend.config.settings import DATABASE_CONFIG
except ImportError:
    # 你的数据库密码
    DATABASE_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': 'YOUR_PASSWORD', 'database': 'grid_forecast_system', 'charset': 'utf8mb4'
    }


def fix_database_v3():
    print("🚀 开始执行 V3 数据库升级程序 (支持用户隔离)...")
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 1. 重建预测表，增加 user_id 字段
        print("🛠️ 重构 prediction_result 表...")
        cursor.execute("DROP TABLE IF EXISTS prediction_result")

        sql_prediction = """
        CREATE TABLE prediction_result (
            result_id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL COMMENT '数据归属用户ID',
            bus_id BIGINT NOT NULL,
            predict_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            forecast_start_time TIMESTAMP NULL DEFAULT NULL,
            pred_value DECIMAL(10, 2),
            lower_bound DECIMAL(10, 2),
            upper_bound DECIMAL(10, 2),
            confidence DECIMAL(5, 4) DEFAULT 0.95,
            confidence_interval JSON,
            model_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_time (user_id, created_at)
        ) ENGINE=InnoDB;
        """
        cursor.execute(sql_prediction)

        # 2. 确保用户表有手机号字段
        print("🛠️ 检查 sys_user 表结构...")
        try:
            cursor.execute("SELECT phone FROM sys_user LIMIT 1")
            cursor.fetchall()
        except:
            print("   - 添加 phone 字段")
            cursor.execute("ALTER TABLE sys_user ADD COLUMN phone VARCHAR(20)")

        # 3. 注入带用户归属的模拟数据
        print("💉 注入模拟数据 (归属于 superadmin)...")
        # 先获取 superadmin 的 ID
        cursor.execute("SELECT user_id FROM sys_user WHERE username='superadmin'")
        res = cursor.fetchone()
        if res:
            uid = res[0]
            now = datetime.now()
            history_data = []
            for i in range(5):
                t = now - timedelta(hours=i)
                meta = json.dumps({"risk_level": "Normal", "latency_ms": 32})
                history_data.append((uid, 120, t, t, 450.5, meta))

            sql_ins = """INSERT INTO prediction_result (user_id, bus_id, predict_time, forecast_start_time, pred_value, confidence_interval) VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.executemany(sql_ins, history_data)

        conn.commit()
        print("✅ 数据库升级完成！现在支持个人数据隔离了。")

    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    fix_database_v3()