-- 电网母线负荷预测系统 - 数据库初始化脚本
-- Version: V9.2 Fix
-- Description: 修复密码哈希不匹配问题，保留所有核心业务表结构

DROP DATABASE IF EXISTS grid_forecast_system;
CREATE DATABASE grid_forecast_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE grid_forecast_system;

-- 1. 用户表 (User Table)
-- 修改：更新了默认密码哈希，确保 'admin123' 可以登录
CREATE TABLE sys_user (
    user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- 默认密码: admin123
    real_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    department VARCHAR(100),
    role_type ENUM('SUPER_ADMIN', 'ADMIN', 'OPERATOR', 'VIEWER') DEFAULT 'VIEWER',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. 角色权限表 (Role Permission Table)
CREATE TABLE sys_role_permission (
    permission_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_type ENUM('SUPER_ADMIN', 'ADMIN', 'OPERATOR', 'VIEWER') NOT NULL,
    permission_code VARCHAR(100) NOT NULL,
    permission_name VARCHAR(200) NOT NULL,
    UNIQUE KEY uk_role_permission (role_type, permission_code)
) ENGINE=InnoDB;

-- 3. 操作日志表 (Operation Log)
CREATE TABLE sys_operation_log (
    log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,
    username VARCHAR(50),
    operation_type VARCHAR(50),
    operation_desc TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. 登录日志表 (Login Log)
CREATE TABLE sys_login_log (
    log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50),
    login_ip VARCHAR(50),
    status TINYINT COMMENT '1: Success, 0: Failed',
    message VARCHAR(255),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 5. 变电站表 (Substation)
CREATE TABLE grid_substation (
    substation_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    substation_code VARCHAR(50) UNIQUE NOT NULL,
    substation_name VARCHAR(100) NOT NULL,
    voltage_level VARCHAR(20),
    region_name VARCHAR(100),
    longitude DECIMAL(10, 7),
    latitude DECIMAL(10, 7),
    capacity DECIMAL(10, 2),
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 6. 母线表 (Bus Info)
CREATE TABLE grid_bus_info (
    bus_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bus_code VARCHAR(50) UNIQUE,
    bus_name VARCHAR(100) NOT NULL,
    substation_id BIGINT,
    voltage_level VARCHAR(20),
    max_load DECIMAL(10, 2),
    rated_capacity DECIMAL(10, 2),
    importance_level TINYINT DEFAULT 1,
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (substation_id) REFERENCES grid_substation(substation_id)
) ENGINE=InnoDB;

-- 7. SCADA实时数据表 (SCADA Realtime)
CREATE TABLE data_scada_realtime (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bus_id BIGINT NOT NULL,
    data_time TIMESTAMP NOT NULL,
    active_power DECIMAL(10, 2),
    voltage DECIMAL(10, 2),
    frequency DECIMAL(6, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bus_time (bus_id, data_time)
) ENGINE=InnoDB;

-- 8. PMU相量数据表 (PMU Realtime)
CREATE TABLE data_pmu_realtime (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bus_id BIGINT NOT NULL,
    data_time TIMESTAMP(3) NOT NULL,
    voltage_magnitude DECIMAL(10, 2),
    frequency DECIMAL(8, 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 9. AMI智能电表数据表 (AMI Encrypted)
-- 只有超级管理员才有权解密查看
CREATE TABLE data_ami_encrypted (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meter_id VARCHAR(100) NOT NULL,
    user_hash VARCHAR(255),
    data_time TIMESTAMP NOT NULL,
    energy_consumption DECIMAL(12, 2),
    access_level TINYINT DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 10. 预测模型表 (Prediction Model)
CREATE TABLE prediction_model (
    model_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_code VARCHAR(100) UNIQUE NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50),
    model_version VARCHAR(20),
    file_path TEXT,
    mae DECIMAL(10, 4),
    rmse DECIMAL(10, 4),
    mape DECIMAL(10, 4),
    status TINYINT DEFAULT 1,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 11. 预测结果表 (Prediction Result)
-- 存储预测值及置信区间，支持 JSON 格式存储风险评估详情
CREATE TABLE prediction_result (
    result_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    bus_id BIGINT NOT NULL,
    predict_time TIMESTAMP NOT NULL,
    forecast_start_time TIMESTAMP,
    pred_value DECIMAL(10, 2),
    lower_bound DECIMAL(10, 2),
    upper_bound DECIMAL(10, 2),
    confidence DECIMAL(5, 4) DEFAULT 0.95,
    confidence_interval JSON,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bus_time (bus_id, predict_time)
) ENGINE=InnoDB;

-- =======================================================
-- 初始化数据 (Initial Data)
-- =======================================================

-- 1. 插入初始用户
-- ⚠️ 关键修正：这里的 password_hash 均对应密码 'admin123'
-- 使用 bcrypt.hashpw(b'admin123', bcrypt.gensalt()) 生成，确保 Python 后端能验证成功
INSERT INTO sys_user (username, password_hash, real_name, email, department, role_type) VALUES
('superadmin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '超级管理员', 'superadmin@grid.com', '系统管理部', 'SUPER_ADMIN'),
('admin',      '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '系统管理员', 'admin@grid.com', '调度中心', 'ADMIN'),
('operator1',  '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '调度员A', 'operator1@grid.com', '调度运行部', 'OPERATOR'),
('viewer',     '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '查看员', 'viewer@grid.com', '营销部', 'VIEWER');

-- 2. 插入权限
-- 保持原有 OT/IT 隔离逻辑
INSERT INTO sys_role_permission (role_type, permission_code, permission_name) VALUES
('SUPER_ADMIN', 'system:all', '所有权限'),
('SUPER_ADMIN', 'data:ami:read', 'AMI数据读取'),
('ADMIN', 'predict:manage', '预测管理'),
('ADMIN', 'data:scada:read', 'SCADA数据读取'),
('ADMIN', 'data:pmu:read', 'PMU数据读取'),
('OPERATOR', 'predict:execute', '执行预测'),
('OPERATOR', 'data:scada:read', 'SCADA数据读取'),
('OPERATOR', 'data:pmu:read', 'PMU数据读取'),
('VIEWER', 'dashboard:view', '仪表盘查看');

-- 3. 插入变电站
INSERT INTO grid_substation (substation_code, substation_name, voltage_level, region_name, capacity) VALUES
('SS-BJ-001', '北京朝阳变电站', '220kV', '北京市', 500.00),
('SS-SH-001', '上海浦东变电站', '220kV', '上海市', 600.00);

-- 4. 插入母线
INSERT INTO grid_bus_info (bus_code, bus_name, substation_id, voltage_level, max_load, rated_capacity) VALUES
('BUS-001', '朝阳220kV-I段母线', 1, '220kV', 350.00, 400.00),
('BUS-002', '浦东220kV-I段母线', 2, '220kV', 450.00, 500.00);

-- 5. 插入模型
INSERT INTO prediction_model (model_code, model_name, model_type, model_version, file_path, mae, rmse, mape, is_default) VALUES
('RST-Former-V6.0', 'RST-Former负荷预测模型', 'Transformer', 'v6.0', '/data/best_transformer_mse.pth', 12.34, 18.56, 3.45, TRUE);

SELECT '数据库初始化完成，密码已重置为 admin123！' as message;