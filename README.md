# 电网母线负荷智能预测系统 V9.2

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
mysql -u root -p < database/init_database.sql
```

### 3. 修改配置
编辑 `backend/config/settings.py`，修改数据库密码：
```python
DATABASE_CONFIG = {
    'password': 'YOUR_MYSQL_PASSWORD',  # 改为你的密码
}
```

### 4. 准备数据文件（可选）
将以下文件放入 `data/` 目录：
- best_transformer_mse.pth
- gnn_X_2016_fusion.npy

如果没有这些文件，系统会使用模拟数据运行。

### 5. 启动系统
```bash
python main.py
```

### 6. 访问系统
打开浏览器：http://localhost:8000

### 测试账号
- 超级管理员: superadmin / admin123
- 管理员: admin / admin123
- 操作员: operator1 / admin123
- 查看员: viewer / admin123

## 核心功能

### 权限隔离
- **调度运行域（OT）**：SCADA、PMU - 操作员可访问
- **营销计量域（IT）**：AMI - 仅超管可访问

### AI预测
- 支持1-168小时预测
- 95%置信区间
- 智能风险评估

### 时间映射
- 展示2026年预测（实际使用2016年数据）
- 证明模型泛化能力

## 项目结构
```
GridSystem/
├── backend/
│   ├── models/model.py
│   ├── services/data_collector.py
│   ├── utils/database.py
│   └── config/settings.py
├── frontend/pages/
│   ├── login.html
│   └── dashboard.html
├── database/init_database.sql
├── main.py
└── requirements.txt
```

## 数据库表
- sys_user - 用户表
- grid_bus_info - 母线表
- prediction_result - 预测结果表
- （共11张核心表）

## API接口
- POST /api/auth/login
- GET /api/predict
- GET /api/history
- GET /api/collect/detail（权限隔离）

## 常见问题

### Q: 数据库连接失败
修改 backend/config/settings.py 中的密码

### Q: 模型文件不存在
系统会使用模拟数据，不影响演示

### Q: AMI数据无法访问
这是设计功能！使用superadmin登录即可

## 技术栈
- Python + FastAPI
- PyTorch
- MySQL
- Vue3 + ECharts
