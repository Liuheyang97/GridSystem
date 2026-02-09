import bcrypt
import jwt
import smtplib
import logging
from email.mime.text import MIMEText
from email.header import Header
from fastapi import Request
from backend.config.settings import JWT_CONFIG, EMAIL_CONFIG

logger = logging.getLogger("GridMaster")


def hash_pwd(password: str) -> str:
    if not password: return ""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_pwd(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password: return False
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except:
        return False


def get_current_user(request: Request):
    auth = request.headers.get('Authorization')
    if not auth: return None
    try:
        token = auth.split(" ")[1]
        return jwt.decode(token, JWT_CONFIG['secret_key'], algorithms=[JWT_CONFIG['algorithm']])
    except:
        return None


def send_email_task(to_email: str, subject: str, body: str):
    """
    发送邮件任务 (修复连接问题)
    """
    # 1. 获取配置 (兼容大小写)
    smtp_server = EMAIL_CONFIG.get('SMTP_SERVER') or EMAIL_CONFIG.get('smtp_server')
    smtp_port = EMAIL_CONFIG.get('SMTP_PORT') or EMAIL_CONFIG.get('smtp_port') or 465
    sender = EMAIL_CONFIG.get('SENDER_EMAIL') or EMAIL_CONFIG.get('sender_email')
    password = EMAIL_CONFIG.get('SENDER_PASSWORD') or EMAIL_CONFIG.get('sender_password')

    if not password or not sender or not smtp_server:
        logger.error("❌ 邮件配置缺失，无法发送。请检查 settings.py")
        return

    try:
        # 2. 构建邮件
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = sender
        msg['To'] = to_email

        # 3. 发送 (使用 with 语句自动管理连接，修复 'please run connect() first')
        logger.info(f"🔄 正在连接邮件服务器: {smtp_server}:{smtp_port}...")

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender, password)
            server.sendmail(sender, [to_email], msg.as_string())

        logger.info(f"✅ 邮件已成功发送至 {to_email}")

    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {str(e)}")