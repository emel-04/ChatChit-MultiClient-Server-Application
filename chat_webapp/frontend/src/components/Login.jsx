import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { User, Lock, Eye, EyeOff } from 'lucide-react';
import ChatChitLogo from '../assets/ChatChit-login.png';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password);
      if (result && result.success) {
        navigate('/message');
      } else {
        setError(result?.message || 'Đăng nhập thất bại');
      }
    } catch (err) {
      console.error('Login error:', err);
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
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="w-full max-w-md px-3">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img src={ChatChitLogo} alt="ChatChit" className="h-20 w-20" />
        </div>

        {/* Heading */}
        <h1 className="w-full max-w-md mb-6 text-center heading-large text-text-primary">
          Chào mừng bạn quay trở lại!
        </h1>

        {/* Error Message */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email Field */}
          <div>
            <label className="mb-2 block label-text text-text-primary">
              Email
            </label>
            <div className="flex items-center rounded-lg border border-border bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-light">
              <div className="flex items-center justify-center pl-4">
                <User className="h-5 w-5 text-text-muted" />
              </div>
              <input
                type="text"
                className="h-14 w-full border-0 bg-transparent px-4 text-base outline-none placeholder:text-text-muted"
                placeholder="Nhập email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label className="mb-2 block label-text text-text-primary">
              Mật khẩu
            </label>
            <div className="flex items-center rounded-lg border border-border bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-light">
              <div className="flex items-center justify-center pl-4">
                <Lock className="h-5 w-5 text-text-muted" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                className="h-14 w-full border-0 bg-transparent px-4 text-base outline-none placeholder:text-text-muted"
                placeholder="Nhập mật khẩu của bạn"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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

          {/* Forgot Password */}
          <div className="flex justify-end">
            <a href="#" className="text-sm text-primary hover:underline">
              Quên mật khẩu?
            </a>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="h-14 w-full rounded-lg bg-primary text-base font-bold text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
          >
            {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
          </button>
        </form>

        {/* Signup Link */}
        <p className="mt-6 text-center body-medium text-text-secondary">
          Chưa có tài khoản?{' '}
          <Link to="/signup" className="font-semibold text-primary hover:underline">
            Đăng ký ngay
          </Link>
        </p>
      </div>
    </div>
  );
}