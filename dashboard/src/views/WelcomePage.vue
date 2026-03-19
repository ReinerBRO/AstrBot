<template>
  <div class="welcome-page">
    <v-container fluid class="pa-0">
      <v-row class="px-4 py-3 pb-6 welcome-hero-row">
        <v-col cols="12">
          <div class="welcome-eyebrow">Persbot Workspace</div>
          <h1 class="text-h1 font-weight-bold mb-2 d-flex align-center">
            {{ greetingText }} {{ greetingEmoji }}
          </h1>
          <p class="text-subtitle-1 text-medium-emphasis mb-0">
            {{ tm('subtitle') }}
          </p>
        </v-col>
      </v-row>

      <v-row class="px-4">
        <v-col cols="12">
          <v-card class="welcome-card welcome-card--showcase pa-6" elevation="0" border>
            <div class="d-flex align-start justify-space-between flex-wrap" style="gap: 16px">
              <div>
                <div class="welcome-eyebrow">Showcase Entry</div>
                <div class="text-h3 font-weight-bold mb-2">{{ showcasePreset.label }}</div>
                <p class="text-body-1 text-medium-emphasis mb-0">
                  {{ showcasePreset.summary }}
                </p>
              </div>
              <v-chip color="primary" variant="flat" rounded="pill" class="font-weight-bold px-4">
                {{ showcasePreset.code.toUpperCase() }}
              </v-chip>
            </div>
            <div class="d-flex flex-wrap mt-4" style="gap: 10px">
              <v-chip
                v-for="highlight in showcasePreset.highlights"
                :key="highlight"
                color="primary"
                variant="tonal"
                rounded="pill"
              >
                {{ highlight }}
              </v-chip>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="px-4">
        <v-col cols="12">
          <v-card class="welcome-card welcome-card--onboard pa-6" elevation="0" border>
            <div class="mb-4 text-h3 font-weight-bold">
              {{ tm('onboard.title') }}
            </div>

            <v-timeline align="start" side="end" density="compact" class="welcome-timeline" truncate-line="both">
              <v-timeline-item
                v-for="(step, index) in onboardingSteps"
                :key="step.key"
                :dot-color="step.state === 'completed' ? 'success' : 'primary'"
                :icon="step.state === 'completed' ? 'mdi-check' : onboardingStepIcons[index] || 'mdi-circle-medium'"
                fill-dot
                size="small"
              >
                <div class="pl-2">
                  <div class="text-h6 font-weight-bold mb-1">{{ step.title }}</div>
                  <p class="text-body-2 text-medium-emphasis mb-3">{{ step.description }}</p>
                  <div class="d-flex align-center">
                    <v-btn
                      color="primary"
                      variant="flat"
                      rounded="pill"
                      class="px-6"
                      :loading="step.loading"
                      @click="step.action"
                    >
                      {{ tm('onboard.configure') }}
                    </v-btn>
                    <div
                      v-if="step.state === 'completed'"
                      class="text-success d-flex align-center text-body-2 font-weight-medium ml-3">
                      {{ tm('onboard.completed') }}
                    </div>
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card>

        </v-col>
      </v-row>

      <v-row class="px-4 mt-4">
        <v-col cols="12">
          <v-card class="welcome-card pa-6" elevation="0" border>
            <div class="mb-4 text-h3 font-weight-bold">
              {{ tm('resources.title') }}
            </div>
            <v-row>
              <v-col cols="12" sm="4">
                <!-- GitHub Card -->
                <v-card variant="outlined" class="resource-link-card h-100 pa-4 d-flex flex-column"
                  href="https://github.com/PersbotDevs/Persbot/" target="_blank">
                  <div class="d-flex align-center mb-3">
                    <v-icon size="32" class="mr-3">mdi-github</v-icon>
                    <span class="text-h6 font-weight-bold">GitHub</span>
                  </div>
                  <p class="text-body-2 text-medium-emphasis mb-0">
                    {{ tm('resources.githubDesc') }}
                  </p>
                </v-card>
              </v-col>

              <v-col cols="12" sm="4">
                <!-- Docs Card -->
                <v-card variant="outlined" class="resource-link-card h-100 pa-4 d-flex flex-column" href="https://docs.persbot.app"
                  target="_blank">
                  <div class="d-flex align-center mb-3">
                    <v-icon size="32" class="mr-3">mdi-book-open-variant</v-icon>
                    <span class="text-h6 font-weight-bold">{{ tm('resources.docsTitle') }}</span>
                  </div>
                  <p class="text-body-2 text-medium-emphasis mb-0">
                    {{ tm('resources.docsDesc') }}
                  </p>
                </v-card>
              </v-col>

              <v-col cols="12" sm="4">
                <!-- Afdian Card -->
                <v-card variant="outlined" class="resource-link-card h-100 pa-4 d-flex flex-column"
                  href="https://afdian.com/a/persbot_team" target="_blank">
                  <div class="d-flex align-center mb-3">
                    <v-icon size="32" class="mr-3">mdi-hand-heart</v-icon>
                    <span class="text-h6 font-weight-bold">{{ tm('resources.afdianTitle') }}</span>
                  </div>
                  <p class="text-body-2 text-medium-emphasis mb-0">
                    {{ tm('resources.afdianDesc') }}
                  </p>
                </v-card>
              </v-col>

            </v-row>
          </v-card>
        </v-col>
      </v-row>

      <v-row v-if="showAnnouncement" class="px-4 mb-4">
        <v-col cols="12">
          <v-card class="welcome-card pa-6" elevation="0" border>
            <div class="mb-4 text-h3 font-weight-bold">
              {{ tm('announcement.title') }}
            </div>
            <MarkdownRender
              :content="welcomeAnnouncement"
              :typewriter="false"
              class="welcome-announcement-markdown markdown-content"
            />
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <AddNewPlatform v-model:show="showAddPlatformDialog" :metadata="platformMetadata" :config_data="platformConfigData"
      @refresh-config="loadPlatformConfigBase" />
    <ProviderConfigDialog v-model="showProviderDialog" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import axios from 'axios';
