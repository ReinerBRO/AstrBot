<script setup>
import { computed } from "vue";
import { memoryTitle } from "./graphLayout.mjs";

const props = defineProps({
  comparison: { type: Object, required: true },
  activeMode: String,
});
defineEmits(["select", "mode"]);
const added = computed(() =>
  props.comparison.helamem.results.filter(
    (item) =>
      !props.comparison.base.results.some((base) => base.id === item.id),
  ),
);
const removed = computed(() =>
  props.comparison.base.results.filter(
    (item) => item.membership === "vector_only",
  ),
);
const sharedCount = computed(
  () => props.comparison.base.results.length - removed.value.length,
);
const isPreset = computed(
  () => props.comparison.presentation?.mode === "preset",
);
const membershipLabel = (item) =>
  ({
    shared: "共同命中",
    vector_only: "纯向量独有 · 被换出",
    hela_only: "HeLa 换入",
  })[item.membership];
const decimal = (value) => Number(value || 0).toFixed(3);
const excerpt = (item) =>
  item.origin?.user_text ||
  item.content.replace(/^User:\s*/, "").split("\nAssistant:")[0];
const reason = (path) =>
  ({
    temporal: "同一对话中的相邻经历",
    consolidation: "经历与归纳知识的来源关系",
    co_retrieval: "历史对话中共同被召回",
    paper_association: "同一个人串起职业建议与初次相遇",
  })[path.reason] || "已保存的关联";
function source(id) {
  return [
    ...props.comparison.base.results,
    ...props.comparison.helamem.results,
  ].find((item) => item.id === id);
}
</script>

