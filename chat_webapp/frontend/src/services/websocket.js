/**
 * WebSocket service cho real-time chat
 */
// WebSocket service - sử dụng native WebSocket API
// (Socket.io có thể được thêm sau nếu cần)

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
  }

  connect(token) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.socket = new WebSocket(`${WS_URL}/ws`);

      this.socket.onopen = () => {
        console.log('WebSocket connected');
        // Gửi token để authenticate
        if (token) {
          this.socket.send(JSON.stringify({
            type: 'AUTH',
            data: { token }
          }));
        }
        this.emit('connected');
      };

      this.socket.onclose = () => {
        console.log('WebSocket disconnected');
        this.emit('disconnected');
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Route messages based on type
          if (data.type === 'BROADCAST') {
            this.emit('broadcast', data.data);
          } else if (data.type === 'PRIVATE_MESSAGE') {
            this.emit('private_message', data.data);
          } else if (data.type === 'CHAT') {
            this.emit('message', data.data);
          } else if (data.type === 'user_online') {
            // User online event
            this.emit('user_online', data.data);
          } else if (data.type === 'user_offline') {
            // User offline event
            this.emit('user_offline', data.data);
          } else if (data.type === 'online_users') {
            // Online users list event
            this.emit('online_users', data.data);
          } else if (data.type === 'SUCCESS' && data.data?.message === 'Xác thực thành công') {
            // AUTH thành công
            console.log('WebSocket authenticated:', data.data.username);
            this.emit('authenticated', data.data);
          } else if (data.type === 'ERROR') {
            // Xử lý lỗi (bao gồm AUTH error)
            console.error('WebSocket error:', data.data?.message || 'Unknown error');
            this.emit('error', data.data);
          } else {
            this.emit('message', data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Error connecting WebSocket:', error);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((callback) => {
        callback(data);
      });
    }
  }

  sendMessage(message, receiver = null) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'CHAT',
        data: { message, receiver },
      }));
    }
  }

  sendFile(file, receiver = null) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      // File transfer qua WebSocket (có thể dùng REST API thay thế)
      this.socket.send(JSON.stringify({
        type: 'FILE_REQUEST',
        data: {
          filename: file.name,
          size: file.size,
          receiver,
        },
      }));
    }
  }
}

export default new WebSocketService();

