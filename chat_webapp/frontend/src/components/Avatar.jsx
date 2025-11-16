// Hàm tạo avatar mặc định từ tên
const getAvatarInitials = (name) => {
  if (!name) return '?';
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[words.length - 1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};

// Hàm tạo màu nền dựa trên tên (để mỗi người có màu nhất quán)
const getAvatarColor = (name) => {
  if (!name) return '#9CA3AF';
  const colors = [
    '#EF4444', // red
    '#F59E0B', // amber
    '#10B981', // emerald
    '#3B82F6', // blue
    '#8B5CF6', // violet
    '#EC4899', // pink
    '#06B6D4', // cyan
    '#F97316', // orange
    '#84CC16', // lime
    '#6366F1', // indigo
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

// Component Avatar
export default function Avatar({ name, size = 'md', showOnline = false, isOnline = false }) {
  const initials = getAvatarInitials(name);
  const bgColor = getAvatarColor(name);
  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
    xl: 'h-32 w-32 text-2xl',
  };
  const indicatorSize = {
    sm: 'h-2.5 w-2.5',
    md: 'h-2.5 w-2.5',
    lg: 'h-3 w-3',
    xl: 'h-4 w-4',
  };

  return (
    <div className="relative">
      <div
        className={`${sizeClasses[size]} flex shrink-0 items-center justify-center rounded-full font-semibold text-white`}
        style={{ backgroundColor: bgColor }}
      >
        {initials}
      </div>
      {showOnline && isOnline && (
        <span
          className={`absolute bottom-0 right-0 ${indicatorSize[size]} rounded-full border-2 border-white bg-success`}
        />
      )}
    </div>
  );
}

