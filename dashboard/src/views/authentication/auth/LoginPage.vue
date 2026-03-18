<script setup lang="ts">
import AuthLogin from '../authForms/AuthLogin.vue';
import LanguageSwitcher from '@/components/shared/LanguageSwitcher.vue';
import { onMounted, ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useCustomizerStore } from "@/stores/customizer";
import { useModuleI18n } from '@/i18n/composables';
import { useTheme } from 'vuetify';

const cardVisible = ref(false);
const router = useRouter();
const authStore = useAuthStore();
const customizer = useCustomizerStore();
const { tm: t } = useModuleI18n('features/auth');
const theme = useTheme();

// 主题切换函数
function toggleTheme() {
  const newTheme = customizer.uiTheme === 'PersbotDarkTheme' ? 'PersbotLightTheme' : 'PersbotDarkTheme';
  customizer.SET_UI_THEME(newTheme);
  theme.global.name.value = newTheme;
}

onMounted(() => {
  // 检查用户是否已登录，如果已登录则重定向
  if (authStore.has_token()) {
    router.push(authStore.returnUrl || '/');
    return;
  }

  // 添加一个小延迟以获得更好的动画效果
  setTimeout(() => {
    cardVisible.value = true;
  }, 100);
});
</script>

<template>
  <div class="login-page-container">
    <v-card class="login-card" :class="{ 'login-card--visible': cardVisible }" elevation="0">
      <v-card-title class="login-card__header">
        <div class="d-flex justify-space-between align-center w-100">
          <img width="80" src="@/assets/images/icon-no-shadow.svg" alt="Persbot Logo">
          <div class="d-flex align-center gap-1">
            <LanguageSwitcher />
            <v-divider vertical class="mx-1"
              style="height: 24px !important; opacity: 0.9 !important; align-self: center !important; border-color: rgba(var(--v-theme-primary), 0.45) !important;"></v-divider>
            <v-btn @click="toggleTheme" class="theme-toggle-btn" icon variant="text" size="small">
              <v-icon size="18" :color="'rgb(var(--v-theme-primary))'">
                mdi-white-balance-sunny
              </v-icon>
              <v-tooltip activator="parent" location="top">
                {{ t('theme.switchToLight') }}
              </v-tooltip>
            </v-btn>
          </div>
        </div>
        <div class="login-badge">Personalized AI Agent</div>
        <div class="ml-2 login-title">{{ t('logo.title') }}</div>
        <div class="mt-2 ml-2 login-subtitle">{{ t('logo.subtitle') }}</div>
      </v-card-title>
      <v-card-text>
        <AuthLogin />
      </v-card-text>
    </v-card>
  </div>
</template>

<style lang="scss">
.login-page-container {
  background:
    radial-gradient(circle at 18% 20%, rgba(var(--v-theme-primary), 0.16), transparent 28%),
    radial-gradient(circle at 82% 14%, rgba(var(--v-theme-secondary), 0.16), transparent 24%),
    linear-gradient(180deg, rgba(var(--v-theme-background), 1) 0%, rgba(var(--v-theme-containerBg), 1) 100%);
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.login-card {
  width: min(440px, calc(100vw - 32px));
  padding: 12px;
  border-radius: 26px !important;
  border: 1px solid var(--persbot-stroke-soft);
  background: var(--persbot-panel-strong) !important;
  box-shadow: var(--persbot-shadow-strong) !important;
  backdrop-filter: blur(18px);
  transform: translateY(16px);
  opacity: 0;
  transition: transform 0.35s ease, opacity 0.35s ease;
}

.login-card--visible {
  transform: translateY(0);
  opacity: 1;
}

.login-card__header {
  padding-bottom: 6px;
}

.login-badge {
  display: inline-flex;
  margin: 14px 0 0 8px;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.login-subtitle {
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.theme-toggle-btn {
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  background: rgba(var(--v-theme-primary), 0.06);
}
</style>
