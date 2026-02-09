import os
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Pages"])

# 路径计算
BASE_DIR = os.getcwd()
HTML_DIR = os.path.join(BASE_DIR, 'frontend', 'pages')

def get_page(name):
    return os.path.join(HTML_DIR, name)

@router.get("/")
async def root(): return FileResponse(get_page("login.html"))

@router.get("/{page}.html")
async def get_html(page: str):
    return FileResponse(get_page(f"{page}.html"))

@router.get("/dashboard")
async def dashboard(): return FileResponse(get_page("dashboard.html"))