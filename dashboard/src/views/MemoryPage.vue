<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import axios from "axios";
import { memoryKinds, memoryTitle } from "@/components/memory/graphLayout.mjs";
import { graphScene } from "@/components/memory/graphScene.mjs";
import MemoryGraph from "@/components/memory/MemoryGraph.vue";
import ActivationComparison from "@/components/memory/ActivationComparison.vue";
import AnswerComparison from "@/components/memory/AnswerComparison.vue";
import { useRouter } from "vue-router";

const router = useRouter();

const emptyGraph = () => ({
  nodes: [],
  edges: [],
  traces: [],
  revision: 0,
  encoder: "local-lexical-v1",
});
const scopes = ref([]),
  scope = ref(""),
  graph = ref(emptyGraph());
const settings = ref({
    enabled: true,
    encoder: "local-lexical-v1",
    encoders: [],
  }),
  draft = ref({});
const comparison = ref(null),
  selected = ref(""),
  selectedSources = ref([]);
const caseGraph = computed(() => comparison.value?.presentation?.graph);
const displayGraph = computed(() => graphScene(graph.value, caseGraph.value));
const answerStage = ref(null);
const query = ref(""),
  topK = ref(4),
  busy = ref(false),
  error = ref(""),
  notice = ref("");
const showSettings = ref(false),
  activeTraceId = ref("");
const showManager = ref(false),
  showTrace = ref(false);
const kindFilter = ref(""),
  replay = ref(0),
  presenting = ref(false);
const graphRenderer = ref(null),
  graphStage = ref(null);
const showcase = ref(true),
  activationMode = ref("helamem");
const selectedEvidence = computed(
  () =>
    currentRecall.value?.results.find((item) => item.id === selected.value) ||
    comparison.value?.base.results.find((item) => item.id === selected.value),
);
const noticeVisible = computed({
  get: () => Boolean(notice.value),
  set: (value) => {
    if (!value) notice.value = "";
  },
});
const related = computed(() =>
  detail.value
    ? displayGraph.value.edges
        .filter(
          (e) => e.source === detail.value.id || e.target === detail.value.id,
        )
        .map((e) =>
          displayGraph.value.nodes.find(
            (n) =>
              n.id === (e.source === detail.value.id ? e.target : e.source),
          ),
        )
        .filter((node) => node && !detail.value.source_ids.includes(node.id))
    : [],
);
const currentRecall = computed(() => comparison.value?.[activationMode.value]);
const linkedCount = computed(
  () => new Set(graph.value.edges.flatMap((e) => [e.source, e.target])).size,
);
const conversationCount = computed(
  () =>
    new Set(graph.value.nodes.map((n) => n.origin?.session_id).filter(Boolean))
      .size,
);
function openChat(sessionId = "") {
  presenting.value = false;
  router.push(sessionId ? `/chat/${sessionId}` : "/chat");
}
function selectNode(id) {
  selected.value = id;
}
function inspectRecall(id) {
  selectNode(id);
  graphStage.value?.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
    block: "center",
  });
}
function sourceLabel(node) {
  return (
    {
      conversation: "会话记录",
      conversation_history: "已保存的会话",
      llm: "模型归纳",
      extractive: "原文合并",
      manual: "手动记录",
      paper_case: "论文案例记忆",
      showcase_background: "演示补充背景",
    }[node.origin?.method] || "来源未标注"
  );
}
function onEscape() {
  if (selected.value) selected.value = "";
  else presenting.value = false;
}
let timer;
let disposed = false;
watch(
  [query, topK],
  () => {
    comparison.value = null;
  },
  { flush: "sync" },
);
const detail = computed(() =>
  displayGraph.value.nodes.find((n) => n.id === selected.value),
);
watch(showcase, () => {
  if (!showcase.value && comparison.value?.presentation?.graph)
    comparison.value = null;
});
const traces = computed(() => [...graph.value.traces].reverse());
const activeTrace = computed(
  () =>
    traces.value.find((t) => t.id === activeTraceId.value) || traces.value[0],
);
const highlights = computed(() => currentRecall.value?.results || []);
const encoderLabel = computed(() =>
  graph.value.encoder === "local-lexical-v1"
    ? "离线词面编码"
    : graph.value.encoder,
);
const semanticEncoder = computed(
  () => graph.value.encoder !== "local-lexical-v1",
);
const showcaseEncoder = computed(() =>
  graph.value.encoder.startsWith("chat-embedding:")
    ? "text-embedding-3-small"
    : encoderLabel.value,
);
function setActivationMode(mode) {
  activationMode.value = mode;
  selected.value = "";
  kindFilter.value = "";
  replay.value++;
}
const date = (seconds) => new Date(seconds * 1000).toLocaleString();
async function api(path, data) {
  const response =
    data === undefined
      ? await axios.get(`/api/memory/${path}`)
      : await axios.post(`/api/memory/${path}`, data);
  if (response.data.status !== "ok")
    throw new Error(response.data.message || "记忆操作失败");
  return response.data.data;
}
async function action(fn) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await fn();
  } catch (e) {
    error.value = e.response?.data?.message || e.message;
  } finally {
    busy.value = false;
  }
}
async function refresh() {
  scopes.value = await api("scopes");
  if (!scopes.value.some((item) => item.scope === scope.value)) {
    scope.value = scopes.value[0]?.scope || "";
  }
  const requested = scope.value;
  const next = requested
    ? await api(`graph?scope=${encodeURIComponent(requested)}`)
    : emptyGraph();
  if (requested !== scope.value) return;
  if (
    comparison.value &&
    !comparison.value.presentation?.snapshot &&
    !comparison.value.presentation?.graph &&
    comparison.value.helamem.revision !== next.revision
  )
    comparison.value = null;
  graph.value = next;
  if (!next.traces.some((t) => t.id === activeTraceId.value))
    activeTraceId.value = next.traces.at(-1)?.id || "";
  if (!displayGraph.value.nodes.some((n) => n.id === selected.value))
    selected.value = "";
  selectedSources.value = selectedSources.value.filter((id) =>
    next.nodes.some((n) => n.id === id),
  );
}
async function compare() {
  await action(async () => {
    comparison.value = null;
    comparison.value = await api("answer-fixed", {
      scope: scope.value,
      query: query.value,
      top_k: topK.value,
    });
    selected.value = "";
    activationMode.value = "helamem";
    kindFilter.value = "";
    replay.value++;
    if (comparison.value.answer_comparison) {
      await nextTick();
      answerStage.value?.scrollIntoView({
        block: "start",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
    }
  });
}
async function consolidate() {
  await action(async () => {
    const result = await api("consolidate", {
      scope: scope.value,
      source_ids: selectedSources.value,
    });
    await refresh();
    selected.value = result.id;
    selectedSources.value = [];
    notice.value =
      result.method === "llm"
        ? "已由当前模型归纳为知识，并保留全部来源链接。"
        : "未配置聊天模型：已合并原文并保留来源，未执行模型归纳。";
  });
}
function openSettings() {
  draft.value = { ...settings.value };
  showSettings.value = true;
}
async function saveSettings() {
  await action(async () => {
    settings.value = await api("settings", {
      enabled: draft.value.enabled,
      encoder: draft.value.encoder,
    });
    showSettings.value = false;
  });
}
onMounted(async () => {
  await action(async () => {
    settings.value = await api("settings");
    await refresh();
  });
  window.addEventListener("keydown", handleEscape);
  if (disposed) {
    window.removeEventListener("keydown", handleEscape);
    return;
  }
  timer = setInterval(() => {
    if (!busy.value)
      refresh().catch((e) => {
        error.value = e.response?.data?.message || e.message;
      });
  }, 3000);
});
function handleEscape(e) {
  if (
    e.key === "Escape" &&
    !showManager.value &&
    !showSettings.value &&
    !showTrace.value
  )
    onEscape();
}
onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleEscape);
  disposed = true;
  clearInterval(timer);
});
</script>

