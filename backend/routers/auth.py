import shutil, jwt, random, time, os, json, sys
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, UploadFile, File, Depends
from backend.common import state, UPLOAD_DIR, get_current_user
from backend.utils.security import hash_pwd, verify_pwd, send_email_task
from backend.config.settings import JWT_CONFIG

# --- 2FA 库检查与调试 ---
print(f"🔍 [Auth Debug] 当前 Python 解释器: {sys.executable}")
try:
    import pyotp

    print("✅ [Auth Debug] pyotp 库导入成功")
except ImportError:
    pyotp = None
    print("❌ [Auth Debug] 严重错误：未找到 pyotp 库！2FA 将无法工作。")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# 内存验证码存储 (生产环境建议用 Redis)
# 格式: { "email": { "code": "123456", "expire": timestamp } }
verification_codes = {}


@router.post("/login")
async def login(request: Request):
    data = await request.json()
    if not state.db_manager: raise HTTPException(500, detail="DB未连接")

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sys_user WHERE username=%s", (data['username'],))
        user = cur.fetchone()

        if not user or not verify_pwd(data['password'], user['password_hash']):
            raise HTTPException(401, detail="用户名或密码错误")

        # =================================================================
        # 🔥 2FA 调试与拦截逻辑
        # =================================================================
        secret = user.get('mfa_secret')
        print(f"🔍 [Auth Debug] 用户 {user['username']} 登录尝试...")

        if secret and len(secret) > 5:
            if pyotp:
                code = data.get('verification_code')

                # 情况A：没传验证码 -> 返回 206 让前端弹窗
                if not code:
                    print("   -> 🛑 拦截登录：返回 206 (需要 2FA)")
                    return {
                        "code": 206,
                        "message": "2FA Required",
                        "data": {"mfa_required": True}
                    }

                # 情况B：传了验证码 -> 校验
                try:
                    totp = pyotp.TOTP(secret)
                    if not totp.verify(code):
                        print(f"   -> ❌ 验证码错误: 输入={code}")
                        raise HTTPException(400, detail="二步验证码错误")
                    print("   -> ✅ 验证码正确，放行")
                except Exception as e:
                    print(f"   -> ⚠️ 校验过程异常: {e}")
                    raise HTTPException(400, detail="验证失败")
            else:
                print("   -> ⚠️ 跳过 2FA：服务器缺少 pyotp 库")
        # =================================================================

        # 生成 Token
        token = jwt.encode({
            "sub": user['username'],
            "role": user['role_type'],
            "uid": user['user_id']
        }, JWT_CONFIG['secret_key'], algorithm=JWT_CONFIG['algorithm'])

        cur.execute("UPDATE sys_user SET last_login=NOW() WHERE user_id=%s", (user['user_id'],))
        conn.commit()

        # 🔥 数据清洗（防止黑屏）
        for k, v in user.items():
            if isinstance(v, datetime):
                user[k] = v.strftime("%Y-%m-%d %H:%M:%S")

        # 确保 preferences 是干净的 JSON 对象
        if user.get('preferences'):
            if isinstance(user['preferences'], str):
                try:
                    user['preferences'] = json.loads(user['preferences'])
                    if "0" in user['preferences'] and "1" in user['preferences']:
                        user['preferences'] = {"alert_method": "site"}
                except:
                    user['preferences'] = {"alert_method": "site"}
        else:
            user['preferences'] = {"alert_method": "site"}

        return {"code": 200, "message": "Success", "data": {"access_token": token, "user": user}}
    finally:
        conn.close()


@router.post("/send_code")
async def send_code(request: Request, bg: BackgroundTasks):
    data = await request.json()
    email = data.get('email')
    username = data.get('username')

    # 简单的验证：确保该邮箱确实属于该用户 (防止恶意请求)
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sys_user WHERE username=%s AND email=%s", (username, email))
        if not cur.fetchone():
            raise HTTPException(404, detail="用户名与邮箱不匹配")
    finally:
        conn.close()

    code = str(random.randint(100000, 999999))
    # 有效期 5 分钟
    verification_codes[email] = {"code": code, "expire": time.time() + 300}

    print(f"📧 [Email Debug] 向 {email} 发送验证码: {code}")  # 方便本地测试看控制台
    bg.add_task(send_email_task, email, "GridMaster 安全验证码", f"您正在进行敏感操作，验证码为：{code}，有效期5分钟。")
    return {"message": "OK"}


