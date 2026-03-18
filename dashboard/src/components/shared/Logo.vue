<template>
  <div class="logo-container">
    <div class="logo-content">
      <div class="logo-image">
        <div class="logo-image-frame">
          <img width="110" src="@/assets/images/persbot_logo_mini.webp" alt="Persbot Logo">
        </div>
      </div>
      <div class="logo-text">
        <div class="logo-badge">PERSONALIZED AI AGENT</div>
        <h2 
          :style="{ color: 'rgb(var(--v-theme-primary))' }"
          v-html="formatTitle(title || t('core.header.logoTitle'))"
        ></h2>
        <!-- 父子组件传递css变量可能会出错，暂时使用十六进制颜色值 -->
        <h4 :style="{ color: 'rgba(var(--v-theme-on-surface), 0.72)' }"
            class="hint-text">{{ subtitle || t('core.header.accountDialog.title') }}</h4>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n/composables';

const { t } = useI18n();

const props = withDefaults(defineProps<{
  title?: string;
  subtitle?: string;
}>(), {
  title: '',  // 默认为空，组件会使用翻译值
  subtitle: ''
})

// 智能格式化标题，在小屏幕上允许在合适位置换行
const formatTitle = (title: string) => {
  // 如果标题包含 "Persbot" 和其他文字，在它们之间添加换行机会
  if (title.includes('Persbot ') || title.includes('Persbot')) {
    // 处理 "Persbot 仪表盘" 或 "Persbot Dashboard" 等格式
    return title.replace(/(Persbot)\s+(.+)/, '$1<wbr> $2');
  }
  return title;
}
</script>

<style scoped>
.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  margin-bottom: 10px;
}

.logo-content {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 16px;
  max-width: 100%;
  overflow: visible;
  border-radius: 22px;
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  background: var(--persbot-panel-soft);
  box-shadow: var(--persbot-shadow-soft);
}

.logo-image {
  display: flex;
  justify-content: center;
  align-items: center;
}

.logo-image-frame {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92px;
  height: 92px;
  border-radius: 28px;
  background:
    linear-gradient(145deg, rgba(var(--v-theme-primary), 0.16), rgba(var(--v-theme-secondary), 0.16));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28);
}

.logo-image img {
  transition: transform 0.3s ease;
  width: 68px;
}

.logo-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}

.logo-badge {
  margin-bottom: 8px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.logo-text h2 {
  margin: 0;
  font-size: 1.9rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
  min-width: fit-content;
}

/* 在小屏幕上允许在指定位置换行 */
@media (max-width: 420px) {
  .logo-text h2 {
    line-height: 1.3;
  }
}

.logo-text h4 {
  margin: 8px 0 0 0;
  font-size: 0.96rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

/* 响应式处理 */
@media (max-width: 520px) {
  .logo-content {
    gap: 15px;
  }
  
  .logo-text h2 {
    font-size: 1.6rem;
  }
  
  .logo-text h4 {
    font-size: 0.9rem;
  }
  
  .logo-image img {
    width: 90px;
  }
}
</style>
