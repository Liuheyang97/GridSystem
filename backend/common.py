# backend/common.py
import os
import time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
# 注意：这里假设你使用的是 python-jose 或 PyJWT，需要根据你的实际环境调整
# 如果报错 import error，请 pip install python-jose[cryptography]
from jose import jwt, JWTError
from backend.config.settings import DATABASE_CONFIG, SECRET_KEY, ALGORITHM
from backend.utils.database import DatabaseManager
from backend.services.data_collector import VirtualDataCollector
from backend.models.model import TransformerModel

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
HTML_DIR = os.path.join(BASE_DIR, 'frontend', 'pages')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 定义 OAuth2 scheme，指向你的登录接口 URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI 依赖项：验证 Token 并获取当前用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码 JWT Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role_type: str = payload.get("role_type")  # 确保 Token 生成时包含此字段

        if username is None:
            raise credentials_exception

        # 返回用户信息字典，供 business.py 使用
        # business.py 需要: user_id, username, role_type, real_name(可选)
        return {
            "username": username,
            "user_id": user_id,
            "role_type": role_type,
            "real_name": payload.get("real_name", username),
            "email": payload.get("email")
        }

    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"Auth Error: {e}")
        raise credentials_exception

class SystemState:
    def __init__(self):
        self.db_manager = None
        self.collector = None
        self.model = None
        self.start_time = time.time()

    def init_db(self):
        try:
            print("🔄 [Common] 正在连接数据库...")
            self.db_manager = DatabaseManager(DATABASE_CONFIG)
            conn = self.db_manager.get_connection()
            if conn:
                print(f"✅ [Common] 数据库连接成功！")
                conn.close()
            else:
                print("⚠️ [Common] 数据库连接返回 None")
        except Exception as e:
            print(f"❌ [Common] 数据库异常: {e}")

# 🔥 全局唯一单例
state = SystemState()
# 预加载（防止其他模块调用时报错）
state.collector = VirtualDataCollector(state)
state.model = TransformerModel()