# 🔥🔥🔥 [新增] 重置密码接口 🔥🔥🔥
@router.post("/reset_password")
async def reset_password(request: Request):
    data = await request.json()
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
    username = data.get('username')

    if not all([email, code, new_password, username]):
        raise HTTPException(400, detail="参数不完整")

    # 1. 校验验证码
    record = verification_codes.get(email)
    if not record:
        raise HTTPException(400, detail="请先获取验证码")

    if str(record['code']) != str(code):
        raise HTTPException(400, detail="验证码错误")

    if time.time() > record['expire']:
        raise HTTPException(400, detail="验证码已过期，请重新获取")

    # 2. 修改数据库
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor()
        # 双重检查用户是否存在
        cur.execute("SELECT user_id FROM sys_user WHERE username=%s AND email=%s", (username, email))
        if not cur.fetchone():
            raise HTTPException(404, detail="用户不存在")

        # 更新密码 (记得 Hash!)
        hashed = hash_pwd(new_password)
        cur.execute("UPDATE sys_user SET password_hash=%s WHERE username=%s", (hashed, username))
        conn.commit()

        # 3. 清除验证码 (防止复用)
        del verification_codes[email]

        return {"code": 200, "message": "密码重置成功"}
    except Exception as e:
        print(f"❌ 重置密码失败: {e}")
        raise HTTPException(500, detail="服务器内部错误")
    finally:
        conn.close()


@router.post("/register")
async def register(request: Request):
    data = await request.json()
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sys_user WHERE username=%s", (data['username'],))
        if cur.fetchone(): raise HTTPException(400, detail="用户已存在")
        cur.execute(
            "INSERT INTO sys_user (username, password_hash, email, role_type, real_name) VALUES (%s, %s, %s, 'VIEWER', '新用户')",
            (data['username'], hash_pwd(data['password']), data['email']))
        conn.commit()
        return {"message": "注册成功"}
    finally:
        conn.close()


@router.post("/avatar/upload")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    u = current_user
    if not u: raise HTTPException(401)
    try:
        ext = file.filename.split('.')[-1]
        filename = f"user_{u['uid']}_{int(time.time())}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        avatar_url = f"/uploads/{filename}"
        conn = state.db_manager.get_connection()
        conn.cursor().execute("UPDATE sys_user SET avatar=%s WHERE user_id=%s", (avatar_url, u['uid']))
        conn.commit()
        conn.close()
        return {"message": "Success", "url": avatar_url}
    except Exception as e:
        raise HTTPException(500, detail="上传失败")

# # 🔥 修复：头像上传 (使用统一 UPLOAD_DIR)
# @router.post("/avatar/upload")  # 前端请求的是 /api/auth/avatar/upload (或者 user/avatar/upload，注意前缀)
# # 为了兼容之前的路径，我们这里修正一下
# async def upload_avatar(request: Request, file: UploadFile = File(...)):
#     u = get_current_user(request)
#     if not u: raise HTTPException(401)
#
#     try:
#         ext = file.filename.split('.')[-1]
#         filename = f"user_{u['uid']}_{int(time.time())}.{ext}"
#         # 使用统一的绝对路径
#         file_path = os.path.join(UPLOAD_DIR, filename)
#
#         print(f"📂 [Upload] Saving to: {file_path}")  # 调试日志
#
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#
#         avatar_url = f"/uploads/{filename}"
#
#         conn = state.db_manager.get_connection();
#         cur = conn.cursor()
#         cur.execute("UPDATE sys_user SET avatar=%s WHERE user_id=%s", (avatar_url, u['uid']))
#         conn.commit();
#         conn.close()
#
#         return {"message": "Success", "url": avatar_url}
#     except Exception as e:
#         print(f"❌ [Upload Error] {e}")
#         raise HTTPException(500, detail="上传失败")