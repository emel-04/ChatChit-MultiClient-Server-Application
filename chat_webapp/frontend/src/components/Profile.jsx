import { X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import websocketService from '../services/websocket';
import Avatar from './Avatar';

export default function Profile({ user, isOpen, onClose }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      // Disconnect WebSocket
      websocketService.disconnect();
      
      // Call logout API
      await logout();
      
      // Clear localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // Navigate to login
      navigate('/login');
      
      // Close profile modal
      onClose();
    } catch (error) {
      console.error('Logout error:', error);
      // Even if API call fails, still logout locally
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      websocketService.disconnect();
      navigate('/login');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1 hover:bg-gray-100"
        >
          <X className="h-5 w-5 text-text-muted" />
        </button>

        {/* Avatar */}
        <div className="mb-4 flex justify-center">
          <Avatar name={user?.username} size="xl" />
        </div>

        {/* User Info */}
        <div className="text-center">
          <h2 className="mb-1 heading-small text-text-primary">
            {user?.username || 'Nguyễn Văn A'}
          </h2>
          <p className="mb-3 body-medium text-text-secondary">
            {user?.email || 'nguyenvana@email.com'}
          </p>
          
          {/* Online Status */}
          <div className="flex items-center justify-center gap-2">
            <span className="h-2 w-2 rounded-full bg-success"></span>
            <span className="body-small font-medium text-success">
              Đang hoạt động
            </span>
          </div>
        </div>

        {/* Logout Button */}
        <div className="mt-4">
          <button
            onClick={handleLogout}
            className="flex w-full min-w-[84px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-10 px-4 bg-red-500/10 text-red-500 text-sm font-bold leading-normal tracking-[0.015em] hover:bg-red-500/20 transition-colors"
          >
            <span className="truncate">Đăng xuất</span>
          </button>
        </div>
      </div>
    </div>
  );
}