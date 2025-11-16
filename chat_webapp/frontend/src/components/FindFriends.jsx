import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { userAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import Avatar from './Avatar';

export default function FindFriends({ isOpen, onClose, onSelectUser }) {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      // Reset khi đóng popup
      setSearchQuery('');
      setSearchResults([]);
      setHasSearched(false);
    }
  }, [isOpen]);

  useEffect(() => {
    // Debounce search
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setHasSearched(false);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setLoading(true);
      setHasSearched(true);
      try {
        const result = await userAPI.searchUsers(searchQuery.trim());
        if (result.success) {
          // Lọc bỏ chính mình khỏi kết quả
          const filteredUsers = (result.users || []).filter(
            (u) => u.username !== user?.username && u.email !== user?.email
          );
          setSearchResults(filteredUsers);
        } else {
          setSearchResults([]);
        }
      } catch (error) {
        console.error('Search error:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    }, 500); // Debounce 500ms

    return () => clearTimeout(timeoutId);
  }, [searchQuery, user]);

  const handleMessage = (selectedUser) => {
    if (onSelectUser) {
      onSelectUser(selectedUser);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="heading-small text-text-primary">
            Tìm bạn bè mới
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 hover:bg-gray-100"
          >
            <X className="h-5 w-5 text-text-muted" />
          </button>
        </div>

        {/* Search Input */}
        <input
          type="text"
          className="h-12 w-full rounded-lg border border-border bg-white px-4 text-base outline-none placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-light"
          placeholder="Tìm kiếm theo email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        {/* Search Results */}
        <div className="mt-4 flex flex-col overflow-y-auto max-h-[60vh] p-2">
          {loading ? (
            <p className="text-slate-800 text-sm text-center">Đang tìm kiếm...</p>
          ) : hasSearched && searchResults.length === 0 ? (
            <p className="text-slate-800 text-sm text-center">Không tìm thấy kết quả</p>
          ) : !hasSearched ? (
            <p className="text-slate-800 text-sm text-center">Không tìm thấy kết quả</p>
          ) : (
            searchResults.map((foundUser, index) => (
              <div
                key={index}
                className="flex items-center gap-4 hover:bg-slate-100 rounded-lg px-2 min-h-[72px] py-2 justify-between"
              >
                <div className="flex items-center gap-4">
                  <Avatar name={foundUser.username} size="lg" />
                  <div className="flex flex-col justify-center">
                    <p className="text-slate-900 text-base font-medium leading-normal line-clamp-1">
                      {foundUser.username || 'Người dùng'}
                    </p>
                    <p className="text-slate-500 text-xs font-normal leading-normal line-clamp-2">
                      {foundUser.email || ''}
                    </p>
                  </div>
                </div>
                <div className="shrink-0">
                  <button
                    onClick={() => handleMessage(foundUser)}
                    className="flex min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-9 px-4 bg-primary text-white text-sm font-medium leading-normal w-fit hover:bg-primary/90 transition-colors"
                  >
                    <span className="truncate">Nhắn tin</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}