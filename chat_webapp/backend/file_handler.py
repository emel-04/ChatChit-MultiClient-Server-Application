"""
Xử lý file transfer (gửi/nhận file)
"""
import os
import base64
import aiofiles
from pathlib import Path
from .database import Database
from .protocol import Message, MessageType
from typing import Dict, Callable, Optional

class FileHandler:
    def __init__(self, db: Database, auth_handler=None, upload_dir: str = "uploads"):
        self.db = db
        self.auth_handler = auth_handler
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.clients: Dict[str, Callable] = {}  # {client_id: send_callback}
        self.file_transfers: Dict[str, dict] = {}  # {transfer_id: {sender, receiver, filename, size, chunks}}
    
    def register_client(self, client_id: str, send_callback: Callable):
        """Đăng ký client"""
        self.clients[client_id] = send_callback
    
    def unregister_client(self, client_id: str):
        """Hủy đăng ký client"""
        if client_id in self.clients:
            del self.clients[client_id]
    
    async def handle_file_request(self, sender_id: str, sender_username: str, data: dict) -> bytes:
        """Xử lý yêu cầu gửi file"""
        filename = data.get('filename', '').strip()
        file_size = data.get('size', 0)
        receiver_username = data.get('receiver', '').strip()
        
        if not filename:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Tên file không được để trống"
            )
        
        if file_size <= 0:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Kích thước file không hợp lệ"
            )
        
        # Tạo transfer_id
        import uuid
        transfer_id = str(uuid.uuid4())
        
        # Lưu thông tin transfer
        self.file_transfers[transfer_id] = {
            "sender_id": sender_id,
            "sender_username": sender_username,
            "receiver_username": receiver_username,
            "filename": filename,
            "size": file_size,
            "chunks": [],
            "received_size": 0
        }
        
        # Nếu có receiver, gửi thông báo đến receiver
        if receiver_username:
            await self._notify_receiver(transfer_id, receiver_username, sender_username, filename, file_size)
        
        return Message.create_response(
            MessageType.SUCCESS,
            True,
            "File request đã được tạo",
            {
                "action": "file_request",
                "transfer_id": transfer_id,
                "filename": filename,
                "size": file_size
            }
        )
    
    async def handle_file_data(self, sender_id: str, transfer_id: str, data: dict) -> bytes:
        """Xử lý dữ liệu file chunk"""
        if transfer_id not in self.file_transfers:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Transfer ID không hợp lệ"
            )
        
        transfer = self.file_transfers[transfer_id]
        
        # Kiểm tra sender
        if transfer["sender_id"] != sender_id:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Không có quyền gửi file này"
            )
        
        chunk_data = data.get('data', '')
        chunk_index = data.get('chunk_index', 0)
        is_last = data.get('is_last', False)
        
        if not chunk_data:
            return Message.create_response(
                MessageType.ERROR,
                False,
                "Chunk data không được để trống"
            )
        
        try:
            # Decode base64
            chunk_bytes = base64.b64decode(chunk_data)
            transfer["chunks"].append({
                "index": chunk_index,
                "data": chunk_bytes
            })
            transfer["received_size"] += len(chunk_bytes)
            
            # Nếu là chunk cuối, lưu file
            if is_last:
                await self._save_file(transfer_id, transfer)
                
                # Gửi thông báo đến receiver nếu có
                if transfer["receiver_username"]:
                    await self._send_file_to_receiver(transfer_id, transfer)
                
                # Xóa transfer
                del self.file_transfers[transfer_id]
                
                return Message.create_response(
                    MessageType.SUCCESS,
                    True,
                    "File đã được nhận và lưu thành công",
                    {
                        "action": "file_complete",
                        "transfer_id": transfer_id,
                        "filename": transfer["filename"]
                    }
                )
            else:
                return Message.create_response(
                    MessageType.FILE_ACK,
                    True,
                    "Chunk đã được nhận",
                    {
                        "transfer_id": transfer_id,
                        "chunk_index": chunk_index,
                        "received_size": transfer["received_size"]
                    }
                )
        
        except Exception as e:
            return Message.create_response(
                MessageType.ERROR,
                False,
                f"Lỗi xử lý file chunk: {str(e)}"
            )
    
    async def _save_file(self, transfer_id: str, transfer: dict):
        """Lưu file vào disk"""
        # Sắp xếp chunks theo index
        chunks = sorted(transfer["chunks"], key=lambda x: x["index"])
        
        # Tạo file path
        safe_filename = "".join(c for c in transfer["filename"] if c.isalnum() or c in "._- ")
        file_path = self.upload_dir / f"{transfer_id}_{safe_filename}"
        
        # Ghi file
        async with aiofiles.open(file_path, 'wb') as f:
            for chunk in chunks:
                await f.write(chunk["data"])
        
        # Lưu vào database
        self.db.save_message(
            transfer["sender_username"],
            transfer["receiver_username"],
            f"File: {transfer['filename']}",
            message_type="file",
            file_path=str(file_path)
        )
    
    async def _notify_receiver(self, transfer_id: str, receiver_username: str, 
                              sender_username: str, filename: str, file_size: int):
        """Thông báo receiver về file sắp được gửi"""
        if not self.auth_handler:
            return
        
        # Tìm receiver client_id
        receiver_id = None
        for client_id in self.clients.keys():
            if self.auth_handler.get_username(client_id) == receiver_username:
                receiver_id = client_id
                break
        
        if receiver_id:
            notification_data = {
                "transfer_id": transfer_id,
                "sender": sender_username,
                "filename": filename,
                "size": file_size,
                "action": "file_incoming"
            }
            notification = Message.encode(MessageType.FILE_REQUEST, notification_data)
            await self.send_to_client(receiver_id, notification)
    
    async def _send_file_to_receiver(self, transfer_id: str, transfer: dict):
        """Gửi thông báo file đã sẵn sàng đến receiver"""
        if not self.auth_handler:
            return
        
        receiver_username = transfer.get("receiver_username")
        if not receiver_username:
            return
        
        # Tìm receiver client_id
        receiver_id = None
        for client_id in self.clients.keys():
            if self.auth_handler.get_username(client_id) == receiver_username:
                receiver_id = client_id
                break
        
        if receiver_id:
            # Đọc file và gửi
            file_path = self.upload_dir / f"{transfer_id}_{transfer['filename']}"
            if file_path.exists():
                notification_data = {
                    "transfer_id": transfer_id,
                    "sender": transfer["sender_username"],
                    "filename": transfer["filename"],
                    "size": transfer["size"],
                    "action": "file_ready",
                    "file_path": str(file_path)
                }
                notification = Message.encode(MessageType.FILE_REQUEST, notification_data)
                await self.send_to_client(receiver_id, notification)
    
    async def send_to_client(self, client_id: str, message: bytes):
        """Gửi message đến một client cụ thể"""
        if client_id in self.clients:
            try:
                await self.clients[client_id](message)
            except Exception as e:
                print(f"Lỗi gửi file message đến {client_id}: {e}")

