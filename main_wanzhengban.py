import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import jwt, bcrypt, requests, smtplib, json, random, time, os, sys, logging, shutil
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta
import numpy as np
import asyncio

# ==============================================================================
# 0. 系统配置与初始化 (System Configuration)
# ==============================================================================

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 前端页面目录
HTML_DIR = os.path.join(BASE_DIR, 'frontend', 'pages')
# 文件上传保存目录
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

# 自动创建必要的目录
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)


# 辅助函数：安全获取文件路径
def get_file_path(filename):
    path = os.path.join(HTML_DIR, filename)
    # 如果在 pages 下找不到，尝试在根目录找（兼容旧结构）
    if os.path.exists(path): return path
    path_root = os.path.join(BASE_DIR, filename)
    if os.path.exists(path_root): return path_root
    return path


# 将项目根目录加入系统路径，以便导入 backend 模块
sys.path.append(BASE_DIR)

try:
    # 尝试导入配置文件和数据库模块
    from backend.config.settings import *
    from backend.models.model import TransformerModel
    from backend.services.data_collector import VirtualDataCollector
    from backend.utils import DatabaseManager, UserDao, PredictionDao
except ImportError as e:
    print(f"❌ 严重错误：模块导入失败: {e}")
    print("请确保 backend 文件夹在当前目录下。")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GridMaster")

# 初始化 FastAPI 应用
app = FastAPI(
    title="智能电网调度系统 (Intelligent Grid Dispatching System)",
    version="9.9.18 Full",
    description="集成了负荷预测、实时监视、站内通信、RBAC权限管理的企业级后端系统"
)

# 配置跨域资源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议修改
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 核心功能：挂载静态文件目录 (用于头像访问)
# 访问地址例如：http://localhost:8001/uploads/user_1_123456.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# --- 全局状态容器 ---
class SystemState:
    def __init__(self):
        self.db_manager = None
        self.collector = None
        self.model = None
        self.start_time = time.time()


state = SystemState()

# 初始化数据库连接
print("\n========== 系统启动初始化 ==========")
try:
    state.db_manager = DatabaseManager(DATABASE_CONFIG)
    # 测试连接
    conn = state.db_manager.get_connection()
    if conn:
        print("✅ 数据库连接成功 (Database Connected)")
        conn.close()
    else:
        print("⚠️ 数据库配置正确但连接失败")
except Exception as e:
    print(f"❌ 数据库连接异常: {e}")
    print("💡 提示：系统将以【离线模式】运行，部分功能可能受限。")

state.collector = VirtualDataCollector(state)
state.model = TransformerModel()
print("====================================\n")

# 内存验证码存储 (Email -> Code)
verification_codes = {}


# ==============================================================================
# 1. 辅助工具函数 (Utilities)
# ==============================================================================

def hash_pwd(password: str) -> str:
    """使用 Bcrypt 对密码进行加密"""
    if not password: return ""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_pwd(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    if not plain_password or not hashed_password: return False
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except:
        return False


def get_current_user(request: Request):
    """从请求头解析 JWT Token，获取当前用户信息"""
    auth_header = request.headers.get('Authorization')
    if not auth_header: return None
    try:
        # Bearer <token>
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_CONFIG['secret_key'], algorithms=[JWT_CONFIG['algorithm']])
        return payload  # {'sub': username, 'role': ..., 'uid': ...}
    except Exception:
        return None


def send_email_task(to_email: str, subject: str, body: str):
    """后台异步发送邮件任务"""
    sender = EMAIL_CONFIG.get('SENDER_EMAIL') or EMAIL_CONFIG.get('sender_email')
    password = EMAIL_CONFIG.get('SENDER_PASSWORD') or EMAIL_CONFIG.get('sender_password')
    smtp_server = EMAIL_CONFIG.get('SMTP_SERVER') or EMAIL_CONFIG.get('smtp_server')
    smtp_port = EMAIL_CONFIG.get('SMTP_PORT', 465)

    if not password or not sender:
        logger.warning("⚠️ 邮件配置缺失，无法发送邮件")
        return

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = sender
        msg['To'] = to_email

        # 默认使用 SSL
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender, password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        logger.info(f"📧 邮件成功发送至 {to_email}")
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {e}")


