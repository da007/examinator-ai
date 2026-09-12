// ─── LoginPage ────────────────────────────────────────────────────────────────
// Строгая форма входа. Нет лишнего.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, getMe } from '@/api/auth';
import { useAppStore } from '@/store/useAppStore';
import { getApiErrorMessage } from '@/api/client';
import { APP_CONFIG } from '@/config/app';

// ИМПОРТ ВЫНЕСЕННЫХ СТИЛЕЙ
import '@/assets/styles/login.css';

export function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAppStore((s) => s.setUser);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const token = await login(email, password);
      localStorage.setItem('access_token', token.accessToken);
      const user = await getMe();
      setUser(user);

      // Роутинг по роли
      if (user.role === 'student') navigate('/dashboard');
      else navigate('/teacher/dashboard');
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Header */}
        <div className="login-header">
          <span className="login-logo">⬡</span>
          <h1 className="login-title">{APP_CONFIG.appName}</h1>
          <p className="login-subtitle">Система интеллектуального контроля знаний</p>
        </div>

        {/* Form */}
        <div className="login-form">
          <form onSubmit={handleSubmit}>
            <div className="login-field">
              <label className="login-label" htmlFor="email">Электронная почта</label>
              <input
                id="email"
                type="email"
                className="login-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@university.kz"
                autoComplete="email"
                required
                disabled={isLoading}
              />
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="password">Пароль</label>
              <input
                id="password"
                type="password"
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                disabled={isLoading}
              />
            </div>

            {error && (
              <div className="login-error" role="alert">{error}</div>
            )}

            <button
              type="submit"
              className="login-submit"
              disabled={isLoading || !email || !password}
            >
              {isLoading ? 'Вход…' : 'Войти'}
            </button>
          </form>
        </div>

        <p className="login-footer">
          Платформа для проведения экзаменов с ИИ-проверкой
        </p>
      </div>
    </div>
  );
}