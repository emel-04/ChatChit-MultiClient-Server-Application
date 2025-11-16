import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Eye, EyeOff } from 'lucide-react';
import ChatChitLogo from '../assets/ChatChit-signup.png';

export default function Signup() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return;
    }

    if (formData.password.length < 6) {
      setError('Mật khẩu phải có ít nhất 6 ký tự');
      return;
    }

    if (!formData.username || formData.username.trim().length < 3) {
      setError('Tên người dùng phải có ít nhất 3 ký tự');
      return;
    }

    setLoading(true);

    try {
      const result = await register(formData.username.trim(), formData.email, formData.password);
      if (result && result.success) {
        navigate('/message');
      } else {
        setError(result?.message || 'Đăng ký thất bại');
      }
    } catch (err) {
      console.error('Signup error:', err);
      if (err.response?.data?.message) {
        setError(err.response.data.message);
      } else if (err.message) {
        setError(`Lỗi kết nối: ${err.message}`);
      } else {
        setError('Lỗi kết nối server. Vui lòng kiểm tra backend đang chạy tại port 8000.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center bg-background-signup p-12">
        <div className="max-w-md text-center">
          <div className="flex justify-center">
            <img src={ChatChitLogo} alt="ChatChit" className="mx-auto mb-8 h-24 w-24" />
          </div>
          <h1 className="mb-4 heading-medium text-text-primary">
            Kết nối mọi lúc, mọi nơi
          </h1>
          <p className="body-large text-text-secondary">
            Tham gia cộng đồng và bắt đầu cuộc trò chuyện của bạn ngay hôm nay. ChitChat giúp bạn giữ liên lạc với những người quan trọng nhất.
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="flex w-full items-center justify-center bg-white p-6 lg:w-1/2">
        <div className="w-full max-w-md">
          <h1 className="mb-6 heading-large text-text-primary">
            Tạo tài khoản mới
          </h1>

          {/* Error Message */}
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="mb-2 block label-text text-text-primary">
                Tên người dùng
              </label>
              <input
                type="text"
                name="username"
                className="h-12 w-full rounded-lg border border-border bg-white px-4 text-base outline-none placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-light"
                placeholder="Nhập tên người dùng"
                value={formData.username}
                onChange={handleChange}
                required
              />
            </div>

            {/* Email */}
            <div>
              <label className="mb-2 block label-text text-text-primary">
                Email
              </label>
              <input
                type="email"
                name="email"
                className="h-12 w-full rounded-lg border border-border bg-white px-4 text-base outline-none placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-light"
                placeholder="Nhập email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>

            {/* Password */}
            <div>
              <label className="mb-2 block label-text text-text-primary">
                Mật khẩu
              </label>
              <div className="flex items-center rounded-lg border border-border bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-light">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  className="h-12 w-full border-0 bg-transparent px-4 text-base outline-none placeholder:text-text-muted"
                  placeholder="Nhập mật khẩu của bạn"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
                <button
                  type="button"
                  className="flex items-center justify-center pr-4"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-text-muted" />
                  ) : (
                    <Eye className="h-5 w-5 text-text-muted" />
                  )}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="mb-2 block label-text text-text-primary">
                Xác nhận Mật khẩu
              </label>
              <div className="flex items-center rounded-lg border border-border bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-light">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  className="h-12 w-full border-0 bg-transparent px-4 text-base outline-none placeholder:text-text-muted"
                  placeholder="Nhập lại mật khẩu của bạn"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                />
                <button
                  type="button"
                  className="flex items-center justify-center pr-4"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5 text-text-muted" />
                  ) : (
                    <Eye className="h-5 w-5 text-text-muted" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="h-12 w-full rounded-lg bg-primary text-base font-bold text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
            >
              {loading ? 'Đang đăng ký...' : 'Đăng ký'}
            </button>
          </form>

          {/* Login Link */}
          <p className="mt-6 text-center body-medium text-text-secondary">
            Đã có tài khoản?{' '}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              Đăng nhập
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}