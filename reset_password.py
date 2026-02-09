import mysql.connector
import bcrypt
from backend.config.settings import DATABASE_CONFIG

# 1. 设置我们要重置的密码
NEW_PASSWORD = "admin123"


def force_reset_password():
    print("🔌 正在连接数据库...")
    try:
        # 连接数据库
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()

        # 2. 生成一个新的、绝对正确的哈希值
        # 这是你的环境生成的Hash，绝对匹配
        hashed = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt())
        # 将 bytes 转为 string 存入数据库
        hashed_str = hashed.decode('utf-8')

        print(f"🔑 生成的新哈希值: {hashed_str}")

        # 3. 强制更新所有用户的密码
        sql = "UPDATE sys_user SET password_hash = %s"
        cursor.execute(sql, (hashed_str,))

        conn.commit()  # 提交修改
        print(f"✅ 成功！已将 {cursor.rowcount} 个用户的密码重置为: {NEW_PASSWORD}")

        # 4. 验证一下
        cursor.execute("SELECT username, password_hash FROM sys_user LIMIT 1")
        user = cursor.fetchone()
        print(f"🧐 验证数据库记录: 用户 {user[0]} 的哈希现在是 {user[1]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        print("请检查 backend/config/settings.py 里的数据库密码是否正确！")


if __name__ == "__main__":
    force_reset_password()