import AddNewPlatform from '@/components/platform/AddNewPlatform.vue';
import ProviderConfigDialog from '@/components/chat/ProviderConfigDialog.vue';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import { useToast } from '@/utils/toast';
import { MarkdownRender } from 'markstream-vue';
import { getShowcaseFeatureMap, getShowcasePreset } from '@/showcase/presets';
import 'markstream-vue/index.css';
import 'highlight.js/styles/github.css';

type StepState = 'pending' | 'completed' | 'skipped';

const { tm } = useModuleI18n('features/welcome');
const { locale } = useI18n();
const { success: showSuccess, error: showError } = useToast();

const showAddPlatformDialog = ref(false);
const showProviderDialog = ref(false);
const loadingPlatformDialog = ref(false);
const showcasePreset = getShowcasePreset();
const showcaseFeatures = getShowcaseFeatureMap();
const onboardingStepIcons = ['mdi-numeric-1', 'mdi-numeric-2', 'mdi-numeric-3', 'mdi-numeric-4'];

const platformMetadata = ref<Record<string, any>>({});
const platformConfigData = ref<Record<string, any>>({});
const platformCountBeforeOpen = ref(0);
const providerCountBeforeOpen = ref(0);

const platformStepState = ref<StepState>('pending');
const providerStepState = ref<StepState>('pending');
const welcomeAnnouncementRaw = ref<unknown>(null);

function resolveWelcomeAnnouncement(raw: unknown, currentLocale: string) {
  if (typeof raw === 'string') {
    return raw.trim();
  }

  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return '';
  }

  const localeMap = raw as Record<string, unknown>;
  const normalized = currentLocale.replace('-', '_');
  const preferredKeys =
    normalized.startsWith('zh')
      ? [normalized, 'zh_CN', 'zh-CN', 'zh', 'en_US', 'en-US', 'en']
      : [normalized, 'en_US', 'en-US', 'en', 'zh_CN', 'zh-CN', 'zh'];

  for (const key of preferredKeys) {
    const value = localeMap[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value.trim();
    }
  }

  return '';
}

