import time
import asyncio
import random
import json
import shutil
import os
import re
import math
import numpy as np
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, UploadFile, File, Depends

from backend.common import state, UPLOAD_DIR
from backend.utils.security import get_current_user, send_email_task
from backend.config.settings import AMAP_CONFIG, MODEL_CONFIG, TIME_MAPPING_CONFIG, ALERT_CONFIG, PERMISSION_CONFIG

try:
    from backend.services.weather_service import weather_service
    from backend.services.professional_data_collector import professional_collector
    from backend.services.ai_dispatch_assistant import ai_assistant
except ImportError:
    weather_service = None
    professional_collector = None
    ai_assistant = None

router = APIRouter(prefix="/api", tags=["Business"])

# ==============================================================================
# 🔥 数据集加载器 & 强制拓扑分配
# ==============================================================================
REAL_DATASET = None
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
NPY_PATH = os.path.join(DATA_DIR, 'gnn_X_2016_fusion.npy')
MAT_FILE_1 = os.path.join(DATA_DIR, 'ACTIVSg2000.m')
MAT_FILE_2 = os.path.join(DATA_DIR, 'case_ACTIVSg2000.m')

TOPOLOGY_CACHE = None
NODE_METADATA_MAP = {}


def load_real_dataset():
    global REAL_DATASET
    if REAL_DATASET is not None: return
    if os.path.exists(NPY_PATH):
        try:
            print(f"🔄 挂载数据集: {NPY_PATH}")
            REAL_DATASET = np.load(NPY_PATH, mmap_mode='r')
            print(f"✅ 数据集挂载成功! Shape: {REAL_DATASET.shape}")
        except:
            try:
                REAL_DATASET = np.load(NPY_PATH, allow_pickle=True)
            except:
                pass


load_real_dataset()


def parse_and_distribute_topology():
    global NODE_METADATA_MAP, TOPOLOGY_CACHE
    if TOPOLOGY_CACHE: return TOPOLOGY_CACHE

    print("📊 开始构建全网拓扑结构...")
    counts = {"wind": 87, "solar": 22, "hydro": 46, "thermal": 400}
    target_file = MAT_FILE_1 if os.path.exists(MAT_FILE_1) else (MAT_FILE_2 if os.path.exists(MAT_FILE_2) else None)

    if target_file:
        try:
            with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                c_wind = len(re.findall(r"'wind'", content, re.IGNORECASE))
                c_solar = len(re.findall(r"'solar'", content, re.IGNORECASE))
                c_hydro = len(re.findall(r"'hydro'", content, re.IGNORECASE))
                c_ng = len(re.findall(r"'ng'", content, re.IGNORECASE))
                c_coal = len(re.findall(r"'coal'", content, re.IGNORECASE))
                c_nuclear = len(re.findall(r"'nuclear'", content, re.IGNORECASE))

                if c_wind > 0 or c_solar > 0:
                    counts["wind"] = c_wind
                    counts["solar"] = c_solar
                    counts["hydro"] = c_hydro
                    counts["thermal"] = c_ng + c_coal + c_nuclear
        except Exception as e:
            print(f"⚠️ 解析 .m 文件失败，使用默认比例: {e}")

    total_nodes = 1351
    assigned_types = []
    assigned_types.extend(['wind'] * counts['wind'])
    assigned_types.extend(['solar'] * counts['solar'])
    assigned_types.extend(['hydro'] * counts['hydro'])
    remaining_slots = total_nodes - len(assigned_types)
    n_thermal = min(counts['thermal'], int(remaining_slots * 0.3))
    assigned_types.extend(['thermal'] * n_thermal)
    n_load = total_nodes - len(assigned_types)
    assigned_types.extend(['load'] * n_load)
    assigned_types = assigned_types[:total_nodes]

    rng = random.Random(2026)
    rng.shuffle(assigned_types)

    categories = {
        "wind": {"label": "风力发电 (Wind)", "icon": "ri-windy-line", "color": "text-emerald-400", "nodes": []},
        "solar": {"label": "光伏发电 (Solar)", "icon": "ri-sun-line", "color": "text-yellow-400", "nodes": []},
        "hydro": {"label": "水力发电 (Hydro)", "icon": "ri-drop-line", "color": "text-blue-400", "nodes": []},
        "thermal": {"label": "火力发电 (Thermal)", "icon": "ri-fire-line", "color": "text-orange-400", "nodes": []},
        "load": {"label": "居民/工业负荷 (Load)", "icon": "ri-home-4-line", "color": "text-slate-400", "nodes": []},
    }

    for i, type_key in enumerate(assigned_types):
        node_id = i + 1
        NODE_METADATA_MAP[node_id] = {"real_id": node_id, "type": type_key}
        categories[type_key]["nodes"].append({
            "id": node_id,
            "name": f"节点 {node_id}",
            "voltage": "220kV"
        })

    for cat in categories.values():
        cat["nodes"].sort(key=lambda x: x["id"])

    TOPOLOGY_CACHE = [
        {"key": k, **v, "count": len(v["nodes"])}
        for k, v in categories.items()
    ]
    return TOPOLOGY_CACHE


