"""
Database models và quản lý kết nối database
"""
import sqlite3
import hashlib
import os
from typing import Optional, Tuple
import bcrypt

class Database:
    def __init__(self, db_path: str = "chat_app.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Tạo kết nối database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Khởi tạo database và tạo bảng users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_username TEXT NOT NULL,
                receiver_username TEXT,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                file_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_username) REFERENCES users(username)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Đăng ký user mới - nhận username từ form
        Returns: (success, message, username)
        """
        try:
            if not username or not email or not password:
                return False, "Username, email và password không được để trống", None
            
            # Validate username
            username = username.strip()
            if len(username) < 3:
                return False, "Username phải có ít nhất 3 ký tự", None
            
            # Validate email format cơ bản
            if '@' not in email:
                return False, "Email không hợp lệ", None
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra username đã tồn tại
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username đã tồn tại", None
            
            # Kiểm tra email đã tồn tại
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return False, "Email đã tồn tại", None
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Thêm user mới
            cursor.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                (username, password_hash, email)
            )
            conn.commit()
            conn.close()
            return True, "Đăng ký thành công", username
        
        except Exception as e:
            return False, f"Lỗi đăng ký: {str(e)}", None
    
    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Xác thực user - chỉ dùng email
        Returns: (success, message, username) - username để trả về cho client
        """
        try:
            if not email or not password:
                return False, "Email và password không được để trống", None
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Tìm user theo email
            cursor.execute(
                "SELECT username, password_hash FROM users WHERE email = ?",
                (email,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "Email không tồn tại", None
            
            username = result['username']
            password_hash = result['password_hash']
            
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                # Cập nhật last_login
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE email = ?",
                    (email,)
                )
                conn.commit()
                conn.close()
                return True, "Đăng nhập thành công", username
            else:
                return False, "Mật khẩu không đúng", None
        
        except Exception as e:
            return False, f"Lỗi đăng nhập: {str(e)}", None
    
    def user_exists(self, username: str) -> bool:
        """Kiểm tra user có tồn tại không"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def save_message(self, sender: str, receiver: str, message: str, 
                    message_type: str = 'text', file_path: str = None):
        """Lưu message vào database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO messages (sender_username, receiver_username, message, message_type, file_path)
                   VALUES (?, ?, ?, ?, ?)""",
                (sender, receiver, message, message_type, file_path)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Lỗi lưu message: {e}")

