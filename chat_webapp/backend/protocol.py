"""
Protocol định nghĩa format message giữa client và server
"""
import json
from enum import Enum
from typing import Dict, Any, Optional

class MessageType(Enum):
    """Các loại message"""
    REGISTER = "REGISTER"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CHAT = "CHAT"
    FILE_REQUEST = "FILE_REQUEST"
    FILE_DATA = "FILE_DATA"
    FILE_ACK = "FILE_ACK"
    BROADCAST = "BROADCAST"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    USER_LIST = "USER_LIST"
    PRIVATE_MESSAGE = "PRIVATE_MESSAGE"
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    ONLINE_USERS = "online_users"

class Message:
    """Class để encode/decode messages"""
    
    @staticmethod
    def encode(message_type: MessageType, data: Dict[str, Any]) -> bytes:
        """
        Encode message thành bytes để gửi qua socket
        Format: [length: 4 bytes][json_data]
        """
        message = {
            "type": message_type.value,
            "data": data
        }
        json_str = json.dumps(message, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        # Thêm length prefix (4 bytes, big-endian)
        length = len(json_bytes)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        return length_bytes + json_bytes
    
    @staticmethod
    def decode(data: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode message từ bytes
        Returns: {"type": MessageType, "data": {...}} hoặc None nếu lỗi
        """
        try:
            if len(data) < 4:
                return None
            
            # Đọc length
            length = int.from_bytes(data[:4], byteorder='big')
            
            if len(data) < 4 + length:
                return None
            
            # Đọc JSON data
            json_bytes = data[4:4+length]
            json_str = json_bytes.decode('utf-8')
            message = json.loads(json_str)
            
            return message
        except Exception as e:
            print(f"Lỗi decode message: {e}")
            return None
    
    @staticmethod
    def create_response(message_type: MessageType, success: bool, 
                       message: str, data: Dict[str, Any] = None) -> bytes:
        """Tạo response message"""
        response_data = {
            "success": success,
            "message": message
        }
        if data:
            response_data.update(data)
        
        return Message.encode(message_type, response_data)