<template>
  <div class="memory-atlas" :class="{ presenting, 'showcase-mode': showcase }">
    <header class="atlas-header">
      <div class="atlas-brand">
        <div class="brand-mark">
          <v-icon size="22">mdi-graph-outline</v-icon>
        </div>
        <div>
          <div class="brand-eyebrow">PERSBOT / MEMORY ATLAS</div>
          <h1>记忆图谱 <span>HeLa-Mem</span></h1>
        </div>
      </div>
      <div class="header-controls">
        <span class="scope-picker"
          ><v-icon size="15">mdi-account-circle-outline</v-icon>我的记忆</span
        >
        <button class="quiet-button" @click="openChat()">继续聊天 ↗</button>
        <button
          class="icon-button"
          :aria-label="presenting ? '退出演示模式' : '进入演示模式'"
          :title="presenting ? '退出演示模式' : '演示模式'"
          @click="presenting = !presenting"
        >
          <v-icon size="19">{{
            presenting ? "mdi-fullscreen-exit" : "mdi-fullscreen"
          }}</v-icon>
        </button>
        <button
          class="icon-button"
          aria-label="记忆设置"
          title="记忆设置"
          @click="openSettings"
        >
          <v-icon size="18">mdi-cog-outline</v-icon>
        </button>
      </div>
    </header>
    <div v-if="error" class="atlas-error" role="alert">
      <v-icon size="17">mdi-alert-circle-outline</v-icon>{{ error
      }}<button aria-label="关闭错误提示" @click="error = ''">×</button>
    </div>
    <div class="conversation-strip">
      <span class="live-dot" :class="{ paused: !settings.enabled }" />
      <span>{{ settings.enabled ? "在聊天中记住你" : "自动记忆已暂停" }}</span>
      <span>{{ conversationCount }} 段对话，连成持续的记忆</span>
    </div>
    <div class="memory-view-tabs" aria-label="记忆展示视图">
      <button
        :class="{ active: !showcase }"
        :aria-pressed="!showcase"
        @click="showcase = false"
      >
        记忆全景
      </button>
      <button
        :class="{ active: showcase }"
        :aria-pressed="showcase"
        @click="showcase = true"
      >
        HeLa 激活对照
      </button>
    </div>
    <section
      v-if="showcase"
      class="showcase-intro"
      aria-label="记忆检索与回答对照"
    >
      <span class="showcase-eyebrow">PERSBOT MEMORY / LIVE RECALL</span>
      <h2>相似之外，还能想起什么？</h2>
      <p>输入一个问题，查看两侧各 Top-{{ topK }} 的记忆检索与回答。</p>
      <form class="showcase-query" @submit.prevent="compare()">
        <input
          v-model="query"
          aria-label="对照召回问题"
          placeholder="问一个需要串起不同经历的问题…"
          :disabled="busy"
        />
        <label
          >每侧 K
          <select
            v-model.number="topK"
            aria-label="每侧最终召回条数"
            :disabled="busy"
          >
            <option v-for="k in [2, 3, 4, 5]" :key="k" :value="k">
              {{ k }}
            </option>
          </select></label
        >
        <button
          :disabled="busy || !query.trim() || !graph.nodes.length"
          type="submit"
        >
          <template v-if="busy"
            ><span class="loader" />正在检索并生成…</template
          >
          <template v-else>提问并对照 ↗</template>
        </button>
      </form>
      <p class="showcase-model" :class="{ warning: !semanticEncoder }">
        <template v-if="comparison?.presentation?.graph"
          >论文案例 · 预设检索分数 ·
          {{ graph.baseline ? "已接入 Chat" : "演示副本" }}</template
        ><template v-else
          >{{
            semanticEncoder
              ? "语义向量"
              : "离线词面向量（不代表语义 embedding）"
          }}
          · {{ showcaseEncoder }}
          <span>同一记忆库 · 只读对照，不改写聊天记忆或关联</span></template
        >
      </p>
      <p
        v-if="comparison?.presentation?.mode === 'preset'"
        class="preset-banner"
        role="status"
      >
        <strong>预设演示</strong>
        {{
          comparison.presentation.note ||
          "记忆原文与向量相似度不变；两条关联权重手动设为 1.000，仅用于本次演示，不写入聊天记忆。"
        }}
      </p>
    </section>
    <div
      v-if="showcase && comparison?.answer_comparison"
      ref="answerStage"
      class="answer-stage"
    >
      <AnswerComparison
        :comparison="comparison"
        :busy="busy"
        @generate="compare"
        @select="inspectRecall"
      />
    </div>
    <section class="atlas-board" aria-label="记忆关系网络">
      <div v-if="showcase && comparison" class="activation-switch">
        <div role="group" aria-label="图谱激活开关">
          <button
            :class="{ active: activationMode === 'base' }"
            :aria-pressed="activationMode === 'base'"
            @click="setActivationMode('base')"
          >
            纯向量 Top-{{ comparison.base.top_k }}
            <span>{{ comparison.base.results.length }} 条</span>
          </button>
          <button
            :class="{ active: activationMode === 'helamem' }"
            :aria-pressed="activationMode === 'helamem'"
            @click="setActivationMode('helamem')"
          >
            HeLa Top-{{ comparison.helamem.top_k }}
            <span>{{ comparison.helamem.results.length }} 条</span>
          </button>
        </div>
        <button class="activation-replay" @click="setActivationMode('helamem')">
          重播激活过程 ↻
        </button>
      </div>
      <div class="graph-toolbar">
        <div class="canvas-caption">
          <span
            class="live-dot"
            :class="{ paused: !settings.enabled }"
          /><span>{{
            caseGraph ? "我的记忆网络 · 案例叠加" : "我的记忆网络"
          }}</span
          ><small
            >{{ displayGraph.nodes.length }} 个节点 ·
            {{ displayGraph.edges.length }} 条关联</small
          >
        </div>
        <div class="kind-filters" aria-label="按记忆类型聚焦">
          <button
            v-for="(kind, key) in memoryKinds"
            :key="key"
            :class="{
              active: kindFilter === key,
              muted: kindFilter && kindFilter !== key,
            }"
            :aria-pressed="kindFilter === key"
            @click="kindFilter = kindFilter === key ? '' : key"
          >
            <i :style="{ background: kind.color }" />{{ kind.label }}
          </button>
        </div>
      </div>
      <div v-if="caseGraph" class="graph-context">
        <span v-if="graph.baseline"
          >{{ graph.nodes.length }} 条已保存记忆 · 案例记忆已接入 Chat</span
        >
        <span v-else
          >{{ graph.nodes.length }} 条已保存记忆 +
          {{ caseGraph.nodes.length }} 个案例节点</span
        >
        <span>背景保留全景 · 高亮为本轮 Top-{{ currentRecall.top_k }}</span>
      </div>
      <div ref="graphStage" class="graph-stage">
        <MemoryGraph
          ref="graphRenderer"
          :nodes="displayGraph.nodes"
          :edges="displayGraph.edges"
          :results="highlights"
          :seeds="
            activationMode === 'helamem' ? comparison?.base.results || [] : []
          "
          :selected="selected"
          :kind-filter="kindFilter"
          :replay="replay"
          @select="selectNode"
          @clear="selected = ''"
        />
        <Transition name="inspector">
          <aside
            v-if="detail || (comparison && !showcase)"
            class="memory-inspector"
            aria-label="记忆详情"
          >
            <div class="inspector-top">
              <span>{{ detail ? "记忆切片" : "一次回忆的路径" }}</span
              ><button
                class="icon-button"
                aria-label="关闭记忆详情"
                @click="detail ? (selected = '') : (comparison = null)"
              >
                <v-icon size="17">mdi-close</v-icon>
              </button>
            </div>
            <template v-if="detail">
              <div
                class="detail-kind"
                :style="{ color: memoryKinds[detail.kind]?.color }"
              >
                <i :style="{ background: memoryKinds[detail.kind]?.color }" />{{
                  memoryKinds[detail.kind]?.label
                }}<span>{{ sourceLabel(detail) }}</span>
              </div>
              <h2>{{ memoryTitle(detail) }}</h2>
              <div
                v-if="showcase && selectedEvidence"
                class="selected-evidence"
              >
                <span>{{
                  {
                    shared: "共同命中",
                    hela_only: "HeLa 关联换入",
                    vector_only: "纯向量独有 · 被换出",
                  }[selectedEvidence.membership]
                }}</span>
                <p>
                  Embedding 相似度 {{ selectedEvidence.cosine.toFixed(3) }} ·
                  向量排名 #{{ selectedEvidence.embedding_rank }}
                </p>
                <p v-if="selectedEvidence.association_score > 0">
                  向量基础 {{ selectedEvidence.base_score.toFixed(3) }} + 关联
                  {{ selectedEvidence.association_score.toFixed(3) }} ≈
                  {{ selectedEvidence.score.toFixed(3) }}
                </p>
              </div>
              <template v-if="detail.origin.user_text">
                <div class="provenance-note">
                  {{ detail.origin.conversation_title || "聊天记录" }} · 第
                  {{ detail.origin.turn_index || "—" }} 轮
                </div>
                <h3 class="source-role">你说</h3>
                <p class="detail-content">{{ detail.origin.user_text }}</p>
                <h3 class="source-role">Persbot 回应</h3>
                <p class="detail-content">{{ detail.origin.assistant_text }}</p>
              </template>
              <template v-else>
                <p class="detail-content">{{ detail.content }}</p>
                <p
                  v-if="detail.origin.conversation_title"
                  class="provenance-note"
                >
                  来自 {{ detail.origin.conversation_title }}
                </p>
              </template>
              <div class="detail-meta">
                <span
                  ><v-icon size="13">mdi-clock-outline</v-icon
                  >{{
                    detail.created_at ? date(detail.created_at) : "案例记忆"
                  }}</span
                ><span>已召回 {{ detail.access_count }} 次</span>
              </div>
              <button
                v-if="detail.origin.session_id"
                class="source-chat-button"
                @click="openChat(detail.origin.session_id)"
              >
                查看原对话 <span>↗</span>
              </button>
              <div v-if="detail.source_ids.length" class="detail-section">
                <h3>从这些经历中沉淀</h3>
                <button
                  v-for="id in detail.source_ids"
                  :key="id"
                  class="source-link"
                  @click="selectNode(id)"
                >
                  <v-icon size="14">mdi-source-branch</v-icon
                  >{{
                    memoryTitle(
                      displayGraph.nodes.find((n) => n.id === id) || {
                        content: id,
                      },
                    )
                  }}<span>↗</span>
                </button>
              </div>
              <div v-if="related.length" class="detail-section">
                <h3>{{ related.length }} 条相连的记忆</h3>
                <button
                  v-for="node in related.slice(0, 5)"
                  :key="node.id"
                  class="source-link"
                  @click="selectNode(node.id)"
                >
                  <i :style="{ background: memoryKinds[node.kind]?.color }" />{{
                    memoryTitle(node)
                  }}<span>↗</span>
                </button>
              </div>
              <button
                v-if="comparison"
                class="back-to-recall"
                @click="selected = ''"
              >
                ← 返回本次召回
              </button>
            </template>
            <template v-else>
              <div class="recall-count">
                <strong>{{ currentRecall?.results.length || 0 }}</strong
                ><span>段记忆被唤起</span>
              </div>
              <p class="recall-question">{{ comparison.helamem.query }}</p>
              <div class="recall-actions">
                <button class="quiet-button" @click="replay++">
                  <v-icon size="14">mdi-replay</v-icon>查看关联路径
                </button>
              </div>
              <div class="recall-list">
                <button
                  v-for="(item, index) in currentRecall?.results"
                  :key="item.id"
                  :class="{ associative: item.source === 'hebbian' }"
                  @click="selectNode(item.id)"
                >
                  <span class="step-number">0{{ index + 1 }}</span>
                  <div>
                    <small>{{
                      item.source === "hebbian"
                        ? "顺着关联，找到另一条线索"
                        : "从问题，找到相关经历"
                    }}</small
                    ><strong>{{
                      memoryTitle(
                        graph.nodes.find((n) => n.id === item.id) || item,
                      )
                    }}</strong>
                  </div>
                  <span>↗</span>
                </button>
              </div>
              <p v-if="!currentRecall?.results.length" class="subtle">
                暂时没有相关记忆，试试换一个问题。
              </p>
              <p class="comparison-note">
                从一段经历，想起与你相关的另一件事。
              </p>
            </template>
          </aside>
        </Transition>
      </div>
      <div v-if="!showcase" class="ask-dock">
        <form @submit.prevent="compare()">
          <span class="ask-spark">✦</span
          ><input
            v-model="query"
            aria-label="想起一件事"
            placeholder="想起一件事，看看记忆如何连接…"
            :disabled="busy"
          /><button
            class="ask-submit"
            type="submit"
            :disabled="busy || !query.trim() || !scope"
          >
            <span v-if="busy" class="loader" /><template v-else
              >唤起记忆 <span>↗</span></template
            >
          </button>
        </form>
      </div>
    </section>
    <ActivationComparison
      v-if="showcase && comparison"
      :comparison="comparison"
      :active-mode="activationMode"
      @select="inspectRecall"
      @mode="setActivationMode"
    />
    <p v-else-if="showcase" class="showcase-empty">
      输入问题后，对照结果会列出每条记忆的相似度、向量排名与关联激活来源。
    </p>
    <footer class="atlas-footer">
      <div>
        <span class="footer-spark">✦</span><span>来自聊天 · 本地保存</span
        ><span class="footer-divider">/</span
        ><span>{{ linkedCount }} 条记忆已有连接</span>
      </div>
      <div>
        <button @click="showTrace = true">
          <v-icon size="14">mdi-history</v-icon>回忆记录</button
        ><button @click="showManager = true">
          <v-icon size="14">mdi-tune-variant</v-icon>管理记忆
        </button>
      </div>
    </footer>
    <v-snackbar
      v-model="noticeVisible"
      :timeout="3800"
      color="#244539"
      location="bottom"
      >{{ notice
      }}<template #actions
        ><v-btn variant="text" @click="notice = ''">关闭</v-btn></template
      ></v-snackbar
    >

    <v-dialog v-model="showManager" max-width="760" theme="PersbotDarkTheme"
      ><v-card class="atlas-dialog" title="整理你的记忆"
        ><v-card-text
          ><p class="dialog-intro">
            选中 2–8 条经历，将它们归纳为保留来源的长期知识。
          </p>
          <div class="manager-list">
            <div v-for="node in graph.nodes" :key="node.id" class="manager-row">
              <v-checkbox
                v-model="selectedSources"
                :value="node.id"
                :aria-label="'选中 ' + memoryTitle(node)"
                :disabled="busy || node.kind !== 'episodic'"
                hide-details
                density="compact"
              /><button
                @click="
                  selectNode(node.id);
                  showManager = false;
                "
              >
                <small :style="{ color: memoryKinds[node.kind]?.color }"
                  >{{ memoryKinds[node.kind]?.label }} ·
                  {{ sourceLabel(node) }}</small
                ><strong>{{ memoryTitle(node) }}</strong>
              </button>
            </div>
          </div>
          <v-btn
            class="my-4"
            color="#79ccb4"
            :disabled="
              busy || selectedSources.length < 2 || selectedSources.length > 8
            "
            @click="
              consolidate();
              showManager = false;
            "
            >归纳选中记忆（{{ selectedSources.length }}）</v-btn
          ></v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="showManager = false"
            >完成</v-btn
          ></v-card-actions
        ></v-card
      ></v-dialog
    >
    <v-dialog v-model="showTrace" max-width="730" theme="PersbotDarkTheme"
      ><v-card class="atlas-dialog" title="回忆记录"
        ><v-card-text
          ><template v-if="activeTrace"
            ><v-select
              v-model="activeTraceId"
              :items="traces"
              item-title="query"
              item-value="id"
              label="最近的对话"
              variant="outlined"
            />
            <h3 class="trace-caption">当时唤起的记忆</h3>
            <p class="trace-caption">
              {{ activeTrace.results.length }} 条 ·
              {{
                activeTrace.strategy === "paper_preset"
                  ? "当前基础案例 · 预设 Top-4"
                  : "实际检索"
              }}
            </p>
            <button
              v-for="item in activeTrace.results"
              :key="item.id"
              class="trace-source"
              @click="
                selectNode(item.id);
                showTrace = false;
              "
            >
              <small
                >{{
                  item.source === "hebbian" ? "HeLa 关联唤起" : "基础命中"
                }}
                · {{ item.id }}</small
              ><br />
              {{ item.content }}
            </button>
            <h3 class="trace-caption">模型的真实回答</h3>
            <p class="trace-answer">{{ activeTrace.answer }}</p>
            <div v-if="activeTrace.edge_updates.length" class="trace-learning">
              {{ activeTrace.edge_updates.length }}
              对共同召回的记忆，在这次回答后强化了关联。
            </div></template
          >
          <p v-else class="dialog-intro">
            真实对话完成后，这里会留下召回依据和模型回答。单独检索不会生成交互记录。
          </p></v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="showTrace = false"
            >关闭</v-btn
          ></v-card-actions
        ></v-card
      ></v-dialog
    >
    <v-dialog v-model="showSettings" max-width="520" theme="PersbotDarkTheme"
      ><v-card class="atlas-dialog" title="记忆设置"
        ><v-card-text
          ><v-switch
            v-model="draft.enabled"
            label="聊天自动读写长期记忆"
            color="#79ccb4"
          /><v-select
            v-model="draft.encoder"
            :items="settings.encoders"
            item-title="label"
            item-value="id"
            label="新记忆空间的编码器"
            variant="outlined"
          /><v-select
            v-model="topK"
            :items="[2, 3, 4, 5]"
            label="展示对照的每侧最终条数 Top-K"
            variant="outlined"
          />
          <p class="dialog-footnote">
            已有记忆空间保留原编码器。当前空间：{{
              encoderLabel
            }}。关闭自动记忆不会删除已有数据。
          </p></v-card-text
        ><v-card-actions
          ><v-spacer /><v-btn @click="showSettings = false">取消</v-btn
          ><v-btn :loading="busy" @click="saveSettings"
            >保存</v-btn
          ></v-card-actions
        ></v-card
      ></v-dialog
    >
  </div>
