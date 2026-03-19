<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useCustomizerStore } from '@/stores/customizer';
import axios from 'axios';
import Logo from '@/components/shared/Logo.vue';
import { md5 } from 'js-md5';
import { useAuthStore } from '@/stores/auth';
import { useCommonStore } from '@/stores/common';
import { useI18n } from '@/i18n/composables';
import { router } from '@/router';
import { useRoute } from 'vue-router';
import { useTheme } from 'vuetify';
import StyledMenu from '@/components/shared/StyledMenu.vue';
import { useLanguageSwitcher } from '@/i18n/composables';
import type { Locale } from '@/i18n/types';
import AboutPage from '@/views/AboutPage.vue';

const customizer = useCustomizerStore();
const theme = useTheme();
const { t } = useI18n();
const route = useRoute();
const LAST_BOT_ROUTE_KEY = 'persbot:last_bot_route';
const authControlsEnabled = false;
let dialog = ref(false);
let accountWarning = ref(false)
let aboutDialog = ref(false);
const username = localStorage.getItem('user');
let password = ref('');
let newPassword = ref('');
let confirmPassword = ref('');
let newUsername = ref('');
let status = ref('');
// Form validation
const formValid = ref(true);
const passwordRules = computed(() => [
  (v: string) => !!v || t('core.header.accountDialog.validation.passwordRequired'),
  (v: string) => v.length >= 8 || t('core.header.accountDialog.validation.passwordMinLength')
]);
const confirmPasswordRules = computed(() => [
  (v: string) => !newPassword.value || !!v || t('core.header.accountDialog.validation.passwordRequired'),
  (v: string) => !newPassword.value || v === newPassword.value || t('core.header.accountDialog.validation.passwordMatch')
]);
const usernameRules = computed(() => [
  (v: string) => !v || v.length >= 3 || t('core.header.accountDialog.validation.usernameMinLength')
]);

// 显示密码相关
const showPassword = ref(false);
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

// 账户修改状态
const accountEditStatus = ref({
  loading: false,
  success: false,
  error: false,
  message: ''
});

// 账户修改
function accountEdit() {
  accountEditStatus.value.loading = true;
  accountEditStatus.value.error = false;
  accountEditStatus.value.success = false;

  const passwordHash = password.value ? md5(password.value) : '';
  const newPasswordHash = newPassword.value ? md5(newPassword.value) : '';
  const confirmPasswordHash = confirmPassword.value ? md5(confirmPassword.value) : '';

  axios.post('/api/auth/account/edit', {
    password: passwordHash,
    new_password: newPasswordHash,
    confirm_password: confirmPasswordHash,
    new_username: newUsername.value ? newUsername.value : username
  })
    .then((res) => {
      if (res.data.status == 'error') {
        accountEditStatus.value.error = true;
        accountEditStatus.value.message = res.data.message;
        password.value = '';
        newPassword.value = '';
        confirmPassword.value = '';
        return;
      }
      accountEditStatus.value.success = true;
      accountEditStatus.value.message = res.data.message;
      setTimeout(() => {
        dialog.value = !dialog.value;
        const authStore = useAuthStore();
        authStore.logout();
      }, 2000);
    })
    .catch((err) => {
      console.log(err);
      accountEditStatus.value.error = true;
      accountEditStatus.value.message = typeof err === 'string' ? err : t('core.header.accountDialog.messages.updateFailed');
      password.value = '';
      newPassword.value = '';
      confirmPassword.value = '';
    })
    .finally(() => {
      accountEditStatus.value.loading = false;
    });
}

function toggleDarkMode() {
  const newTheme = customizer.uiTheme === 'PersbotDarkTheme' ? 'PersbotLightTheme' : 'PersbotDarkTheme';
  customizer.SET_UI_THEME(newTheme);
  theme.global.name.value = newTheme;
}