<template>
  <section class="activation-comparison" aria-label="HeLa 激活前后对照">
    <p v-if="isPreset" class="preset-note">
      <strong>预设演示</strong> ·
      {{
        comparison.presentation.note || "手动关联权重，真实向量排序与记忆原文"
      }}
    </p>
    <div class="comparison-summary" aria-live="polite">
      <div>
        <span class="eyebrow">SAME K / DIFFERENT MEMORIES</span>
        <h2>同样 {{ comparison.base.effective_k }} 条，HeLa 换入了什么？</h2>
      </div>
      <div class="gain">
        <strong>{{ sharedCount }}</strong
        ><span>共同命中</span>
      </div>
      <div class="gain warm">
        <strong>{{ added.length }}</strong
        ><span>关联换入<br />同时换出 {{ removed.length }} 条</span>
      </div>
    </div>
    <div v-for="item in added" :key="`preview-${item.id}`" class="swap-preview">
      <span>关联换入</span>
      <button @click="$emit('select', item.id)">
        {{ memoryTitle(item) }} ↗
      </button>
      <strong
        >向量 #{{ item.embedding_rank }} → HeLa #{{
          item.activated_rank
        }}</strong
      >
      <small
        >相似度 {{ decimal(item.cosine) }} · 原纯向量 Top-{{
          comparison.base.top_k
        }}
        未入选</small
      >
    </div>
    <div class="result-columns">
      <article
        v-for="mode in ['base', 'helamem']"
        :key="mode"
        class="result-column"
        :class="{ enhanced: mode === 'helamem', active: activeMode === mode }"
      >
        <button
          class="column-heading"
          @click="$emit('mode', mode)"
          :aria-pressed="activeMode === mode"
        >
          <div>
            <span class="eyebrow">{{
              mode === "base"
                ? "01 / WITHOUT ACTIVATION"
                : "02 / WITH ACTIVATION"
            }}</span>
            <h3>
              {{ mode === "base" ? "纯向量" : "HeLa" }} Top-{{
                comparison[mode].top_k
              }}
            </h3>
          </div>
          <span class="result-count"
            >{{ comparison[mode].results.length }}<small>条</small></span
          >
        </button>
        <p class="column-note">
          {{
            mode === "base"
              ? "仅按余弦相似度排序，不加词面与时间分"
              : isPreset
              ? comparison.presentation.id === "paper-career"
                ? "论文案例预设：关联激活后保留 4 条"
                : "手动设定关联权重，实际重排后取同样条数"
              : "同一候选集加入图关联激活，重排后取同样条数"
          }}
        </p>
        <button
          v-for="item in comparison[mode].results"
          :key="item.id"
          class="result-card"
          :class="{
            extra: item.membership === 'hela_only',
            removed: item.membership === 'vector_only',
          }"
          @click="$emit('select', item.id)"
        >
          <div class="card-label">
            <span>{{ membershipLabel(item) }}</span
            ><span>入选 #{{ item.selected_rank }}</span>
          </div>
          <div class="rank-movement">
            向量 #{{ item.embedding_rank
            }}<template v-if="mode === 'helamem'">
              → HeLa #{{ item.activated_rank }}</template
            >
          </div>
          <h4>{{ memoryTitle(item) }} <span>↗</span></h4>
          <p>{{ excerpt(item) }}</p>
          <div class="score-line">
            <span>Embedding 余弦相似度</span
            ><strong>{{ decimal(item.cosine) }}</strong>
          </div>
          <div class="similarity-meter">
            <i
              :style="{
                width: Math.max(0, Math.min(100, item.cosine * 100)) + '%',
              }"
            />
          </div>
          <div v-if="mode === 'helamem'" class="boost-line">
            <span>向量基础 {{ decimal(item.base_score) }}</span
            ><span>关联 +{{ decimal(item.association_score) }}</span
            ><strong>≈ {{ decimal(item.score) }}</strong>
          </div>
          <div v-if="item.membership === 'hela_only'" class="delta-tags">
            <span class="distinctive"
              >未进入纯向量 Top-{{
                comparison.base.top_k
              }}，经关联激活换入</span
            >
          </div>
        </button>
        <p v-if="!comparison[mode].results.length" class="empty-result">
          当前还没有保存的记忆。
        </p>
        <footer>
          最终 {{ comparison[mode].results.length }} /
          {{ comparison[mode].top_k }} 条
          <span v-if="comparison[mode].effective_k < comparison[mode].top_k">
            · 记忆库不足 K 条，两侧均展示全部</span
          >
        </footer>
      </article>
    </div>
    <div class="bridge-heading">
      <span class="eyebrow">FOLLOW THE CONNECTION</span>
      <h3>不是只看相似度：沿着哪条线索找到它？</h3>
    </div>
    <p v-if="!added.length" class="empty-result">
      这个问题没有发生换入／换出。两组入选记忆相同，排序可能不同。
    </p>
    <article v-for="item in added" :key="item.id" class="bridge-card">
      <div class="bridge-title">
        <span>关联换入</span
        ><button @click="$emit('select', item.id)">
          {{ memoryTitle(item) }} ↗</button
        ><small
          >向量 #{{ item.embedding_rank }} → HeLa #{{ item.activated_rank }} ·
          相似度 {{ decimal(item.cosine) }}</small
        >
      </div>
      <div
        v-for="path in item.paths"
        :key="path.source + path.target"
        class="bridge-path"
      >
        <button @click="$emit('select', path.source)">
          <small>激活源</small
          >{{
            source(path.source)
              ? memoryTitle(source(path.source))
              : "直接命中的记忆"
          }}
        </button>
        <div class="path-connection">
          <span
            >权重 {{ decimal(path.weight) }} · 激活 +{{
              decimal(path.boost)
            }}</span
          ><i>→</i
          ><small
            >{{ reason(path)
            }}<template v-if="path.preset_path"> · 论文图示预设</template
            ><template v-else-if="path.preset_weight">
              · 手动权重（原 {{ decimal(path.stored_weight) }}）</template
            ><template v-else-if="path.reinforcements">
              · 共同召回强化 {{ path.reinforcements }} 次</template
            ></small
          >
        </div>
        <button @click="$emit('select', item.id)">
          <small>被关联唤起</small>{{ memoryTitle(item) }}
        </button>
      </div>
      <p class="bridge-evidence">{{ excerpt(item) }}</p>
    </article>
    <p class="method-note">
      <template v-if="comparison.presentation?.method_note">{{
        comparison.presentation.method_note
      }}</template
      ><template v-else>
        <template v-if="isPreset"
          >本次是手动编排的机制演示：只在副本中调整两条现有关联的权重，不代表自动学习得到的效果，也不修改原记忆库。</template
        >
        两侧使用同一问题、记忆快照和查询向量，最终都取 Top-{{
          comparison.base.top_k
        }}，不额外补条数。 左侧只按余弦相似度排序；右侧将相似度映射为向量基础分
        b = (1 + cosine) / 2， 再叠加从左侧 Top-K 出发的一跳激活：Σ
        {{ comparison.helamem.activation_scale }} × 源节点基础分 × 关联权重
        （源节点基础分 &gt;
        {{ comparison.helamem.activation_threshold }}），按总分重排全部候选。
        这里比较记忆选择，不代表回答准确率提高；点击记忆可核对原对话。
      </template>
    </p>
  </section>
