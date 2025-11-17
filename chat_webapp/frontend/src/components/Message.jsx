import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { chatAPI, userAPI, fileAPI } from '../services/api';
import websocketService from '../services/websocket';
import { Search, UserPlus, Send, PlusCircle, Download } from 'lucide-react';
import ChatChitLogo from '../assets/ChatChit.png';
import Profile from './Profile';
import FindFriends from './FindFriends';
import Avatar from './Avatar';

export default function Message() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [showProfile, setShowProfile] = useState(false);
  const [showFindFriends, setShowFindFriends] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const selectedConversationRef = useRef(selectedConversation);

  useEffect(() => {
    loadConversations();
    loadOnlineUsers();
    
    const token = localStorage.getItem('token');
    if (token) {
      websocketService.connect(token);
      
      websocketService.on('message', handleNewMessage);
      websocketService.on('broadcast', handleNewMessage);
      websocketService.on('private_message', handleNewMessage);
      websocketService.on('user_online', handleUserOnline);
      websocketService.on('user_offline', handleUserOffline);
      websocketService.on('online_users', handleOnlineUsersList);
    }

    // Polling để cập nhật danh sách online users mỗi 30 giây (fallback nếu WebSocket events không hoạt động)
    const onlineUsersInterval = setInterval(() => {
      // Chỉ polling nếu không có WebSocket events trong 30 giây
      // (WebSocket events sẽ cập nhật real-time, polling chỉ là fallback)
      loadOnlineUsers();
    }, 30000);

    return () => {
      websocketService.off('message', handleNewMessage);
      websocketService.off('broadcast', handleNewMessage);
      websocketService.off('private_message', handleNewMessage);
      websocketService.off('user_online', handleUserOnline);
      websocketService.off('user_offline', handleUserOffline);
      websocketService.off('online_users', handleOnlineUsersList);
      clearInterval(onlineUsersInterval);
    };
  }, []);

  useEffect(() => {
    selectedConversationRef.current = selectedConversation;
    if (selectedConversation) {
      loadMessages(selectedConversation.username);
    }
  }, [selectedConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = async () => {
    try {
      const result = await chatAPI.getConversations();
      if (result.success) {
        setConversations(result.conversations || []);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadMessages = async (receiver) => {
    try {
      const result = await chatAPI.getMessages(receiver);
      if (result.success) {
        setMessages((result.messages || []).reverse());
      }
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  const loadOnlineUsers = async () => {
    try {
      const result = await userAPI.getOnlineUsers();
      if (result.success) {
        const users = result.users || [];
        console.log('Loaded online users from API:', users);
        // Chỉ cập nhật nếu danh sách từ API khác với danh sách hiện tại
        // (để tránh ghi đè lên real-time updates từ WebSocket)
        setOnlineUsers((prev) => {
          // So sánh và merge: giữ lại những user có trong cả hai danh sách
          // hoặc thêm user mới từ API
          const merged = [...new Set([...prev, ...users])];
          if (JSON.stringify(merged.sort()) !== JSON.stringify(prev.sort())) {
            console.log('Merging online users:', { prev, users, merged });
            return merged;
          }
          return prev;
        });
      }
    } catch (error) {
      console.error('Error loading online users:', error);
    }
  };

  const handleNewMessage = (data) => {
    // Chỉ thêm message nếu có nội dung thực sự
    if (data && (data.message || data.message_text)) {
      // Kiểm tra xem tin nhắn có thuộc conversation hiện tại không
      const sender = data.sender_username || data.sender;
      const receiver = data.receiver_username || data.receiver;
      
      // Sử dụng ref để lấy giá trị hiện tại của selectedConversation
      const currentConv = selectedConversationRef.current;
      
      // Nếu đang có conversation được chọn
      if (currentConv) {
        const currentUsername = currentConv.username;
        // Chỉ thêm tin nhắn nếu:
        // - Người gửi là user hiện tại và người nhận là conversation hiện tại, HOẶC
        // - Người gửi là conversation hiện tại và người nhận là user hiện tại
        const isForCurrentConversation = 
          (sender === user?.username && receiver === currentUsername) ||
          (sender === currentUsername && receiver === user?.username);
        
        if (isForCurrentConversation) {
          setMessages((prev) => {
            // Kiểm tra xem message đã tồn tại chưa để tránh duplicate
            // So sánh dựa trên sender, receiver, message content, và file_id (nếu có)
            const exists = prev.some(msg => {
              const msgSender = msg.sender_username || msg.sender;
              const msgReceiver = msg.receiver_username || msg.receiver;
              const msgText = msg.message || msg.message_text;
              const msgFileId = msg.file_id;
              
              // So sánh sender và receiver
              if (msgSender !== sender || msgReceiver !== receiver) {
                return false;
              }
              
              // Nếu là file message, so sánh file_id
              if (data.file_id || msgFileId) {
                return data.file_id === msgFileId;
              }
              
              // Nếu là text message, so sánh nội dung và timestamp (trong vòng 5 giây)
              if (msgText === (data.message || data.message_text)) {
                if (data.timestamp && msg.timestamp) {
                  const timeDiff = Math.abs(new Date(data.timestamp) - new Date(msg.timestamp));
                  return timeDiff < 5000; // Trong vòng 5 giây
                }
                // Nếu không có timestamp, coi như duplicate nếu nội dung giống nhau
                return true;
              }
              
              return false;
            });
            
            if (exists) {
              return prev; // Không thêm nếu đã tồn tại
            }
            return [...prev, data];
          });
        }
      }
      
      // Luôn cập nhật conversations list để hiển thị tin nhắn mới trong sidebar
      loadConversations();
    }
  };

  const handleUserOnline = (data) => {
    // Khi có user online, thêm vào danh sách
    console.log('User online event:', data);
    if (data && data.username) {
      setOnlineUsers((prev) => {
        if (!prev.includes(data.username)) {
          console.log('Adding user to online list:', data.username, 'Current list:', prev);
          return [...prev, data.username];
        }
        return prev;
      });
    }
  };

  const handleUserOffline = (data) => {
    // Khi có user offline, xóa khỏi danh sách
    console.log('User offline event:', data);
    if (data && data.username) {
      setOnlineUsers((prev) => {
        const filtered = prev.filter(u => u !== data.username);
        console.log('Removing user from online list:', data.username, 'New list:', filtered);
        return filtered;
      });
    }
  };

  const handleOnlineUsersList = (data) => {
    // Cập nhật toàn bộ danh sách online users
    console.log('Online users list event:', data);
    if (data && data.users && Array.isArray(data.users)) {
      console.log('Updating online users list:', data.users);
      setOnlineUsers(data.users);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!messageInput.trim() || !selectedConversation) return;

    websocketService.sendMessage(messageInput, selectedConversation.username);
    setMessageInput('');
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedConversation) return;

    try {
      const result = await fileAPI.uploadFile(file, selectedConversation.username);
      if (result.success) {
        websocketService.sendMessage(
          JSON.stringify({
            type: 'file',
            file_id: result.file_id,
            filename: result.filename,
            file_size: result.file_size || file.size,
            message: `File: ${result.filename}`
          }),
          selectedConversation.username
        );
      }
    } catch (error) {
      console.error('Error uploading file:', error);
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleFileDownload = async (fileId, filename) => {
    try {
      const blob = await fileAPI.downloadFile(fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'file';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading file:', error);
    }
  };

  const filteredConversations = conversations.filter((conv) =>
    conv.username?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      <div className="flex h-screen w-full bg-background-secondary">
        {/* Sidebar */}
        <aside className="flex h-full w-[360px] flex-col border-r border-border bg-white">
          {/* Header */}
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-border px-4">
            <div class="flex items-center gap-2">
              <img alt="ChitChat Application Logo" class="h-24 w-24 object-contain" src={ChatChitLogo}/>
            </div>
            <button
              onClick={() => setShowFindFriends(true)}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-background-secondary"
            >
              <UserPlus className="h-5 w-5 text-text-secondary" />
            </button>
          </header>

          {/* Search */}
          <div className="border-b border-border p-4">
            <div className="flex h-10 items-center rounded-lg bg-background-secondary px-3">
              <Search className="h-4 w-4 text-text-muted" />
              <input
                className="w-full border-0 bg-transparent px-3 text-sm outline-none placeholder:text-text-muted"
                placeholder="Tìm kiếm cuộc trò chuyện"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Conversations List */}
          <nav className="flex-1 overflow-y-auto">
            {filteredConversations.map((conv, index) => (
              <div
                key={index}
                className={`cursor-pointer border-b border-border px-4 py-3 hover:bg-background-secondary ${
                  selectedConversation?.username === conv.username ? 'bg-primary-light' : ''
                }`}
                onClick={() => setSelectedConversation(conv)}
              >
                <div className="flex items-center gap-3">
                  <Avatar
                    name={conv.username}
                    size="lg"
                    showOnline={true}
                    isOnline={onlineUsers.includes(conv.username)}
                  />
                  <div className="flex-1 overflow-hidden">
                    <p className="body-medium font-semibold text-text-primary truncate">
                      {conv.username}
                    </p>
                    <p className={`body-small truncate ${
                      conv.last_message?.sender_username === user?.username 
                        ? 'text-text-muted' 
                        : 'text-primary'
                    }`}>
                      {conv.last_message?.sender_username === user?.username && 'Bạn: '}
                      {conv.last_message?.message || 'Đang gõ...'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="body-small text-text-muted">
                      {conv.last_message_time
                        ? new Date(conv.last_message_time).toLocaleTimeString('vi-VN', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}
                    </p>
                    {conv.unread_count > 0 && (
                      <span className="mt-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs text-white">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </nav>

          {/* User Profile Footer */}
          <div
            className="flex cursor-pointer items-center gap-3 border-t border-border p-4 hover:bg-background-secondary"
            onClick={() => setShowProfile(true)}
          >
            <Avatar name={user?.username} size="md" />
            <div className="flex-1">
              <p className="body-medium font-medium text-text-primary">{user?.username}</p>
            </div>
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="flex h-full flex-1 flex-col">
          {selectedConversation ? (
            <>
              {/* Chat Header */}
              <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-white px-6">
                <div className="flex items-center gap-4">
                  <Avatar
                    name={selectedConversation.username}
                    size="md"
                    showOnline={true}
                    isOnline={onlineUsers.includes(selectedConversation.username)}
                  />
                  <div>
                    <h2 className="body-large font-semibold text-text-primary">
                      {selectedConversation.username}
                    </h2>
                    <p className="body-small text-text-muted">
                      {onlineUsers.includes(selectedConversation.username) ? 'Online' : 'Offline'}
                    </p>
                  </div>
                </div>
              </header>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="flex flex-col gap-2">
                  {messages.map((msg, index) => {
                    // Chỉ hiển thị message nếu có nội dung
                    const messageText = msg.message || msg.message_text;
                    if (!messageText) return null;

                    const isOwn = msg.sender_username === user.username || msg.sender === user.username;
                    const senderName = msg.sender_username || msg.sender;
                    
                    // Không hiển thị nếu không có sender name
                    if (!senderName) return null;

                    // Kiểm tra xem message trước đó có cùng người gửi không
                    const prevMsg = index > 0 ? messages[index - 1] : null;
                    const prevSender = prevMsg ? (prevMsg.sender_username || prevMsg.sender) : null;
                    const isSameSender = prevSender === senderName;
                    
                    // Kiểm tra xem message sau có cùng người gửi không
                    const nextMsg = index < messages.length - 1 ? messages[index + 1] : null;
                    const nextSender = nextMsg ? (nextMsg.sender_username || nextMsg.sender) : null;
                    const isLastInGroup = nextSender !== senderName;

                    return (
                      <div
                        key={index}
                        className={`flex gap-3 ${isOwn ? 'ml-auto flex-row-reverse' : ''} ${
                          isSameSender ? (isOwn ? 'items-end' : 'items-start') : 'items-end'
                        }`}
                      >
                        {/* Chỉ hiển thị avatar cho tin nhắn cuối cùng trong nhóm */}
                        {!isOwn && (
                          <div className="w-8 flex items-end">
                            {isLastInGroup ? (
                              <Avatar name={senderName} size="sm" />
                            ) : (
                              <div className="w-8" />
                            )}
                          </div>
                        )}
                        
                        <div className={`flex max-w-lg flex-col gap-1 ${isOwn ? 'items-end' : ''}`}>
                          <div
                            className={`rounded-2xl px-4 py-2 ${
                              isOwn
                                ? 'bg-primary text-white'
                                : 'bg-gray-200 text-text-primary'
                            }`}
                          >
                            {msg.message_type === 'file' || msg.file_id ? (
                              <div className="flex items-center gap-3 min-w-[200px]">
                                <div className="flex-1 min-w-0">
                                  <p className={`body-medium truncate ${
                                    isOwn ? 'text-white' : 'text-text-primary'
                                  }`}>
                                    {msg.filename || 'file'}
                                  </p>
                                  <p className={`text-xs mt-1 ${
                                    isOwn ? 'text-white/70' : 'text-text-muted'
                                  }`}>
                                    {formatFileSize(msg.file_size)}
                                  </p>
                                </div>
                                <button
                                  onClick={() => handleFileDownload(msg.file_id, msg.filename)}
                                  className={`flex-shrink-0 p-2 rounded-lg hover:opacity-80 transition-opacity ${
                                    isOwn 
                                      ? 'bg-white/20 hover:bg-white/30' 
                                      : 'bg-gray-300 hover:bg-gray-400'
                                  }`}
                                  title="Tải xuống"
                                >
                                  <Download className={`h-5 w-5 ${
                                    isOwn ? 'text-white' : 'text-text-primary'
                                  }`} />
                                </button>
                              </div>
                            ) : (
                              <p className="body-medium">{messageText}</p>
                            )}
                          </div>
                          {/* Chỉ hiển thị timestamp cho tin nhắn cuối cùng trong nhóm */}
                          {isLastInGroup && (
                            <span className="body-small text-text-muted">
                              {msg.timestamp
                                ? new Date(msg.timestamp).toLocaleTimeString('vi-VN', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })
                                : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Message Input */}
              <div className="shrink-0 border-t border-border bg-white p-4">
                <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                  <button
                    type="button"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg hover:bg-background-secondary"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <PlusCircle className="h-6 w-6 text-text-secondary" />
                  </button>
                  <input
                    className="h-10 flex-1 rounded-lg border border-border bg-white px-4 text-sm outline-none placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-light"
                    placeholder="Nhập tin nhắn..."
                    type="text"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                  />
                  <button
                    type="submit"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-white hover:bg-primary-hover"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="body-large text-text-muted">Chọn một cuộc trò chuyện để bắt đầu</p>
            </div>
          )}
        </main>
      </div>

      {/* Modals */}
      <Profile user={user} isOpen={showProfile} onClose={() => setShowProfile(false)} />
      <FindFriends
        isOpen={showFindFriends}
        onClose={() => setShowFindFriends(false)}
        onSelectUser={(selectedUser) => {
          const existingConv = conversations.find(
            (conv) => conv.username === selectedUser.username
          );
          if (existingConv) {
            setSelectedConversation(existingConv);
          } else {
            const newConv = {
              username: selectedUser.username,
              last_message: null,
              last_message_time: null,
            };
            setSelectedConversation(newConv);
            loadMessages(selectedUser.username);
          }
        }}
      />
    </>
  );
}