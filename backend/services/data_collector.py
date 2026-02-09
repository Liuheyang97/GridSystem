import numpy as np
from datetime import datetime, timedelta
import random


class VirtualDataCollector:
    def __init__(self, system_state):
        self.state = system_state

    # 1. 仪表盘左侧：实时概览数据
    def fetch_realtime_data(self, node_id, current_sim_time_str):
        # 尝试解析当前仿真时间
        try:
            target_dt = datetime.strptime(current_sim_time_str, "%H:%M:%S")
        except:
            target_dt = datetime.now()

        # --- 🔥 修复：改为真实的分时电价逻辑 ---
        hour = target_dt.hour
        base_price = 0.65  # 平段电价

        # 峰段 (08:00-11:00, 18:00-22:00) 电价高
        if (8 <= hour < 11) or (18 <= hour < 22):
            base_price = 1.15
        # 谷段 (22:00-08:00) 电价低
        elif (22 <= hour) or (0 <= hour < 8):
            base_price = 0.35

        # 加一点点微小的随机扰动 (0.001元)，让数据看起来在“呼吸”，而不是死值
        final_price = base_price + random.uniform(-0.005, 0.005)
        # -------------------------------------

        if self.state.data_raw is None:
            return {"scada": {"bus_load": 0}, "market": {"price": final_price}}

        try:
            node_idx = (node_id - 1) % self.state.total_nodes
            val = self.state.data_raw[random.randint(0, 100), node_idx, 0]
            load_val = float(val) if val > 10 else float(val * self.state.data_max)

            return {
                "scada": {"bus_load": round(load_val, 2)},
                "weather": {"temp": 26.5, "condition": "多云"},  # 汉化
                "market": {"price": round(final_price, 3)}  # 保留3位小数
            }
        except:
            return {}

    # 2. 弹窗：详细数据列表
    def fetch_detailed_logs(self, source_type):
        data_list = []
        base_time = datetime.now()

        if source_type == "scada":
            # SCADA 数据：常规遥测
            for i in range(15):
                t = base_time - timedelta(seconds=i * 5)
                data_list.append({
                    "id": f"测点_{10000 + i}",  # 汉化
                    "name": random.choice(["A相电压", "B相电压", "C相电压", "有功功率", "无功功率"]),
                    "time": t.strftime("%H:%M:%S.%f")[:-3],  # 精确到毫秒
                    "value": f"{round(random.uniform(218, 222), 2)}",
                    "unit": random.choice(["kV", "MW", "MVar"]),
                    "quality": "优 (Good)"  # 汉化
                })

        elif source_type == "pmu":
            # PMU 数据：相量监测
            for i in range(15):
                t = base_time - timedelta(milliseconds=i * 40)  # PMU 采样密度很高
                data_list.append({
                    "id": f"PMU装置_{200 + i}",
                    "time": t.strftime("%H:%M:%S.%f")[:-3],
                    "freq": f"{round(random.uniform(49.98, 50.02), 4)} Hz",  # 频率波动很小
                    "angle": f"{round(random.uniform(-180, 180), 3)}°",  # 相角
                    "status": "同步锁定"  # 汉化
                })

        elif source_type == "ami":
            # AMI 数据：智能电表
            for i in range(15):
                uid = random.randint(100000, 999999)
                data_list.append({
                    "id": f"电表_{uid}",
                    "user_name": f"用户_****_{str(uid)[-4:]}",
                    "time": base_time.strftime("%H:%M:%S"),
                    "reading": f"{random.uniform(100, 800):.1f}",
                    "status": "加密保护 🔒"  # 汉化
                })

        return data_list