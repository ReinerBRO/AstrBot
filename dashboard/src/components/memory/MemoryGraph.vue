<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  edgeCurve,
  graphLayout,
  memoryKinds,
  memoryTitle,
} from "./graphLayout.mjs";
const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  results: { type: Array, default: () => [] },
  seeds: { type: Array, default: () => [] },
  selected: { type: String, default: "" },
  kindFilter: { type: String, default: "" },
  replay: { type: Number, default: 0 },
});
const emit = defineEmits(["select", "clear"]);
const host = ref(null),
  svg = ref(null),
  width = ref(900),
  height = ref(590);
const positions = ref([]),
  centers = ref([]),
  zoom = ref(1),
  pan = ref({ x: 0, y: 0 });
const hovered = ref(""),
  phase = ref(2);
let observer,
  phaseTimer,
  drag,
  moved = false;
const shownNodes = computed(() => {
  if (props.nodes.length <= 80) return props.nodes;
  const important = new Set([
    ...props.results.map((n) => n.id),
    ...props.seeds.map((n) => n.id),
    props.selected,
  ]);
  return [...props.nodes]
    .sort(
      (a, b) =>
        Number(important.has(b.id)) - Number(important.has(a.id)) ||
        b.created_at - a.created_at,
    )
    .slice(0, 80);
});
const nodeMap = computed(() => new Map(positions.value.map((n) => [n.id, n])));
const resultMap = computed(
  () =>
    new Map(
      (phase.value === 1 && props.seeds.length ? props.seeds : props.results)
        .filter((r) => phase.value === 2 || r.source === "base")
        .map((r) => [r.id, r]),
    ),
);
const paths = computed(
  () =>
    new Set(
      props.results.flatMap((r) =>
        (r.paths || []).map((p) => [p.source, p.target].sort().join(":")),
      ),
    ),
);
const neighbors = computed(() => {
  const ids = new Set([props.selected]);
  for (const e of props.edges) {
    if (e.source === props.selected) ids.add(e.target);
    if (e.target === props.selected) ids.add(e.source);
  }
  return ids;
});
const lines = computed(() =>
  props.edges
    .filter((e) => nodeMap.value.has(e.source) && nodeMap.value.has(e.target))
    .map((e) => ({
      ...e,
      d: edgeCurve(nodeMap.value.get(e.source), nodeMap.value.get(e.target)),
      active:
        phase.value === 2 &&
        paths.value.has([e.source, e.target].sort().join(":")),
      selected: e.source === props.selected || e.target === props.selected,
    })),
);
const hoverNode = computed(() => nodeMap.value.get(hovered.value));
function color(n) {
  if (resultMap.value.get(n.id)?.source === "base") return "#7fd6bf";
  return resultMap.value.get(n.id)?.source === "hebbian"
    ? "#f0bc78"
    : memoryKinds[n.kind]?.color || "#7fd6bf";
}
function dimmed(n) {
  if (props.kindFilter) return n.kind !== props.kindFilter;
  if (props.results.length) return !resultMap.value.has(n.id);
  if (props.selected) return !neighbors.value.has(n.id);
  return false;
}
function layout() {
  const result = graphLayout(
    shownNodes.value,
    props.edges,
    width.value,
    height.value,
  );
  positions.value = result.nodes;
  centers.value = result.centers;
}
watch(
  () => [
    shownNodes.value.map((n) => n.id).join(","),
    width.value,
    height.value,
  ],
  layout,
);
watch(
  () => [props.results, props.replay],
  () => {
    clearTimeout(phaseTimer);
    phase.value = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? 2
      : 1;
    phaseTimer = setTimeout(() => {
      phase.value = 2;
    }, 700);
  },
);
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    width.value = entry.contentRect.width;
    height.value = entry.contentRect.height;
  });
  observer.observe(host.value);
  layout();
});
onBeforeUnmount(() => {
  observer?.disconnect();
  clearTimeout(phaseTimer);
});
function reset() {
  zoom.value = 1;
  pan.value = { x: 0, y: 0 };
  layout();
}
function scale(factor, x = width.value / 2, y = height.value / 2) {
  const next = Math.max(0.45, Math.min(2.8, zoom.value * factor)),
    ratio = next / zoom.value;
  pan.value = {
    x: x - (x - pan.value.x) * ratio,
    y: y - (y - pan.value.y) * ratio,
  };
  zoom.value = next;
}
function wheel(event) {
  const rect = svg.value.getBoundingClientRect();
  scale(
    event.deltaY > 0 ? 0.92 : 1.08,
    event.clientX - rect.left,
    event.clientY - rect.top,
  );
}
function pointerDown(event, node = null) {
  if (event.button !== 0) return;
  moved = false;
  drag = {
    node,
    x: event.clientX,
    y: event.clientY,
    startX: event.clientX,
    startY: event.clientY,
  };
  svg.value.setPointerCapture(event.pointerId);
}
function pointerMove(event) {
  if (!drag) return;
  const dx = event.clientX - drag.x,
    dy = event.clientY - drag.y;
  if (Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 4)
    moved = true;
  if (drag.node) {
    drag.node.x += dx / zoom.value;
    drag.node.y += dy / zoom.value;
  } else pan.value = { x: pan.value.x + dx, y: pan.value.y + dy };
  drag.x = event.clientX;
  drag.y = event.clientY;
}
function pointerUp(event) {
  if (!drag) return;
  if (!moved) drag.node ? emit("select", drag.node.id) : emit("clear");
  drag = null;
  if (svg.value.hasPointerCapture(event.pointerId))
    svg.value.releasePointerCapture(event.pointerId);
}
function moveKey(event, node) {
  const offset = {
    ArrowUp: [0, -12],
    ArrowDown: [0, 12],
    ArrowLeft: [-12, 0],
    ArrowRight: [12, 0],
  }[event.key];
  if (offset) {
    event.preventDefault();
    node.x += offset[0];
    node.y += offset[1];
  }
}
defineExpose({ reset });
</script>
<template>
  <div ref="host" class="memory-cosmos">
    <svg
      ref="svg"
      :viewBox="`0 0 ${width} ${height}`"
      aria-label="交互记忆图谱：拖拽节点、缩放画布，点击查看来源"
      role="group"
      @wheel.prevent="wheel"
      @pointerdown="pointerDown($event)"
      @pointermove="pointerMove"
      @pointerup="pointerUp"
      @pointercancel="drag = null"
      @keydown.esc="emit('clear')"
    >
      <defs>
        <filter id="memory-glow" x="-150%" y="-150%" width="400%" height="400%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
        <radialGradient id="memory-mist">
          <stop offset="0" stop-color="#7fd6bf" stop-opacity=".065" />
          <stop offset="1" stop-color="#7fd6bf" stop-opacity="0" />
        </radialGradient>
      </defs>
      <g :transform="`translate(${pan.x},${pan.y}) scale(${zoom})`">
        <g v-for="center in centers" :key="center.topic" class="cluster">
          <ellipse
            :cx="center.x"
            :cy="center.y"
            rx="180"
            ry="160"
            fill="url(#memory-mist)"
          />
          <text
            :x="center.x"
            :y="Math.max(44, center.y - 135)"
            text-anchor="middle"
          >
            {{ center.topic }}
          </text>
        </g>
        <g class="connections">
          <g
            v-for="(edge, index) in lines"
            :key="`${edge.source}-${edge.target}`"
          >
            <path
              :d="edge.d"
              :class="{
                activated: edge.active,
                connected: edge.selected,
                faded: results.length && !edge.active,
              }"
              :stroke-width="edge.active ? 2 : 0.5 + edge.weight * 1.5"
            />
            <path
              v-if="edge.active"
              :d="edge.d"
              class="travel"
              :style="{ animationDelay: `${(index % 5) * -0.4}s` }"
            />
          </g>
        </g>
        <g
          v-for="node in positions"
          :key="node.id"
          class="memory-node"
          :class="{
            dimmed: dimmed(node),
            chosen: selected === node.id,
            recalled: resultMap.has(node.id),
            derived: node.kind !== 'episodic',
          }"
          :style="{ '--node-color': color(node) }"
          :transform="`translate(${node.x},${node.y})`"
          role="button"
          tabindex="0"
          :aria-label="`${memoryTitle(node)}，${
            memoryKinds[node.kind]?.label
          }：${node.content}`"
          :aria-pressed="selected === node.id"
          @pointerdown.stop="pointerDown($event, node)"
          @pointerenter="hovered = node.id"
          @pointerleave="hovered = ''"
          @keydown.enter.prevent="emit('select', node.id)"
          @keydown.space.prevent="emit('select', node.id)"
          @keydown="moveKey($event, node)"
        >
          <circle r="25" fill="transparent" />
          <circle
            v-if="node.kind !== 'episodic' || resultMap.has(node.id)"
            :r="node.radius * 2.8"
            class="aura"
            filter="url(#memory-glow)"
          />
          <circle :r="node.radius + 7" class="orbit" />
          <circle v-if="resultMap.has(node.id)" r="23" class="recall-ring" />
          <circle :r="node.radius" class="core" />
          <circle :r="Math.max(1.5, node.radius * 0.25)" class="spark" />
          <text
            v-if="
              positions.length <= 50 ||
              node.kind !== 'episodic' ||
              selected === node.id ||
              resultMap.has(node.id)
            "
            class="node-title"
            text-anchor="middle"
            :y="node.radius + 25"
          >
            {{ memoryTitle(node) }}
          </text>
          <text
            v-if="resultMap.has(node.id)"
            class="recall-label"
            text-anchor="middle"
            :y="-node.radius - 18"
          >
            {{
              resultMap.get(node.id).membership === "hela_only"
                ? "关联换入"
                : resultMap.get(node.id).source === "hebbian"
                ? "关联唤起"
                : "向量命中"
            }}
          </text>
        </g>
      </g>
    </svg>
    <div v-if="!nodes.length" class="empty-cosmos">
      <span class="empty-orbit">✦</span>
      <h2>每一段对话，都可以留下星光。</h2>
      <p>在 Chat 中开始一段对话，Persbot 会把记住的经历连接在这里。</p>
    </div>
    <div v-if="hoverNode && !selected" class="hover-preview">
      <i :style="{ background: color(hoverNode) }" />
      <div>
        <strong>{{ memoryTitle(hoverNode) }}</strong>
        <p>{{ hoverNode.content.slice(0, 80) }}</p>
      </div>
    </div>
    <div class="canvas-tools" aria-label="图谱缩放控制">
      <button aria-label="放大图谱" @click="scale(1.2)">+</button
      ><span>{{ Math.round(zoom * 100) }}%</span
      ><button aria-label="缩小图谱" @click="scale(0.8)">−</button><b /><button
        aria-label="重置图谱视角"
        title="回到全景"
        @click="reset"
      >
        <v-icon size="17">mdi-crosshairs-gps</v-icon>
      </button>
    </div>
    <span class="canvas-hint"
      >{{
        nodes.length > 80
          ? `显示 ${positions.length} / ${nodes.length} 条 · `
          : ""
      }}拖拽探索 · 滚轮缩放</span
    >
  </div>
</template>
<style scoped>
.memory-cosmos {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}
svg {
  width: 100%;
  height: 100%;
  display: block;
  touch-action: none;
  cursor: grab;
  user-select: none;
}
svg:active {
  cursor: grabbing;
}
.cluster text {
  fill: #829baf;
  font-size: 11px;
  letter-spacing: 0.2em;
  opacity: 0.8;
}
.connections path {
  fill: none;
  stroke: #5e8e9d;
  stroke-opacity: 0.32;
  transition:
    stroke-opacity 0.6s,
    stroke 0.6s;
}
.connections .connected {
  stroke: #a8dccf;
  stroke-opacity: 0.75;
}
.connections .faded {
  stroke-opacity: 0.22;
}
.connections .activated {
  stroke: #e6b87e;
  stroke-opacity: 0.65;
}
.connections .travel {
  stroke: #ffe1b8;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-dasharray: 4 150;
  stroke-opacity: 1;
  animation: travel 4s linear infinite;
}
.memory-node {
  cursor: grab;
  transition: opacity 0.6s;
  outline: none;
}
.memory-node.dimmed {
  opacity: 0.5;
}
.memory-node:hover,
.memory-node:focus-visible {
  opacity: 1;
}
.core {
  fill: var(--node-color);
  stroke: var(--node-color);
  stroke-width: 1;
}
.spark {
  fill: #effff9;
  opacity: 0.8;
}
.aura {
  fill: var(--node-color);
  opacity: 0.18;
}
.orbit {
  stroke: var(--node-color);
  fill: none;
  stroke-opacity: 0.16;
  stroke-width: 0.7;
}
.derived .core {
  fill: #172d3b;
  stroke-width: 2;
}
.derived .spark {
  fill: var(--node-color);
}
.chosen .orbit,
.memory-node:hover .orbit,
.memory-node:focus-visible .orbit {
  stroke-opacity: 0.9;
  stroke-width: 1.5;
}
.chosen .aura {
  opacity: 0.4;
}
.recall-ring {
  stroke: var(--node-color);
  fill: none;
  opacity: 0.25;
  stroke-dasharray: 2 5;
  animation: orbit-turn 20s linear infinite;
}
.node-title {
  fill: #c0cfd9;
  font-size: 11px;
  paint-order: stroke;
  stroke: #0c1925;
  stroke-width: 4px;
  stroke-linejoin: round;
}
.derived .node-title {
  fill: #e5ecf3;
  font-size: 12px;
}
.chosen .node-title,
.recalled .node-title {
  fill: #f3fbff;
}
.recall-label {
  fill: var(--node-color);
  font-size: 10px;
  letter-spacing: 0.06em;
  paint-order: stroke;
  stroke: #0c1925;
  stroke-width: 4;
}
.canvas-tools {
  position: absolute;
  bottom: 20px;
  left: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  background: #15232de8;
  border: 1px solid #ffffff17;
  border-radius: 9px;
  color: #a9bdcb;
}
.canvas-tools button {
  width: 30px;
  height: 30px;
  border-radius: 5px;
  font-size: 19px;
  color: #c8dbe6;
}
.canvas-tools button:hover {
  background: #ffffff10;
}
.canvas-tools button:focus-visible {
  outline: 2px solid #7fd6bf;
}
.canvas-tools span {
  font:
    10px ui-monospace,
    monospace;
  min-width: 34px;
  text-align: center;
}
.canvas-tools b {
  height: 14px;
  width: 1px;
  background: #ffffff20;
}
.canvas-hint {
  position: absolute;
  bottom: 33px;
  right: 24px;
  color: #8198ab;
  font-size: 10px;
  letter-spacing: 0.04em;
  pointer-events: none;
}
.hover-preview {
  position: absolute;
  top: 78px;
  left: 24px;
  width: 245px;
  pointer-events: none;
  padding: 15px;
  display: flex;
  gap: 10px;
  border: 1px solid #a8c8db28;
  background: #142431ed;
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow: 0 12px 45px #0003;
}
.hover-preview i {
  flex: 0 0 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 6px;
}
.hover-preview strong {
  color: #e3eff4;
  font-size: 12px;
}
.hover-preview p {
  color: #99afbf;
  font-size: 11px;
  line-height: 1.8;
  margin: 5px 0 0;
}
.empty-cosmos {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  text-align: center;
  padding: 28px;
}
.empty-orbit {
  color: #82cbb7;
  font-size: 45px;
  margin-bottom: 26px;
}
.empty-cosmos h2 {
  font-size: 19px;
  font-weight: 450;
  color: #d3e5ee;
}
.empty-cosmos p {
  color: #7d98aa;
  font-size: 12px;
  margin-top: 12px;
}
@keyframes travel {
  to {
    stroke-dashoffset: -308;
  }
}
@keyframes orbit-turn {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 600px) {
  .canvas-tools {
    bottom: 18px;
    left: 16px;
  }
  .canvas-hint {
    right: 16px;
    font-size: 9px;
  }
  .hover-preview {
    display: none;
  }
  .node-title {
    font-size: 10px;
  }
  .derived .node-title {
    font-size: 11px;
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
