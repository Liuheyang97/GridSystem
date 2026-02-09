import mysql.connector
from mysql.connector import pooling
import logging
import json
import bcrypt

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, config):
        self.pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="grid_pool", pool_size=5, **config)

    def get_connection(self):
        try:
            return self.pool.get_connection()
        except Exception as e:
            logger.error(f"DB连接失败: {e}")
            return None


class BaseDao:
    def __init__(self, db_manager): self.db = db_manager


class UserDao(BaseDao):
    def find_by_username(self, username):
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sys_user WHERE username = %s", (username,))
            return cursor.fetchone()
        finally:
            conn.close()

    def find_by_id(self, uid):
        conn = self.db.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sys_user WHERE user_id = %s", (uid,))
            return cursor.fetchone()
        finally:
            conn.close()

    def check_exists(self, field, value):
        conn = self.db.get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            if field not in ['username', 'phone', 'email']: return False
            sql = f"SELECT user_id FROM sys_user WHERE {field} = %s"
            cursor.execute(sql, (value,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_user_v4(self, data):
        conn = self.db.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            pwd_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
            sql = "INSERT INTO sys_user (username, password_hash, phone, email, real_name, role_type, created_at) VALUES (%s, %s, %s, %s, %s, 'VIEWER', NOW())"
            cursor.execute(sql, (data['username'], pwd_hash, data['phone'], data['email'], data['username']))
            conn.commit()
        finally:
            conn.close()

    # 🔥 修复点：确保 address 被正确更新
    def update_profile_v4(self, uid, data):
        conn = self.db.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            sql = """UPDATE sys_user SET 
                     real_name=%s, gender=%s, employee_id=%s, phone=%s, email=%s, 
                     address=%s, department=%s, preferences=%s, mfa_enabled=%s
                     WHERE user_id=%s"""

            pref = json.dumps(data.get('preferences', {}))
            mfa = 1 if data.get('mfa_enabled') else 0

            vals = (data.get('real_name'), data.get('gender'), data.get('employee_id'),
                    data.get('phone'), data.get('email'), data.get('address'), data.get('department'),
                    pref, mfa, uid)
            cursor.execute(sql, vals)
            conn.commit()
        except Exception as e:
            logger.error(f"更新失败: {e}")
            raise e  # 抛出异常让上层知道
        finally:
            conn.close()

    def update_password(self, uid, new_hash):
        conn = self.db.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE sys_user SET password_hash=%s WHERE user_id=%s", (new_hash, uid))
            conn.commit()
        finally:
            conn.close()

    def log_access(self, uid, ip, action, status):
        conn = self.db.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sys_access_log (user_id, ip_address, action, status) VALUES (%s, %s, %s, %s)",
                           (uid, ip, action, status))
            conn.commit()
        except:
            pass
        finally:
            conn.close()

    def get_access_logs(self, uid):
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM sys_access_log WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (uid,))
            for row in cursor:
                if row.get('created_at'): row['created_at'] = row['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            return cursor.fetchall()
        finally:
            conn.close()


class PredictionDao(BaseDao):
    # 🔥 修复点：确保字段名与数据库完全一致
    def save_result(self, data):
        conn = self.db.get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            sql = """INSERT INTO prediction_result 
                     (user_id, bus_id, predict_time, forecast_start_time, pred_value, lower_bound, upper_bound, confidence_interval, model_version)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            vals = (data['user_id'], data['bus_id'], data['predict_time'], data['forecast_start_time'],
                    data['pred_value'], data['lower_bound'], data['upper_bound'],
                    json.dumps(data['confidence_interval']), data['model_version'])
            cursor.execute(sql, vals)
            conn.commit()
        except Exception as e:
            logger.error(f"预测结果保存失败: {e}")
            raise e
        finally:
            conn.close()

    def get_history_by_user(self, user_id, limit=20):
        conn = self.db.get_connection()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            sql = "SELECT * FROM prediction_result WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
            cursor.execute(sql, (user_id, limit))
            return cursor.fetchall()
        finally:
            conn.close()


def create_dao(manager, type):
    if type == 'user': return UserDao(manager)
    if type == 'prediction': return PredictionDao(manager)