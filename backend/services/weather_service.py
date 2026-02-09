"""
改进的天气服务 - 支持真实IP定位和城市搜索
"""
import requests
import logging
from typing import Dict, List, Optional
from backend.config.settings import AMAP_CONFIG

logger = logging.getLogger(__name__)


class WeatherService:
    """天气服务 - 基于高德地图API"""

    def __init__(self):
        self.api_key = AMAP_CONFIG['api_key']
        self.timeout = 5
        self.cache = {}  # 简单缓存，避免频繁请求

    def get_current_weather_by_ip(self, client_ip: str = None) -> Dict:
        """
        根据IP获取当前天气
        """
        try:
            # 1. 通过IP获取城市代码
            adcode = self._get_adcode_by_ip(client_ip)

            # 2. 获取天气信息
            weather_data = self._get_weather_by_adcode(adcode)

            return weather_data

        except Exception as e:
            logger.error(f"获取天气失败: {e}")
            return self._get_default_weather()

    def search_city(self, keywords: str) -> List[Dict]:
        """
        搜索城市
        返回: [{'name': '北京市', 'adcode': '110000', 'location': '116.405285,39.904989'}, ...]
        """
        try:
            url = f"https://restapi.amap.com/v3/config/district"
            params = {
                'keywords': keywords,
                'key': self.api_key,
                'subdistrict': 0,
                'extensions': 'base'
            }

            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()

            if data.get('status') == '1' and data.get('districts'):
                cities = []
                for district in data['districts']:
                    cities.append({
                        'name': district['name'],
                        'adcode': district['adcode'],
                        'location': district.get('center', ''),
                        'level': district.get('level', '')
                    })
                return cities

            return []

        except Exception as e:
            logger.error(f"搜索城市失败: {e}")
            return []

    def get_weather_by_city(self, city_name: str) -> Dict:
        """
        根据城市名获取天气
        """
        try:
            # 先搜索城市
            cities = self.search_city(city_name)
            if not cities:
                return self._get_default_weather()

            # 使用第一个结果
            adcode = cities[0]['adcode']
            return self._get_weather_by_adcode(adcode)

        except Exception as e:
            logger.error(f"获取城市天气失败: {e}")
            return self._get_default_weather()

    def get_weather_by_adcode(self, adcode: str) -> Dict:
        """
        根据行政区划代码获取天气
        """
        return self._get_weather_by_adcode(adcode)

    def _get_adcode_by_ip(self, client_ip: str = None) -> str:
        """
        通过IP获取城市代码
        """
        try:
            url = f"https://restapi.amap.com/v3/ip"
            params = {
                'key': self.api_key
            }

            if client_ip and not client_ip.startswith('127.') and not client_ip.startswith('192.168.'):
                params['ip'] = client_ip

            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()

            if data.get('status') == '1':
                adcode = data.get('adcode')
                if isinstance(adcode, list):
                    adcode = adcode[0] if adcode else '110000'
                return adcode or '110000'

            return '110000'  # 默认北京

        except Exception as e:
            logger.error(f"IP定位失败: {e}")
            return '110000'

    def _get_weather_by_adcode(self, adcode: str) -> Dict:
        """
        根据adcode获取天气详情
        """
        try:
            # 检查缓存（5分钟有效期）
            cache_key = f"weather_{adcode}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                import time
                if time.time() - cached_time < 300:  # 5分钟
                    return cached_data

            url = f"https://restapi.amap.com/v3/weather/weatherInfo"
            params = {
                'key': self.api_key,
                'city': adcode,
                'extensions': 'base'
            }

            response = requests.get(url, params=params, timeout=self.timeout)
            data = response.json()

            if data.get('status') == '1' and data.get('lives'):
                live = data['lives'][0]

                weather_data = {
                    'city': live.get('city', '未知'),
                    'temperature': live.get('temperature', '--'),
                    'weather': live.get('weather', '--'),
                    'wind': self._format_wind(live.get('winddirection', ''), live.get('windpower', '')),
                    'humidity': live.get('humidity', '--'),
                    'reporttime': live.get('reporttime', ''),
                    'adcode': adcode,
                    'url': f"https://www.amap.com/search?query={live.get('city', '')}&city={adcode}"
                }

                # 缓存结果
                import time
                self.cache[cache_key] = (weather_data, time.time())

                return weather_data

            return self._get_default_weather()

        except Exception as e:
            logger.error(f"获取天气详情失败: {e}")
            return self._get_default_weather()

    def _format_wind(self, direction: str, power: str) -> str:
        """格式化风向风力"""
        if not direction or not power:
            return ''

        # 转换方向
        dir_map = {
            '东': 'E', '南': 'S', '西': 'W', '北': 'N',
            '东北': 'NE', '东南': 'SE', '西南': 'SW', '西北': 'NW'
        }

        dir_short = dir_map.get(direction, direction)

        return f"{dir_short} {power}级"

    def _get_default_weather(self) -> Dict:
        """获取默认天气数据"""
        return {
            'city': '演示模式',
            'temperature': '25',
            'weather': '晴',
            'wind': 'N 2级',
            'humidity': '60',
            'reporttime': '',
            'adcode': '000000',
            'url': '#'
        }


# 单例实例
weather_service = WeatherService()