# ==============================================================================
# 2. 页面路由 (Page Routes)
# ==============================================================================

@app.get("/")
async def root(): return FileResponse(get_file_path("login.html"))


@app.get("/login.html")
async def page_login(): return FileResponse(get_file_path("login.html"))


@app.get("/register.html")
async def page_register(): return FileResponse(get_file_path("register.html"))


@app.get("/dashboard")
async def page_dashboard(): return FileResponse(get_file_path("dashboard.html"))


@app.get("/profile.html")
async def page_profile(): return FileResponse(get_file_path("profile.html"))


@app.get("/chat.html")
async def page_chat(): return FileResponse(get_file_path("chat.html"))


# ==============================================================================
# 3. 认证与用户管理 API (Authentication & User Management)
# ==============================================================================

@app.post("/api/auth/login")
async def login(request: Request):
    """用户登录接口"""
    data = await request.json()
    if not state.db_manager:
        raise HTTPException(status_code=500, detail="数据库未连接")

    dao = UserDao(state.db_manager)
    user = dao.find_by_username(data['username'])

    if not user or not verify_pwd(data['password'], user['password_hash']):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 JWT Token
    token_data = {
        "sub": user['username'],
        "role": user['role_type'],
        "uid": user['user_id']
    }
    token = jwt.encode(token_data, JWT_CONFIG['secret_key'], algorithm=JWT_CONFIG['algorithm'])

    # 记录最后登录时间
    try:
        conn = state.db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sys_user SET last_login=NOW() WHERE user_id=%s", (user['user_id'],))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"更新登录时间失败: {e}")

    return {
        "message": "Login Success",
        "data": {
            "access_token": token,
            "user": user  # 返回用户信息供前端缓存
        }
    }


@app.post("/api/auth/send_code")
async def send_verification_code(request: Request, background_tasks: BackgroundTasks):
    """发送验证码 (注册/找回密码)"""
    data = await request.json()
    email = data.get('email')
    if not email: raise HTTPException(400, detail="邮箱不能为空")

    code = str(random.randint(100000, 999999))
    verification_codes[email] = {"code": code, "expire": time.time() + 300}

    # 控制台打印备份
    print(f"\n👉 【验证码】 发送给 {email} : {code} \n")

    # 异步发送邮件
    background_tasks.add_task(send_email_task, email, "【GridMaster】安全验证码", f"您的验证码是：{code}，5分钟内有效。")
    return {"message": "验证码已发送"}


@app.post("/api/auth/register")
async def register(request: Request):
    """用户注册"""
    data = await request.json()
    email = data.get('email')
    code = data.get('code')

    # 校验验证码
    record = verification_codes.get(email)
    if not record or record['code'] != code:
        raise HTTPException(400, detail="验证码错误或已过期")

    dao = UserDao(state.db_manager)
    if dao.check_exists('username', data['username']):
        raise HTTPException(400, detail="用户名已存在")

    try:
        pwd_hash = hash_pwd(data['password'])
        conn = state.db_manager.get_connection()
        cur = conn.cursor()
        # 默认角色为 VIEWER，默认工号为空
        sql = """
            INSERT INTO sys_user (username, password_hash, email, role_type, real_name, employee_id) 
            VALUES (%s, %s, %s, 'VIEWER', '新用户', '')
        """
        cur.execute(sql, (data['username'], pwd_hash, email))
        conn.commit()
        conn.close()
        # 清除验证码
        del verification_codes[email]
        return {"message": "注册成功"}
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(500, detail="注册失败，请重试")


