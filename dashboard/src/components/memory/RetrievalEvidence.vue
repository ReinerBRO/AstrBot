<script setup>
defineProps({ trace: { type: Object, required: true }, enhanced: Boolean });
defineEmits(["select"]);
</script>
<template>
  <article class="evidence" :class="{ enhanced }">
    <div class="evidence-heading">
      <h3>{{ enhanced ? "HeLa-Mem · 双路径" : "基础检索 · Top-K" }}</h3>
      <span>{{ trace.results.length }} 条</span>
    </div>
    <p class="caption">
      {{ enhanced ? "直接命中 + 图关联补全" : "仅使用词面 / 向量相关性" }} ·
      {{ trace.context_chars }} / {{ trace.budget_chars }} 字符
    </p>
    <div v-if="trace.answer" class="model-answer">
      <span class="answer-label">{{ trace.model }} · 实际回答</span>
      <p>{{ trace.answer }}</p>
      <small>{{ (trace.latency_ms / 1000).toFixed(1) }} s · 相同模型配置</small>
    </div>
    <p v-if="!trace.results.length" class="caption">
      没有符合当前预算的相关记忆。
    </p>
    <button
      v-for="result in trace.results"
      :key="result.id"
      class="evidence-item"
      @click="$emit('select', result.id)"
    >
      <span
        class="evidence-tag"
        :class="{ extra: result.source === 'hebbian' }"
        >{{ result.source === "hebbian" ? "关联补全" : "直接命中" }}</span
      >
      <p>{{ result.content }}</p>
      <small
        >基础 {{ result.base_score.toFixed(3)
        }}<template v-if="enhanced">
          · 关联 +{{ result.association_score.toFixed(3) }}</template
        ></small
      >
      <small v-for="path in result.paths" :key="path.source" class="path"
        >{{ path.source.slice(0, 6) }} → {{ result.id.slice(0, 6) }} · 权重
        {{ path.weight.toFixed(3) }}</small
      >
    </button>
  </article>
</template>
<style scoped>
.evidence {
  padding: 20px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 12px;
  min-width: 0;
}
.enhanced {
  border-color: #458a74;
}
.model-answer {
  margin: 20px 0;
  padding: 16px;
  border-left: 3px solid #8b9c98;
  background: rgb(var(--v-theme-surface));
  border-radius: 4px;
}
.enhanced .model-answer {
  border-left-color: #277b63;
}
.answer-label {
  font-size: 11px;
  opacity: 0.65;
}
.model-answer p {
  font-size: 15px;
  line-height: 1.9;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 10px 0;
}
.evidence-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
h3 {
  font-size: 16px;
}
.caption {
  font-size: 12px;
  opacity: 0.65;
  margin: 8px 0 16px;
}
.evidence-item {
  display: block;
  text-align: left;
  width: 100%;
  color: inherit;
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  padding: 16px 0 0;
  margin-top: 16px;
  overflow-wrap: anywhere;
}
.evidence-item:focus-visible {
  outline: 2px solid #458a74;
  outline-offset: 4px;
}
.evidence-item p {
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}
.evidence-tag {
  font-size: 11px;
  color: #176b53;
  background: #dff3eb;
  padding: 3px 6px;
  border-radius: 4px;
}
.evidence-tag.extra {
  color: #855408;
  background: #fff0ce;
}
small {
  opacity: 0.7;
  font:
    11px ui-monospace,
    monospace;
}
.path {
  display: block;
  margin-top: 6px;
}
</style>