</template>

<style scoped>
.activation-comparison {
  --mint: #91d8c3;
  --amber: #f0bc78;
  color: #d8e6ea;
  padding: 30px 2px 10px;
}
.preset-note {
  color: #d7b986;
  font-size: 11px;
  margin-bottom: 16px;
}
.preset-note strong {
  font-weight: 500;
}
.swap-preview {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 18px;
  border-left: 2px solid var(--amber);
  background: #f0bc7808;
  padding: 15px 18px;
  margin-bottom: 20px;
  color: var(--amber);
}
.swap-preview > span,
.swap-preview small {
  font-size: 10px;
  color: #c8bda9;
}
.swap-preview button {
  color: #f0d5ae;
  font-size: 14px;
}
.swap-preview strong {
  font:
    12px ui-monospace,
    monospace;
}
.eyebrow {
  font-size: 9px;
  letter-spacing: 1.6px;
  color: #8ea6b4;
}
.comparison-summary {
  display: flex;
  align-items: center;
  gap: 26px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.comparison-summary > div:first-child {
  margin-right: auto;
}
h2 {
  font-size: 22px;
  font-weight: 500;
  margin-top: 8px;
}
.gain {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--mint);
}
.gain strong {
  font:
    38px ui-monospace,
    monospace;
  font-weight: 400;
}
.gain span {
  font-size: 10px;
  line-height: 1.8;
  color: #a0b6c2;
}
.gain.warm strong {
  color: var(--amber);
}
.result-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
}
.result-column {
  min-width: 0;
  border: 1px solid #2a3d47;
  border-radius: 14px;
  padding: 20px;
  background: #12202a;
}
.result-column.enhanced {
  background: #16241f;
  border-color: #436459;
}
.result-column.active {
  box-shadow: inset 0 2px 0 var(--mint);
}
.column-heading {
  display: flex;
  justify-content: space-between;
  text-align: left;
  width: 100%;
  align-items: center;
  gap: 10px;
  color: inherit;
}
h3 {
  font-size: 18px;
  font-weight: 500;
  margin-top: 8px;
}
.result-count {
  font:
    30px ui-monospace,
    monospace;
}
.result-count small {
  font: 11px sans-serif;
  margin-left: 5px;
  color: #9eafb6;
}
.column-note {
  font-size: 10px;
  color: #9cb0bb;
  margin: 15px 0 18px;
}
.result-card {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid #334651;
  background: #ffffff03;
  padding: 16px;
  margin-top: 10px;
  border-radius: 10px;
  color: inherit;
  transition: border-color 0.2s;
}
.result-card:hover {
  border-color: var(--mint);
}
.result-card.extra {
  border-color: #e9b56d60;
  background: #f0bc7805;
}
.result-card.removed {
  border-style: dashed;
}
.removed .card-label {
  color: #aab6c3;
}
.rank-movement {
  margin-top: 7px;
  color: #a6bbc6;
  font:
    10px ui-monospace,
    monospace;
}
.card-label {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  color: #94cabc;
  font-size: 10px;
  flex-wrap: wrap;
}
.extra .card-label {
  color: var(--amber);
}
h4 {
  font-size: 14px;
  font-weight: 500;
  margin: 13px 0 10px;
  line-height: 1.7;
}
h4 span {
  float: right;
  color: #9eb3bb;
}
.result-card p {
  color: #b3c2ca;
  font-size: 11px;
  line-height: 1.8;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}