@app.post("/api/user/avatar/upload")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    """头像上传接口"""
    u = get_current_user(request)
    if not u: raise HTTPException(401, detail="未登录")

    try:
        # 生成唯一文件名
        ext = file.filename.split('.')[-1]
        filename = f"user_{u['uid']}_{int(time.time())}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # 写入文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 更新数据库
        avatar_url = f"/uploads/{filename}"
        conn = state.db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sys_user SET avatar=%s WHERE user_id=%s", (avatar_url, u['uid']))
        conn.commit()
        conn.close()

        return {"message": "上传成功", "url": avatar_url}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, detail="文件上传失败")


# ==============================================================================
# 4. 个人中心与权限管理 (Profile & Admin)
# ==============================================================================

@app.get("/api/user/profile")
async def get_profile(request: Request):
    """获取个人详细信息 (含日志)"""
    u = get_current_user(request)
    if not u: raise HTTPException(401)

    dao = UserDao(state.db_manager)
    # 使用 DAO 可能拿不到 employee_id，所以手动查一次全量
    user = dao.find_by_username(u['sub'])
    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sys_user WHERE user_id=%s", (u['uid'],))
        full_user = cur.fetchone()
        if full_user:
            user = full_user
            # 格式化时间对象
            for k in ['created_at', 'last_login']:
                if isinstance(user.get(k), datetime): user[k] = user[k].strftime("%Y-%m-%d %H:%M")
        conn.close()
    except:
        pass

    # 解析偏好设置
    if user.get('preferences') and isinstance(user['preferences'], str):
        try:
            user['preferences'] = json.loads(user['preferences'])
        except:
            user['preferences'] = {"alert_method": "site"}
    if not user.get('preferences'):
        user['preferences'] = {"alert_method": "site"}

    # 获取最近日志
    logs = []
    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sys_operation_log WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (u['uid'],))
        logs = cur.fetchall()
        conn.close()
        for log in logs:
            if isinstance(log['created_at'], datetime): log['created_at'] = log['created_at'].strftime("%Y-%m-%d %H:%M")
    except:
        pass

    return {"code": 200, "data": {"user": user, "logs": logs}}


@app.put("/api/user/profile")
async def update_profile(request: Request):
    """更新个人信息 (含工号、偏好)"""
    u = get_current_user(request)
    data = await request.json()

    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor()
        prefs = json.dumps(data.get('preferences', {}))

        cur.execute("""
            UPDATE sys_user 
            SET real_name=%s, email=%s, phone=%s, department=%s, 
                preferences=%s, employee_id=%s, avatar=%s 
            WHERE user_id=%s
        """, (
            data.get('real_name'), data.get('email'), data.get('phone'),
            data.get('department'), prefs, data.get('employee_id'),
            data.get('avatar'), u['uid']
        ))
        conn.commit();
        conn.close()
        return {"message": "OK"}
    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(500, detail="更新失败")


@app.delete("/api/user/profile")
async def delete_self(request: Request):
    """用户自行注销账户"""
    u = get_current_user(request)
    if not u: raise HTTPException(401)

    if u['role'] == 'SUPER_ADMIN':
        raise HTTPException(400, detail="超级管理员不能注销，请联系后台维护人员")

    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor()
        cur.execute("DELETE FROM sys_user WHERE user_id=%s", (u['uid'],))
        conn.commit();
        conn.close()
        return {"message": "账户已注销"}
    except:
        raise HTTPException(500, detail="操作失败")


# --- 超级管理员接口 ---

@app.get("/api/admin/users")
async def get_all_users(request: Request):
    """获取所有用户列表 (超管专用)"""
    u = get_current_user(request)
    if not u or u['role'] != 'SUPER_ADMIN': raise HTTPException(403, detail="无权访问")

    conn = state.db_manager.get_connection();
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT user_id, employee_id, username, real_name, role_type, email, department, last_login FROM sys_user")
    users = cur.fetchall()
    conn.close()

    for user in users:
        if isinstance(user.get('last_login'), datetime):
            user['last_login'] = user['last_login'].strftime("%Y-%m-%d %H:%M")
    return users


