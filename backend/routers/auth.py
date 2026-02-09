# backend/routers/auth.py
import shutil, jwt, random, time, os
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, UploadFile, File, Depends
from backend.common import state, UPLOAD_DIR, get_current_user  # 👈 引用统一配置
from backend.utils.security import hash_pwd, verify_pwd, send_email_task, get_current_user
from backend.config.settings import JWT_CONFIG

router = APIRouter(prefix="/api/auth", tags=["Auth"])
verification_codes = {}


@router.post("/login")
async def login(request: Request):
    data = await request.json()
    if not state.db_manager: raise HTTPException(500, detail="DB未连接")

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        # 🔥 调试日志：看看前端到底传了啥
        print(f"🔐 [Login Attempt] Username: {data.get('username')}")

        cur.execute("SELECT * FROM sys_user WHERE username=%s", (data['username'],))
        user = cur.fetchone()

        # 🔥 调试日志：看看数据库到底查出了啥
        if user:
            print(f"👤 [User Found] ID: {user['user_id']}, Role: {user['role_type']}")
        else:
            print("❌ [User Not Found]")

        if not user or not verify_pwd(data['password'], user['password_hash']):
            raise HTTPException(401, detail="用户名或密码错误")

        # 生成 Token
        token = jwt.encode({
            "sub": user['username'],
            "role": user['role_type'],
            "uid": user['user_id']
        }, JWT_CONFIG['secret_key'], algorithm=JWT_CONFIG['algorithm'])

        # 更新登录时间
        cur.execute("UPDATE sys_user SET last_login=NOW() WHERE user_id=%s", (user['user_id'],))
        conn.commit()

        return {"message": "Success", "data": {"access_token": token, "user": user}}
    finally:
        conn.close()


@router.post("/send_code")
async def send_code(request: Request, bg: BackgroundTasks):
    data = await request.json()
    code = str(random.randint(100000, 999999))
    verification_codes[data['email']] = {"code": code, "expire": time.time() + 300}
    print(f"📧 [Email Code] To: {data['email']} Code: {code}")
    bg.add_task(send_email_task, data['email'], "验证码", f"验证码：{code}")
    return {"message": "OK"}


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

# 2. 修改头像上传接口
@router.post("/avatar/upload")
# 3. 参数变化：使用 Depends 注入用户，而不是在函数体里手动解析 request
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user) # 👈 使用 FastAPI 的依赖注入
):
    # 这一行删掉，因为 Depends 已经帮你拿到了
    # u = get_current_user(request)
    u = current_user # 为了兼容下面的代码，把变量名赋给 u

    if not u: raise HTTPException(401)

    try:
        # 下面的逻辑保持不变
        ext = file.filename.split('.')[-1]
        filename = f"user_{u['user_id']}_{int(time.time())}.{ext}" # 注意：common返回的是user_id还是uid，要保持一致
        file_path = os.path.join(UPLOAD_DIR, filename)

        print(f"📂 [Upload] Saving to: {file_path}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avatar_url = f"/uploads/{filename}"

        if state.db_manager:
            conn = state.db_manager.get_connection()
            cur = conn.cursor()
            # 注意 key 名：common.py 返回的是 'user_id' 还是 'uid'？通常建议统一用 user_id
            cur.execute("UPDATE sys_user SET avatar=%s WHERE user_id=%s", (avatar_url, u['user_id']))
            conn.commit()
            conn.close()

        return {"message": "Success", "url": avatar_url}
    except Exception as e:
        print(f"❌ [Upload Error] {e}")
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