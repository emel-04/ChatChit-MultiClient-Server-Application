"""
WebSocket Server để frontend web có thể kết nối
Sử dụng aiohttp WebSocket để tương thích với browser
"""
import asyncio
import json
import ssl
import jwt
from typing import Dict, Set, Callable
from pathlib import Path
from aiohttp import web

from .database import Database
from .protocol import Message, MessageType
from .auth_handler import AuthHandler
from .chat_handler import ChatHandler
from .file_handler import FileHandler

# JWT Secret (phải giống với REST API)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"

class WebSocketChatServer:
    """WebSocket server cho frontend web"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080, 
                 ssl_cert: str = None, ssl_key: str = None):
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        
        # Initialize components (shared với TCP server)
        self.db = Database()
        self.auth_handler = AuthHandler(self.db)
        self.chat_handler = ChatHandler(self.db, self.auth_handler)
        self.file_handler = FileHandler(self.db, self.auth_handler)
        
        # WebSocket clients
        self.ws_clients: Dict[str, web.WebSocketResponse] = {}  # {client_id: websocket}
        self.send_to_client_callbacks: Dict[str, Callable] = {}  # {client_id: send_callback}
        self.client_counter = 0
        
        # Create aiohttp app
        self.app = web.Application()
        self.app.router.add_get('/', self.websocket_handler)
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # CORS middleware (cho phép frontend kết nối từ domain khác)
        self.setup_cors()
    
    def setup_cors(self):
        """Setup CORS middleware"""
        async def cors_middleware(app, handler):
            async def middleware_handler(request):
                if request.method == 'OPTIONS':
                    return web.Response(
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type',
                        }
                    )
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            return middleware_handler
        self.app.middlewares.append(cors_middleware)
    
    async def websocket_handler(self, request: web.Request):
        """Xử lý WebSocket connection"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        client_id = f"ws_client_{self.client_counter}"
        self.client_counter += 1
        
        client_addr = request.remote
        print(f"[{client_id}] WebSocket client kết nối từ {client_addr}")
        
        # Lưu WebSocket connection
        self.ws_clients[client_id] = ws
        
        # Đăng ký callback để gửi message
        async def send_to_client(data):
            try:
                # Nếu là dict (JSON), gửi trực tiếp
                if isinstance(data, dict):
                    await ws.send_json(data)
                # Nếu là bytes, decode trước
                elif isinstance(data, bytes):
                    message = Message.decode(data)
                    if message:
                        await ws.send_json(message)
                else:
                    print(f"Lỗi: data type không hợp lệ: {type(data)}")
            except Exception as e:
                print(f"Lỗi gửi WebSocket message: {e}")
                # Nếu decode lỗi, thử gửi trực tiếp JSON
                try:
                    await ws.send_json({"type": "ERROR", "data": {"message": "Lỗi xử lý message"}})
                except:
                    pass
        
        # Lưu callback để đăng ký sau khi authenticate
        self.send_to_client_callbacks[client_id] = send_to_client
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        # Parse JSON message từ frontend
                        data = json.loads(msg.data)
                        await self.process_websocket_message(client_id, data, ws)
                    except json.JSONDecodeError:
                        await ws.send_json({
                            "type": "ERROR",
                            "data": {
                                "success": False,
                                "message": "Invalid JSON format"
                            }
                        })
                    except Exception as e:
                        print(f"[{client_id}] Lỗi xử lý message: {e}")
                        await ws.send_json({
                            "type": "ERROR",
                            "data": {
                                "success": False,
                                "message": f"Server error: {str(e)}"
                            }
                        })
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[{client_id}] WebSocket error: {ws.exception()}")
                    break
        except Exception as e:
            print(f"[{client_id}] Lỗi WebSocket: {e}")
        finally:
            # Cleanup
            await self.disconnect_client(client_id)
        
        return ws
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def process_websocket_message(self, client_id: str, message: dict, ws: web.WebSocketResponse):
        """Xử lý message từ WebSocket client"""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        # Convert WebSocket message format sang internal format và xử lý
        response = None
        
        # Xử lý AUTH - xác thực JWT token từ frontend
        if msg_type == "AUTH":
            token = data.get('token', '')
            if not token:
                response = {
                    "type": "ERROR",
                    "data": {
                        "success": False,
                        "message": "Token không được cung cấp"
                    }
                }
            else:
                payload = self.verify_token(token)
                if payload:
                    username = payload.get('username')
                    if username:
                        # Đăng nhập user vào auth_handler
                        # Tạo một login request giả để authenticate
                        login_data = {'username': username, 'password': ''}  # Password không cần vì đã verify token
                        # Kiểm tra user có tồn tại trong DB không
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                        user = cursor.fetchone()
                        conn.close()
                        
                        if user:
                            # Authenticate user
                            self.auth_handler.authenticated_users[client_id] = username
                            
                            # Đăng ký client sau khi authenticate thành công
                            send_to_client = self.send_to_client_callbacks.get(client_id)
                            if send_to_client:
                                await self.chat_handler.register_client(client_id, send_to_client)
                                self.file_handler.register_client(client_id, send_to_client)
                            
                            # Gửi danh sách online users cho user mới (bao gồm cả user hiện tại)
                            # Đợi một chút để đảm bảo user đã được thêm vào danh sách
                            import asyncio
                            await asyncio.sleep(0.1)  # Đợi 100ms để đảm bảo register_client đã hoàn thành
                            online_users = self.chat_handler.get_online_users()
                            online_users_msg = {
                                "type": "online_users",
                                "data": {
                                    "users": online_users
                                }
                            }
                            await ws.send_json(online_users_msg)
                            
                            response = {
                                "type": "SUCCESS",
                                "data": {
                                    "success": True,
                                    "message": "Xác thực thành công",
                                    "username": username
                                }
                            }
                            print(f"[{client_id}] User {username} đã xác thực qua JWT token")
                        else:
                            response = {
                                "type": "ERROR",
                                "data": {
                                    "success": False,
                                    "message": "User không tồn tại"
                                }
                            }
                    else:
                        response = {
                            "type": "ERROR",
                            "data": {
                                "success": False,
                                "message": "Token không hợp lệ"
                            }
                        }
                else:
                    response = {
                        "type": "ERROR",
                        "data": {
                            "success": False,
                            "message": "Token không hợp lệ hoặc đã hết hạn"
                        }
                    }
        
        elif msg_type == MessageType.REGISTER.value:
            response_bytes = await self.auth_handler.handle_register(client_id, data)
            response = Message.decode(response_bytes)
        
        elif msg_type == MessageType.LOGIN.value:
            response_bytes = await self.auth_handler.handle_login(client_id, data)
            response = Message.decode(response_bytes)
            if response and response.get('data', {}).get('success'):
                username = response['data'].get('username')
                if username:
                    # Lưu username mapping
                    pass
        
        elif msg_type == MessageType.LOGOUT.value:
            response_bytes = await self.auth_handler.handle_logout(client_id)
            response = Message.decode(response_bytes)
        
        elif msg_type == MessageType.CHAT.value:
            if not self.auth_handler.is_authenticated(client_id):
                response = {
                    "type": "ERROR",
                    "data": {
                        "success": False,
                        "message": "Bạn cần đăng nhập trước"
                    }
                }
            else:
                username = self.auth_handler.get_username(client_id)
                response_bytes = await self.chat_handler.handle_chat(client_id, username, data)
                response = Message.decode(response_bytes)
        
        elif msg_type == MessageType.FILE_REQUEST.value:
            if not self.auth_handler.is_authenticated(client_id):
                response = {
                    "type": "ERROR",
                    "data": {
                        "success": False,
                        "message": "Bạn cần đăng nhập trước"
                    }
                }
            else:
                username = self.auth_handler.get_username(client_id)
                response_bytes = await self.file_handler.handle_file_request(client_id, username, data)
                response = Message.decode(response_bytes)
        
        elif msg_type == MessageType.FILE_DATA.value:
            if not self.auth_handler.is_authenticated(client_id):
                response = {
                    "type": "ERROR",
                    "data": {
                        "success": False,
                        "message": "Bạn cần đăng nhập trước"
                    }
                }
            else:
                transfer_id = data.get('transfer_id', '')
                response_bytes = await self.file_handler.handle_file_data(client_id, transfer_id, data)
                response = Message.decode(response_bytes)
        
        elif msg_type == "USER_LIST":
            if not self.auth_handler.is_authenticated(client_id):
                response = {
                    "type": "ERROR",
                    "data": {
                        "success": False,
                        "message": "Bạn cần đăng nhập trước"
                    }
                }
            else:
                users = self.auth_handler.get_all_users()
                response = {
                    "type": "USER_LIST",
                    "data": {
                        "success": True,
                        "message": "Danh sách users",
                        "users": users
                    }
                }
        
        else:
            response = {
                "type": "ERROR",
                "data": {
                    "success": False,
                    "message": f"Loại message không hợp lệ: {msg_type}"
                }
            }
        
        # Gửi response
        if response:
            await ws.send_json(response)
    
    async def disconnect_client(self, client_id: str):
        """Xử lý khi client disconnect"""
        if client_id in self.ws_clients:
            username = self.auth_handler.get_username(client_id) if self.auth_handler.is_authenticated(client_id) else None
            print(f"[{client_id}] WebSocket client {username or 'unknown'} đã ngắt kết nối")
            
            # Unregister từ handlers (phải làm trước khi logout để broadcast offline status)
            if self.auth_handler.is_authenticated(client_id):
                await self.chat_handler.unregister_client(client_id)
                self.file_handler.unregister_client(client_id)
                await self.auth_handler.handle_logout(client_id)
            
            # Đóng WebSocket
            try:
                ws = self.ws_clients[client_id]
                await ws.close()
            except:
                pass
            
            # Xóa khỏi clients và callbacks
            del self.ws_clients[client_id]
            if hasattr(self, 'send_to_client_callbacks') and client_id in self.send_to_client_callbacks:
                del self.send_to_client_callbacks[client_id]
    
    def get_ssl_context(self):
        """Tạo SSL context nếu có certificate"""
        if not self.ssl_cert or not self.ssl_key:
            return None
        
        if not Path(self.ssl_cert).exists() or not Path(self.ssl_key).exists():
            return None
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.ssl_cert, self.ssl_key)
        return context
    
    async def start(self):
        """Khởi động WebSocket server"""
        ssl_context = self.get_ssl_context()
        
        if ssl_context:
            print(f"WebSocket Server đang khởi động với SSL tại {self.host}:{self.port}")
        else:
            print(f"WebSocket Server đang khởi động không SSL tại {self.host}:{self.port}")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            self.host,
            self.port,
            ssl_context=ssl_context
        )
        
        await site.start()
        print(f"WebSocket Server đã sẵn sàng. Kết nối tại ws://{self.host}:{self.port}/ws")
        
        # Chạy forever
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nĐang dừng WebSocket server...")
            await runner.cleanup()