function handleLogoClick() {
  if (customizer.viewMode === 'chat') {
    aboutDialog.value = true;
  } else {
    router.push('/about');
  }
}

const commonStore = useCommonStore();
commonStore.createEventSource(); // log
commonStore.getStartTime();

// 视图模式切换
const viewMode = computed({
  get: () => customizer.viewMode,
  set: (value: 'bot' | 'chat') => {
    customizer.SET_VIEW_MODE(value);
  }
});

// 监听 viewMode 变化，切换到 bot 模式时跳转到首页
// 保存 bot 模式的最後路由
// 監聽 route 變化，保存最後一次 bot 路由
watch(() => route.fullPath, (newPath) => {
  if (customizer.viewMode === 'bot' && typeof window !== 'undefined') {
    try {
      localStorage.setItem(LAST_BOT_ROUTE_KEY, newPath);
    } catch (e) {
      console.error('Failed to save last bot route to localStorage:', e);
    }
  }
});

// 監聽 viewMode 切換
watch(() => customizer.viewMode, (newMode, oldMode) => {
  if (newMode === 'bot' && oldMode === 'chat' && typeof window !== 'undefined') {
    // 從 chat 切換回 bot，跳轉到最後一次的 bot 路由
    let lastBotRoute = '/';
    try {
      lastBotRoute = localStorage.getItem(LAST_BOT_ROUTE_KEY) || '/';
    } catch (e) {
      console.error('Failed to read last bot route from localStorage:', e);
    }
    router.push(lastBotRoute);
  }
});

// Merry Christmas! 🎄
const isChristmas = computed(() => {
  const today = new Date();
  const month = today.getMonth() + 1; // getMonth() 返回 0-11
  const day = today.getDate();
  return month === 12 && day === 25;
});

// 语言切换相关
const { languageOptions, currentLanguage, switchLanguage, locale } = useLanguageSwitcher();
const languages = computed(() => 
  languageOptions.value.map(lang => ({
    code: lang.value,
    name: lang.label,
    flag: lang.flag
  }))
);
const currentLocale = computed(() => locale.value);
const changeLanguage = async (langCode: string) => {
  await switchLanguage(langCode as Locale);
};

</script>

