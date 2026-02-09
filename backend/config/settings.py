"""系统配置文件"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库配置
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '131421',  # ⚠️ 请修改为你的MySQL密码
    'database': 'grid_forecast_system',
    'charset': 'utf8mb4'
}

# 模型配置
MODEL_CONFIG = {
    'history_len': 168,
    'pred_len': 24,
    'in_features': 10,
    'hidden_dim': 128,
    'num_layers': 3,
    'num_heads': 4,
    'dropout': 0.1,
    'device': 'cpu'
}

# 文件路径
PATH_CONFIG = {
    'model_path': os.path.join(BASE_DIR, 'data', 'best_transformer_mse.pth'),
    'data_path': os.path.join(BASE_DIR, 'data', 'gnn_X_2016_fusion.npy'),
    'template_dir': os.path.join(BASE_DIR, 'frontend', 'pages')
}

# JWT配置
JWT_CONFIG = {
    'secret_key': 'grid-forecast-secret-2026',
    'algorithm': 'HS256',
    'access_token_expire_minutes': 480
}

# 权限配置
PERMISSION_CONFIG = {
    'SUPER_ADMIN': {'name': '超级管理员', 'permissions': ['*'], 'data_access': ['SCADA', 'PMU', 'AMI']},
    'ADMIN': {'name': '系统管理员', 'permissions': ['predict:manage'], 'data_access': ['SCADA', 'PMU']},
    'OPERATOR': {'name': '调度操作员', 'permissions': ['predict:execute'], 'data_access': ['SCADA', 'PMU']},
    'VIEWER': {'name': '查看员', 'permissions': ['dashboard:view'], 'data_access': []}
}

# 时间映射
TIME_MAPPING_CONFIG = {
    'enable_mapping': True,
    'source_year': 2016,
    'target_year': 2026,
    'base_date': '2016-01-01 00:00:00'
}

# 模型配置
MODEL_CONFIG = {
    'device': 'cpu',
    'history_len': 96
}

# 告警阈值
ALERT_CONFIG = {
    'load_warning_ratio': 0.90,
    'load_critical_ratio': 1.05
}

# 高德地图API
AMAP_CONFIG = {
    'api_key': '5d7d9c7dbb4025f9b266b05e4b35931f'
}

# Redis配置（可选）
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None
}

# 📧 邮件发送配置 (请修改为你自己的)
EMAIL_CONFIG = {
    'SMTP_SERVER': 'smtp.qq.com',   # 例如 QQ邮箱是 smtp.qq.com
    'SMTP_PORT': 465,               # SSL端口通常是 465
    'SENDER_EMAIL': '2474084380@qq.com', # 你的发件邮箱
    'SENDER_PASSWORD': 'nlwwjcbocwyadjch',  # ⚠️ 这里填邮箱的“授权码”，不是登录密码！
    'use_ssl': True                     # 是否使用SSL加密
}
PERMISSION_CONFIG = {'SUPER_ADMIN': {'data_access': ['SCADA', 'PMU', 'AMI']},
                     'ADMIN': {'data_access': ['SCADA', 'PMU']},
                     'OPERATOR': {'data_access': ['SCADA', 'PMU']},
                     'VIEWER': {'data_access': []}}
# 将配置从字典中提取出来，作为全局变量暴露
SECRET_KEY = JWT_CONFIG['secret_key']
ALGORITHM = JWT_CONFIG['algorithm']