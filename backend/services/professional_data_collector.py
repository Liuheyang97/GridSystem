"""
专业的电网数据采集服务 - 模拟真实SCADA/PMU/AMI系统
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict
import math


class ProfessionalDataCollector:
    """
    专业级数据采集服务
    模拟真实电网SCADA、WAMS/PMU、AMI集抄系统
    """

    def __init__(self, system_state=None):
        self.state = system_state
        self.scada_buffer = []  # SCADA数据缓冲
        self.pmu_buffer = []  # PMU数据缓冲
        self.ami_buffer = []  # AMI数据缓冲

    def fetch_scada_realtime(self, bus_id: int, limit: int = 20) -> List[Dict]:
        """
        获取SCADA实时遥测数据
        模拟IEC 60870-5-104协议数据
        """
        data_list = []
        base_time = datetime.now()

        # 模拟母线基础负荷
        base_load = 200 + (bus_id % 100) * 3
        base_voltage = 220.0
        base_current = base_load / (base_voltage * math.sqrt(3)) * 1000

        for i in range(limit):
            timestamp = base_time - timedelta(seconds=i * 4)  # SCADA采集周期4秒

            # 添加随机波动
            load_fluctuation = random.uniform(-5, 5)
            voltage_fluctuation = random.uniform(-2, 2)

            data_list.append({
                'timestamp': timestamp.strftime('%H:%M:%S'),
                'yc_points': [
                    {
                        'name': 'A相电压',
                        'tag': 'YC_UA',
                        'value': f'{base_voltage + voltage_fluctuation:.2f}',
                        'unit': 'kV',
                        'quality': 'GOOD' if random.random() > 0.05 else 'UNCERTAIN'
                    },
                    {
                        'name': 'B相电压',
                        'tag': 'YC_UB',
                        'value': f'{base_voltage + voltage_fluctuation - 0.5:.2f}',
                        'unit': 'kV',
                        'quality': 'GOOD'
                    },
                    {
                        'name': 'C相电压',
                        'tag': 'YC_UC',
                        'value': f'{base_voltage + voltage_fluctuation + 0.3:.2f}',
                        'unit': 'kV',
                        'quality': 'GOOD'
                    },
                    {
                        'name': 'A相电流',
                        'tag': 'YC_IA',
                        'value': f'{base_current:.1f}',
                        'unit': 'A',
                        'quality': 'GOOD'
                    },
                    {
                        'name': '有功功率',
                        'tag': 'YC_P',
                        'value': f'{base_load + load_fluctuation:.2f}',
                        'unit': 'MW',
                        'quality': 'GOOD'
                    },
                    {
                        'name': '无功功率',
                        'tag': 'YC_Q',
                        'value': f'{base_load * 0.2:.2f}',
                        'unit': 'MVar',
                        'quality': 'GOOD'
                    },
                    {
                        'name': '功率因数',
                        'tag': 'YC_PF',
                        'value': f'{0.98 + random.uniform(-0.02, 0.01):.3f}',
                        'unit': '',
                        'quality': 'GOOD'
                    },
                    {
                        'name': '频率',
                        'tag': 'YC_FREQ',
                        'value': f'{50.0 + random.uniform(-0.02, 0.02):.3f}',
                        'unit': 'Hz',
                        'quality': 'GOOD'
                    }
                ]
            })

        return data_list

    def fetch_pmu_realtime(self, bus_id: int, limit: int = 20) -> List[Dict]:
        """
        获取PMU相量测量数据
        模拟IEEE C37.118协议数据
        高频采样（30帧/秒）
        """
        data_list = []
        base_time = datetime.now()

        base_voltage_mag = 220.0
        base_current_mag = 500.0
        base_angle = random.uniform(-30, 30)

        for i in range(limit):
            timestamp = base_time - timedelta(milliseconds=i * 33)  # 30fps

            # 频率微小波动
            freq = 50.0 + random.uniform(-0.005, 0.005)
            rocof = random.uniform(-0.01, 0.01)  # 频率变化率

            data_list.append({
                'timestamp': timestamp.strftime('%H:%M:%S.%f')[:-3],
                'synchrophasor': {
                    'voltage': {
                        'magnitude': f'{base_voltage_mag + random.uniform(-0.5, 0.5):.4f}',
                        'angle': f'{base_angle + random.uniform(-0.1, 0.1):.6f}°',
                        'unit': 'kV'
                    },
                    'current': {
                        'magnitude': f'{base_current_mag + random.uniform(-10, 10):.2f}',
                        'angle': f'{base_angle - 30 + random.uniform(-0.5, 0.5):.6f}°',
                        'unit': 'A'
                    },
                    'frequency': {
                        'value': f'{freq:.6f}',
                        'rocof': f'{rocof:.6f}',
                        'unit': 'Hz'
                    }
                },
                'quality': {
                    'sync_status': 'LOCKED',
                    'time_quality': 'ACCURATE',
                    'measurement_quality': 'VALID'
                },
                'pdc_id': f'PDC_{bus_id:03d}',
                'station': f'Station_{bus_id}'
            })

        return data_list

    def fetch_ami_realtime(self, bus_id: int, limit: int = 20) -> List[Dict]:
        """
        获取AMI智能电表数据
        模拟DL/T 698.45协议数据
        数据已脱敏和加密
        """
        data_list = []
        base_time = datetime.now()

        # 模拟用户用电数据
        for i in range(limit):
            user_id = random.randint(100000, 999999)
            meter_id = f'METER_{user_id}'

            # 时间戳（15分钟采集间隔）
            timestamp = base_time - timedelta(minutes=i * 15)

            # 模拟用电量
            hour = timestamp.hour
            if 8 <= hour < 12 or 18 <= hour < 22:
                base_power = random.uniform(2.0, 5.0)  # 用电高峰
            elif 0 <= hour < 6:
                base_power = random.uniform(0.3, 1.0)  # 低谷
            else:
                base_power = random.uniform(1.0, 3.0)  # 平段

            data_list.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
                'meter_id': meter_id,
                'user_id': f'****{str(user_id)[-4:]}',  # 脱敏
                'data': {
                    'total_energy': f'{random.uniform(1000, 5000):.2f}',  # 总电量
                    'current_power': f'{base_power:.3f}',  # 当前功率
                    'voltage': f'{220 + random.uniform(-5, 5):.1f}',
                    'current': f'{base_power / 0.22:.2f}',
                    'power_factor': f'{random.uniform(0.90, 0.99):.3f}'
                },
                'encryption': {
                    'method': 'SM4-CBC',
                    'status': 'ENCRYPTED',
                    'key_version': 'V2.1'
                },
                'access_level': 3,  # 需要最高权限
                'station': f'District_{bus_id % 10}',
                'collector': f'CC_{(bus_id % 100):03d}'
            })

        return data_list

    def fetch_system_monitoring(self) -> Dict:
        """
        获取系统运行监控数据
        """
        return {
            'scada': {
                'status': 'normal' if random.random() > 0.1 else 'warning',
                'message': 'SCADA系统运行正常' if random.random() > 0.1 else '部分测点通信超时',
                'connection_rate': f'{random.uniform(98, 100):.2f}%',
                'data_quality': f'{random.uniform(95, 100):.2f}%',
                'update_time': datetime.now().strftime('%H:%M:%S')
            },
            'pmu': {
                'status': 'normal' if random.random() > 0.05 else 'warning',
                'message': 'PMU同步正常' if random.random() > 0.05 else 'GPS时钟漂移检测',
                'sync_accuracy': f'{random.uniform(0.001, 0.01):.4f}ms',
                'data_rate': '30 fps',
                'update_time': datetime.now().strftime('%H:%M:%S')
            },
            'ami': {
                'status': 'normal',
                'message': 'AMI集抄系统正常',
                'online_meters': f'{random.randint(9500, 9999)}',
                'total_meters': '10000',
                'success_rate': f'{random.uniform(95, 99):.2f}%',
                'update_time': datetime.now().strftime('%H:%M:%S')
            }
        }

    def get_grid_overview(self) -> Dict:
        """
        获取电网运行总览
        """
        return {
            'total_load': f'{random.uniform(44000, 46000):.0f}',  # MW
            'frequency': f'{50.0 + random.uniform(-0.02, 0.02):.3f}',  # Hz
            'voltage_qualified_rate': f'{random.uniform(99.5, 100):.2f}',  # %
            'active_buses': random.randint(98, 100),
            'total_buses': 100,
            'alarm_count': random.randint(0, 3),
            'system_health': 'HEALTHY' if random.random() > 0.1 else 'WARNING'
        }


# 全局实例
professional_collector = ProfessionalDataCollector()