.score-line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin: 16px 0 8px;
  font-size: 10px;
  color: #a6bbc6;
}
.score-line strong {
  font:
    12px ui-monospace,
    monospace;
  color: #dce9ef;
}
.similarity-meter {
  height: 3px;
  background: #46607140;
  border-radius: 2px;
  overflow: hidden;
}
.similarity-meter i {
  display: block;
  height: 100%;
  background: var(--mint);
}
.extra .similarity-meter i {
  background: var(--amber);
}
.boost-line {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  font:
    10px ui-monospace,
    monospace;
  margin-top: 13px;
  color: #99afa8;
}
.boost-line strong {
  font-weight: 400;
  color: var(--amber);
}
.delta-tags {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 15px;
}
.delta-tags span {
  font-size: 9px;
  line-height: 1.6;
  padding: 4px 6px;
  background: #ffffff07;
  color: #b1c0c6;
  border-radius: 4px;
}
.delta-tags .distinctive {
  color: #efc995;
  background: #f0bc7811;
}
.result-column footer {
  margin-top: 18px;
  font:
    10px ui-monospace,
    monospace;
  color: #8aa19f;
}
.bridge-heading {
  margin: 30px 0 18px;
}
.bridge-heading h3 {
  font-size: 17px;
  line-height: 1.8;
}
.bridge-card {
  border: 1px solid #d9ab7040;
  border-radius: 12px;
  padding: 20px;
  margin-top: 12px;
  background: #f0bc7804;
}
.bridge-title {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.bridge-title > span {
  font-size: 10px;
  color: var(--amber);
}
.bridge-title button {
  color: #f5e1c4;
  font-size: 14px;
  text-align: left;
}
.bridge-title small {
  margin-left: auto;
  font:
    10px ui-monospace,
    monospace;
  color: #b2a491;
}
.bridge-path {
  display: grid;
  grid-template-columns: 1fr 1.5fr 1fr;
  align-items: center;
  gap: 12px;
  margin-top: 22px;
}
.bridge-path button {
  padding: 12px;
  border: 1px solid #4d665e;
  border-radius: 8px;
  background: #91d8c305;
  font-size: 12px;
  line-height: 1.8;
  color: #c5e6db;
  text-align: left;
}
.bridge-path button:last-child {
  color: #edcc9f;
  border-color: #8b6b414d;
}
.bridge-path button small {
  display: block;
  font-size: 9px;
  opacity: 0.7;
  margin-bottom: 6px;
}
.path-connection {
  text-align: center;
  color: var(--amber);
}
.path-connection span {
  font:
    10px ui-monospace,
    monospace;
}
.path-connection i {
  display: block;
  font-size: 22px;
  font-style: normal;
  line-height: 1.2;
}
.path-connection small {
  display: block;
  font-size: 9px;
  color: #a9b6bc;
  line-height: 1.7;
}
.bridge-evidence {
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid #ffffff0d;
  font-size: 11px;
  color: #b0bec6;
  line-height: 1.9;
}
.method-note,
.empty-result {
  font-size: 10px;
  color: #9bb0be;
  line-height: 1.9;
  margin-top: 20px;
}
button:focus-visible {
  outline: 2px solid var(--mint);
  outline-offset: 5px;
}
@media (max-width: 520px) {
  .result-columns {
    grid-template-columns: 1fr;
  }
  .bridge-path {
    grid-template-columns: 1fr;
  }
  .path-connection i {
    transform: rotate(90deg);
    margin: 8px;
  }
  .comparison-summary {
    gap: 16px;
  }
  .comparison-summary > div:first-child {
    width: 100%;
  }
  .bridge-title small {
    margin-left: 0;
  }
}
</style>
