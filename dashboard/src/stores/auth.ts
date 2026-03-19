import { defineStore } from 'pinia';
import { router } from '@/router';

const SHOWCASE_USER = 'persbot';
const SHOWCASE_TOKEN = 'persbot-showcase-token';

export const useAuthStore = defineStore({
  id: 'auth',
  state: () => ({
    // @ts-ignore
    username: '',
    returnUrl: null
  }),
  actions: {
    ensureSession() {
      this.username = localStorage.getItem('user') || SHOWCASE_USER;
      localStorage.setItem('user', this.username);
      localStorage.setItem('token', localStorage.getItem('token') || SHOWCASE_TOKEN);
      localStorage.removeItem('change_pwd_hint');
    },
    async login(username: string, password: string): Promise<void> {
      void username;
      void password;
      this.ensureSession();
      await router.push(this.returnUrl || '/dashboard/default');
    },
    logout() {
      this.ensureSession();
      router.push('/');
    },
    has_token(): boolean {
      this.ensureSession();
      return true;
    }
  }
});
