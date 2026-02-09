import mysql.connector
import json
from datetime import datetime, timedelta

# 尝试导入配置，如果路径不对则手动定义
try:
    from backend.config.settings import DATABASE_CONFIG
except ImportError:
    # 如果找不到，临时使用硬编码配置（防止路径报错）
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'YOUR_PASSWORD',  # ⚠️ 如果报错，请确保这里密码正确，或者 settings.py 能被导入
        'database': 'grid_forecast_system',
        'charset': 'utf8mb4'
    }
    print("⚠️ 警告: 未能导入 settings.py，正在尝试使用默认配置...")


def fix_database():
    print("🚑 开始数据库深度修复程序 (v2.0)...")

    conn = None
    try:
        # 1. 连接数据库
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        print("✅ 数据库连接成功")

        # 2. 彻底重置表结构 (先删除，再创建，解决所有结构冲突)
        print("🛠️ 正在重建核心表...")

        # 删除旧表 (防止结构不兼容)
        cursor.execute("DROP TABLE IF EXISTS prediction_result")

        # 创建新表 (关键修改：增加了 DEFAULT CURRENT_TIMESTAMP 和 NULL)
        sql_prediction = """
        CREATE TABLE prediction_result (
            result_id BIGINT PRIMARY KEY AUTO_INCREMENT,
            bus_id BIGINT NOT NULL,

            -- ⬇️ 修复点：明确指定默认值为当前时间
            predict_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            -- ⬇️ 修复点：允许为空，默认值为 NULL
            forecast_start_time TIMESTAMP NULL DEFAULT NULL,

            pred_value DECIMAL(10, 2),
            lower_bound DECIMAL(10, 2),
            upper_bound DECIMAL(10, 2),
            confidence DECIMAL(5, 4) DEFAULT 0.95,
            confidence_interval JSON,
            model_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_bus_time (bus_id, predict_time)
        ) ENGINE=InnoDB;
        """
        cursor.execute(sql_prediction)
        print("   - 表 'prediction_result' 重建完成")

        # 补充创建母线表 (如果不存在)
        sql_bus = """
        CREATE TABLE IF NOT EXISTS grid_bus_info (
            bus_id BIGINT PRIMARY KEY AUTO_INCREMENT,
            bus_code VARCHAR(50) UNIQUE,
            bus_name VARCHAR(100) NOT NULL,
            substation_id BIGINT,
            voltage_level VARCHAR(20),
            max_load DECIMAL(10, 2),
            rated_capacity DECIMAL(10, 2),
            importance_level TINYINT DEFAULT 1,
            status TINYINT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
        cursor.execute(sql_bus)

        # 3. 注入模拟数据
        print("💉 正在注入模拟数据...")

        # 3.1 确保有母线数据
        cursor.execute("SELECT count(*) FROM grid_bus_info")
        if cursor.fetchone()[0] == 0:
            sql_insert_bus = """
            INSERT INTO grid_bus_info (bus_id, bus_name, voltage_level) VALUES 
            (1, 'Bus-001 主变高压侧', '220kV'),
            (2, 'Bus-002 工业园专线', '110kV'),
            (120, 'Bus-120 城区中心站', '220kV');
            """
            cursor.execute(sql_insert_bus)
            print("   - 母线基础数据已插入")

        # 3.2 插入历史预测记录
        now = datetime.now()
        history_data = []

        for i in range(10):
            t = now - timedelta(hours=i)
            risk = "Normal"
            val = 400.0 + (i * 10)
            if i == 2: risk = "Warning"
            if i == 5: risk = "Critical"

            meta = json.dumps({"risk_level": risk, "latency_ms": 32})

            # 注意：这里对应上面新的表结构
            history_data.append((
                120, t, t, val, meta, t
            ))

        sql_insert_history = """
        INSERT INTO prediction_result 
        (bus_id, predict_time, forecast_start_time, pred_value, confidence_interval, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(sql_insert_history, history_data)
        print(f"   - 已注入 {len(history_data)} 条历史预测记录")

        conn.commit()
        print("✅ 数据注入完成！")
        print("\n🎉 修复成功！请重新运行 main.py")

    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        # 如果是密码错误，这里会提示
        if "Access denied" in str(e):
            print("👉 看起来是密码不对，请检查 settings.py")
        elif "1067" in str(e):
            print("👉 依然是时间格式错误，请确保你的 MySQL 版本不是太老 (5.5以下) 或太新配置了极端的严格模式。")

    finally:
        if conn: conn.close()


if __name__ == "__main__":
    fix_database()