</template>

<style scoped>
.answer-stage {
  scroll-margin-top: 76px;
}
.memory-view-tabs {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: #15222b;
  border-radius: 9px;
  width: fit-content;
  margin: 0 0 28px;
}
.memory-view-tabs button {
  font-size: 11px;
  padding: 9px 17px;
  color: #91a7b5;
  border-radius: 6px;
}
.memory-view-tabs button.active {
  background: #28433d;
  color: #b4e5d4;
}
.showcase-intro {
  margin-bottom: 28px;
}
.showcase-eyebrow {
  font-size: 9px;
  letter-spacing: 1.8px;
  color: #89ada7;
}
.showcase-intro h2 {
  font-weight: 500;
  font-size: clamp(22px, 3vw, 32px);
  letter-spacing: 0.7px;
  margin: 10px 0 12px;
  color: #e8f1ed;
}
.showcase-intro > p {
  font-size: 11px;
  color: #a3b7c3;
  line-height: 1.9;
}
.showcase-query {
  display: flex;
  gap: 12px;
  background: #1a2c37;
  border: 1px solid #516c7060;
  border-radius: 11px;
  margin-top: 22px;
  padding: 8px;
  align-items: center;
}
.showcase-query input {
  min-width: 0;
  flex: 1;
  font-size: 12px;
  color: #e2eded;
  padding: 12px 8px;
  outline: none;
}
.showcase-query label {
  font:
    10px ui-monospace,
    monospace;
  white-space: nowrap;
  color: #9fb4be;
}
.showcase-query select {
  color: #d3e9df;
  background: #213c36;
  border-radius: 4px;
  padding: 7px;
  margin-left: 5px;
}
.showcase-query button {
  background: #9bdbc5;
  border-radius: 7px;
  color: #163c31;
  padding: 12px 17px;
  font-size: 12px;
  white-space: nowrap;
}
.showcase-query button:disabled {
  opacity: 0.4;
}
.showcase-intro > .preset-banner {
  color: #d7b986;
  padding: 12px 16px;
  margin-top: 16px;
  border-left: 2px solid #e9be7e;
  background: #e9be7e08;
}
.preset-banner strong {
  margin-right: 10px;
  font-weight: 500;
}
.showcase-model {
  font-size: 9px !important;
  color: #8fa8a2 !important;
}
.showcase-model span {
  margin-left: 10px;
  color: #8a9dac;
}
.showcase-model.warning {
  color: #edc294 !important;
}
.activation-switch {
  display: flex;
  gap: 15px;
  justify-content: space-between;
  align-items: center;
  padding: 15px 18px;
  border-bottom: 1px solid #d0dcd611;
  flex-wrap: wrap;
}
.activation-switch > div {
  display: flex;
  background: #0c1720;
  border-radius: 7px;
  padding: 4px;
}
.activation-switch button {
  color: #94adb9;
  font-size: 11px;
  padding: 10px 14px;
  border-radius: 5px;
}
.activation-switch button.active {
  color: #c4e8dc;
  background: #28433a;
}
.activation-switch button.active:last-child {
  color: #eed4ac;
  background: #59472877;
}
.activation-switch button span {
  margin-left: 10px;
  font:
    10px ui-monospace,
    monospace;
}
.activation-switch .activation-replay {
  padding: 6px;
  color: #b9d6ca;
}
.selected-evidence {
  padding: 12px;
  margin: 14px 0;
  border: 1px solid #c99f6350;
  border-radius: 7px;
  background: #f0bc7808;
}
.selected-evidence > span {
  color: #edc995;
  font-size: 10px;
}
.selected-evidence p {
  margin-top: 8px;
  color: #abc0c9;
  font:
    10px/1.8 ui-monospace,
    monospace;
}
.showcase-empty {
  padding: 18px 0;
  font-size: 11px;
  color: #95acbb;
  line-height: 1.8;
}
.showcase-mode .graph-stage {
  height: 560px;
  min-height: 560px;
}
.showcase-mode .graph-toolbar {
  position: relative;
  flex-wrap: wrap;
}
.graph-context {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  padding: 0 23px 12px;
  color: #8fa8b8;
  font-size: 10px;
  border-bottom: 1px solid #7999ac18;
}
.memory-view-tabs button:focus-visible,
.showcase-query:focus-within,
.activation-switch button:focus-visible {
  outline: 2px solid #8ed4bf;
  outline-offset: 3px;
}
@media (max-width: 600px) {
  .showcase-query {
    flex-wrap: wrap;
    gap: 6px;
  }
  .showcase-query input {
    flex-basis: 100%;
  }
  .showcase-query label {
    margin: 0 auto 0 8px;
  }
  .activation-switch {
    gap: 8px;
    padding: 10px;
  }
  .activation-switch button {
    padding: 9px;
    font-size: 10px;
  }
}
.source-chat-button {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin: 18px 0 4px;
  padding: 11px 14px;
  color: #a4dfcd;
  background: #7fd6bf10;
  border: 1px solid #7fd6bf30;
  border-radius: 9px;
  font-size: 12px;
}
.conversation-strip {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 10px;
  color: #94aebb;
  padding: 0 2px 14px;
  margin-bottom: 17px;
}
.memory-atlas {
  --atlas-ink: #e2edf4;
  --atlas-muted: #8ca3b5;
  --atlas-mint: #8edbc2;
  color: var(--atlas-ink);
  background: #0b1520;
  border: 1px solid #1d2c38;
  border-radius: 18px;
  padding: 24px 26px 14px;
  min-width: 0;
  font-family:
    "Outfit",
    -apple-system,
    BlinkMacSystemFont,
    "PingFang SC",
    sans-serif;
  box-shadow: 0 12px 40px #0b15201a;
}
.memory-atlas.presenting {
  position: fixed;
  inset: 0;
  z-index: 1800;
  border-radius: 0;
  padding: 28px 36px 14px;
  overflow-y: auto;
}
.atlas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  margin-bottom: 25px;
}
.atlas-brand {
  display: flex;
  gap: 13px;
  align-items: center;
  flex-shrink: 0;
}
.brand-mark {
  width: 43px;
  height: 43px;
  border: 1px solid #7fd6bf36;
  border-radius: 13px;
  color: #92d4c2;
  display: grid;
  place-items: center;
  background: #7fd6bf09;
}
.brand-eyebrow {
  color: #7a96a8;
  font-size: 9px;
  letter-spacing: 0.18em;
  font-weight: 500;
}
h1 {
  font-size: 23px;
  font-weight: 550;
  letter-spacing: -0.025em;
  margin: 3px 0 0;
  line-height: 1.4;
}
h1 span {
  font-size: 11px;
  letter-spacing: 0.02em;
  color: #94b7b1;
  font-weight: 400;
  margin-left: 9px;
}
.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.scope-picker {
  max-width: 225px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px;
  border: 1px solid #c0d5e31d;
  background: #ffffff03;
  border-radius: 7px;
  color: #a6bbca;
}
.scope-picker select {
  appearance: none;
  font-size: 11px;
  color: #b7cad7;
  outline: none;
  min-width: 0;
  max-width: 170px;
  cursor: pointer;
}
.scope-picker option {
  color: #d9e7ef;
  background: #172835;
}
button {
  color: inherit;
  cursor: pointer;
}
button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}
button:focus-visible,
select:focus-visible,
input:focus-visible {
  outline: 2px solid #8edbc2;
  outline-offset: 4px;
}
.icon-button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #8ea8b8;
  border-radius: 7px;
  flex-shrink: 0;
}
.icon-button:hover {
  background: #ffffff09;
  color: #d9f5ea;
}
.quiet-button {
  padding: 7px 10px;
  border: 1px solid #b2d1e021;
  color: #a7bccb;
  border-radius: 7px;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.quiet-button:hover {
  background: #ffffff09;
}
.accent-button {
  color: #142e29;
  background: #8edbc2;
  padding: 8px 12px;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 550;
}
.accent-button span {
  padding-left: 10px;
}
.atlas-board {
  position: relative;
  background: radial-gradient(ellipse at 35% 42%, #152c3540, transparent 65%),
    radial-gradient(circle, #a0bed00d 0.7px, transparent 1px), #0d1925;
  background-size:
    auto,
    24px 24px,
    auto;
  border: 1px solid #7999ac24;
  border-radius: 13px;
  overflow: hidden;
}
.graph-toolbar {
  position: absolute;
  z-index: 2;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 23px;
  background: linear-gradient(#0d1925, #0d1925dd 70%, transparent);
  pointer-events: none;
}
.canvas-caption {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 11px;
  color: #b9cedb;
}
.canvas-caption small {
  margin-left: 9px;
  color: #6f8a9d;
  font:
    10px ui-monospace,
    monospace;
}
.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #82cbb5;
  box-shadow: 0 0 10px #82cbb555;
}
.live-dot.paused {
  background: #8293a4;
}
.kind-filters {
  display: flex;
  gap: 14px;
  pointer-events: auto;
}
.kind-filters button {
  font-size: 10px;
  color: #9bb0c0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  transition: opacity 0.2s;
}
.kind-filters i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.kind-filters .active {
  color: #f0f9ff;
}
.kind-filters .muted {
  opacity: 0.35;
}
.graph-stage {
  position: relative;
  height: clamp(450px, calc(100dvh - 315px), 820px);
}
.presenting .graph-stage {
  height: calc(100dvh - 260px);
  min-height: 440px;
}
.graph-intro {
  position: absolute;
  top: 66px;
  left: 24px;
  z-index: 1;
  pointer-events: none;
}
.graph-intro > span {
  font-size: 8px;
  letter-spacing: 0.18em;
  color: #557283;
}
.graph-intro p {
  font-size: 12px;
  color: #9db5c3;
  margin-top: 6px;
}
.graph-intro em {
  font-style: normal;
  color: #68889a;
}
.ask-dock {
  border-top: 1px solid #ffffff0c;
  background: #0d1927f5;
  padding: 16px 24px 13px;
}
.ask-dock form {
  max-width: 720px;
  margin: auto;
  display: flex;
  gap: 12px;
  align-items: center;
  border: 1px solid #769eaa42;
  border-radius: 10px;
  padding: 6px 7px 6px 17px;
  background: #152431;
  box-shadow: 0 8px 30px #0002;
}
.ask-dock form:focus-within {
  border-color: #8edbc288;
  box-shadow: 0 0 0 3px #8edbc208;
}
.ask-spark {
  color: #b0dacb;
  font-size: 20px;
}
.ask-dock input {
  flex: 1;
  width: 0;
  color: #d7e5ed;
  font-size: 12px;
  outline: none;
  border: 0;
  height: 35px;
}
.ask-dock input::placeholder {
  color: #829aaa;
}
.ask-submit {
  min-width: 100px;
  min-height: 35px;
  padding: 7px 11px;
  background: #a3dcc8;
  color: #18362f;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.ask-submit span:last-child {
  margin-left: 8px;
}
.ask-suggestions {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 17px;
  margin-top: 10px;
  font-size: 9px;
  color: #728b9e;
}
.ask-suggestions > span {
  color: #506d80;
}
.ask-suggestions button {
  color: #8ca6b7;
}
.ask-suggestions button span {
  margin-left: 7px;
  opacity: 0.55;
}
.memory-inspector {
  position: absolute;
  top: 65px;
  right: 18px;
  width: 292px;
  max-height: calc(100% - 128px);
  overflow-y: auto;
  z-index: 4;
  background: #152633f5;
  backdrop-filter: blur(20px);
  border: 1px solid #91b4c334;
  border-radius: 12px;
  padding: 14px 18px 18px;
  box-shadow: 0 20px 70px #0006;
  scrollbar-width: thin;
  scrollbar-color: #385566 transparent;
}
.inspector-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 17px;
  color: #7d9aad;
  font-size: 10px;
  letter-spacing: 0.05em;
}
.inspector-top .icon-button {
  width: 22px;
  height: 22px;
}
.detail-kind {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
}
.detail-kind i,
.source-link i {
  height: 5px;
  width: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.detail-kind span {
  color: #7b94a6;
  margin-left: auto;
  font-size: 9px;
}
.memory-inspector h2 {
  font-size: 17px;
  font-weight: 500;
  line-height: 1.6;
  margin: 12px 0 8px;
  color: #e0eff5;
}
.detail-content {
  font-size: 12px;
  line-height: 1.95;
  color: #aac0ce;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: #6e8a9d;
  font-size: 9px;
  margin: 17px 0;
}
.detail-meta span {
  display: flex;
  align-items: center;
  gap: 5px;
}
.detail-section {
  border-top: 1px solid #ffffff10;
  margin-top: 16px;
  padding-top: 15px;
}
.detail-section h3 {
  color: #84a1b3;
  font-size: 10px;
  font-weight: 450;
  margin-bottom: 9px;
}
.source-link {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  font-size: 11px;
  text-align: left;
  color: #bfd1dc;
}
.source-link > span {
  margin-left: auto;
  color: #708d9d;
}
.source-link:hover {
  color: #9de3c9;
}
.back-to-recall {
  color: #8bd1bb;
  font-size: 10px;
  margin-top: 22px;
}
.recall-count {
  display: flex;
  gap: 10px;
  align-items: baseline;
}
.recall-count strong {
  font-size: 39px;
  color: #b3e6d4;
  font-weight: 300;
  line-height: 1;
}
.recall-count span {
  color: #aac1cf;
  font-size: 12px;
}
.recall-question {
  color: #7e9aab;
  font-size: 11px;
  line-height: 1.8;
  margin: 13px 0 18px;
}
.path-toggle {
  display: flex;
  padding: 3px;
  border: 1px solid #6f92a129;
  border-radius: 7px;
  background: #0b1922;
}
.path-toggle button {
  flex: 1;
  padding: 6px;
  font-size: 10px;
  color: #7694a6;
  border-radius: 4px;
}
.path-toggle .active {
  background: #244638;
  color: #a4e4ca;
}
.recall-list {
  margin: 18px 0;
}
.recall-list button {
  display: flex;
  text-align: left;
  gap: 10px;
  align-items: center;
  width: 100%;
  padding: 12px 0;
  border-bottom: 1px solid #ffffff0b;
}
.step-number {
  color: #70b8a5;
  font:
    12px ui-monospace,
    monospace;
}
.recall-list small {
  color: #709d92;
  font-size: 9px;
  display: block;
}
.recall-list strong {
  color: #bfd5df;
  font-size: 11px;
  font-weight: 450;
  display: block;
  margin-top: 5px;
}
.recall-list button > span:last-child {
  margin-left: auto;
  color: #6d8999;
}
.associative .step-number,
.associative small {
  color: #d5ad77;
}
.recall-actions {
  display: flex;
  margin-top: 14px;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}
.comparison-note,
.subtle {
  color: #6e8b9d;
  font-size: 9px;
  line-height: 1.8;
  margin-top: 12px;
}
.atlas-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
  color: #6f899c;
  font-size: 9px;
}
.atlas-footer > div {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.footer-spark {
  color: #648f85;
}
.footer-divider {
  color: #344f62;
}
.atlas-footer button {
  color: #99b1c2;
  display: flex;
  gap: 5px;
  align-items: center;
  font-size: 10px;
}
.atlas-footer button + button {
  margin-left: 10px;
}
.atlas-error {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  margin-bottom: 15px;
  color: #efb5ac;
  background: #a43b3222;
  font-size: 12px;
  border-radius: 8px;
}
.atlas-error button {
  margin-left: auto;
}
.atlas-dialog {
  background: #14232f !important;
  color: #d6e7f0 !important;
  border: 1px solid #ffffff1c;
  border-radius: 18px !important;
}
.dialog-intro {
  font-size: 13px;
  line-height: 1.9;
  color: #a4bcca;
  margin-bottom: 20px;
}
.comparison-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.dialog-footnote {
  font-size: 11px;
  line-height: 1.8;
  color: #87a1b4;
  margin-top: 18px;
}
.manager-list {
  max-height: 360px;
  overflow-y: auto;
}
.manager-row {
  display: flex;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid #ffffff10;
}
.manager-row :deep(.v-input) {
  flex: 0 0 40px;
}
.manager-row button {
  flex: 1;
  text-align: left;
  padding: 12px 0;
}
.manager-row small {
  display: block;
  font-size: 10px;
  margin-bottom: 4px;
}
.manager-row strong {
  color: #c8dbe6;
  font-size: 13px;
  font-weight: 450;
}
.trace-caption {
  font-size: 12px;
  font-weight: 500;
  color: #8dafc0;
  margin: 25px 0 10px;
}
.trace-source {
  display: block;
  text-align: left;
  width: 100%;
  color: #bdd1dd;
  padding: 13px;
  background: #ffffff05;
  border: 1px solid #ffffff0c;
  margin: 8px 0;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.9;
}
.trace-answer {
  white-space: pre-wrap;
  line-height: 1.9;
  font-size: 14px;
  color: #d9e8ee;
}
.trace-learning {
  padding: 15px;
  margin-top: 20px;
  border-radius: 8px;
  background: #87cdb510;
  color: #a1d8c5;
  font-size: 12px;
}
.model-wait {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 25px 0;
  color: #98caba;
  font-size: 13px;
}
.loader {
  width: 13px;
  height: 13px;
  display: inline-block;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  border-right-color: transparent;
  animation: spin 0.8s linear infinite;
}
.inspector-enter-active,
.inspector-leave-active {
  transition:
    opacity 0.25s,
    transform 0.25s;
}
.inspector-enter-from,
.inspector-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 1100px) {
  .atlas-header {
    align-items: flex-start;
  }
  .header-controls {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .scope-picker {
    max-width: 180px;
  }
  .canvas-caption small {
    display: none;
  }
}
@media (max-width: 720px) {
  .memory-atlas {
    padding: 19px 14px 13px;
    border-radius: 13px;
  }
  .atlas-header {
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 17px;
  }
  .header-controls {
    width: 100%;
    justify-content: flex-start;
    gap: 10px;
  }
  .scope-picker {
    margin-right: auto;
    max-width: 250px;
    flex: 1;
  }
  .scope-picker select {
    max-width: none;
    width: 100%;
  }
  .sample-button {
    display: inline-flex;
  }
  .brand-mark {
    width: 37px;
    height: 37px;
  }
  h1 {
    font-size: 21px;
  }
  .brand-eyebrow {
    font-size: 8px;
  }
  .graph-toolbar {
    padding: 17px 14px;
    gap: 9px;
  }
  .canvas-caption {
    font-size: 10px;
  }
  .kind-filters {
    gap: 9px;
  }
  .kind-filters button {
    font-size: 9px;
    gap: 4px;
  }
  .graph-stage {
    height: 520px;
  }
  .graph-intro {
    left: 17px;
    top: 57px;
  }
  .graph-intro p {
    font-size: 10px;
  }
  .graph-intro > span {
    font-size: 7px;
  }
  .memory-inspector {
    right: 12px;
    width: 270px;
    max-height: calc(100% - 126px);
  }
  .ask-dock {
    padding: 13px 13px 11px;
  }
  .ask-dock form {
    gap: 8px;
    padding-left: 11px;
  }
  .ask-dock input {
    font-size: 11px;
  }
  .ask-submit {
    min-width: 78px;
    padding: 7px;
    font-size: 10px;
  }
  .ask-suggestions {
    gap: 12px;
    font-size: 8px;
  }
  .atlas-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 13px;
    font-size: 8px;
  }
  .atlas-footer > div:last-child {
    align-self: flex-end;
  }
  .comparison-grid {
    grid-template-columns: 1fr;
  }
  .memory-atlas.presenting {
    padding: 16px;
  }
  .presenting .graph-stage {
    height: calc(100dvh - 300px);
    min-height: 420px;
  }
}
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
  }
}
</style>
