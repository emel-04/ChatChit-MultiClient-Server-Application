"""
Xử lý chat messages
"""
from .database import Database
from .protocol import Message, MessageType
from typing import Dict, Callable, Optional

class ChatHandler:
    def __init__(self, db: Database, auth_handler=None):
        self.db = db
        self.auth_handler = auth_handler
        self.clients: Dict[str, Callable] = {}  # {client_id: send_callback}
    
    async def register_client(self, client_id: str, send_callback: Callable):
        """Đăng ký client để nhận messages"""
        self.clients[client_id] = send_callback
        
        # Gửi thông báo user online đến tất cả clients
        if self.auth_handler:
            username = self.auth_handler.get_username(client_id)
            if username:
                print(f"[ChatHandler] Registering client {client_id} for user {username}")
                # Broadcast user online status
                await self._broadcast_user_status(username, True, exclude_id=client_id)
            else:
                print(f"[ChatHandler] Warning: No username found for client {client_id}")
    
    async def unregister_client(self, client_id: str):
        """Hủy đăng ký client"""
        if client_id in self.clients:
            # Gửi thông báo user offline đến tất cả clients
            if self.auth_handler:
                username = self.auth_handler.get_username(client_id)
                if username:
                    # Broadcast user offline status
                    await self._broadcast_user_status(username, False)
            
            del self.clients[client_id]
    
    async def _broadcast_user_status(self, username: str, is_online: bool, exclude_id: str = None):
        """Broadcast trạng thái online/offline của user"""
        status_data = {
            "username": username,
            "status": "online" if is_online else "offline"
        }
        
        message_type = MessageType.USER_ONLINE.value if is_online else MessageType.USER_OFFLINE.value
        status_msg = {
            "type": message_type,
            "data": status_data
        }
        
        print(f"[ChatHandler] Broadcasting user status: {username} is {'online' if is_online else 'offline'}, clients: {list(self.clients.keys())}, exclude: {exclude_id}")
        
        # Gửi đến tất cả clients
        for client_id, callback in self.clients.items():
            if client_id != exclude_id:
                try:
                    # Gửi JSON message trực tiếp (không encode thành bytes)
                    await callback(status_msg)
                    print(f"[ChatHandler] Sent {message_type} to {client_id}")
                except Exception as e:
                    print(f"[ChatHandler] Lỗi gửi user status đến {client_id}: {e}")
    
    async def handle_chat(self, sender_id: str, sender_username: str, data: dict) -> bytes:
        """Xử lý chat message"""
        message_text = data.get('message', '').strip()
        receiver_username = data.get('receiver', '').strip()
        
        # Kiểm tra nếu là file message (JSON string)
        file_id = None
        filename = None
        file_size = None
        message_type = 'text'
        file_path = None
        
        try:
            import json
            parsed = json.loads(message_text)
            if isinstance(parsed, dict) and parsed.get('type') == 'file':
                file_id = parsed.get('file_id')
                filename = parsed.get('filename')
                file_size = parsed.get('file_size')
                message_text = parsed.get('message', f"File: {filename}")
                message_type = 'file'
                # Tìm file_path từ file_id
                from pathlib import Path
                uploads_dir = Path('uploads')
                if uploads_dir.exists():
                    for file_path_obj in uploads_dir.glob(f"{file_id}_*"):
                        file_path = str(file_path_obj)
                        # Nếu chưa có file_size, lấy từ file
                        if not file_size and file_path_obj.exists():
                            file_size = file_path_obj.stat().st_size
                        break
        except (json.JSONDecodeError, ValueError):
            # Không phải JSON, xử lý như message text bình thường
            pass
        
        if not message_text:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Message không được để trống"
            )
        
        # Lưu vào database
        self.db.save_message(
            sender_username, 
            receiver_username, 
            message_text,
            message_type=message_type,
            file_path=file_path
        )
        
        # Tạo message data với file info nếu có
        message_data = message_text
        if file_id and filename:
            message_data = {
                "message": message_text,
                "file_id": file_id,
                "filename": filename,
                "file_size": file_size,
                "message_type": "file"
            }
        
        # Nếu có receiver, gửi private message
        if receiver_username:
            return await self._send_private_message(
                sender_username, receiver_username, message_data
            )
        else:
            # Broadcast message
            return await self._broadcast_message(sender_username, message_data, exclude_id=sender_id)
    
    async def _send_private_message(self, sender: str, receiver: str, message_data) -> bytes:
        """Gửi private message đến một user cụ thể"""
        # Xử lý message_data có thể là dict hoặc string
        if isinstance(message_data, dict):
            message_text = message_data.get("message", "")
            file_info = {k: v for k, v in message_data.items() if k in ["file_id", "filename", "file_size", "message_type"]}
        else:
            message_text = message_data
            file_info = {}
        
        # Tìm client_id của receiver
        receiver_id = None
        if self.auth_handler:
            for client_id in self.clients.keys():
                if self.auth_handler.get_username(client_id) == receiver:
                    receiver_id = client_id
                    break
        
        # Gửi message đến receiver nếu tìm thấy
        if receiver_id:
            private_msg_data = {
                "sender": sender,
                "receiver": receiver,
                "message": message_text,
                "type": "private",
                **file_info
            }
            private_msg = Message.encode(MessageType.PRIVATE_MESSAGE, private_msg_data)
            await self.send_to_client(receiver_id, private_msg)
        
        # Gửi message lại cho sender để hiển thị trong UI
        sender_id = None
        if self.auth_handler:
            for client_id in self.clients.keys():
                if self.auth_handler.get_username(client_id) == sender:
                    sender_id = client_id
                    break
        
        if sender_id:
            sender_msg_data = {
                "sender": sender,
                "receiver": receiver,
                "message": message_text,
                "type": "private",
                **file_info
            }
            sender_msg = Message.encode(MessageType.PRIVATE_MESSAGE, sender_msg_data)
            await self.send_to_client(sender_id, sender_msg)
        
        # Response cho sender
        return Message.create_response(
            MessageType.SUCCESS,
            True,
            "Message đã được gửi" if receiver_id else f"User {receiver} không online",
            {
                "action": "chat",
                "receiver": receiver,
                "message": message_text,
                **file_info
            }
        )
    
    async def _broadcast_message(self, sender: str, message_data, exclude_id: str = None):
        """Broadcast message đến tất cả clients"""
        # Xử lý message_data có thể là dict hoặc string
        if isinstance(message_data, dict):
            message_text = message_data.get("message", "")
            file_info = {k: v for k, v in message_data.items() if k in ["file_id", "filename", "file_size", "message_type"]}
        else:
            message_text = message_data
            file_info = {}
        
        broadcast_data = {
            "sender": sender,
            "message": message_text,
            "type": "broadcast",
            **file_info
        }
        
        broadcast_msg = Message.encode(MessageType.BROADCAST, broadcast_data)
        
        # Gửi đến tất cả clients trừ sender
        for client_id, callback in self.clients.items():
            if client_id != exclude_id:
                try:
                    await callback(broadcast_msg)
                except Exception as e:
                    print(f"Lỗi gửi message đến {client_id}: {e}")
        
        # Response cho sender
        return Message.create_response(
            MessageType.SUCCESS,
            True,
            "Message đã được gửi",
            {"action": "chat", "message": message_text, **file_info}
        )
    
    async def send_to_client(self, client_id: str, message: bytes):
        """Gửi message đến một client cụ thể"""
        if client_id in self.clients:
            try:
                await self.clients[client_id](message)
            except Exception as e:
                print(f"Lỗi gửi message đến {client_id}: {e}")
    
    def get_online_users(self) -> list:
        """Lấy danh sách username của các user đang online"""
        online_users = []
        if self.auth_handler:
            for client_id in self.clients.keys():
                username = self.auth_handler.get_username(client_id)
                if username and username not in online_users:
                    online_users.append(username)
        return online_users