def get_node_type_info(node_id: int):
    if not NODE_METADATA_MAP: parse_and_distribute_topology()
    return NODE_METADATA_MAP.get(node_id, {"real_id": node_id, "type": "load"})


def get_node_stats(node_id: int):
    if REAL_DATASET is not None:
        try:
            node_idx = node_id - 1
            if node_idx < REAL_DATASET.shape[1]:
                if len(REAL_DATASET.shape) == 3:
                    series = REAL_DATASET[:, node_idx, 0]
                else:
                    series = REAL_DATASET[:, node_idx]
                return {'mean': float(np.mean(series)), 'max': float(np.max(series))}
        except:
            pass
    return None


def get_node_max_capacity(node_id: int):
    stats = get_node_stats(node_id)
    if stats: return stats['max'] * 1.1
    return (100 + (node_id % 50) * 2) * 1.8


def get_node_val(node_id: int, dt: datetime, force_real_only=False):
    if dt.year == 2016 and REAL_DATASET is not None:
        try:
            start_2016 = datetime(2016, 1, 1, 0, 0)
            hour_idx = int((dt - start_2016).total_seconds() // 3600)
            node_idx = node_id - 1
            if 0 <= hour_idx < len(REAL_DATASET):
                val = float(REAL_DATASET[hour_idx, node_idx, 0] if len(REAL_DATASET.shape) == 3 else REAL_DATASET[
                    hour_idx, node_idx])
                return val
        except:
            pass

    if force_real_only: return None

    stats = get_node_stats(node_id)
    base = stats['mean'] if stats else (100 + (node_id % 50) * 2)
    meta = get_node_type_info(node_id)
    ntype = meta['type']
    hour = dt.hour + dt.minute / 60.0

    if ntype == 'solar':
        if 6 <= hour <= 19:
            pattern = math.sin((hour - 6) * math.pi / 13);
            pattern = max(0, pattern) * 3.0
        else:
            pattern = 0
        season = 1.3 if dt.month in [6, 7, 8] else 0.7
    elif ntype == 'wind':
        pattern = 1 + 0.4 * math.cos((hour) * math.pi / 12)
        season = 1.3 if dt.month in [12, 1, 2] else 0.8
    else:
        pattern = 1 + 0.5 * (math.sin((hour - 6) * math.pi / 12) ** 2 + 0.5 * math.sin((hour - 18) * math.pi / 6) ** 2)
        season = 1.2 if dt.month in [6, 7, 8, 12, 1, 2] else 1.0

    seed = node_id + dt.year + dt.month * 100 + dt.day * 10 + dt.hour
    np.random.seed(seed)
    val = base * season * pattern + np.random.normal(0, base * 0.05)
    return max(0, val)


# ==============================================================================
# 🔥 接口区
# ==============================================================================
@router.get("/topology/structure")
async def get_topology_structure(request: Request):
    return parse_and_distribute_topology()


@router.get("/chat/contacts")
async def chat_contacts(request: Request):
    u = get_current_user(request)
    if not u: raise HTTPException(401, detail="Not logged in")  # 🛡️ 安检门
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute("UPDATE sys_user SET last_login = NOW() WHERE user_id = %s", (u['uid'],))
        conn.commit()
        sql = """SELECT u.user_id, u.username, u.real_name, u.role_type, u.avatar, u.last_login,
                (SELECT COUNT(*) FROM sys_message m WHERE m.sender_id = u.user_id AND m.receiver_id = %s AND m.is_read = 0) as unread_count,
                IF(u.last_login > NOW() - INTERVAL 60 SECOND, 1, 0) as is_online
            FROM sys_user u WHERE u.user_id != %s"""
        cur.execute(sql, (u['uid'], u['uid']))
        res = cur.fetchall()
        for user in res:
            if isinstance(user.get('last_login'), datetime): user['last_login'] = user['last_login'].strftime(
                "%Y-%m-%d %H:%M")
        return res
    finally:
        conn.close()


@router.post("/chat/upload")
async def chat_upload(request: Request, file: UploadFile = File(...)):
    u = get_current_user(request)
    if not u: raise HTTPException(401)
    try:
        ext = file.filename.split('.')[-1]
        filename = f"chat_{u['uid']}_{int(time.time())}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_type = "image" if ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else "file"
        return {"code": 200, "url": f"/uploads/{filename}", "type": file_type, "name": file.filename}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/chat/history")
async def chat_history(request: Request, partner_id: int):
    u = get_current_user(request)
    if not u: raise HTTPException(401, detail="Not logged in")  # 🛡️ 安检门
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        if partner_id != 0:
            cur.execute("UPDATE sys_message SET is_read = 1 WHERE sender_id = %s AND receiver_id = %s",
                        (partner_id, u['uid']))
            conn.commit()
        if partner_id == 0:
            sql = "SELECT m.*, u.username as sender_name, u.role_type as sender_role FROM sys_message m LEFT JOIN sys_user u ON m.sender_id = u.user_id WHERE m.receiver_id = 0 OR (m.sender_id = 0 AND m.receiver_id = %s) ORDER BY created_at ASC"
            cur.execute(sql, (u['uid'],))
        else:
            sql = "SELECT m.*, u.username as sender_name FROM sys_message m LEFT JOIN sys_user u ON m.sender_id = u.user_id WHERE (m.sender_id = %s AND m.receiver_id = %s) OR (m.sender_id = %s AND m.receiver_id = %s) ORDER BY created_at ASC"
            cur.execute(sql, (u['uid'], partner_id, partner_id, u['uid']))
        msgs = cur.fetchall()
        for m in msgs:
            if isinstance(m['created_at'], datetime): m['created_at'] = m['created_at'].strftime("%m-%d %H:%M")
        return msgs
    finally:
        conn.close()


@router.post("/chat/send")
async def chat_send(request: Request):
    u = get_current_user(request);
    if not u: raise HTTPException(401, detail="Not logged in")  # 🛡️ 安检门
    data = await request.json()
    receiver_id = int(data.get('receiver_id'));
    raw_content = data.get('content')
    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        if receiver_id == 0:
            if u['role'] != 'SUPER_ADMIN': raise HTTPException(403, detail="权限不足")
            cur.execute("SELECT real_name FROM sys_user WHERE user_id=%s", (u['uid'],))
            row = cur.fetchone()
            real_name = row['real_name'] if row else u['sub']
            final_content = f"【系统公告】由超级管理员 {real_name} 发布：\n{raw_content}"
            cur.execute("INSERT INTO sys_message (sender_id, receiver_id, content) VALUES (%s, 0, %s)",
                        (u['uid'], final_content))
        else:
            cur.execute("INSERT INTO sys_message (sender_id, receiver_id, content) VALUES (%s, %s, %s)",
                        (u['uid'], receiver_id, raw_content))
        conn.commit()
        return {"message": "OK"}
    finally:
        conn.close()


@router.get("/chat/users")
async def chat_search(keyword: str = ""):
    conn = state.db_manager.get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    cur.execute(
        "SELECT user_id, username, real_name, role_type, avatar FROM sys_user WHERE (username LIKE %s OR real_name LIKE %s) LIMIT 10",
        (f"%{keyword}%", f"%{keyword}%"))
    res = cur.fetchall();
    conn.close()
    return res


@router.post("/predict/execute")
async def execute_predict(request: Request, bg: BackgroundTasks):
    u = get_current_user(request);
    data = await request.json()
    start_str = data.get('start_time', '2026-01-01 08:00')
    bus_id = data.get('bus_id', 1)
    horizon = int(data.get('horizon', 24))

    if horizon < 1: horizon = 1
    if horizon > 24: horizon = 24
    if not (1 <= bus_id <= 1351): raise HTTPException(400, "无效节点ID")

    await asyncio.sleep(0.1)
    load_real_dataset()
    try:
        target_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
    except:
        target_dt = datetime.now()

    rated_capacity = get_node_max_capacity(bus_id)
    time_axis, pred_vals, truth_vals = [], [], []

    for i in range(horizon):
        curr_dt = target_dt + timedelta(hours=i)
        time_axis.append(curr_dt.strftime("%Y-%m-%d %H:%M"))
        base_for_pred = get_node_val(bus_id, curr_dt, force_real_only=False)
        np.random.seed(int(curr_dt.timestamp()) + bus_id)
        pred = base_for_pred * (1 + np.random.normal(0, 0.03))
        pred_vals.append(round(pred, 2))
        real_val = get_node_val(bus_id, curr_dt, force_real_only=True)
        truth_vals.append(round(real_val, 2) if real_val is not None else None)

    mx = max(pred_vals)
    risk = "Normal"
    if mx > rated_capacity * 1.0:
        risk = "Critical"
    elif mx > rated_capacity * 0.9:
        risk = "Warning"
    capacity_usage_val = (mx / rated_capacity) * 100 if rated_capacity > 0 else 0

    if ai_assistant:
        ai_assistant.update_prediction_context({
            'bus_id': bus_id, 'risk_level': risk, 'peak_load': mx,
            'peak_time': time_axis[np.argmax(pred_vals)], 'capacity_usage': capacity_usage_val
        })

    if u:
        conn = state.db_manager.get_connection()
        try:
            cur = conn.cursor(dictionary=True, buffered=True)
            cur.execute("INSERT INTO sys_operation_log (user_id, operation_type, ip_address) VALUES (%s, %s, %s)",
                        (u['uid'], f'预测节点{bus_id} ({horizon}h) 风险:{risk}', request.client.host))
            if risk != "Normal":
                msg = f"⚠️ [风险告警] 节点{bus_id} 预测峰值 {mx:.1f}MW (负荷率{capacity_usage_val:.1f}%)"
                cur.execute("INSERT INTO sys_message (sender_id, receiver_id, content) VALUES (0, %s, %s)",
                            (u['uid'], msg))
                cur.execute("SELECT email FROM sys_user WHERE user_id=%s", (u['uid'],))
                if user_info := cur.fetchone():
                    if user_info['email']: bg.add_task(send_email_task, user_info['email'], f"GridMaster 告警", msg)
            conn.commit()
        finally:
            conn.close()

    return {
        "chart_data": {"time_axis": time_axis, "pred_vals": pred_vals, "truth_vals": truth_vals},
        "risk_assessment": {"level": risk, "score": 95 if risk == "Normal" else 50}
    }


@router.post("/ai/chat")
async def ai_chat(request: Request):
    u = get_current_user(request);
    data = await request.json()
    if ai_assistant:
        resp = ai_assistant.process_message(data.get('message', ''), {'user': u})
        return {"success": True, "message": resp}
    return {"success": True, "message": "AI初始化中"}


@router.get("/ai/auto-report")
async def ai_report(request: Request):
    if ai_assistant: return {"success": True,
                             "report": ai_assistant.generate_auto_report(ai_assistant.prediction_cache)}
    return {"success": False}


@router.get("/monitor/overview")
async def m_over():
    if professional_collector: return professional_collector.fetch_system_monitoring()
    return {"scada": {"status": "normal"}}


@router.get("/collect/detail")
async def c_detail(source_type: str, request: Request):
    u = get_current_user(request)
    if source_type == 'ami':
        if not u: raise HTTPException(401, detail="Not logged in")  # 🛡️ 安检门
        if u['role'] != 'SUPER_ADMIN': return [{"access_denied": True, "message": "权限不足"}]

    if professional_collector:
        if source_type == 'scada': return professional_collector.fetch_scada_realtime(1)
        if source_type == 'pmu': return professional_collector.fetch_pmu_realtime(1)
        if source_type == 'ami': return professional_collector.fetch_ami_realtime(1)
    return []


@router.get("/weather/current")
async def get_w(request: Request):
    if weather_service: return weather_service.get_current_weather_by_ip(request.client.host)
    return {'city': '模拟', 'weather': '晴', 'temperature': '25'}


@router.get("/weather/search")
async def s_city(keywords: str):
    if weather_service: return weather_service.search_city(keywords)
    return []


@router.get("/weather/city/{adcode}")
async def w_city(adcode: str):
    if weather_service: return weather_service.get_weather_by_adcode(adcode)
    return {}


@router.get("/history")
async def get_history(request: Request):
    u = get_current_user(request)
    if not u: raise HTTPException(401, detail="Not logged in")  # 🛡️ 修复：这里就是您刚才报错的地方

    conn = state.db_manager.get_connection()
    try:
        cur = conn.cursor(dictionary=True, buffered=True)
        cur.execute(
            "SELECT created_at as op_time, operation_type as action FROM sys_operation_log WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
            (u['uid'],))
        rows = cur.fetchall()
        for r in rows:
            if isinstance(r['op_time'], datetime): r['op_time'] = r['op_time'].strftime("%H:%M")
            act = r.get('action', '')
            if 'Critical' in act:
                r['risk_label'] = 'Critical'
            elif 'Warning' in act:
                r['risk_label'] = 'Warning'
            else:
                r['risk_label'] = 'Normal'
        return rows
    finally:
        conn.close()


@router.get("/system/health")
async def health(): return {"status": "online", "uptime": f"{int(time.time() - state.start_time)}s"}