@app.put("/api/admin/user/role")
async def update_user_role(request: Request):
    """修改用户权限"""
    u = get_current_user(request)
    if not u or u['role'] != 'SUPER_ADMIN': raise HTTPException(403)

    data = await request.json()
    if int(data['user_id']) == int(u['uid']):
        raise HTTPException(400, detail="为了安全，不能修改自己的权限")

    conn = state.db_manager.get_connection();
    cur = conn.cursor()
    cur.execute("UPDATE sys_user SET role_type=%s WHERE user_id=%s", (data['role_type'], data['user_id']))
    conn.commit();
    conn.close()
    return {"message": "权限已更新"}


@app.delete("/api/admin/user/{target_uid}")
async def delete_user_admin(request: Request, target_uid: int):
    """管理员删除用户"""
    u = get_current_user(request)
    if not u or u['role'] != 'SUPER_ADMIN': raise HTTPException(403)

    if int(target_uid) == int(u['uid']):
        raise HTTPException(400, detail="不能删除自己")

    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor()
        cur.execute("DELETE FROM sys_user WHERE user_id=%s", (target_uid,))
        conn.commit();
        conn.close()
        return {"message": "用户已删除"}
    except:
        raise HTTPException(500, detail="删除失败")


@app.get("/api/admin/user/{target_uid}/logs")
async def get_user_logs(request: Request, target_uid: int):
    """查看指定用户的审计日志"""
    u = get_current_user(request)
    if not u or u['role'] != 'SUPER_ADMIN': raise HTTPException(403)

    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sys_operation_log WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (target_uid,))
        logs = cur.fetchall()
        conn.close()
        for log in logs:
            if isinstance(log['created_at'], datetime):
                log['created_at'] = log['created_at'].strftime("%Y-%m-%d %H:%M")
        return logs
    except:
        return []


# ==============================================================================
# 5. 核心业务：预测、监视、通信 (Core Business Logic)
# ==============================================================================

@app.post("/api/predict/execute")
async def execute_prediction(request: Request, bg_tasks: BackgroundTasks):
    """执行负荷预测 (包含告警逻辑)"""
    u = get_current_user(request)
    data = await request.json()
    start_time_str = data.get('start_time', '2016-05-20 08:00')

    # 模拟计算延迟
    await asyncio.sleep(0.8)

    time_axis = []
    try:
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    except:
        start_dt = datetime.now()

    for i in range(24):
        time_axis.append((start_dt + timedelta(hours=i)).strftime("%H:%M"))

    # 生成预测曲线 (模拟 Transformer 输出)
    base_load = 80 + np.random.rand() * 20
    # 加入正弦波动和随机噪声
    pred_vals = (base_load + np.sin(np.linspace(0, 6, 24)) * 10 + np.random.normal(0, 2, 24)).tolist()

    # 真实值逻辑 (仅2016年有)
    truth_vals = []
    if start_dt.year == 2016:
        truth_vals = [v + random.uniform(-5, 5) for v in pred_vals]

    # 风险评估
    max_load = max(pred_vals)
    risk_level = "Normal"
    if max_load > 105:
        risk_level = "Critical"
    elif max_load > 95:
        risk_level = "Warning"

    # 记录审计日志
    if u:
        try:
            conn = state.db_manager.get_connection();
            cur = conn.cursor()
            log_msg = f"执行节点 {data.get('bus_id')} 预测，结果: {risk_level}"
            cur.execute("INSERT INTO sys_operation_log (user_id, operation_type, ip_address) VALUES (%s, %s, %s)",
                        (u['uid'], log_msg, request.client.host))
            conn.commit();
            conn.close()
        except:
            pass

        # ⚠️ 告警触发逻辑
        if risk_level != "Normal":
            # 获取用户配置
            dao = UserDao(state.db_manager)
            user_info = dao.find_by_username(u['sub'])
            prefs = user_info.get('preferences')
            if isinstance(prefs, str): prefs = json.loads(prefs)
            method = (prefs or {}).get('alert_method', 'site')

            msg_content = f"⚠️ [负荷预警] 节点 {data.get('bus_id')} 预测峰值达 {max_load:.2f} MW，风险等级: {risk_level}"

            # 1. 站内信
            try:
                conn = state.db_manager.get_connection();
                cur = conn.cursor()
                cur.execute("INSERT INTO sys_message (sender_id, receiver_id, content) VALUES (0, %s, %s)",
                            (u['uid'], msg_content))
                conn.commit();
                conn.close()
            except:
                pass

            # 2. 邮件推送
            if (method == 'email' or method == 'both') and user_info.get('email'):
                bg_tasks.add_task(send_email_task, user_info['email'], f"【GridMaster】负荷{risk_level}告警", msg_content)

    return {
        "chart_data": {
            "time_axis": time_axis,
            "pred_vals": pred_vals,
            "truth_vals": truth_vals
        },
        "risk_assessment": {"level": risk_level, "score": 85 if risk_level == "Normal" else 40}
    }


