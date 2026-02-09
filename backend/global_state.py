import time
from backend.config.settings import DATABASE_CONFIG
from backend.utils.database import DatabaseManager
from backend.services.data_collector import VirtualDataCollector
from backend.models.model import TransformerModel

class SystemState:
    def __init__(self):
        self.db_manager = None
        self.collector = None
        self.model = None
        self.start_time = time.time()

    def init_db(self):
        try:
            self.db_manager = DatabaseManager(DATABASE_CONFIG)
            conn = self.db_manager.get_connection()
            if conn:
                print("✅ 数据库连接成功 (Database Connected)")
                conn.close()
        except Exception as e:
            print(f"❌ 数据库连接异常: {e}")
            self.db_manager = None

# 全局单例
state = SystemState()
state.collector = VirtualDataCollector(state)
state.model = TransformerModel()