const welcomeAnnouncement = computed(() =>
  resolveWelcomeAnnouncement(welcomeAnnouncementRaw.value, locale.value)
);
const showAnnouncement = computed(() => welcomeAnnouncement.value.length > 0);
const onboardingSteps = computed(() => {
  const steps = [];

  if (showcaseFeatures.platforms) {
    steps.push({
      key: 'platforms',
      title: tm('onboard.step1Title'),
      description: tm('onboard.step1Desc'),
      state: platformStepState.value,
      loading: loadingPlatformDialog.value,
      action: openPlatformDialog,
    });
  }

  if (showcaseFeatures.providers) {
    steps.push({
      key: 'providers',
      title: tm('onboard.step2Title'),
      description: tm('onboard.step2Desc'),
      state: providerStepState.value,
      loading: false,
      action: openProviderDialog,
    });
  }

  return steps;
});

const springFestivalDates: Record<number, string> = {
  2025: '01-29',
  2026: '02-17',
  2027: '02-06',
  2028: '01-26',
  2029: '02-13',
  2030: '02-03'
}

function isSpringFestival() {
  const now = new Date();
  const year = now.getFullYear();
  const dateStr = springFestivalDates[year];

  if (!dateStr) return false;

  const [month, day] = dateStr.split('-').map(Number);
  const festivalDate = new Date(year, month - 1, day);

  const start = new Date(festivalDate);
  start.setDate(festivalDate.getDate() - 5);

  const end = new Date(festivalDate);
  end.setDate(festivalDate.getDate() + 5);

  // start of day for comparison
  const nowTime = now.setHours(0, 0, 0, 0);
  const startTime = start.setHours(0, 0, 0, 0);
  const endTime = end.setHours(0, 0, 0, 0);

  return nowTime >= startTime && nowTime <= endTime;
}

function isExactSpringFestivalDay() {
  const now = new Date();
  const year = now.getFullYear();
  const dateStr = springFestivalDates[year];

  if (!dateStr) return false;

  const [month, day] = dateStr.split('-').map(Number);
  const festivalDate = new Date(year, month - 1, day);

  const nowTime = new Date(now).setHours(0, 0, 0, 0);
  const festivalTime = festivalDate.setHours(0, 0, 0, 0);

  return nowTime === festivalTime;
}

const greetingEmoji = computed(() => {
  if (isExactSpringFestivalDay()) {
    return '🧨';
  }
  const hour = new Date().getHours();
  if (hour >= 0 && hour < 5) {
    return '😴';
  }
  return '😊';
});

const greetingText = computed(() => {
  if (isSpringFestival()) {
    return tm('greeting.newYear');
  }
  const hour = new Date().getHours();
  if (hour < 12) return tm('greeting.morning');
  if (hour < 18) return tm('greeting.afternoon');
  return tm('greeting.evening');
});

async function loadPlatformConfigBase() {
  const res = await axios.get('/api/config/get');
  platformMetadata.value = res.data.data.metadata || {};
  platformConfigData.value = res.data.data.config || {};
}

function getChatProvidersFromTemplatePayload(payload: any) {
  const providers = payload?.providers || [];
  const sources = payload?.provider_sources || [];
  const sourceMap = new Map();
  sources.forEach((s: any) => sourceMap.set(s.id, s.provider_type));

  return providers.filter((provider: any) => {
    if (provider.provider_type) {
      return provider.provider_type === 'chat_completion';
    }
    if (provider.provider_source_id) {
      const type = sourceMap.get(provider.provider_source_id);
      if (type === 'chat_completion') return true;
    }
    return String(provider.type || '').includes('chat_completion');
  });
}

async function fetchChatProviders() {
  const response = await axios.get('/api/config/provider/template');
  if (response.data.status !== 'ok') {
    throw new Error(response.data.message || tm('onboard.providerLoadFailed'));
  }
  return getChatProvidersFromTemplatePayload(response.data.data);
}

function pickDefaultProviderId(providers: any[]) {
  if (!providers.length) return '';
  const enabledProvider = providers.find((provider) => provider.enable !== false);
  return (enabledProvider || providers[0]).id || '';
}

