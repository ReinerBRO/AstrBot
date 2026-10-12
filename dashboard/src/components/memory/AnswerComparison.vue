<script setup>
import { computed } from "vue";
import { memoryTitle } from "./graphLayout.mjs";

const props = defineProps({
  comparison: { type: Object, required: true },
  busy: Boolean,
});
defineEmits(["generate", "select"]);
const answers = computed(() => props.comparison.answer_comparison);
const isPreset = computed(
  () => props.comparison.presentation?.mode === "preset",
);
const title = (id) => {
  const item = [
    ...props.comparison.base.results,
    ...props.comparison.helamem.results,
  ].find((item) => item.id === id);
  return item ? memoryTitle(item) : id;
};
</script>

<template>
  <section class="answer-showcase" aria-label="不同记忆带来的回答对比">
    <header>
      <div>
        <span class="eyebrow">FROM MEMORY TO ANSWER</span>
        <h2>本次回答对比</h2>
      </div>
      <span class="source-badge">
        {{ isPreset ? "预设检索" : "实时检索" }} · {{ answers.model }} 本次生成
      </span>
    </header>
    <div class="question">
      <small>你问</small>
      <h3>{{ answers.question }}</h3>
    </div>
    <div class="answer-columns" aria-live="polite">
      <article
        v-for="side in ['base', 'helamem']"
        :key="side"
        class="answer-panel"
        :class="[side, answers[side].status]"
      >
        <div class="answer-heading">
          <span
            >{{ side === "base" ? "纯向量" : "HeLa" }} Top-{{
              comparison[side].top_k
            }}</span
          >
          <strong v-if="answers[side].status !== 'ungraded'">{{
            answers[side].verdict
          }}</strong>
        </div>
        <div v-if="answers[side].evidence?.length" class="evidence-chain">
          <template v-for="item in answers[side].evidence" :key="item.id">
            <button
              v-if="item.found"
              class="found"
              @click="$emit('select', item.id)"
            >
              {{ item.label }} ✓
            </button>
            <span v-else class="missing-slot">{{ item.label }}缺失</span>
          </template>
        </div>
        <blockquote>{{ answers[side].text }}</blockquote>
        <div v-if="answers[side].citations.length" class="answer-citations">
          <span>回答引用</span>
          <button
            v-for="id in answers[side].citations"
            :key="id"
            @click="$emit('select', id)"
          >
            {{ title(id) }} ↗
          </button>
        </div>
      </article>
    </div>
    <div class="generation-actions">
      <span
        >同一模型 · 同一提示词 · 每侧 Top-{{ comparison.base.top_k }} ·
        {{ new Date(answers.generated_at * 1000).toLocaleTimeString() }}</span
      >
      <button :disabled="busy" @click="$emit('generate')">
        {{ busy ? "正在生成…" : "重新回答 ↻" }}
      </button>
    </div>
    <details v-if="isPreset">
      <summary>检索说明</summary>
      <p>{{ comparison.presentation.note }}</p>
    </details>
  </section>
</template>

<style scoped>
.answer-showcase {
  --mint: #94dec2;
  color: #deebe9;
  margin: 26px 0 30px;
  padding: 26px;
  border: 1px solid #58706855;
  border-radius: 16px;
  background: #0d1b23;
  scroll-margin-top: 72px;
}
header {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: space-between;
}
.eyebrow {
  color: #91b3a8;
  font-size: 9px;
  letter-spacing: 1.7px;
}
h2 {
  font-size: clamp(19px, 2vw, 25px);
  font-weight: 500;
  margin-top: 8px;
}
.source-badge {
  font-size: 10px;
  color: #d6bd94;
  border: 1px solid #b5986640;
  border-radius: 5px;
  padding: 6px 9px;
}
.question {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 22px 0;
}
.question small {
  font-size: 10px;
  color: #91aab8;
  white-space: nowrap;
}
h3 {
  font-size: 15px;
  font-weight: 500;
  line-height: 1.8;
}
.answer-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.answer-panel {
  padding: 20px;
  border: 1px solid #5f565452;
  border-radius: 12px;
  background: #24242640;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 20px;
}
.answer-panel.helamem {
  border-color: #80c7aa70;
  background: #14332970;
  box-shadow: inset 0 2px 0 #80c7aa;
}
.answer-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
}
.answer-heading strong {
  color: #edb7a7;
  font-size: 11px;
  font-weight: 500;
  padding: 5px 8px;
  border-radius: 5px;
  background: #a8705918;
}
.correct .answer-heading strong {
  color: #b7efd6;
  background: #77bb9c20;
}
.evidence-chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: #879d9f;
  font-size: 10px;
}
.evidence-chain button {
  padding: 6px 8px;
  border-radius: 4px;
}
.found {
  color: #b8efd3;
  background: #7cd6ae20;
}
.missing-slot {
  border: 1px dashed #826d6b7a;
  padding: 5px 8px;
  color: #c3a59e;
  border-radius: 4px;
}
blockquote {
  font-size: 14px;
  line-height: 2;
  margin: 0;
  padding: 0;
  flex: 1;
  color: #d7e3e4;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.answer-citations {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  font-size: 10px;
}
.answer-citations > span {
  width: 100%;
  color: #91aab8;
}
.answer-citations button {
  color: #b6d7cf;
  text-align: left;
  line-height: 1.8;
  padding: 4px 0;
}
.generation-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 20px;
  font-size: 11px;
  color: #96aeb6;
}
.generation-actions button {
  padding: 9px 12px;
  border: 1px solid #91c6b14f;
  border-radius: 6px;
  color: #c7eadd;
}
button:disabled {
  opacity: 0.5;
  cursor: wait;
}
button:focus-visible,
summary:focus-visible {
  outline: 2px solid var(--mint);
  outline-offset: 3px;
}
details {
  margin-top: 16px;
  color: #96aeb6;
  font-size: 11px;
  line-height: 1.8;
}
summary {
  cursor: pointer;
  width: fit-content;
}
details p {
  margin: 8px 0 0;
}
@media (max-width: 520px) {
  .answer-showcase {
    padding: 18px;
  }
  .answer-columns {
    grid-template-columns: 1fr;
  }
}
</style>
