import json
import shutil
import os
import time
import random
import io
import base64
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from backend.common import state, UPLOAD_DIR
from backend.utils.security import get_current_user, hash_pwd, verify_pwd

# 尝试导入 2FA 库
try:
    import pyotp
    import qrcode
except ImportError:
    pyotp = None
    qrcode = None
    print("⚠️ 警告: 未安装 pyotp 或 qrcode，2FA 功能不可用")

router = APIRouter(prefix="/api", tags=["User & Admin"])

# ==============================================================================
# 👤 个人中心接口
# ==============================================================================

@router.get("/user/profile")
async def get_profile(request: Request):
    u = get_current_user(request)
    if not u: raise HTTPException(401, detail="Not logged in")

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute("SELECT * FROM sys_user WHERE user_id=%s", (u['uid'],))
        user = cur.fetchone()
        if not user: raise HTTPException(404, detail="User not found")

        # 🛡️ 偏好设置解析与容错
        if user.get('preferences'):
            if isinstance(user['preferences'], str):
                try:
                    user['preferences'] = json.loads(user['preferences'])
                    # 如果解析出来是那种坏掉的字典 (key是数字字符串)，强制重置
                    if "0" in user['preferences'] and "1" in user['preferences']:
                        user['preferences'] = {"alert_method": "site"}
                except:
                    user['preferences'] = {"alert_method": "site"}
        else:
            user['preferences'] = {"alert_method": "site"}

        # 格式化时间
        for k in ['last_login', 'created_at']:
            if isinstance(user.get(k), datetime): user[k] = user[k].strftime("%Y-%m-%d %H:%M")

        # 🔥 权限与角色逻辑 🔥
        raw_role = user.get('role_type', 'VIEWER')
        if raw_role is None: raw_role = 'VIEWER'
        role = str(raw_role).upper().strip()

        # 2. OT 域逻辑
        if role == 'VIEWER':
            ot_status = "locked"
            ot_desc = "No Access (Operator+)"
        else:
            ot_status = "active"
            ot_desc = "Real-time Monitoring/Control"

        # 3. IT 域逻辑
        if role == 'SUPER_ADMIN':
            it_status = "active"
            it_desc = "Advanced Metering (Admin)"
        else:
            it_status = "locked"
            it_desc = "Access Denied (Super Admin Only)"

        access_domains = [
            {"name": "SCADA (OT)", "desc": ot_desc, "status": ot_status},
            {"name": "WAMS (OT)", "desc": ot_desc, "status": ot_status},
            {"name": "AMI (IT)", "desc": it_desc, "status": it_status}
        ]

        # 📜 获取审计日志
        logs = []
        try:
            cur.execute("SELECT operation_type, created_at FROM sys_operation_log WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (u['uid'],))
            logs = cur.fetchall()
            for log in logs:
                if isinstance(log['created_at'], datetime):
                    log['created_at'] = log['created_at'].strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            print(f"Error fetching logs: {e}")
            logs = []

        response_data = {
            "user": user,
            "logs": logs,
            "permissions": {
                "role_label": get_role_label(role),
                "access_domains": access_domains,
                "can_edit_system": role == 'SUPER_ADMIN',
                "mfa_enabled": bool(user.get('mfa_secret')) # 以前端判断密钥是否存在为准
            }
        }
        return {"code": 200, "data": response_data}
    finally:
        conn.close()


@router.put("/user/profile")
async def update_profile(request: Request):
    u = get_current_user(request)
    data = await request.json()
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(buffered=True)
        update_fields = []
        params = []

        if 'real_name' in data:
            update_fields.append("real_name=%s")
            params.append(data['real_name'])
        if 'phone' in data:
            update_fields.append("phone=%s")
            params.append(data['phone'])
        if 'email' in data:
            update_fields.append("email=%s")
            params.append(data['email'])

        if update_fields:
            params.append(u['uid'])
            cur.execute(f"UPDATE sys_user SET {', '.join(update_fields)} WHERE user_id=%s", tuple(params))

        if 'preferences' in data:
            # 🔥 修复：确保正确存入 JSON，防止坏数据
            pref_data = data['preferences']
            if isinstance(pref_data, dict):
                pref_json = json.dumps(pref_data, ensure_ascii=False)
            elif isinstance(pref_data, str):
                # 如果发来的是字符串，先校验是否为有效JSON，避免双重序列化
                try:
                    json.loads(pref_data) # 尝试解析
                    pref_json = pref_data # 是有效的JSON串，直接用
                except:
                    # 不是JSON串，可能是普通字符串，封装一下
                    pref_json = json.dumps({"alert_method": pref_data}, ensure_ascii=False)
            else:
                pref_json = json.dumps({"alert_method": "site"}) # 默认

            cur.execute("UPDATE sys_user SET preferences=%s WHERE user_id=%s", (pref_json, u['uid']))

        conn.commit()
        return {"code": 200, "message": "Saved successfully"}
    finally:
        conn.close()


# ==============================================================================
# 🔐 2FA 接口 (修复版)
# ==============================================================================

@router.get("/user/2fa/generate")
async def generate_2fa(request: Request):
    u = get_current_user(request)
    if pyotp is None or qrcode is None:
        raise HTTPException(501, detail="Server missing 2FA libraries")

    secret = pyotp.random_base32()
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=u['sub'], issuer_name="GridMaster")

    img = qrcode.make(otp_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return {
        "secret": secret,
        "qrcode": f"data:image/png;base64,{img_str}",
        "otp_auth_url": otp_uri
    }


@router.post("/user/2fa/enable")
async def enable_2fa(request: Request):
    u = get_current_user(request)
    data = await request.json()
    secret = data.get('secret')
    code = data.get('code')

    if not pyotp: raise HTTPException(501, detail="2FA libraries missing")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        raise HTTPException(400, detail="验证码错误")

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor()
        # 🔥 修复：同时更新 mfa_secret 和 mfa_enabled
        cur.execute("UPDATE sys_user SET mfa_secret=%s, mfa_enabled=1 WHERE user_id=%s", (secret, u['uid']))
        conn.commit()
        return {"code": 200, "message": "2FA 已开启"}
    finally:
        conn.close()


@router.post("/user/2fa/disable")
async def disable_2fa(request: Request):
    u = get_current_user(request)
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor()
        # 🔥 修复：同时清空密钥和关闭开关，并修复了逗号缺失的 Bug (u['uid'],)
        cur.execute("UPDATE sys_user SET mfa_secret=NULL, mfa_enabled=0 WHERE user_id=%s", (u['uid'],))
        conn.commit()
        return {"code": 200, "message": "2FA 已关闭"}
    finally:
        conn.close()


# ... 辅助函数 ...

def get_role_label(role):
    role = str(role).upper().strip()
    return {"SUPER_ADMIN": "Super Admin", "ADMIN": "System Admin", "OPERATOR": "Operator", "VIEWER": "Viewer"}.get(role, role)


@router.post("/user/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    u = get_current_user(request)
    try:
        ext = file.filename.split('.')[-1]
        filename = f"avatar_{u['uid']}_{int(time.time())}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as b:
            shutil.copyfileobj(file.file, b)
        url = f"/uploads/{filename}"
        conn = state.db_manager.get_connection()
        conn.cursor().execute("UPDATE sys_user SET avatar=%s WHERE user_id=%s", (url, u['uid']))
        conn.commit()
        conn.close()
        return {"code": 200, "url": url}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.post("/user/password")
async def change_pwd(request: Request):
    u = get_current_user(request)
    data = await request.json()
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute("SELECT password_hash FROM sys_user WHERE user_id=%s", (u['uid'],))
        if not verify_pwd(data.get('old_password'), cur.fetchone()['password_hash']):
            raise HTTPException(400, detail="Old password incorrect")
        cur.execute("UPDATE sys_user SET password_hash=%s WHERE user_id=%s",
                    (hash_pwd(data['new_password']), u['uid']))
        conn.commit()
        return {"code": 200, "message": "Password changed"}
    finally:
        conn.close()


# --- Admin 接口 ---
@router.get("/admin/users")
async def list_users(request: Request, page: int = 1, size: int = 10, keyword: str = ""):
    u = get_current_user(request)
    role = str(u.get('role', '')).upper().strip()
    if role != 'SUPER_ADMIN': raise HTTPException(403)

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        off = (page - 1) * size
        cur.execute(
            "SELECT user_id, username, real_name, role_type, email, last_login, mfa_enabled FROM sys_user WHERE username LIKE %s LIMIT %s OFFSET %s",
            (f"%{keyword}%", size, off))
        users = cur.fetchall()
        cur.execute("SELECT COUNT(*) as total FROM sys_user WHERE username LIKE %s", (f"%{keyword}%",))
        return {"data": users, "total": cur.fetchone()['total']}
    finally:
        conn.close()


@router.post("/admin/user/role")
async def update_user_role(request: Request):
    u = get_current_user(request)
    role = str(u.get('role', '')).upper().strip()
    if role != 'SUPER_ADMIN': raise HTTPException(403)

    data = await request.json()
    if int(data['user_id']) == int(u['uid']): raise HTTPException(400, detail="Cannot change own role")
    conn = state.db_manager.get_connection()
    try:
        conn.cursor().execute("UPDATE sys_user SET role_type=%s WHERE user_id=%s",
                              (data['role_type'], data['user_id']))
        conn.commit()
        return {"message": "OK"}
    finally:
        conn.close()


@router.delete("/admin/user/{tid}")
async def delete_user(request: Request, tid: int):
    u = get_current_user(request)
    role = str(u.get('role', '')).upper().strip()
    if role != 'SUPER_ADMIN': raise HTTPException(403)
    if int(tid) == int(u['uid']): raise HTTPException(400, detail="Cannot delete self")
    conn = state.db_manager.get_connection()
    try:
        conn.cursor().execute("DELETE FROM sys_user WHERE user_id=%s", (tid,))
        conn.commit()
        return {"message": "Deleted"}
    finally:
        conn.close()


@router.get("/admin/user/{tid}/logs")
async def get_user_logs(request: Request, tid: int):
    u = get_current_user(request)
    role = str(u.get('role', '')).upper().strip()
    if role != 'SUPER_ADMIN': raise HTTPException(403)
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute("SELECT * FROM sys_operation_log WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (tid,))
        logs = cur.fetchall()
        for l in logs:
            if isinstance(l['created_at'], datetime): l['created_at'] = l['created_at'].strftime("%Y-%m-%d %H:%M")
        return logs
    finally:
        conn.close()