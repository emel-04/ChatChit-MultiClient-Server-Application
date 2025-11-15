"""
Xử lý authentication (đăng ký, đăng nhập)
"""
from .database import Database
from .protocol import Message, MessageType

class AuthHandler:
    def __init__(self, db: Database):
        self.db = db
        self.authenticated_users = {}  # {client_id: username}
    
    async def handle_register(self, client_id: str, data: dict) -> bytes:
        """Xử lý đăng ký - nhận username từ form"""
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Username, email và password không được để trống"
            )
        
        if len(username) < 3:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Username phải có ít nhất 3 ký tự"
            )
        
        if '@' not in email:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Email không hợp lệ"
            )
        
        if len(password) < 6:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Password phải có ít nhất 6 ký tự"
            )
        
        success, message, registered_username = self.db.register_user(username, email, password)
        
        if success:
            return Message.create_response(
                MessageType.SUCCESS,
                True,
                message,
                {"action": "register", "email": email, "username": registered_username}
            )
        else:
            return Message.create_response(
                MessageType.ERROR,
                False,
                message
            )
    
    async def handle_login(self, client_id: str, data: dict) -> bytes:
        """Xử lý đăng nhập - chỉ dùng email"""
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Email và password không được để trống"
            )
        
        success, message, username = self.db.authenticate_user(email, password)
        
        if success and username:
            self.authenticated_users[client_id] = username
            return Message.create_response(
                MessageType.SUCCESS,
                True,
                message,
                {
                    "action": "login",
                    "username": username,
                    "email": email
                }
            )
        else:
            return Message.create_response(
                MessageType.ERROR,
                False,
                message
            )
    
    async def handle_logout(self, client_id: str) -> bytes:
        """Xử lý đăng xuất"""
        if client_id in self.authenticated_users:
            username = self.authenticated_users.pop(client_id)
            return Message.create_response(
                MessageType.SUCCESS,
                True,
                f"Đăng xuất thành công",
                {"action": "logout", "username": username}
            )
        else:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Bạn chưa đăng nhập"
            )
    
    def is_authenticated(self, client_id: str) -> bool:
        """Kiểm tra client đã đăng nhập chưa"""
        return client_id in self.authenticated_users
    
    def get_username(self, client_id: str) -> str:
        """Lấy username của client"""
        return self.authenticated_users.get(client_id, None)
    
    def get_all_users(self) -> list:
        """Lấy danh sách tất cả users đang online"""
        return list(self.authenticated_users.values())