async function syncDefaultConfigProviderIfNeeded() {
  const providers = await fetchChatProviders();
  if (!providers.length) return;

  const targetProviderId = pickDefaultProviderId(providers);
  if (!targetProviderId) return;

  const configRes = await axios.get('/api/config/abconf', { params: { id: 'default' } });
  const configData = configRes.data?.data?.config || {};
  if (!configData.provider_settings) {
    configData.provider_settings = {};
  }

  if (configData.provider_settings.default_provider_id === targetProviderId) return;

  configData.provider_settings.default_provider_id = targetProviderId;

  const updateRes = await axios.post('/api/config/persbot/update', {
    conf_id: 'default',
    config: configData
  });
  if (updateRes.data.status !== 'ok') {
    throw new Error(updateRes.data.message || tm('onboard.providerUpdateFailed'));
  }

  showSuccess(tm('onboard.providerDefaultUpdated', { id: targetProviderId }));
}

async function loadWelcomeAnnouncement() {
  try {
    const res = await axios.get('https://cloud.persbot.app/api/v1/announcement');
    welcomeAnnouncementRaw.value = res?.data?.data?.notice?.welcome_page ?? null;
  } catch (e) {
    welcomeAnnouncementRaw.value = null;
    console.error(e);
  }
}

onMounted(async () => {
  await loadWelcomeAnnouncement();

  try {
    await loadPlatformConfigBase();
    if ((platformConfigData.value.platform || []).length > 0) {
      platformStepState.value = 'completed';
    }
  } catch (e) {
    console.error(e);
  }

  try {
    const providers = await fetchChatProviders();
    if (providers.length > 0) {
      providerStepState.value = 'completed';
    }
  } catch (e) {
    console.error(e);
  }
});

async function openPlatformDialog() {
  loadingPlatformDialog.value = true;
  try {
    await loadPlatformConfigBase();
    platformCountBeforeOpen.value = (platformConfigData.value.platform || []).length;
    showAddPlatformDialog.value = true;
  } catch (err: any) {
    showError(err?.response?.data?.message || err?.message || tm('onboard.platformLoadFailed'));
  } finally {
    loadingPlatformDialog.value = false;
  }
}

async function openProviderDialog() {
  try {
    const providers = await fetchChatProviders();
    providerCountBeforeOpen.value = providers.length;
    showProviderDialog.value = true;
  } catch (err: any) {
    showError(err?.response?.data?.message || err?.message || tm('onboard.providerLoadFailed'));
  }
}

watch(showAddPlatformDialog, async (visible, wasVisible) => {
  if (!wasVisible || visible) return;
  try {
    await loadPlatformConfigBase();
    const newCount = (platformConfigData.value.platform || []).length;
    if (newCount > platformCountBeforeOpen.value) {
      platformStepState.value = 'completed';
    }
  } catch (err: any) {
    showError(err?.response?.data?.message || err?.message || tm('onboard.platformLoadFailed'));
  }
});

watch(showProviderDialog, async (visible, wasVisible) => {
  if (!wasVisible || visible) return;
  try {
    const providers = await fetchChatProviders();
    if (providers.length > providerCountBeforeOpen.value) {
      providerStepState.value = 'completed';
      await syncDefaultConfigProviderIfNeeded();
    }
  } catch (err: any) {
    showError(err?.response?.data?.message || err?.message || tm('onboard.providerUpdateFailed'));
  }
});
</script>

<style scoped>
.welcome-page {
  height: 100%;
}

.welcome-hero-row {
  position: relative;
}

.welcome-eyebrow {
  display: inline-flex;
  align-items: center;
  margin-bottom: 16px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.welcome-card {
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.16) 0%, rgba(255, 255, 255, 0.04) 100%);
}

.welcome-card--onboard {
  position: relative;
  overflow: hidden;
}

.welcome-card--onboard::after {
  content: '';
  position: absolute;
  inset: auto -30px -60px auto;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--v-theme-secondary), 0.16) 0%, transparent 68%);
  pointer-events: none;
}

.welcome-announcement-markdown {
  line-height: 1.7;
}

.resource-link-card {
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.resource-link-card:hover {
  transform: translateY(-4px);
  border-color: rgba(var(--v-theme-primary), 0.16) !important;
  box-shadow: var(--persbot-shadow-soft);
}
</style>