<template>
  <v-app-bar elevation="0" height="50" class="top-header">

    <!-- 桌面端 menu 按钮 - 仅在 bot 模式下显示 -->
    <v-btn v-if="customizer.viewMode === 'bot'"
      style="margin-left: 16px;"
      class="hidden-md-and-down" icon rounded="sm" variant="flat"
      @click.stop="customizer.SET_MINI_SIDEBAR(!customizer.mini_sidebar)">
      <v-icon>mdi-menu</v-icon>
    </v-btn>
    <!-- 移动端 menu 按钮 - 仅在 bot 模式下显示 -->
    <v-btn v-if="customizer.viewMode === 'bot'" class="hidden-lg-and-up ms-3" icon rounded="sm" variant="flat"
      @click.stop="customizer.SET_SIDEBAR_DRAWER">
      <v-icon>mdi-menu</v-icon>
    </v-btn>

    <!-- 移动端 chat sidebar 展开按钮 - 仅在 chat 模式下的小屏幕显示 -->
    <v-btn v-if="customizer.viewMode === 'chat'" class="hidden-lg-and-up ms-1" icon rounded="sm" variant="flat"
      @click.stop="customizer.TOGGLE_CHAT_SIDEBAR()">
      <v-icon>mdi-menu</v-icon>
    </v-btn>

    <div class="logo-container" :class="{ 'mobile-logo': $vuetify.display.xs, 'chat-mode-logo': customizer.viewMode === 'chat' }" @click="handleLogoClick">
      <span class="logo-text Outfit">Pers<span class="logo-text bot-text-wrapper">bot
        <img v-if="isChristmas" src="@/assets/images/xmas-hat.png" alt="Christmas hat" class="xmas-hat" />
      </span></span>
      <span class="logo-text logo-text-light Outfit" v-if="customizer.viewMode === 'chat'">Control Deck</span>
    </div>

  <v-spacer />
    
    <!-- Bot/Chat 模式切换按钮 - 手机端隐藏，移入 ... 菜单 -->
    <v-btn-toggle
      v-model="viewMode"
      mandatory
      variant="outlined"
      density="compact"
      class="mr-4 hidden-xs"
      color="primary"
    >
      <v-btn value="bot" size="small">
        <v-icon start>mdi-robot</v-icon>
        Bot
      </v-btn>
      <v-btn value="chat" size="small">
        <v-icon start>mdi-chat</v-icon>
        Chat
      </v-btn>
    </v-btn-toggle>


    <!-- 功能菜单 -->
    <StyledMenu offset="12" location="bottom end">
      <template v-slot:activator="{ props: activatorProps }">
        <v-btn
          v-bind="activatorProps"
          size="small"
          class="action-btn mr-4"
          color="var(--v-theme-surface)"
          variant="flat"
          rounded="sm"
          icon
        >
          <v-icon>mdi-dots-vertical</v-icon>
        </v-btn>
      </template>

      <!-- Bot/Chat 模式切换 - 仅在手机端显示 -->
      <template v-if="$vuetify.display.xs">
        <div class="mobile-mode-toggle-wrapper">
          <v-btn-toggle
            v-model="viewMode"
            mandatory
            variant="outlined"
            density="compact"
            color="primary"
            class="mobile-mode-toggle"
          >
            <v-btn value="bot" size="small">
              <v-icon start>mdi-robot</v-icon>
              Bot
            </v-btn>
            <v-btn value="chat" size="small">
              <v-icon start>mdi-chat</v-icon>
              Chat
            </v-btn>
          </v-btn-toggle>
        </div>
        <v-divider class="my-1" />
      </template>

      <!-- 语言切换分组 -->
      <v-menu
        :open-on-hover="!$vuetify.display.xs"
        :open-on-click="$vuetify.display.xs"
        :open-delay="!$vuetify.display.xs ? 60 : 0"
        :close-delay="!$vuetify.display.xs ? 120 : 0"
        :location="$vuetify.display.xs ? 'bottom' : 'start center'"
        offset="8"
      >
        <template v-slot:activator="{ props: languageMenuProps }">
          <v-list-item
            v-bind="languageMenuProps"
            class="styled-menu-item language-group-trigger"
            rounded="md"
          >
            <template v-slot:prepend>
              <v-icon>mdi-translate</v-icon>
            </template>
            <v-list-item-title>{{ t('core.common.language') }}</v-list-item-title>
            <template v-slot:append>
              <span class="language-group-current">{{ currentLanguage?.flag }}</span>
              <v-icon size="18" class="language-group-arrow">mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </template>

        <v-card class="styled-menu-card" style="min-width: 180px;" elevation="8" rounded="lg">
          <v-list density="compact" class="styled-menu-list pa-1">
            <v-list-item
              v-for="lang in languages"
              :key="lang.code"
              :value="lang.code"
              @click="changeLanguage(lang.code)"
              :class="{ 'styled-menu-item-active': currentLocale === lang.code }"
              class="styled-menu-item"
              rounded="md"
            >
              <template v-slot:prepend>
                <span class="language-flag">{{ lang.flag }}</span>
              </template>
              <v-list-item-title>{{ lang.name }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-menu>

      <!-- 主题切换 -->
      <v-list-item
        @click="toggleDarkMode()"
        class="styled-menu-item"
        rounded="md"
      >
        <template v-slot:prepend>
          <v-icon>
            {{ useCustomizerStore().uiTheme === 'PersbotDarkTheme' ? 'mdi-weather-night' : 'mdi-white-balance-sunny' }}
          </v-icon>
        </template>
        <v-list-item-title>
          {{ useCustomizerStore().uiTheme === 'PersbotDarkTheme' ? t('core.header.buttons.theme.light') : t('core.header.buttons.theme.dark') }}
        </v-list-item-title>
      </v-list-item>

      <!-- 账户按钮 -->
      <v-list-item
        v-if="authControlsEnabled"
        @click="dialog = true"
        class="styled-menu-item"
        rounded="md"
      >
        <template v-slot:prepend>
          <v-icon>mdi-account</v-icon>
        </template>
        <v-list-item-title>{{ t('core.header.accountDialog.title') }}</v-list-item-title>
      </v-list-item>
    </StyledMenu>

    <!-- 账户对话框 -->
    <v-dialog v-if="authControlsEnabled" v-model="dialog" persistent :max-width="$vuetify.display.xs ? '90%' : '500'">
      <v-card class="account-dialog">
        <v-card-text class="py-6">
          <div class="d-flex flex-column align-center mb-6">
            <logo :title="t('core.header.logoTitle')" :subtitle="t('core.header.accountDialog.title')"></logo>
          </div>
          <v-alert v-if="accountWarning" type="warning" variant="tonal" border="start" class="mb-4">
            <strong>{{ t('core.header.accountDialog.securityWarning') }}</strong>
          </v-alert>

          <v-alert v-if="accountEditStatus.success" type="success" variant="tonal" border="start" class="mb-4">
            {{ accountEditStatus.message }}
          </v-alert>

          <v-alert v-if="accountEditStatus.error" type="error" variant="tonal" border="start" class="mb-4">
            {{ accountEditStatus.message }}
          </v-alert>

          <v-form v-model="formValid" @submit.prevent="accountEdit">
            <v-text-field v-model="password" :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
              :type="showPassword ? 'text' : 'password'" :label="t('core.header.accountDialog.form.currentPassword')"
              variant="outlined" required clearable @click:append-inner="showPassword = !showPassword"
              prepend-inner-icon="mdi-lock-outline" hide-details="auto" class="mb-4"></v-text-field>

            <v-text-field v-model="newPassword" :append-inner-icon="showNewPassword ? 'mdi-eye-off' : 'mdi-eye'"
              :type="showNewPassword ? 'text' : 'password'" :rules="passwordRules"
              :label="t('core.header.accountDialog.form.newPassword')" variant="outlined" clearable
              @click:append-inner="showNewPassword = !showNewPassword" prepend-inner-icon="mdi-lock-plus-outline"
              :hint="t('core.header.accountDialog.form.passwordHint')" persistent-hint class="mb-4"></v-text-field>

            <v-text-field v-model="confirmPassword" :append-inner-icon="showConfirmPassword ? 'mdi-eye-off' : 'mdi-eye'"
              :type="showConfirmPassword ? 'text' : 'password'" :rules="confirmPasswordRules"
              :label="t('core.header.accountDialog.form.confirmPassword')" variant="outlined" clearable
              @click:append-inner="showConfirmPassword = !showConfirmPassword" prepend-inner-icon="mdi-lock-check-outline"
              :hint="t('core.header.accountDialog.form.confirmPasswordHint')" persistent-hint class="mb-4"></v-text-field>

            <v-text-field v-model="newUsername" :rules="usernameRules"
              :label="t('core.header.accountDialog.form.newUsername')" variant="outlined" clearable
              prepend-inner-icon="mdi-account-edit-outline" :hint="t('core.header.accountDialog.form.usernameHint')"
              persistent-hint class="mb-3"></v-text-field>
          </v-form>

          <div class="text-caption text-medium-emphasis mt-2">
            {{ t('core.header.accountDialog.form.defaultCredentials') }}
          </div>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn v-if="!accountWarning" variant="tonal" color="secondary" @click="dialog = false"
            :disabled="accountEditStatus.loading">
            {{ t('core.header.accountDialog.actions.cancel') }}
          </v-btn>
          <v-btn color="primary" @click="accountEdit" :loading="accountEditStatus.loading" :disabled="!formValid"
            prepend-icon="mdi-content-save">
            {{ t('core.header.accountDialog.actions.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- About 对话框 - 仅在 chat mode 下使用 -->
    <v-dialog v-model="aboutDialog"
      width="600">
      <v-card>
        <v-card-text style="overflow-y: auto;">
          <AboutPage />
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-app-bar>
</template>

<style>
.markdown-content h1 {
  font-size: 1.3em;
}

.markdown-content ol {
  padding-left: 24px;
  /* Adds indentation to ordered lists */
  margin-top: 8px;
  margin-bottom: 8px;
}

.markdown-content ul {
  padding-left: 24px;
  /* Adds indentation to unordered lists */
  margin-top: 8px;
  margin-bottom: 8px;
}

.account-dialog .v-card-text {
  padding-top: 24px;
  padding-bottom: 24px;
}

.account-dialog .v-alert {
  margin-bottom: 20px;
}

.account-dialog .v-btn {
  text-transform: none;
  font-weight: 500;
  border-radius: 8px;
}

.account-dialog .v-avatar {
  transition: transform 0.3s ease;
}

.account-dialog .v-avatar:hover {
  transform: scale(1.05);
}

/* 响应式布局样式 */
.logo-container {
  margin-left: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 18px;
  border: 1px solid var(--persbot-stroke-soft);
  background: var(--persbot-panel-strong);
  box-shadow: var(--persbot-shadow-soft);
  backdrop-filter: blur(16px);
}

.mobile-logo {
  margin-left: 8px;
  gap: 4px;
  padding: 7px 10px;
}

.chat-mode-logo {
  margin-left: 22px;
}

.mobile-logo.chat-mode-logo {
  margin-left: 4px;
}

.logo-text {
  color: rgb(var(--v-theme-primaryText));
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0.01em;
}

.logo-text-light {
  color: rgba(var(--v-theme-primaryText), 0.62);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.bot-text-wrapper {
  position: relative;
  display: inline-block;
  color: rgb(var(--v-theme-primary));
}

.xmas-hat {
  position: absolute;
  top: -3px;
  right: -14px;
  width: 24px;
  height: 24px;
  z-index: 1;
}

.version-text {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 600;
  margin-left: 2px;
}

.action-btn {
  margin-right: 6px;
}

.language-flag {
  font-size: 16px;
  margin-right: 8px;
}

.language-group-trigger :deep(.v-list-item__append) {
  display: flex;
  align-items: center;
  gap: 6px;
}

.language-group-current {
  font-size: 16px;
  line-height: 1;
}

.language-group-arrow {
  opacity: 0.7;
}

.language-submenu-card {
  min-width: 180px;
}

.mobile-mode-toggle-wrapper {
  display: flex;
  justify-content: center;
  padding: 8px 12px 4px;
}

.mobile-mode-toggle {
  width: 100%;
}

.mobile-mode-toggle .v-btn {
  flex: 1;
}

/* 移动端对话框标题样式 */
.mobile-card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 移动端样式优化 */
@media (max-width: 600px) {
  .logo-text {
    font-size: 20px;
  }

  .action-btn {
    margin-right: 4px;
    min-width: 32px !important;
    width: 32px;
  }

  .v-card-title {
    padding: 12px 16px;
  }

  .v-card-text {
    padding: 16px;
  }

  .v-tabs .v-tab {
    padding: 0 10px;
    font-size: 0.9rem;
  }

  /* 移动端模式切换按钮样式 */
  .v-btn-toggle {
    margin-right: 8px;
  }

  .v-btn-toggle .v-btn {
    font-size: 0.75rem;
    padding: 0 8px;
  }

  .v-btn-toggle .v-icon {
    font-size: 16px;
  }
}
</style>
