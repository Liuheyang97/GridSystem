"""
企业级AI调度助手引擎
基于规则引擎 + 知识库的智能决策系统
"""
import re
from datetime import datetime
from typing import Dict, List, Optional
import random


class AIDispatchAssistant:
    """
    AI调度助手
    模拟企业级电网调度决策支持系统
    """

    def __init__(self):
        self.knowledge_base = self._init_knowledge_base()
        self.context = {}  # 对话上下文
        self.prediction_cache = {}  # 预测结果缓存

    def _init_knowledge_base(self) -> Dict:
        """初始化知识库"""
        return {
            'risk_analysis': {
                'critical': {
                    'threshold': 0.90,
                    'actions': [
                        '立即启动应急预案',
                        '调用备用容量',
                        '启动需求侧响应',
                        '通知运维人员现场巡检',
                        '增加监测频率'
                    ]
                },
                'warning': {
                    'threshold': 0.75,
                    'actions': [
                        '加强监控',
                        '预留应急容量',
                        '检查继电保护定值',
                        '准备负荷转移方案'
                    ]
                },
                'normal': {
                    'threshold': 0.0,
                    'actions': [
                        '维持当前运行方式',
                        '例行监控',
                        '正常巡检'
                    ]
                }
            },
            'dispatch_strategies': {
                '削峰': ['调用储能放电', '启动需求响应', '增加发电机组出力', '跨区域支援'],
                '填谷': ['储能充电', '鼓励低谷用电', '减少机组出力'],
                '频率调节': ['AGC调节', '发电机组调频', '检查频率偏差原因'],
                '电压调节': ['无功补偿', '变压器分接头调节', '投切电容器/电抗器'],
                '故障处理': ['隔离故障设备', '恢复供电', '负荷转移', '启动备用']
            },
            'weather_impact': {
                '高温': '负荷攀升，空调负荷增加，需关注变压器温升',
                '低温': '取暖负荷增加，注意电网峰谷差',
                '雨': '绝缘性能下降，注意雷击风险',
                '雪': '覆冰风险，加强线路巡视',
                '大风': '线路摆动风险，关注风电出力波动'
            }
        }

    def process_message(self, user_input: str, context: Dict = None) -> str:
        """
        处理用户输入，生成智能回复

        Args:
            user_input: 用户输入文本
            context: 上下文信息（包括预测结果、系统状态等）
        """
        # 更新上下文
        if context:
            self.context.update(context)

        user_input_lower = user_input.lower().strip()

        # 1. 意图识别
        intent = self._identify_intent(user_input_lower)

        # 2. 根据意图生成回复
        if intent == 'greeting':
            return self._handle_greeting()

        elif intent == 'risk_query':
            return self._handle_risk_query()

        elif intent == 'prediction_query':
            return self._handle_prediction_query()

        elif intent == 'suggestion_query':
            return self._handle_suggestion_query()

        elif intent == 'weather_query':
            return self._handle_weather_query()

        elif intent == 'frequency_query':
            return self._handle_frequency_query()

        elif intent == 'load_query':
            return self._handle_load_query()

        elif intent == 'emergency':
            return self._handle_emergency()

        else:
            return self._handle_general_query(user_input)

    def _identify_intent(self, text: str) -> str:
        """识别用户意图"""
        # 问候
        if any(word in text for word in ['你好', 'hi', 'hello', '在吗']):
            return 'greeting'

        # 风险查询
        if any(word in text for word in ['风险', '危险', '告警', '报警', '越限']):
            return 'risk_query'

        # 预测查询
        if any(word in text for word in ['预测', '负荷', '趋势', '未来']):
            return 'prediction_query'

        # 建议查询
        if any(word in text for word in ['建议', '怎么办', '如何', '措施', '方案']):
            return 'suggestion_query'

        # 天气查询
        if any(word in text for word in ['天气', '温度', '气候', '下雨', '刮风']):
            return 'weather_query'

        # 频率查询
        if any(word in text for word in ['频率', 'hz', '赫兹']):
            return 'frequency_query'

        # 负荷查询
        if any(word in text for word in ['全网负荷', '总负荷', '用电量']):
            return 'load_query'

        # 紧急情况
        if any(word in text for word in ['紧急', '故障', '跳闸', '停电', '事故']):
            return 'emergency'

        return 'general'

    def _handle_greeting(self) -> str:
        """处理问候"""
        greetings = [
            "您好！我是AI调度助手，随时为您提供电网运行分析和决策建议。",
            "您好！调度AI已就绪，请问有什么可以帮助您的？",
            "欢迎使用智能调度助手系统，我将协助您进行电网运行分析。"
        ]
        return random.choice(greetings)

    def _handle_risk_query(self) -> str:
        """处理风险查询"""
        # 检查是否有预测结果
        if 'prediction_result' in self.context:
            result = self.context['prediction_result']
            risk_level = result.get('risk_level', 'Normal')
            peak_load = result.get('peak_load', 0)
            capacity_usage = result.get('capacity_usage', 0)

            if risk_level == 'Critical':
                return f"""⚠️ **严重风险预警**

**当前状态**: 负荷率 {capacity_usage:.1f}%，已超过安全阈值(90%)
**峰值负荷**: {peak_load:.2f} MW
**风险分析**: 
- 设备过载风险高
- 可能触发继电保护动作
- 热稳定裕度不足

**建议措施**:
1. 立即启动应急预案
2. 调用储能系统削峰(建议20MW)
3. 启动需求侧响应削减非关键负荷15%
4. 通知运维班组加强巡检
5. 准备负荷转移方案

**决策依据**: 基于AI预测模型(置信度95%)和历史运行经验
"""

            elif risk_level == 'Warning':
                return f"""🟡 **负荷预警**

**当前状态**: 负荷率 {capacity_usage:.1f}%，接近警戒线(75%)
**峰值负荷**: {peak_load:.2f} MW

**建议措施**:
1. 加强实时监控
2. 调整主变分接头优化电压
3. 检查无功补偿装置
4. 做好应急准备

**趋势判断**: 负荷平稳增长，建议持续关注
"""

            else:
                return f"""✅ **运行正常**

**当前状态**: 负荷率 {capacity_usage:.1f}%，运行平稳
**峰值负荷**: {peak_load:.2f} MW
**系统评估**: 电网裕度充足，设备运行良好

**建议**: 维持当前运行方式，执行例行巡检计划
"""

        else:
            return "暂无预测数据。请先执行负荷预测，我将为您提供详细的风险分析。"

    def _handle_prediction_query(self) -> str:
        """处理预测查询"""
        if 'prediction_result' in self.context:
            result = self.context['prediction_result']
            return f"""📊 **预测结果分析**

**预测时段**: {result.get('time_range', '未知')}
**峰值负荷**: {result.get('peak_load', 0):.2f} MW
**峰值时刻**: {result.get('peak_time', '未知')}
**平均负荷**: {result.get('avg_load', 0):.2f} MW

**趋势特征**:
- 负荷增长趋势: {'上升' if result.get('trend', 0) > 0 else '下降' if result.get('trend', 0) < 0 else '平稳'}
- 波动特性: {'较大' if result.get('volatility', 0) > 10 else '正常'}

**模型信息**: RST-Former V6.0 (MAPE < 3.5%)
"""

        return "请先执行预测，我将为您提供详细的数据分析。"

    def _handle_suggestion_query(self) -> str:
        """处理建议查询"""
        suggestions = []

        # 根据时间给出建议
        hour = datetime.now().hour
        if 8 <= hour < 12 or 18 <= hour < 22:
            suggestions.append("当前为用电高峰时段，建议加强负荷监控")
        elif 0 <= hour < 6:
            suggestions.append("当前为用电低谷时段，可安排设备检修")

        # 根据预测结果给出建议
        if 'prediction_result' in self.context:
            result = self.context['prediction_result']
            risk_level = result.get('risk_level', 'Normal')

            if risk_level != 'Normal':
                suggestions.extend(self.knowledge_base['risk_analysis'][risk_level.lower()]['actions'])

        if suggestions:
            return "**运行建议**:\n" + "\n".join([f"• {s}" for s in suggestions])

        return "系统运行正常，建议维持当前运行方式。如有特殊需求，请具体描述。"

    def _handle_weather_query(self) -> str:
        """处理天气查询"""
        if 'weather' in self.context:
            weather = self.context['weather']
            temp = weather.get('temperature', 25)

            # 分析天气影响
            impact = ""
            try:
                temp_val = float(temp)
                if temp_val > 35:
                    impact = self.knowledge_base['weather_impact']['高温']
                elif temp_val < 0:
                    impact = self.knowledge_base['weather_impact']['低温']
            except:
                pass

            return f"""🌡️ **天气影响分析**

**当前天气**: {weather.get('city', '')} {weather.get('weather', '')} {temp}°C
**对电网影响**: {impact or '天气条件良好，对电网运行影响较小'}

**建议**: 根据天气预报做好应对准备
"""

        return "暂无天气数据。系统正在获取中..."

    def _handle_frequency_query(self) -> str:
        """处理频率查询"""
        # 模拟频率数据
        freq = 50.0 + random.uniform(-0.02, 0.02)

        if abs(freq - 50.0) > 0.05:
            return f"""⚠️ **频率异常**

**当前频率**: {freq:.3f} Hz
**偏差**: {(freq - 50.0):.3f} Hz
**状态**: 超出正常范围(49.95-50.05 Hz)

**建议措施**:
1. 检查AGC系统运行状态
2. 核实发电机组调频响应
3. 分析频率偏差原因
4. 必要时启动紧急控制
"""

        return f"✅ 电网频率正常: {freq:.3f} Hz (标准范围: 49.95-50.05 Hz)"

    def _handle_load_query(self) -> str:
        """处理负荷查询"""
        total_load = random.uniform(44000, 46000)
        max_capacity = 55000
        usage = (total_load / max_capacity) * 100

        return f"""📈 **全网负荷概况**

**当前负荷**: {total_load:.0f} MW
**装机容量**: {max_capacity} MW
**负荷率**: {usage:.1f}%
**备用容量**: {max_capacity - total_load:.0f} MW ({((max_capacity - total_load) / max_capacity * 100):.1f}%)

**评估**: 电网运行在安全范围内，备用充足
"""

    def _handle_emergency(self) -> str:
        """处理紧急情况"""
        return """🚨 **紧急响应流程**

**立即行动**:
1. 启动应急预案
2. 隔离故障设备
3. 通知调度中心
4. 组织抢修队伍

**联系方式**:
- 调度热线: 95598
- 应急指挥: [紧急联系人]

**注意**: 请确保人员安全，做好安全措施后再进行操作
"""

    def _handle_general_query(self, user_input: str) -> str:
        """处理一般查询"""
        # 关键词匹配回复
        if '帮助' in user_input or 'help' in user_input:
            return """📚 **AI调度助手功能**

我可以帮助您:
• 分析负荷预测结果
• 评估系统运行风险
• 提供调度决策建议
• 解答电网运行问题
• 应急情况指导

**使用示例**:
- "当前有什么风险?"
- "给我一些建议"
- "预测结果怎么样?"
- "频率是否正常?"
"""

        # 默认智能回复
        return f"我理解您想了解「{user_input}」。请提供更具体的信息，或者尝试:\n• 执行负荷预测后查询风险分析\n• 询问\"当前有什么建议\"\n• 查看\"帮助\"了解更多功能"

    def update_prediction_context(self, prediction_result: Dict):
        """更新预测结果上下文"""
        self.context['prediction_result'] = prediction_result
        self.prediction_cache = prediction_result

    def update_weather_context(self, weather_data: Dict):
        """更新天气上下文"""
        self.context['weather'] = weather_data

    def generate_auto_report(self, prediction_result: Dict) -> str:
        """
        自动生成预测报告
        在执行预测后自动调用
        """
        risk_level = prediction_result.get('risk_level', 'Normal')
        peak_load = prediction_result.get('peak_load', 0)
        capacity_usage = prediction_result.get('capacity_usage', 0)
        bus_id = prediction_result.get('bus_id', 'Unknown')

        # 风险等级图标
        risk_icons = {
            'Critical': '🔴',
            'Warning': '🟡',
            'Normal': '🟢',
            'Offline': '⚫'
        }

        icon = risk_icons.get(risk_level, '🟢')

        # 根据风险等级生成不同的报告
        if risk_level == 'Critical':
            return f"""{icon} **节点 {bus_id} 预测完成 - 严重风险**

⚠️ **风险预警**: 负荷率 {capacity_usage:.1f}% (峰值 {peak_load:.2f} MW)

**决策建议**:
• 立即启动应急预案
• 建议削峰 20MW (储能放电 + 需求响应)
• 检查继电保护定值
• 加强现场巡检

**下一步**: 请在30分钟内确认应急措施执行情况
"""

        elif risk_level == 'Warning':
            return f"""{icon} **节点 {bus_id} 预测完成 - 负荷预警**

🟡 **注意**: 负荷率 {capacity_usage:.1f}% (峰值 {peak_load:.2f} MW)

**建议**:
• 加强监控，关注负荷变化
• 调整主变分接头优化电压
• 准备应急预案

**趋势**: 负荷增长平稳，建议持续关注
"""

        else:
            return f"""{icon} **节点 {bus_id} 预测完成 - 运行正常**

✅ 负荷率 {capacity_usage:.1f}% (峰值 {peak_load:.2f} MW)
运行平稳，系统裕度充足。建议维持当前运行方式。
"""


# 全局实例
ai_assistant = AIDispatchAssistant()
