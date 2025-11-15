"""
RESTful API Server với HTTP/HTTPS
Hỗ trợ các endpoints: đăng ký, đăng nhập, chat, file, tìm kiếm
"""
import asyncio
import json
import ssl
import traceback
from pathlib import Path
from aiohttp import web
from aiohttp.web_middlewares import normalize_path_middleware
import jwt
from datetime import datetime, timedelta

from .database import Database
from .protocol import Message
from .auth_handler import AuthHandler
from .chat_handler import ChatHandler
from .file_handler import FileHandler

# JWT Secret (trong production nên dùng environment variable)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

class RESTAPIServer:
    """RESTful API Server"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8000,
                 ssl_cert: str = None, ssl_key: str = None):
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        
        # Initialize components
        self.db = Database()
        self.auth_handler = AuthHandler(self.db)
        self.chat_handler = ChatHandler(self.db, self.auth_handler)
        self.file_handler = FileHandler(self.db, self.auth_handler)
        
        # Create aiohttp app
        # CORS middleware phải chạy đầu tiên để xử lý OPTIONS requests
        self.app = web.Application(middlewares=[
            self.cors_middleware,  # CORS middleware phải đứng đầu
            normalize_path_middleware(),
            self.logging_middleware,
            self.error_middleware
        ])
        
        # Routes
        self.setup_routes()
    
    @web.middleware
    async def cors_middleware(self, request: web.Request, handler):
        """CORS middleware để xử lý preflight requests"""
        # Lấy origin từ request header
        origin = request.headers.get('Origin', '*')
        
        print(f"[CORS] {request.method} {request.path_qs} - Origin: {origin}")
        
        # Xử lý OPTIONS preflight request
        if request.method == 'OPTIONS':
            print(f"[CORS] Handling OPTIONS preflight for {request.path_qs}")
            response = web.Response(
                status=200,
                headers={
                    'Access-Control-Allow-Origin': origin if origin != '*' else '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                    'Access-Control-Max-Age': '3600',
                }
            )
            print(f"[CORS] OPTIONS response headers: {dict(response.headers)}")
            return response
        
        # Xử lý các request khác
        try:
            response = await handler(request)
        except Exception as e:
            # Nếu có lỗi, vẫn cần thêm CORS headers
            print(f"[CORS] Error in handler: {e}")
            raise
        
        # Thêm CORS headers vào response
        cors_origin = origin if origin != '*' else '*'
        response.headers['Access-Control-Allow-Origin'] = cors_origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        print(f"[CORS] Added headers to {request.method} {request.path_qs}: Origin={cors_origin}")
        
        return response
    
    @web.middleware
    async def logging_middleware(self, request: web.Request, handler):
        """Middleware để log requests"""
        start_time = datetime.utcnow()
        try:
            response = await handler(request)
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path_qs} - {response.status} ({duration:.3f}s)")
            return response
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path_qs} - ERROR ({duration:.3f}s): {str(e)}")
            raise
    
    @web.middleware
    async def error_middleware(self, request: web.Request, handler):
        """Middleware để xử lý errors"""
        try:
            response = await handler(request)
            return response
        except web.HTTPException:
            raise
        except Exception as e:
            print(f"Unhandled error in {request.method} {request.path_qs}:")
            traceback.print_exc()
            return web.json_response(
                {'success': False, 'message': f'Lỗi server: {str(e)}'},
                status=500
            )
    
    def setup_routes(self):
        """Setup API routes"""
        # Auth routes
        self.app.router.add_post('/api/auth/register', self.register)
        self.app.router.add_post('/api/auth/login', self.login)
        self.app.router.add_post('/api/auth/logout', self.logout)
        self.app.router.add_get('/api/auth/me', self.get_current_user)
        
        # Chat routes
        self.app.router.add_get('/api/chat/messages', self.get_messages)
        self.app.router.add_post('/api/chat/send', self.send_message)
        self.app.router.add_get('/api/chat/conversations', self.get_conversations)
        
        # User routes
        self.app.router.add_get('/api/users/search', self.search_users)
        self.app.router.add_get('/api/users/online', self.get_online_users)
        self.app.router.add_get('/api/users/{username}', self.get_user_info)
        
        # File routes
        self.app.router.add_post('/api/files/upload', self.upload_file)
        self.app.router.add_get('/api/files/{file_id}', self.download_file)
        
        # Health check
        self.app.router.add_get('/api/health', self.health_check)
        
        # Root endpoint
        self.app.router.add_get('/', self.root)
    
    def generate_token(self, username: str) -> str:
        """Tạo JWT token"""
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def get_current_user_from_request(self, request: web.Request) -> str:
        """Lấy username từ JWT token trong request"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer '
        payload = self.verify_token(token)
        if not payload:
            return None
        
        return payload.get('username')
    
    # Auth endpoints
    async def register(self, request: web.Request):
        """POST /api/auth/register - nhận username từ form"""
        try:
            data = await request.json()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            
            print(f"[REGISTER] Attempt: username={username}, email={email}")
            
            if not username or not email or not password:
                return web.json_response(
                    {'success': False, 'message': 'Username, email và password không được để trống'},
                    status=400
                )
            
            # Sử dụng auth_handler
            client_id = f"rest_{username}_{datetime.utcnow().timestamp()}"
            response_bytes = await self.auth_handler.handle_register(client_id, {
                'username': username,
                'email': email,
                'password': password
            })
            
            response = Message.decode(response_bytes)
            print(f"[REGISTER] Response: {response}")
            
            if response and response.get('data', {}).get('success'):
                # Lấy username từ response
                registered_username = response.get('data', {}).get('username', username)
                # Tạo token
                token = self.generate_token(registered_username)
                print(f"[REGISTER] Success: username={registered_username}, email={email}")
                return web.json_response({
                    'success': True,
                    'message': 'Đăng ký thành công',
                    'token': token,
                    'user': {'username': registered_username, 'email': email}
                })
            else:
                message = response.get('data', {}).get('message', 'Đăng ký thất bại') if response else 'Đăng ký thất bại'
                print(f"[REGISTER] Failed: {message}")
                return web.json_response(
                    {'success': False, 'message': message},
                    status=400
                )
        except json.JSONDecodeError as e:
            print(f"[REGISTER] JSON decode error: {e}")
            return web.json_response(
                {'success': False, 'message': 'Invalid JSON format'},
                status=400
            )
        except Exception as e:
            print(f"[REGISTER] Exception: {e}")
            traceback.print_exc()
            return web.json_response(
                {'success': False, 'message': f'Lỗi server: {str(e)}'},
                status=500
            )
    
    async def login(self, request: web.Request):
        """POST /api/auth/login - chỉ dùng email"""
        try:
            data = await request.json()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            
            print(f"[LOGIN] Attempt: email={email}")
            
            if not email or not password:
                return web.json_response(
                    {'success': False, 'message': 'Email và password không được để trống'},
                    status=400
                )
            
            client_id = f"rest_{email}_{datetime.utcnow().timestamp()}"
            response_bytes = await self.auth_handler.handle_login(client_id, {
                'email': email,
                'password': password
            })
            
            from .protocol import Message
            response = Message.decode(response_bytes)
            print(f"[LOGIN] Response: {response}")
            
            if response and response.get('data', {}).get('success'):
                # Lấy username từ response
                username = response.get('data', {}).get('username', '')
                # Tạo token
                token = self.generate_token(username)
                print(f"[LOGIN] Success: email={email}, username={username}")
                return web.json_response({
                    'success': True,
                    'message': 'Đăng nhập thành công',
                    'token': token,
                    'user': {'username': username, 'email': email}
                })
            else:
                message = response.get('data', {}).get('message', 'Đăng nhập thất bại') if response else 'Đăng nhập thất bại'
                print(f"[LOGIN] Failed: {message}")
                return web.json_response(
                    {'success': False, 'message': message},
                    status=401
                )
        except json.JSONDecodeError as e:
            print(f"[LOGIN] JSON decode error: {e}")
            return web.json_response(
                {'success': False, 'message': 'Invalid JSON format'},
                status=400
            )
        except Exception as e:
            print(f"[LOGIN] Exception: {e}")
            traceback.print_exc()
            return web.json_response(
                {'success': False, 'message': f'Lỗi server: {str(e)}'},
                status=500
            )
    
    async def logout(self, request: web.Request):
        """POST /api/auth/logout"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        # Logout logic (có thể thêm vào auth_handler)
        return web.json_response({
            'success': True,
            'message': 'Đăng xuất thành công'
        })
    
    async def get_current_user(self, request: web.Request):
        """GET /api/auth/me"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        # Lấy thông tin user từ database
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return web.json_response({
                'success': True,
                'user': {
                    'username': user['username'],
                    'email': user['email'],
                    'created_at': user['created_at']
                }
            })
        else:
            return web.json_response(
                {'success': False, 'message': 'User not found'},
                status=404
            )
    
    # Chat endpoints
    async def get_messages(self, request: web.Request):
        """GET /api/chat/messages?receiver=username&limit=50&offset=0"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        receiver = request.query.get('receiver', '')
        limit = int(request.query.get('limit', 50))
        offset = int(request.query.get('offset', 0))
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if receiver:
            # Private messages
            cursor.execute("""
                SELECT * FROM messages 
                WHERE (sender_username = ? AND receiver_username = ?) 
                   OR (sender_username = ? AND receiver_username = ?)
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (username, receiver, receiver, username, limit, offset))
        else:
            # Broadcast messages
            cursor.execute("""
                SELECT * FROM messages 
                WHERE receiver_username IS NULL
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        messages = []
        for row in cursor.fetchall():
            msg_dict = dict(row)
            # Extract file_id từ file_path nếu có
            if msg_dict.get('file_path'):
                file_path = msg_dict['file_path']
                # Format: uploads/{file_id}_{filename}
                import os
                from pathlib import Path
                path_obj = Path(file_path)
                filename = os.path.basename(file_path)
                if '_' in filename:
                    file_id = filename.split('_', 1)[0]
                    msg_dict['file_id'] = file_id
                    # Extract filename từ file_path
                    if len(filename.split('_', 1)) > 1:
                        original_filename = filename.split('_', 1)[1]
                        msg_dict['filename'] = original_filename
                    # Lấy file_size từ file nếu file tồn tại
                    if path_obj.exists():
                        msg_dict['file_size'] = path_obj.stat().st_size
            messages.append(msg_dict)
        
        conn.close()
        
        return web.json_response({
            'success': True,
            'messages': messages
        })
    
    async def send_message(self, request: web.Request):
        """POST /api/chat/send"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        try:
            data = await request.json()
            message_text = data.get('message', '').strip()
            receiver = data.get('receiver', '').strip()
            
            if not message_text:
                return web.json_response(
                    {'success': False, 'message': 'Message không được để trống'},
                    status=400
                )
            
            # Lưu message
            self.db.save_message(username, receiver if receiver else None, message_text)
            
            return web.json_response({
                'success': True,
                'message': 'Message đã được gửi'
            })
        except Exception as e:
            return web.json_response(
                {'success': False, 'message': f'Lỗi server: {str(e)}'},
                status=500
            )
    
    async def get_conversations(self, request: web.Request):
        """GET /api/chat/conversations"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Lấy danh sách conversations (người đã chat với)
        cursor.execute("""
            SELECT DISTINCT 
                CASE 
                    WHEN sender_username = ? THEN receiver_username
                    ELSE sender_username
                END as other_user,
                MAX(timestamp) as last_message_time
            FROM messages
            WHERE sender_username = ? OR receiver_username = ?
            GROUP BY other_user
            ORDER BY last_message_time DESC
        """, (username, username, username))
        
        conversations = []
        for row in cursor.fetchall():
            other_user = row['other_user']
            if other_user:
                # Lấy message cuối cùng
                cursor.execute("""
                    SELECT * FROM messages
                    WHERE (sender_username = ? AND receiver_username = ?)
                       OR (sender_username = ? AND receiver_username = ?)
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (username, other_user, other_user, username))
                last_msg = cursor.fetchone()
                
                conversations.append({
                    'username': other_user,
                    'last_message': dict(last_msg) if last_msg else None,
                    'last_message_time': row['last_message_time']
                })
        
        conn.close()
        
        return web.json_response({
            'success': True,
            'conversations': conversations
        })
    
    # User endpoints
    async def search_users(self, request: web.Request):
        """GET /api/users/search?q=email_or_username"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        query = request.query.get('q', '').strip()
        if not query:
            return web.json_response(
                {'success': False, 'message': 'Query không được để trống'},
                status=400
            )
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Tìm user theo username hoặc email
        cursor.execute("""
            SELECT username, email, created_at
            FROM users
            WHERE username LIKE ? OR email LIKE ?
            LIMIT 20
        """, (f'%{query}%', f'%{query}%'))
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return web.json_response({
            'success': True,
            'users': users
        })
    
    async def get_online_users(self, request: web.Request):
        """GET /api/users/online"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        online_users = self.auth_handler.get_all_users()
        return web.json_response({
            'success': True,
            'users': online_users
        })
    
    async def get_user_info(self, request: web.Request):
        """GET /api/users/{username}"""
        current_username = await self.get_current_user_from_request(request)
        if not current_username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        target_username = request.match_info['username']
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users WHERE username = ?", (target_username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return web.json_response({
                'success': True,
                'user': dict(user)
            })
        else:
            return web.json_response(
                {'success': False, 'message': 'User not found'},
                status=404
            )
    
    # File endpoints
    async def upload_file(self, request: web.Request):
        """POST /api/files/upload"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        try:
            data = await request.post()
            receiver = data.get('receiver', '').strip()
            
            if 'file' not in data:
                return web.json_response(
                    {'success': False, 'message': 'Không có file'},
                    status=400
                )
            
            file_obj = data['file']
            filename = file_obj.filename
            file_content = file_obj.file.read()
            
            # Lưu file
            import uuid
            import aiofiles
            file_id = str(uuid.uuid4())
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            file_path = Path('uploads') / f"{file_id}_{safe_filename}"
            file_path.parent.mkdir(exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Lấy file size
            file_size = len(file_content)
            
            # KHÔNG lưu vào database ở đây - sẽ lưu khi WebSocket message được gửi
            # để tránh duplicate messages
            
            return web.json_response({
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'file_size': file_size,
                'message': 'File đã được upload thành công'
            })
        except Exception as e:
            return web.json_response(
                {'success': False, 'message': f'Lỗi upload: {str(e)}'},
                status=500
            )
    
    async def download_file(self, request: web.Request):
        """GET /api/files/{file_id}"""
        username = await self.get_current_user_from_request(request)
        if not username:
            return web.json_response(
                {'success': False, 'message': 'Unauthorized'},
                status=401
            )
        
        file_id = request.match_info['file_id']
        
        # Tìm file trong uploads
        uploads_dir = Path('uploads')
        for file_path in uploads_dir.glob(f"{file_id}_*"):
            return web.Response(
                body=file_path.read_bytes(),
                headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{file_path.name}"'
                }
            )
        
        return web.json_response(
            {'success': False, 'message': 'File not found'},
            status=404
        )
    
    async def health_check(self, request: web.Request):
        """GET /api/health"""
        return web.json_response({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def root(self, request: web.Request):
        """GET / - Root endpoint"""
        return web.json_response({
            'success': True,
            'message': 'Chat API Server',
            'version': '1.0.0',
            'endpoints': {
                'auth': {
                    'register': 'POST /api/auth/register',
                    'login': 'POST /api/auth/login',
                    'logout': 'POST /api/auth/logout',
                    'me': 'GET /api/auth/me'
                },
                'chat': {
                    'messages': 'GET /api/chat/messages?receiver=username',
                    'send': 'POST /api/chat/send',
                    'conversations': 'GET /api/chat/conversations'
                },
                'users': {
                    'search': 'GET /api/users/search?q=query',
                    'online': 'GET /api/users/online',
                    'info': 'GET /api/users/{username}'
                },
                'files': {
                    'upload': 'POST /api/files/upload',
                    'download': 'GET /api/files/{file_id}'
                },
                'health': 'GET /api/health'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_ssl_context(self):
        """Tạo SSL context"""
        if not self.ssl_cert or not self.ssl_key:
            return None
        
        if not Path(self.ssl_cert).exists() or not Path(self.ssl_key).exists():
            return None
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.ssl_cert, self.ssl_key)
        return context
    
    async def start(self):
        """Khởi động server"""
        ssl_context = self.get_ssl_context()
        
        if ssl_context:
            print(f"REST API Server đang khởi động với SSL tại {self.host}:{self.port}")
        else:
            print(f"REST API Server đang khởi động không SSL tại {self.host}:{self.port}")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            self.host,
            self.port,
            ssl_context=ssl_context
        )
        
        await site.start()
        protocol = 'https' if ssl_context else 'http'
        print(f"REST API Server đã sẵn sàng tại {protocol}://{self.host}:{self.port}")
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nĐang dừng REST API server...")
            await runner.cleanup()

