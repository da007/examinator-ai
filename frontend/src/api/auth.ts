// ─── Auth API ─────────────────────────────────────────────────────────────────
import { apiClient } from './client';
import type { AuthUser, TokenResponse } from '@/types';

/** POST /auth/login — form-data, как требует OAuth2PasswordRequestForm */
export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);

  const { data } = await apiClient.post<TokenResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

/** GET /users/me — текущий пользователь */
export async function getMe(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>('/auth/me');
  return data;
}