# 🔥 之前缺失的功能：生成 AI 报告
@app.post("/api/report/generate")
async def generate_report(request: Request):
    """生成 AI 调度分析报告 (模拟)"""
    await asyncio.sleep(1.5)  # 模拟 AI 生成耗时
    return {
        "title": "GridMaster 智能调度分析报告",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "content": """
        【系统概况】
        当前电网运行平稳，全网总负荷 45,210 MW，频率维持在 50.02 Hz。

        【预测分析】
        基于 RST-Former 模型的推演结果显示，未来 24 小时内，大部分节点负荷处于安全区间。
        重点关注时段：14:00 - 16:00，预计出现日负荷高峰。

        【调度建议】
        1. 建议增加 3 号机组出力 5% 以应对午高峰。
        2. 密切监视 120 号母线电压波动情况。
        3. 备用电源系统保持热备状态。
        """,
        "author": "GridMaster AI Engine"
    }


# 通信相关接口
@app.get("/api/chat/users")
async def chat_search_users(keyword: str = ""):
    conn = state.db_manager.get_connection();
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT user_id, username, real_name, role_type, avatar FROM sys_user WHERE username LIKE %s OR real_name LIKE %s LIMIT 10",
        (f"%{keyword}%", f"%{keyword}%"))
    res = cur.fetchall()
    conn.close()
    return res


@app.post("/api/chat/send")
async def chat_send_msg(request: Request):
    u = get_current_user(request);
    data = await request.json()
    conn = state.db_manager.get_connection();
    cur = conn.cursor()
    cur.execute("INSERT INTO sys_message (sender_id, receiver_id, content) VALUES (%s, %s, %s)",
                (u['uid'], data['receiver_id'], data['content']))
    conn.commit();
    conn.close()
    return {"message": "Sent"}


@app.get("/api/chat/history")
async def chat_history(request: Request, partner_id: int):
    u = get_current_user(request)
    conn = state.db_manager.get_connection();
    cur = conn.cursor(dictionary=True)
    # 联表查询发送者名字
    sql = """
        SELECT m.*, u.username as sender_name 
        FROM sys_message m 
        JOIN sys_user u ON m.sender_id = u.user_id
        WHERE (sender_id = %s AND receiver_id = %s) 
           OR (sender_id = %s AND receiver_id = %s)
        ORDER BY created_at ASC
    """
    cur.execute(sql, (u['uid'], partner_id, partner_id, u['uid']))
    msgs = cur.fetchall()
    conn.close()
    for m in msgs: m['created_at'] = m['created_at'].strftime("%H:%M")
    return msgs


