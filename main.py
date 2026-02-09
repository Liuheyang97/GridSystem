import uvicorn
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 🔥 核心修正：从 common 导入 state，保证全局唯一！
from backend.common import state, UPLOAD_DIR, HTML_DIR, BASE_DIR
# 导入路由
from backend.routers import auth, user_admin, business, pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GridMaster")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n========== 系统正在启动 (Lifespan) ==========")
    # 🔥 关键：在这里初始化 common 里的 state
    state.init_db()

    print(f"✅ 静态目录: {UPLOAD_DIR}")
    print(f"✅ 页面目录: {HTML_DIR}")

    # 再次检查 DB 是否真的连上了
    if state.db_manager:
        print("✅ 全局 State 数据库状态: 已连接")
    else:
        print("❌ 全局 State 数据库状态: 未连接 (请检查配置)")

    print("===========================================\n")
    yield
    print("🛑 系统关闭")


app = FastAPI(title="GridMaster V9.9.23 Modular", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载资源
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
if os.path.exists(os.path.join(BASE_DIR, 'frontend', 'static')):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, 'frontend', 'static')), name="static")

# 注册路由
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(user_admin.router)
app.include_router(business.router)

if __name__ == "__main__":
    # 端口可以改，避免端口冲突
    uvicorn.run(app, host="0.0.0.0", port=8001)