@app.get("/api/chat/contacts")
async def chat_contacts(request: Request):
    u = get_current_user(request)
    conn = state.db_manager.get_connection();
    cur = conn.cursor(dictionary=True)
    # 简单逻辑：返回所有用户除自己 (实际应返回最近联系人)
    cur.execute("SELECT user_id, username, real_name, role_type, avatar FROM sys_user WHERE user_id != %s", (u['uid'],))
    res = cur.fetchall()
    conn.close()
    return res


# 监控相关接口
@app.get("/api/monitor/overview")
async def get_monitor_overview():
    # 模拟实时数据
    status = {
        "scada": {"status": "normal", "msg": "运行正常", "value": f"{220 + random.uniform(-1, 1):.1f} kV"},
        "pmu": {"status": "normal", "msg": "相量同步", "value": f"{50 + random.uniform(-0.02, 0.02):.3f} Hz"},
        "ami": {"status": "normal", "msg": "采集率 99.8%", "value": "45210 MW"}
    }
    # 随机异常模拟
    if random.random() < 0.05:
        status["scada"] = {"status": "warning", "msg": "⚠️ 电压越下限", "value": "208.1 kV"}
    return status


@app.get("/api/collect/detail")
async def collect_detail(source_type: str):
    data = []
    now = datetime.now()
    if source_type == 'scada':
        for i in range(1, 15):
            data.append(
                {"id": f"P-{100 + i}", "time": now.strftime("%H:%M:%S"), "value": f"{220 + random.randint(-5, 5)}",
                 "unit": "kV", "status": "正常"})
    elif source_type == 'pmu':
        for i in range(1, 15):
            data.append({"id": f"PMU-{i}", "time": now.strftime("%S.%f")[:-3],
                         "value": f"{50.0 + random.uniform(-0.05, 0.05):.4f}", "unit": "Hz", "status": "同步"})
    elif source_type == 'ami':
        for i in range(1, 15):
            data.append({"id": f"M-{800 + i}", "time": now.strftime("%H:%M"), "value": f"{random.randint(100, 500)}",
                         "unit": "kWh", "status": "Success"})
    return data


@app.get("/api/history")
async def get_system_history(request: Request):
    """Dashboard 用的全站审计日志 (近24h)"""
    try:
        conn = state.db_manager.get_connection();
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT created_at as time, operation_type as action, username as user FROM sys_operation_log JOIN sys_user ON sys_operation_log.user_id = sys_user.user_id ORDER BY created_at DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            if isinstance(r['time'], datetime): r['time'] = r['time'].strftime("%H:%M")
        return rows
    except:
        return []


# 天气接口
@app.get("/api/weather/current")
async def get_weather(request: Request):
    key = AMAP_CONFIG.get('api_key')
    ip = request.client.host
    code = "110000"
    if ip != '127.0.0.1':
        try:
            r = requests.get(f"https://restapi.amap.com/v3/ip?key={key}&ip={ip}", timeout=1).json()
            if r['status'] == '1': code = r['adcode']
        except:
            pass
    try:
        r = requests.get(f"https://restapi.amap.com/v3/weather/weatherInfo?city={code}&key={key}", timeout=2).json()
        if r['lives']:
            l = r['lives'][0]
            return {"city": l['city'], "weather": l['weather'], "temperature": l['temperature'],
                    "wind": l['winddirection'] + "风", "url": "#"}
    except:
        pass
    return {"city": "模拟城市", "weather": "晴", "temperature": "25", "url": "#"}


@app.get("/api/weather/search")
async def search_city(keywords: str):
    key = AMAP_CONFIG.get('api_key')
    try:
        r = requests.get(f"https://restapi.amap.com/v3/config/district?keywords={keywords}&subdistrict=0&key={key}",
                         timeout=2).json()
        if r['districts']: return [{"name": d['name'], "adcode": d['adcode']} for d in r['districts']]
    except:
        pass
    return []


# 系统健康检查
@app.get("/api/system/health")
async def health_check():
    return {
        "status": "online",
        "db": "connected" if state.db_manager else "disconnected",
        "uptime": f"{int(time.time() - state.start_time)}s"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)