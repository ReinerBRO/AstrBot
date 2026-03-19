const statusBadge = document.getElementById("statusBadge");
const UI_BUILD = "20260213-remove-logical-tree";
const startTimeInput = document.getElementById("startTime");
const endTimeInput = document.getElementById("endTime");
const intervalInput = document.getElementById("intervalInput");
const categoriesInput = document.getElementById("categoriesInput");
const applyCategoriesBtn = document.getElementById("applyCategoriesBtn");
const categoryLegend = document.getElementById("categoryLegend");
const dateDropdown = document.getElementById("dateDropdown");
const dateDropdownBtn = document.getElementById("dateDropdownBtn");
const dateDropdownMenu = document.getElementById("dateDropdownMenu");
const treeSelect = document.getElementById("treeSelect");
const newTreeBtn = document.getElementById("newTreeBtn");
const deleteTreeBtn = document.getElementById("deleteTreeBtn");
const reloadHistoryBtn = document.getElementById("reloadHistoryBtn");
const branchFilters = document.getElementById("branchFilters");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const settingsToggleBtn = document.getElementById("settingsToggleBtn");
const settingsCloseBtn = document.getElementById("settingsCloseBtn");
const settingsDrawer = document.getElementById("settingsDrawer");
const settingsOverlay = document.getElementById("settingsOverlay");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const manualBtn = document.getElementById("manualBtn");
const logsPanel = document.getElementById("logsPanel");
const treeDate = document.getElementById("treeDate");
const rangeLabel = document.getElementById("rangeLabel");
const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const resetViewBtn = document.getElementById("resetViewBtn");
const canvas = document.getElementById("treeCanvas");
const treeCanvasVignette = document.getElementById("treeCanvasVignette");
const tooltip = document.getElementById("tooltip");
const treeList = document.getElementById("treeList");
const treeEmptyOverlay = document.getElementById("treeEmptyOverlay");
const workspaceSection = document.querySelector(".workspace");
const viewSwitcherMount = document.getElementById("viewSwitcherMount");
const cardsViewSection = document.getElementById("cardsViewSection");
const logsViewSection = document.getElementById("logsViewSection");
const flowViewSection = document.getElementById("flowViewSection");
const flowCanvas = document.getElementById("flowCanvas");
const flowZoomInBtn = document.getElementById("flowZoomInBtn");
const flowZoomOutBtn = document.getElementById("flowZoomOutBtn");
const flowResetBtn = document.getElementById("flowResetBtn");
const flowEmptyOverlay = document.getElementById("flowEmptyOverlay");
const summaryViewSection = document.getElementById("summaryViewSection");
const summaryGenerateBtn = document.getElementById("summaryGenerateBtn");
const summaryRegenerateBtn = document.getElementById("summaryRegenerateBtn");
const summaryCopyBtn = document.getElementById("summaryCopyBtn");
const summaryViewMeta = document.getElementById("summaryViewMeta");
const summaryStreamArea = document.getElementById("summaryStreamArea");
const summaryPhaseIndicator = document.getElementById("summaryPhaseIndicator");
const summaryAiBlock = document.getElementById("summaryAiBlock");
const summaryAiText = document.getElementById("summaryAiText");
const summaryAiCursor = document.getElementById("summaryAiCursor");
const summaryHighlightsBlock = document.getElementById("summaryHighlightsBlock");
const summaryHighlightsList = document.getElementById("summaryHighlightsList");
const summaryTimelineBlock = document.getElementById("summaryTimelineBlock");
const summaryTimelineList = document.getElementById("summaryTimelineList");
const summaryViewEmpty = document.getElementById("summaryViewEmpty");
const summaryViewError = document.getElementById("summaryViewError");
const monitorSelect = document.getElementById("monitorSelect");
const monitorPreview = document.getElementById("monitorPreview");

const MAIN_LANES = {
  写代码: -1,
  研究: 0,
  娱乐: 1,
};

const OTHER_LANES = [-2, 2, -3, 3];
const COLOR_PALETTE = [
  "#7bb0ff",
  "#79d9b8",
  "#f1bb63",
  "#ff89a8",
  "#be9dff",
  "#8bd2ff",
];

const viewState = {
  fullStart: 9 * 60,
  fullEnd: 18 * 60,
  viewStart: 9 * 60,
  viewEnd: 18 * 60,
  minSpan: 30,
  initialized: false,
  userAdjusted: false,
};

const uiState = {
  categories: ["写代码", "研究", "娱乐"],
  selectedDate: "",
  selectedTreeId: "",
  availableDates: [],
  trees: [],
  trimmedCategories: new Set(),
  dateMenuOpen: false,
  settingsOpen: false,
  theme: "dark",
  activeView: "tree",
};

let fruits = [];
let selectedFruitIndex = -1;
let lastTreeData = null;
let lastCanvasMetrics = null;
let isPanning = false;
let controlsHydrated = false;
let panStartY = 0;
let panAnchorStart = 0;
let panAnchorEnd = 0;
let activeScene = null;
let renderErrorFingerprint = "";
let lastViewportSelectionKey = "";
let resizeFrame = null;
let flowResizeFrame = null;
let treeRequestSeq = 0;
let viewSwitcher = null;
let cardView = null;
let cardFallbackWarned = false;
let flowView = null;
const summaryViewState = {
  date: "",
  payload: null,
  status: "idle",
  streamConnection: null,
  activeRequestId: 0,
  tokenBuffer: "",
};

const treeMotionMedia = window.matchMedia?.("(prefers-reduced-motion: reduce)") || null;
const treeAnimationState = {
  rafId: 0,
  lastFrameMs: 0,
  introStartMs: 0,
  sceneFingerprint: "",
  reducedMotion: Boolean(treeMotionMedia?.matches),
  primedScene: "",
};

function ensureTooltipRichStyles() {
  if (!document?.head) return;
  if (document.getElementById("tree-tooltip-rich-style")) return;
  const style = document.createElement("style");
  style.id = "tree-tooltip-rich-style";
  style.textContent = `
    .tooltip .tip-head {
      display: flex;
      align-items: center;
      gap: 0.45rem;
      margin-bottom: 0.22rem;
    }
    .tooltip .tip-time {
      font: 700 0.8rem/1.1 "IBM Plex Mono", monospace;
      letter-spacing: 0.02em;
    }
    .tooltip .tip-cat {
      display: inline-flex;
      align-items: center;
      padding: 0.1rem 0.42rem;
      border-radius: 999px;
      font: 700 0.66rem/1 "IBM Plex Mono", monospace;
      letter-spacing: 0.02em;
    }
    .tooltip .tip-summary {
      font: 600 0.78rem/1.45 "Plus Jakarta Sans", sans-serif;
      margin-top: 0.2rem;
      word-break: break-word;
    }
    .tooltip .tip-meta {
      margin-top: 0.24rem;
      font: 600 0.68rem/1.4 "IBM Plex Mono", monospace;
      color: var(--muted);
      opacity: 0.9;
    }
  `;
  document.head.appendChild(style);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDurationCompact(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) {
    return "";
  }
  if (value < 60) {
    return `${Math.max(1, Math.round(value))}s`;
  }
  if (value < 3600) {
    return `${Math.max(1, Math.round(value / 60))}min`;
  }
  const hours = Math.floor(value / 3600);
  const minutes = Math.round((value % 3600) / 60);
  if (!minutes) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

function parseSummaryMeta(text) {
  const raw = String(text || "").trim();
  const marker = " (source=";
  const index = raw.lastIndexOf(marker);
  if (index < 0 || !raw.endsWith(")")) {
    return { summary: raw, meta: {} };
  }
  const payload = raw.slice(index + 2, -1);
  const meta = {};
  for (const chunk of payload.split(";")) {
    if (!chunk.includes("=")) continue;
    const pair = chunk.split("=", 2);
    const key = pair[0].trim();
    const value = pair[1].trim();
    if (key) meta[key] = value;
  }
  if (!meta.source) {
    return { summary: raw, meta: {} };
  }
  return { summary: raw.slice(0, index).trim(), meta };
}

function extractConfidenceFromMeta(meta = {}) {
  const raw = String(meta.confidence || "").trim();
  if (raw) {
    const value = Number(raw);
    if (Number.isFinite(value)) {
      return clamp(value, 0, 1);
    }
  }
  const reason = String(meta.reason || "");
  const matches = reason.match(/\b(?:0(?:\.\d+)?|1(?:\.0+)?)\b/g) || [];
  for (const token of matches) {
    const value = Number(token);
    if (Number.isFinite(value)) {
      return clamp(value, 0, 1);
    }
  }
  return 0;
}

function normalizeSourceLabel(rawSource) {
  const source = String(rawSource || "vl").trim().toLowerCase();
  if (source === "fusion" || source === "vl+event") {
    return "VL+Event";
  }
  if (source === "event") {
    return "Event";
  }
  return "VL";
}

function buildTooltipHtml(data) {
  const color = /^#[0-9a-fA-F]{3,8}$/.test(data?.color) ? data.color : "#8fb2d9";
  const time = escapeHtml(data?.time || "--:--");
  const category = escapeHtml(data?.category || "未分类");
  const summary = escapeHtml(data?.summary || data?.text || "无摘要");
  const clickCount = Number(data?.clickCount);
  const topApp = String(data?.topApp || "").trim();
  const activeSeconds = Number(data?.activeSeconds);
  const metaBits = [];
  if (Number.isFinite(clickCount) && clickCount > 0) {
    metaBits.push(`${Math.round(clickCount)}次点击`);
  }
  if (topApp) {
    metaBits.push(topApp);
  }
  const duration = formatDurationCompact(activeSeconds);
  if (duration) {
    metaBits.push(duration);
  }
  if (!metaBits.length) {
    const source = String(data?.source || "").trim();
    if (source) {
      metaBits.push(source);
    }
    const confidence = Number(data?.confidence);
    if (Number.isFinite(confidence) && confidence > 0) {
      metaBits.push(`置信 ${(confidence * 100).toFixed(0)}%`);
    }
  }
  return `
    <div class="tip-head">
      <span class="tip-time">${time}</span>
      <span class="tip-cat" style="background:${color}; color:#0d1724">${category}</span>
    </div>
    <div class="tip-summary">${summary}</div>
    <div class="tip-meta">${escapeHtml(metaBits.join(" · ") || "无事件元数据")}</div>
  `;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function parseMinutes(text, fallback) {
  if (!text || typeof text !== "string" || !text.includes(":")) {
    return fallback;
  }
  const [hourText, minuteText] = text.split(":");
  const hour = Number.parseInt(hourText, 10);
  const minute = Number.parseInt(minuteText, 10);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return fallback;
  }
  return clamp(hour, 0, 23) * 60 + clamp(minute, 0, 59);
}

function formatHHMM(minutes) {
  let value = minutes % (24 * 60);
  if (value < 0) value += 24 * 60;
  const hours = Math.floor(value / 60);
  const mins = value % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

function normalizeMinute(minutes, start, end) {
  if (end >= start) {
    return clamp(minutes, start, end);
  }
  if (minutes >= start) return minutes;
  return minutes + 24 * 60;
}

function parseCategories(value) {
  return [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))].slice(0, 8);
}

function getTodayISO() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function shiftIsoDate(isoDate, offsetDays) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function buildDateCandidates(baseDate, availableDates) {
  const candidates = [];
  for (let i = -30; i <= 30; i += 1) {
    candidates.push(shiftIsoDate(baseDate, i));
  }
  const unique = new Set(candidates);
  for (const item of availableDates) {
    unique.add(item);
  }
  return [...unique].sort((a, b) => (a > b ? -1 : 1));
}

function parseCommaList(value) {
  if (!value) return [];
  if (Array.isArray(value)) {
    return [...new Set(value.map((item) => String(item || "").trim()).filter(Boolean))];
  }
  return [...new Set(String(value).split(",").map((item) => item.trim()).filter(Boolean))];
}

function buildDateRangeValues(startISO, endISO) {
  const startDate = new Date(`${startISO}T00:00:00`);
  const endDate = new Date(`${endISO}T00:00:00`);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
    return [];
  }
  const [begin, end] = startDate <= endDate ? [startDate, endDate] : [endDate, startDate];
  const output = [];
  const current = new Date(begin.getTime());
  while (current <= end) {
    output.push(current.toISOString().slice(0, 10));
    current.setDate(current.getDate() + 1);
  }
  return output;
}

function toCardDateStamp(isoDate) {
  return String(isoDate || "").replace(/-/g, "");
}

function getCategoryColor(category) {
  const index = uiState.categories.indexOf(category);
  if (index >= 0) {
    return COLOR_PALETTE[index % COLOR_PALETTE.length];
  }
  return "#9ba8bb";
}

function setBadge(running) {
  statusBadge.textContent = running ? "Running" : "Stopped";
  statusBadge.classList.toggle("running", running);
  statusBadge.classList.toggle("stopped", !running);
}

function setTreeEmptyOverlay(message = "") {
  if (!treeEmptyOverlay) return;
  if (message) {
    treeEmptyOverlay.textContent = message;
    treeEmptyOverlay.classList.remove("hidden");
    return;
  }
  treeEmptyOverlay.textContent = "";
  treeEmptyOverlay.classList.add("hidden");
}

function setCanvasRenderMode(mode) {
  const showCanvas = mode === "tree";
  if (canvas) {
    canvas.classList.toggle("hidden", !showCanvas);
  }
  if (treeCanvasVignette) {
    treeCanvasVignette.classList.toggle("hidden", !showCanvas);
  }
}

function setFlowEmptyOverlay(message = "") {
  if (!flowEmptyOverlay) return;
  if (message) {
    flowEmptyOverlay.textContent = message;
    flowEmptyOverlay.classList.remove("hidden");
    return;
  }
  flowEmptyOverlay.textContent = "";
  flowEmptyOverlay.classList.add("hidden");
}

function renderFlowFromTreeData(data = null) {
  if (!flowView) return;
  const entries = Array.isArray(data?.entries) ? data.entries : [];
  const categories = Array.isArray(uiState.categories) ? uiState.categories : [];
  flowView.setData(entries, categories);
}

function setActiveView(view, syncSwitcher = true) {
  const previous = uiState.activeView;
  const next = ["tree", "cards", "flow", "summary", "logs"].includes(view) ? view : "tree";
  uiState.activeView = next;

  workspaceSection?.classList.toggle("hidden", next !== "tree");
  cardsViewSection?.classList.toggle("hidden", next !== "cards");
  flowViewSection?.classList.toggle("hidden", next !== "flow");
  summaryViewSection?.classList.toggle("hidden", next !== "summary");
  logsViewSection?.classList.toggle("hidden", next !== "logs");

  if (next === "tree") {
    if (activeScene?.kind === "tree" && !treeAnimationState.reducedMotion) {
      startTreeAnimationLoop();
    }
    if (lastTreeData) {
      drawTree(lastTreeData);
    }
  } else {
    hideTooltip();
    stopTreeAnimationLoop();
  }

  if (next === "cards") {
    const selectedDate = uiState.selectedDate || getTodayISO();
    cardView?.applyMeta({
      categories: uiState.categories,
      trees: uiState.trees,
      selectedDate,
    });
    cardView?.loadCards({ date: selectedDate }, { syncUrl: true }).catch((error) => {
      pushLogLine(`cards load failed: ${error.message}`);
    });
  }

  if (next === "flow") {
    if (!flowView) {
      setFlowEmptyOverlay("FlowView is not available yet.");
    } else if (lastTreeData) {
      setFlowEmptyOverlay("");
      renderFlowFromTreeData(lastTreeData);
    } else {
      setFlowEmptyOverlay("No tree data. Please select a tree first.");
      renderFlowFromTreeData({ entries: [] });
    }
  }

  if (next === "logs") {
    refreshLogs().catch(() => {});
  }

  if (next === "summary") {
    const date = uiState.selectedDate || getTodayISO();
    loadSummaryForDate(date, { forceFetch: false, useLoading: !summaryViewState.payload }).catch((error) => {
      pushLogLine(`summary load failed: ${error instanceof Error ? error.message : String(error)}`);
    });
  } else if (previous === "summary") {
    nextSummaryRequestId();
    closeSummaryStreamConnection();
    summaryAiCursor?.classList.add("hidden");
    setSummaryButtonsBusy(false);
  }

  if (syncSwitcher && viewSwitcher) {
    viewSwitcher.setActiveView(next, { silent: true });
  }
}

function applyTheme(theme) {
  uiState.theme = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", uiState.theme);
  if (themeToggleBtn) {
    themeToggleBtn.textContent = uiState.theme === "light" ? "Dark Theme" : "Light Theme";
  }
  try {
    localStorage.setItem("watcher_theme", uiState.theme);
  } catch (error) {
  }
}

function renderTreeList(entries) {
  treeList.innerHTML = "";
  if (!entries.length) {
    const li = document.createElement("li");
    li.textContent = "No activity entries yet.";
    treeList.appendChild(li);
    return;
  }
  for (const entry of entries) {
    const li = document.createElement("li");
    li.textContent = `${entry.time} [${entry.category}] ${entry.summary}`;
    treeList.appendChild(li);
  }
}

function renderCategoryLegend() {
  categoryLegend.innerHTML = "";
  for (const category of uiState.categories) {
    const row = document.createElement("span");
    const dot = document.createElement("i");
    dot.className = "dot";
    dot.style.background = getCategoryColor(category);
    row.appendChild(dot);
    row.append(category);
    categoryLegend.appendChild(row);
  }
}

function renderBranchFilters() {
  branchFilters.innerHTML = "";
  for (const category of uiState.categories) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "branch-chip";
    chip.textContent = category;
    chip.style.color = getCategoryColor(category);
    if (uiState.trimmedCategories.has(category)) {
      chip.classList.add("trimmed");
    }
    chip.addEventListener("click", () => {
      if (uiState.trimmedCategories.has(category)) {
        uiState.trimmedCategories.delete(category);
      } else {
        uiState.trimmedCategories.add(category);
      }
      renderBranchFilters();
      if (lastTreeData) drawTree(lastTreeData);
    });
    branchFilters.appendChild(chip);
  }
}

function setCategories(categories, syncInput = true) {
  uiState.categories = categories.length ? categories : ["写代码", "研究", "娱乐"];
  for (const category of [...uiState.trimmedCategories]) {
    if (!uiState.categories.includes(category)) {
      uiState.trimmedCategories.delete(category);
    }
  }
  if (syncInput) {
    categoriesInput.value = uiState.categories.join(",");
  }
  renderCategoryLegend();
  renderBranchFilters();
  cardView?.applyMeta({
    categories: uiState.categories,
    trees: uiState.trees,
    selectedDate: uiState.selectedDate || getTodayISO(),
  });
  if (flowView && uiState.activeView === "flow") {
    renderFlowFromTreeData(lastTreeData);
  }
}

function setDateMenuOpen(open) {
  uiState.dateMenuOpen = open;
  dateDropdownBtn?.setAttribute("aria-expanded", open ? "true" : "false");
  dateDropdownMenu?.classList.toggle("hidden", !open);
  if (open && dateDropdownMenu) {
    const active = dateDropdownMenu.querySelector(".active");
    if (active) {
      active.scrollIntoView({ block: "center" });
    }
  }
}

function setSettingsOpen(open) {
  const nextOpen = Boolean(open);
  uiState.settingsOpen = nextOpen;
  settingsDrawer?.classList.toggle("open", nextOpen);
  settingsDrawer?.setAttribute("aria-hidden", nextOpen ? "false" : "true");
  settingsOverlay?.classList.toggle("hidden", !nextOpen);
  settingsToggleBtn?.setAttribute("aria-expanded", nextOpen ? "true" : "false");
  document.body.classList.toggle("drawer-open", nextOpen);
}

function renderDateDropdown() {
  if (!dateDropdownBtn || !dateDropdownMenu) return;
  const selectedDate = uiState.selectedDate || getTodayISO();
  const today = getTodayISO();
  const availableSet = new Set(uiState.availableDates || []);
  const options = buildDateCandidates(selectedDate, uiState.availableDates || []);

  dateDropdownBtn.textContent = selectedDate;
  dateDropdownMenu.innerHTML = "";
  for (const optionDate of options) {
    const hasData = availableSet.has(optionDate);
    const isFutureDate = optionDate > today;
    const isTodayOrFuture = optionDate >= today;
    const selectable = hasData || isTodayOrFuture || optionDate === selectedDate;
    const item = document.createElement("button");
    item.type = "button";
    const optionClasses = ["date-option", hasData ? "has-data" : "no-data"];
    if (isFutureDate && !hasData) {
      optionClasses.push("future-selectable");
    }
    item.className = optionClasses.join(" ");
    if (optionDate === selectedDate) {
      item.classList.add("active");
    }
    item.textContent = optionDate;
    if (!selectable) {
      item.disabled = true;
      item.setAttribute("aria-disabled", "true");
    } else {
      item.addEventListener("click", async () => {
        uiState.selectedDate = optionDate;
        uiState.selectedTreeId = "";
        viewState.userAdjusted = false;
        setDateMenuOpen(false);
        await refreshTree().catch((error) => pushLogLine(`history failed: ${error.message}`));
        await refreshLogs().catch(() => {});
      });
    }
    dateDropdownMenu.appendChild(item);
  }
}

function updateTreeSelect(trees, selectedTreeId) {
  treeSelect.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = trees.length ? "Latest Tree" : "No Trees (Create One)";
  treeSelect.appendChild(allOption);

  for (const tree of trees) {
    const option = document.createElement("option");
    option.value = tree.id;
    option.textContent = `${tree.name} (${tree.count})`;
    treeSelect.appendChild(option);
  }
  treeSelect.value = selectedTreeId || "";
  if (deleteTreeBtn) {
    deleteTreeBtn.disabled = !selectedTreeId;
  }
}

function resolveFullRange(data) {
  let start = parseMinutes(data.start_time, 9 * 60);
  let end = parseMinutes(data.end_time, 18 * 60);
  if (end <= start) {
    end += 24 * 60;
  }
  const entries = Array.isArray(data.entries) ? data.entries : [];
  for (const entry of entries) {
    const m = parseMinutes(entry.time, -1);
    if (m < 0) continue;
    if (m < start) start = m - 10;
    if (m > end) end = m + 10;
  }
  return { start, end };
}

function setViewRange(start, end) {
  const fullStart = viewState.fullStart;
  const fullEnd = viewState.fullEnd;
  const fullSpan = Math.max(fullEnd - fullStart, 1);
  const requestedSpan = Math.max(end - start, viewState.minSpan);
  const span = clamp(requestedSpan, viewState.minSpan, fullSpan);
  const boundedStart = clamp(start, fullStart, fullEnd - span);
  viewState.viewStart = boundedStart;
  viewState.viewEnd = boundedStart + span;
  rangeLabel.textContent = `${formatHHMM(viewState.viewStart)} - ${formatHHMM(viewState.viewEnd)}`;
}

function syncViewport(fullStart, fullEnd, hardReset = false) {
  viewState.fullStart = fullStart;
  viewState.fullEnd = fullEnd;
  const fullSpan = Math.max(fullEnd - fullStart, 1);
  viewState.minSpan = clamp(Math.round(fullSpan / 18), 20, 120);
  if (!viewState.initialized || hardReset) {
    viewState.initialized = true;
    setViewRange(fullStart, fullEnd);
    return;
  }
  const currentSpan = Math.max(viewState.viewEnd - viewState.viewStart, viewState.minSpan);
  const center = (viewState.viewStart + viewState.viewEnd) / 2;
  const nextSpan = clamp(currentSpan, viewState.minSpan, fullSpan);
  setViewRange(center - nextSpan / 2, center + nextSpan / 2);
}

function zoomView(factor, anchorRatio) {
  const span = Math.max(viewState.viewEnd - viewState.viewStart, viewState.minSpan);
  const fullSpan = Math.max(viewState.fullEnd - viewState.fullStart, 1);
  const newSpan = clamp(span * factor, viewState.minSpan, fullSpan);
  const ratio = clamp(anchorRatio, 0, 1);
  const anchorMinute = viewState.viewStart + span * ratio;
  const start = anchorMinute - newSpan * ratio;
  setViewRange(start, start + newSpan);
}

function getCanvasMetrics(width, height) {
  const pad = clamp(width * 0.06, 24, 56);
  const metrics = {
    pad,
    trunkX: width * 0.5,
    trunkTop: pad + 18,
    trunkBottom: height - pad + 10,
  };
  return metrics;
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createSeededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
    return value / 0x100000000;
  };
}

function normalizeHex(hex) {
  if (typeof hex !== "string") return "9ba8bb";
  const value = hex.trim().replace(/^#/, "");
  if (value.length === 3) {
    return `${value[0]}${value[0]}${value[1]}${value[1]}${value[2]}${value[2]}`.toLowerCase();
  }
  if (value.length === 6) return value.toLowerCase();
  return "9ba8bb";
}

function colorWithAlpha(hex, alpha) {
  const safe = normalizeHex(hex);
  const r = Number.parseInt(safe.slice(0, 2), 16);
  const g = Number.parseInt(safe.slice(2, 4), 16);
  const b = Number.parseInt(safe.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${clamp(alpha, 0, 1)})`;
}

function pathRoundedRect(ctx, x, y, width, height, radius) {
  const safeRadius = Math.max(0, Math.min(radius, width / 2, height / 2));
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, width, height, safeRadius);
    return;
  }
  ctx.moveTo(x + safeRadius, y);
  ctx.lineTo(x + width - safeRadius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
  ctx.lineTo(x + width, y + height - safeRadius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
  ctx.lineTo(x + safeRadius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
  ctx.lineTo(x, y + safeRadius);
  ctx.quadraticCurveTo(x, y, x + safeRadius, y);
}

function shiftHex(hex, amount) {
  const safe = normalizeHex(hex);
  const channels = [0, 2, 4].map((offset) => Number.parseInt(safe.slice(offset, offset + 2), 16));
  const next = channels.map((channel) => {
    if (amount >= 0) {
      return clamp(Math.round(channel + (255 - channel) * amount), 0, 255);
    }
    return clamp(Math.round(channel * (1 + amount)), 0, 255);
  });
  return `#${next.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

const noisePatternCache = new Map();

function getNoisePattern(ctx, themeKey) {
  const cacheKey = `${themeKey}-grain`;
  const cached = noisePatternCache.get(cacheKey);
  if (cached) return cached;
  const offscreen = document.createElement("canvas");
  offscreen.width = 96;
  offscreen.height = 96;
  const offCtx = offscreen.getContext("2d");
  if (!offCtx) return null;
  const image = offCtx.createImageData(offscreen.width, offscreen.height);
  for (let i = 0; i < image.data.length; i += 4) {
    const value = Math.floor(Math.random() * 255);
    const alpha = Math.random() < 0.84 ? 0 : Math.floor(22 + Math.random() * 40);
    image.data[i] = value;
    image.data[i + 1] = value;
    image.data[i + 2] = value;
    image.data[i + 3] = alpha;
  }
  offCtx.putImageData(image, 0, 0);
  const pattern = ctx.createPattern(offscreen, "repeat");
  if (pattern) noisePatternCache.set(cacheKey, pattern);
  return pattern;
}

function drawCanvasBackground(ctx, width, height, pad, idleSeconds) {
  const isLight = uiState.theme === "light";
  const sky = ctx.createLinearGradient(0, 0, 0, height);
  sky.addColorStop(0, isLight ? "#f7f3e8" : "#141f2f");
  sky.addColorStop(0.5, isLight ? "#efe7d6" : "#1a2a3f");
  sky.addColorStop(1, isLight ? "#d8e6f2" : "#0f1623");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, width, height);

  const sunGlow = ctx.createRadialGradient(width * 0.78, pad + 8, 12, width * 0.78, pad + 8, 270);
  sunGlow.addColorStop(0, isLight ? "rgba(255, 186, 94, 0.28)" : "rgba(238, 171, 84, 0.34)");
  sunGlow.addColorStop(1, "rgba(255, 185, 96, 0)");
  ctx.fillStyle = sunGlow;
  ctx.fillRect(0, 0, width, height);

  const cloudAlpha = isLight ? 0.24 : 0.2;
  for (let i = 0; i < 3; i += 1) {
    const drift = Math.sin(idleSeconds * 0.16 + i * 1.8) * 12;
    const cloudX = width * (0.22 + i * 0.26) + drift;
    const cloudY = pad + 30 + i * 24;
    const cloud = ctx.createRadialGradient(cloudX, cloudY, 4, cloudX, cloudY, 90 + i * 12);
    cloud.addColorStop(0, isLight ? `rgba(255, 255, 255, ${cloudAlpha})` : `rgba(213, 229, 247, ${cloudAlpha})`);
    cloud.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = cloud;
    ctx.fillRect(0, 0, width, height);
  }

  const grain = getNoisePattern(ctx, isLight ? "light" : "dark");
  if (grain) {
    ctx.save();
    ctx.globalAlpha = isLight ? 0.09 : 0.07;
    ctx.fillStyle = grain;
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  }

  ctx.save();
  ctx.strokeStyle = isLight ? "rgba(86, 116, 148, 0.18)" : "rgba(187, 209, 235, 0.14)";
  ctx.lineWidth = 1;
  ctx.setLineDash([2.5, 6.5]);
  for (let i = 0; i <= 4; i += 1) {
    const y = pad + i * ((height - pad * 2) / 4);
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawTimeScale(ctx, width, height, pad) {
  const start = viewState.viewStart;
  const end = viewState.viewEnd;
  const total = Math.max(end - start, 1);
  const isLight = uiState.theme === "light";
  const plotHeight = height - pad * 2;
  const hourStep = 60;

  ctx.save();
  ctx.textBaseline = "middle";
  ctx.font = '600 9px "IBM Plex Mono", monospace';

  for (let minute = Math.ceil(start / hourStep) * hourStep; minute <= end; minute += hourStep) {
    const ratio = (minute - start) / total;
    const y = pad + ratio * plotHeight;
    ctx.strokeStyle = isLight ? "rgba(24, 58, 92, 0.12)" : "rgba(220, 235, 251, 0.12)";
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.textAlign = "left";
    ctx.fillStyle = isLight ? "rgba(41, 76, 111, 0.72)" : "rgba(205, 224, 244, 0.72)";
    ctx.fillText(formatHHMM(minute), pad + 4, y);
  }

  const isToday = !uiState.selectedDate || uiState.selectedDate === getTodayISO();
  if (isToday) {
    const now = new Date();
    const minuteNow = now.getHours() * 60 + now.getMinutes();
    const normalizedNow = normalizeMinute(minuteNow, viewState.fullStart, viewState.fullEnd);
    if (normalizedNow >= start && normalizedNow <= end) {
      const ratio = (normalizedNow - start) / total;
      const y = pad + ratio * plotHeight;
      ctx.strokeStyle = isLight ? "rgba(50, 104, 255, 0.65)" : "rgba(122, 182, 255, 0.72)";
      ctx.setLineDash([7, 3]);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(pad, y);
      ctx.lineTo(width - pad, y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  ctx.fillStyle = isLight ? "rgba(63, 95, 132, 0.84)" : "rgba(179, 202, 227, 0.78)";
  ctx.font = '600 11px "IBM Plex Mono", monospace';
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i += 1) {
    const ratio = i / 4;
    const minute = Math.round(start + ratio * total);
    const y = pad + ratio * plotHeight;
    ctx.fillText(formatHHMM(minute), width - pad - 8, y);
  }
  ctx.restore();
}

function drawMessage(ctx, text, width, height) {
  const isLight = uiState.theme === "light";
  const boxWidth = Math.min(width * 0.78, 620);
  const boxHeight = 50;
  const left = (width - boxWidth) / 2;
  const top = height / 2 - boxHeight / 2;
  ctx.fillStyle = isLight ? "rgba(244, 251, 255, 0.95)" : "rgba(8, 16, 26, 0.88)";
  ctx.strokeStyle = isLight ? "rgba(76, 112, 150, 0.44)" : "rgba(168, 198, 228, 0.34)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  pathRoundedRect(ctx, left, top, boxWidth, boxHeight, 12);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = isLight ? "rgba(31, 63, 98, 0.96)" : "rgba(224, 237, 251, 0.94)";
  ctx.font = '700 15px "Plus Jakarta Sans", sans-serif';
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, width / 2, height / 2);
}

function drawGuaranteedTree(ctx, scene) {
  const isLight = uiState.theme === "light";
  const { trunkX, trunkTop, trunkBottom } = scene.metrics;
  if (!Number.isFinite(trunkX) || !Number.isFinite(trunkTop) || !Number.isFinite(trunkBottom)) {
    return;
  }
  ctx.save();
  ctx.strokeStyle = isLight ? "rgba(108, 82, 58, 0.92)" : "rgba(177, 146, 118, 0.9)";
  ctx.lineWidth = 10;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(trunkX, trunkTop);
  ctx.lineTo(trunkX, trunkBottom);
  ctx.stroke();

  for (const fruit of scene.fruits || []) {
    const x = Number.isFinite(fruit.renderX) ? fruit.renderX : fruit.x;
    const y = Number.isFinite(fruit.renderY) ? fruit.renderY : fruit.y;
    const r = Math.max(6, Number.isFinite(fruit.renderR) ? fruit.renderR : fruit.r || 10);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(r)) {
      continue;
    }
    ctx.strokeStyle = isLight ? "rgba(117, 91, 67, 0.88)" : "rgba(148, 114, 87, 0.86)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(trunkX, y);
    ctx.lineTo(x, y);
    ctx.stroke();

    ctx.fillStyle = colorWithAlpha(fruit.color || "#7bb0ff", 0.9);
    ctx.beginPath();
    ctx.arc(x, y, r * 0.72, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function buildFruitLayout(entries, metrics, width) {
  const laneGap = clamp(width * 0.11, 60, 124);
  const laneLastY = new Map();
  let otherCount = 0;
  const minGap = clamp((metrics.trunkBottom - metrics.trunkTop) / 28, 18, 30);
  const start = viewState.viewStart;
  const end = viewState.viewEnd;
  const total = Math.max(end - start, 1);
  const output = [];

  const normalizedEntries = entries
    .map((entry, index) => {
      const minute = parseMinutes(entry.time, start);
      return {
        ...entry,
        index,
        normalized: normalizeMinute(minute, viewState.fullStart, viewState.fullEnd),
      };
    })
    .sort((a, b) => a.normalized - b.normalized || a.index - b.index);

  for (const item of normalizedEntries) {
    if (item.normalized < start || item.normalized > end) continue;
    if (uiState.trimmedCategories.has(item.category)) continue;

    let lane = MAIN_LANES[item.category];
    if (lane === undefined) {
      lane = OTHER_LANES[otherCount % OTHER_LANES.length];
      otherCount += 1;
    }

    const ratio = (item.normalized - start) / total;
    const rawY = metrics.trunkTop + ratio * (metrics.trunkBottom - metrics.trunkTop);
    const laneKey = String(lane);
    const previousY = laneLastY.get(laneKey);
    const y = previousY ? Math.max(rawY, previousY + minGap) : rawY;
    const boundedY = clamp(y, metrics.trunkTop + 8, metrics.trunkBottom - 10);
    laneLastY.set(laneKey, boundedY);

    const wiggle = Math.sin((boundedY + item.index * 13) * 0.026) * 11;
    const laneOffset = lane * laneGap;
    const centerLaneBias =
      lane === 0 ? (item.index % 2 === 0 ? -1 : 1) * clamp(laneGap * 0.36, 22, 44) : 0;
    const x = clamp(
      metrics.trunkX + laneOffset + centerLaneBias + wiggle,
      metrics.pad + 18,
      width - metrics.pad - 28,
    );

    const { summary, meta } = parseSummaryMeta(item.summary);
    const eventData = item && typeof item.event_data === "object" && item.event_data
      ? item.event_data
      : null;
    const rawClickCount = Number(
      eventData?.click_count ?? item.click_count ?? item.eventClickCount ?? NaN,
    );
    const hasClickData = Number.isFinite(rawClickCount) && rawClickCount >= 0;
    const clickCount = hasClickData ? rawClickCount : 0;
    const radius = hasClickData
      ? clamp(8 + Math.log2(clickCount + 1) * 3, 8, 20)
      : 11;
    const topApp = String(
      eventData?.top_app ?? item.top_app ?? item.event_top_app ?? "",
    ).trim();
    const activeSeconds = Number(
      eventData?.active_seconds ?? item.active_seconds ?? item.event_active_seconds ?? 0,
    );
    const source = normalizeSourceLabel(item.source || meta.source);
    const confidence = Number(item.confidence);
    const resolvedConfidence = Number.isFinite(confidence) && confidence > 0
      ? clamp(confidence, 0, 1)
      : extractConfidenceFromMeta(meta);

    output.push({
      x,
      y: boundedY,
      r: radius,
      lane,
      category: item.category,
      color: getCategoryColor(item.category),
      time: item.time,
      summary,
      clickCount,
      topApp,
      activeSeconds: Number.isFinite(activeSeconds) ? Math.max(activeSeconds, 0) : 0,
      source,
      confidence: resolvedConfidence,
      text: `${item.time} [${item.category}] ${summary}`,
      tooltip: {
        time: item.time,
        category: item.category,
        summary,
        clickCount,
        topApp,
        activeSeconds: Number.isFinite(activeSeconds) ? Math.max(activeSeconds, 0) : 0,
        source,
        confidence: resolvedConfidence,
        color: getCategoryColor(item.category),
      },
      renderX: x,
      renderY: boundedY,
      renderR: radius,
    });
  }
  return output;
}

function easeOutCubic(value) {
  return 1 - (1 - value) ** 3;
}

function easeOutBack(value) {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * (value - 1) ** 3 + c1 * (value - 1) ** 2;
}

function buildTreeFingerprint(data, entries) {
  const entryKey = entries
    .map((entry) => `${entry.time}|${entry.category}|${entry.summary}|${entry.tree_id || ""}`)
    .join("~");
  return [
    data.date || "",
    uiState.selectedTreeId || "",
    entryKey,
  ].join("::");
}

function buildTreeScene(data, width, height, metrics) {
  const entries = Array.isArray(data.entries) ? data.entries : [];
  const trees = Array.isArray(data.trees) ? data.trees : [];
  const fingerprint = buildTreeFingerprint(data, entries);

  if (!trees.length) {
    return {
      kind: "message",
      message: "No Trees. Click New Tree to create one.",
      width,
      height,
      metrics,
      fingerprint: `${fingerprint}::no-tree`,
    };
  }
  if (!entries.length) {
    return {
      kind: "message",
      message: "Selected tree has no fruits yet. Use Manual Snapshot.",
      width,
      height,
      metrics,
      fingerprint: `${fingerprint}::empty`,
    };
  }

  const layout = buildFruitLayout(entries, metrics, width);
  if (!layout.length) {
    return {
      kind: "message",
      message: "No fruits in this range. Pan/zoom or untrim branches.",
      width,
      height,
      metrics,
      fingerprint: `${fingerprint}::out-of-range`,
    };
  }

  const seed = hashString(fingerprint);
  const random = createSeededRandom(seed);
  const count = layout.length;
  const indexDenominator = Math.max(count - 1, 1);
  const trunkStrokes = Array.from({ length: 5 }, (_, index) => ({
    offset: (random() - 0.5) * (6 + index * 0.75),
    width: 9.8 - index * 1.45 + random() * 0.8,
    alpha: 0.22 + random() * 0.28,
    wobble: 1.4 + random() * 2.1,
    phase: random() * Math.PI * 2,
  }));
  const fruitsWithMotion = layout.map((fruit, index) => {
    const ratio = index / indexDenominator;
    return {
      ...fruit,
      branchDelay: 0.26 + ratio * 0.44 + random() * 0.06,
      bloomDelay: 0.57 + ratio * 0.4 + random() * 0.08,
      swayPhase: random() * Math.PI * 2,
      swayAmp: 0.7 + random() * 1.25,
      stemCurve: (random() - 0.5) * 20,
      trunkOffset: (random() - 0.5) * 6,
      leafAngle: -0.8 + random() * 1.6,
      pulsePhase: random() * Math.PI * 2,
    };
  });
  const particles = Array.from({ length: clamp(Math.round(count * 0.35) + 6, 8, 20) }, () => ({
    x: random(),
    y: random(),
    speed: 0.2 + random() * 0.4,
    radius: 0.7 + random() * 1.4,
    phase: random() * Math.PI * 2,
  }));

  return {
    kind: "tree",
    width,
    height,
    metrics,
    fruits: fruitsWithMotion,
    trunkStrokes,
    particles,
    fingerprint: `${fingerprint}::tree`,
  };
}

function fillRibbonPath(ctx, leftPoints, rightPoints) {
  if (!leftPoints.length || !rightPoints.length) return;
  ctx.beginPath();
  ctx.moveTo(leftPoints[0].x, leftPoints[0].y);
  for (let i = 1; i < leftPoints.length; i += 1) {
    ctx.lineTo(leftPoints[i].x, leftPoints[i].y);
  }
  for (let i = rightPoints.length - 1; i >= 0; i -= 1) {
    ctx.lineTo(rightPoints[i].x, rightPoints[i].y);
  }
  ctx.closePath();
  ctx.fill();
}

function cubicBezierPoint(t, p0, p1, p2, p3) {
  const inv = 1 - t;
  const inv2 = inv * inv;
  const inv3 = inv2 * inv;
  const t2 = t * t;
  const t3 = t2 * t;
  return {
    x: inv3 * p0.x + 3 * inv2 * t * p1.x + 3 * inv * t2 * p2.x + t3 * p3.x,
    y: inv3 * p0.y + 3 * inv2 * t * p1.y + 3 * inv * t2 * p2.y + t3 * p3.y,
  };
}

function cubicBezierTangent(t, p0, p1, p2, p3) {
  const inv = 1 - t;
  const t2 = t * t;
  const inv2 = inv * inv;
  return {
    x: 3 * inv2 * (p1.x - p0.x) + 6 * inv * t * (p2.x - p1.x) + 3 * t2 * (p3.x - p2.x),
    y: 3 * inv2 * (p1.y - p0.y) + 6 * inv * t * (p2.y - p1.y) + 3 * t2 * (p3.y - p2.y),
  };
}

function drawPainterlyTrunk(ctx, scene, introProgress, idleSeconds) {
  const { trunkX, trunkTop, trunkBottom } = scene.metrics;
  const grow = treeAnimationState.reducedMotion
    ? 1
    : easeOutCubic(clamp(introProgress / 0.35, 0, 1));
  const topVisible = trunkBottom - (trunkBottom - trunkTop) * grow;
  const barkDark = uiState.theme === "light" ? "#6f533f" : "#6a4e3a";
  const barkMid = uiState.theme === "light" ? "#8a6850" : "#87664e";
  const barkLight = uiState.theme === "light" ? "#ac8a70" : "#a5856b";
  const steps = 32;
  const left = [];
  const right = [];
  const sway = Math.sin(idleSeconds * 0.45) * 0.8;
  const trunkPhase = scene.trunkStrokes[0]?.phase || 0;

  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const y = trunkBottom - (trunkBottom - topVisible) * t;
    const taper = 1 - t * 0.72;
    const centerWave = Math.sin(t * 8.2 + idleSeconds * 0.82 + trunkPhase) * 1.25 * taper;
    const grainWave = Math.sin(t * 28 + trunkPhase * 1.7) * 0.45;
    const centerX = trunkX + centerWave + sway * (1 - t);
    const halfWidth = 5.6 + (1 - t) * 6.7 + grainWave;
    left.push({ x: centerX - halfWidth, y });
    right.push({ x: centerX + halfWidth, y });
  }

  const barkGrad = ctx.createLinearGradient(trunkX - 16, 0, trunkX + 16, 0);
  barkGrad.addColorStop(0, barkDark);
  barkGrad.addColorStop(0.55, barkMid);
  barkGrad.addColorStop(1, barkLight);
  ctx.fillStyle = barkGrad;
  fillRibbonPath(ctx, left, right);

  ctx.save();
  try {
    ctx.beginPath();
    ctx.moveTo(left[0].x, left[0].y);
    for (let i = 1; i < left.length; i += 1) {
      ctx.lineTo(left[i].x, left[i].y);
    }
    for (let i = right.length - 1; i >= 0; i -= 1) {
      ctx.lineTo(right[i].x, right[i].y);
    }
    ctx.closePath();
    ctx.clip();

    for (const stroke of scene.trunkStrokes) {
      const xBase = trunkX + stroke.offset * 1.25;
      ctx.beginPath();
      for (let i = 0; i <= steps; i += 1) {
        const t = i / steps;
        const y = trunkBottom - (trunkBottom - topVisible) * t;
        const wave = Math.sin(t * 12 + idleSeconds * 1.18 + stroke.phase) * stroke.wobble * 0.42;
        const x = xBase + wave;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#614734" : "#4f3928", 0.18 + stroke.alpha * 0.2);
      ctx.lineWidth = 0.9 + stroke.width * 0.05;
      ctx.lineCap = "round";
      ctx.stroke();
    }

    for (let i = 0; i < 3; i += 1) {
      const t = 0.22 + i * 0.23;
      const y = trunkBottom - (trunkBottom - topVisible) * t;
      const knotX = trunkX + Math.sin(t * 14 + trunkPhase + i) * 3.3;
      ctx.fillStyle = colorWithAlpha(uiState.theme === "light" ? "#6d4f39" : "#5a412f", 0.22);
      ctx.beginPath();
      ctx.ellipse(knotX, y, 1.8, 1.1, 0.2, 0, Math.PI * 2);
      ctx.fill();
    }
  } finally {
    ctx.restore();
  }

  ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#5f4634" : "#583f2d", 0.45);
  ctx.lineWidth = 0.9;
  ctx.beginPath();
  for (let i = 0; i < left.length; i += 1) {
    const point = left[i];
    if (i === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  }
  ctx.stroke();

  ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#c1a386" : "#b59374", 0.34);
  ctx.beginPath();
  for (let i = 0; i < right.length; i += 1) {
    const point = right[i];
    if (i === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  }
  ctx.stroke();
}

function resolveFruitPose(fruit, introProgress, idleSeconds) {
  const bloomProgress = treeAnimationState.reducedMotion
    ? 1
    : clamp((introProgress - fruit.bloomDelay) / 0.25, 0, 1);
  const bloom = treeAnimationState.reducedMotion ? 1 : clamp(easeOutBack(bloomProgress), 0, 1.18);
  const sway = treeAnimationState.reducedMotion
    ? 0
    : Math.sin(idleSeconds * 1.08 + fruit.swayPhase) * fruit.swayAmp;
  const bob = treeAnimationState.reducedMotion
    ? 0
    : Math.cos(idleSeconds * 1.52 + fruit.swayPhase * 0.8) * (0.8 + fruit.swayAmp * 0.5);
  const radius = fruit.r * clamp(0.48 + bloom * 0.54, 0.38, 1.28);
  return {
    x: fruit.x + sway,
    y: fruit.y + bob,
    radius,
    bloom,
    opacity: clamp(0.14 + bloom * 0.86, 0, 1),
  };
}

function drawPainterlyBranch(ctx, trunkX, fruit, pose, introProgress, idleSeconds) {
  const branchProgress = treeAnimationState.reducedMotion
    ? 1
    : easeOutCubic(clamp((introProgress - fruit.branchDelay) / 0.42, 0, 1));
  if (branchProgress <= 0.001) return;

  const startX = trunkX + fruit.trunkOffset;
  const startY = fruit.y + Math.sin(idleSeconds + fruit.swayPhase) * 1.3;
  const tipX = startX + (pose.x - startX) * branchProgress;
  const tipY = startY + (pose.y - startY) * branchProgress;
  const laneDirection = fruit.lane < 0 ? -1 : 1;
  const bend = laneDirection * (12 + Math.abs(fruit.lane) * 4.2) + fruit.stemCurve;
  const cp1X = startX + (tipX - startX) * 0.35 + bend * 0.5;
  const cp1Y = startY + (tipY - startY) * 0.12 - bend * 0.38;
  const cp2X = startX + (tipX - startX) * 0.74 + bend * 0.28;
  const cp2Y = startY + (tipY - startY) * 0.9 + bend * 0.06;
  const p0 = { x: startX, y: startY };
  const p1 = { x: cp1X, y: cp1Y };
  const p2 = { x: cp2X, y: cp2Y };
  const p3 = { x: tipX, y: tipY };
  const barkDark = uiState.theme === "light" ? "#674d39" : "#604634";
  const barkMid = uiState.theme === "light" ? "#8a6950" : "#896850";
  const barkLight = uiState.theme === "light" ? "#b09275" : "#ab8a6f";
  const widthBase = (Math.abs(fruit.lane) <= 1 ? 4.6 : 3.6) * (0.55 + branchProgress * 0.45);
  const widthTip = 0.7 + branchProgress * 0.35;
  const steps = 15;
  const left = [];
  const right = [];

  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const point = cubicBezierPoint(t, p0, p1, p2, p3);
    const tangent = cubicBezierTangent(t, p0, p1, p2, p3);
    const len = Math.max(Math.hypot(tangent.x, tangent.y), 0.001);
    const nx = -tangent.y / len;
    const ny = tangent.x / len;
    const width = widthBase + (widthTip - widthBase) * t;
    const jitter = Math.sin(i * 1.9 + fruit.pulsePhase + idleSeconds * 1.4) * 0.16;
    left.push({ x: point.x + nx * (width + jitter), y: point.y + ny * (width + jitter) });
    right.push({ x: point.x - nx * (width - jitter), y: point.y - ny * (width - jitter) });
  }

  const shadowLeft = left.map((point) => ({ x: point.x + 0.6, y: point.y + 0.9 }));
  const shadowRight = right.map((point) => ({ x: point.x + 0.6, y: point.y + 0.9 }));
  ctx.fillStyle = colorWithAlpha(uiState.theme === "light" ? "#4f3a2a" : "#2e231a", 0.16);
  fillRibbonPath(ctx, shadowLeft, shadowRight);

  const branchGrad = ctx.createLinearGradient(startX, startY, tipX, tipY);
  branchGrad.addColorStop(0, barkDark);
  branchGrad.addColorStop(0.52, barkMid);
  branchGrad.addColorStop(1, barkLight);
  ctx.fillStyle = branchGrad;
  fillRibbonPath(ctx, left, right);

  ctx.beginPath();
  ctx.moveTo(p0.x, p0.y);
  ctx.bezierCurveTo(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y);
  ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#5d4330" : "#4c3728", 0.24);
  ctx.lineWidth = 0.9;
  ctx.lineCap = "round";
  ctx.stroke();
}

function drawAmbientPollen(ctx, scene, idleSeconds) {
  const { pad } = scene.metrics;
  const width = scene.width;
  const height = scene.height;
  for (const particle of scene.particles) {
    const x = pad + ((particle.x + idleSeconds * particle.speed * 0.014) % 1) * (width - pad * 2);
    const wave = Math.sin(idleSeconds * (0.7 + particle.speed) + particle.phase);
    const y = pad + particle.y * (height - pad * 2) + wave * 10;
    const alpha = (uiState.theme === "light" ? 0.2 : 0.24) + wave * 0.03;
    ctx.fillStyle = uiState.theme === "light"
      ? `rgba(120, 97, 62, ${clamp(alpha, 0.08, 0.3)})`
      : `rgba(220, 199, 158, ${clamp(alpha, 0.08, 0.32)})`;
    ctx.beginPath();
    ctx.arc(x, y, particle.radius, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawPainterlyFruit(ctx, fruit, pose, selected, idleSeconds) {
  if (pose.bloom <= 0.01) return;
  const glowRadius = pose.radius * 2.8;
  const halo = ctx.createRadialGradient(pose.x, pose.y, pose.radius * 0.2, pose.x, pose.y, glowRadius);
  halo.addColorStop(0, colorWithAlpha(fruit.color, 0.35 * pose.opacity));
  halo.addColorStop(1, colorWithAlpha(fruit.color, 0));
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(pose.x, pose.y, glowRadius, 0, Math.PI * 2);
  ctx.fill();

  const body = ctx.createRadialGradient(
    pose.x - pose.radius * 0.35,
    pose.y - pose.radius * 0.44,
    pose.radius * 0.16,
    pose.x,
    pose.y,
    pose.radius * 1.18,
  );
  body.addColorStop(0, colorWithAlpha(shiftHex(fruit.color, 0.38), pose.opacity));
  body.addColorStop(0.6, colorWithAlpha(fruit.color, pose.opacity));
  body.addColorStop(1, colorWithAlpha(shiftHex(fruit.color, -0.36), pose.opacity));
  ctx.fillStyle = body;
  ctx.beginPath();
  ctx.arc(pose.x, pose.y, pose.radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = colorWithAlpha(shiftHex(fruit.color, -0.42), 0.46 * pose.opacity);
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(pose.x, pose.y, pose.radius * 0.96, 0, Math.PI * 2);
  ctx.stroke();

  const shimmer = 0.18 + Math.sin(idleSeconds * 2 + fruit.pulsePhase) * 0.08;
  ctx.fillStyle = colorWithAlpha("#ffffff", clamp(shimmer, 0.08, 0.3) * pose.opacity);
  ctx.beginPath();
  ctx.ellipse(
    pose.x - pose.radius * 0.28,
    pose.y - pose.radius * 0.36,
    pose.radius * 0.32,
    pose.radius * 0.22,
    -0.6,
    0,
    Math.PI * 2,
  );
  ctx.fill();

  ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#6f543b" : "#89705a", 0.65 * pose.opacity);
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(pose.x - pose.radius * 0.15, pose.y - pose.radius * 0.78);
  ctx.quadraticCurveTo(
    pose.x + pose.radius * 0.06,
    pose.y - pose.radius * 1.35,
    pose.x + pose.radius * 0.34,
    pose.y - pose.radius * 1.24,
  );
  ctx.stroke();

  ctx.fillStyle = colorWithAlpha(uiState.theme === "light" ? "#6fb36d" : "#78c082", 0.78 * pose.opacity);
  ctx.beginPath();
  ctx.ellipse(
    pose.x + pose.radius * 0.62,
    pose.y - pose.radius * 1.04,
    pose.radius * 0.48,
    pose.radius * 0.22,
    fruit.leafAngle,
    0,
    Math.PI * 2,
  );
  ctx.fill();

  if (selected) {
    ctx.strokeStyle = colorWithAlpha(uiState.theme === "light" ? "#f8fbff" : "#f2f8ff", 0.92);
    ctx.lineWidth = 1.7;
    ctx.beginPath();
    ctx.arc(pose.x, pose.y, pose.radius + 3.7, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawFruitSideLabels(ctx, fruitsToRender) {
  if (!Array.isArray(fruitsToRender) || !fruitsToRender.length) return;
  const isLight = uiState.theme === "light";
  const sorted = [...fruitsToRender]
    .filter((fruit) => Number.isFinite(fruit.renderY ?? fruit.y))
    .sort((a, b) => (a.renderY ?? a.y) - (b.renderY ?? b.y));
  const lastLabelYBySide = {
    left: Number.NEGATIVE_INFINITY,
    right: Number.NEGATIVE_INFINITY,
  };

  ctx.save();
  ctx.textBaseline = "middle";
  ctx.font = '600 9px "IBM Plex Mono", monospace';
  for (const fruit of sorted) {
    const timeText = String(fruit.time || "").trim();
    if (!timeText) continue;
    const y = fruit.renderY ?? fruit.y;
    const r = Math.max(6, fruit.renderR ?? fruit.r ?? 10);
    const side = fruit.lane < 0 ? "left" : "right";
    if (Math.abs(y - lastLabelYBySide[side]) < 25) {
      continue;
    }
    lastLabelYBySide[side] = y;
    const x = fruit.renderX ?? fruit.x;
    const anchorX = side === "left" ? x - r - 8 : x + r + 8;

    ctx.textAlign = side === "left" ? "right" : "left";
    ctx.fillStyle = isLight ? "rgba(42, 75, 108, 0.74)" : "rgba(211, 227, 244, 0.74)";
    ctx.fillText(timeText, anchorX, y - 5);
    ctx.font = '700 8px "IBM Plex Mono", monospace';
    ctx.fillStyle = colorWithAlpha(fruit.color || "#8fb2d9", isLight ? 0.82 : 0.74);
    ctx.fillText(String(fruit.category || ""), anchorX, y + 6);
    ctx.font = '600 9px "IBM Plex Mono", monospace';
  }
  ctx.restore();
}

function renderTreeFrame(now = performance.now()) {
  if (!activeScene) return;
  const rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return;

  if (
    Math.abs(rect.width - activeScene.width) > 0.5
    || Math.abs(rect.height - activeScene.height) > 0.5
  ) {
    if (lastTreeData) drawTree(lastTreeData);
    return;
  }

  const ratio = window.devicePixelRatio || 1;
  const targetWidth = Math.max(1, Math.floor(rect.width * ratio));
  const targetHeight = Math.max(1, Math.floor(rect.height * ratio));
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  if (typeof ctx.reset === "function") {
    ctx.reset();
  } else {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, rect.width, rect.height);

  const idleSeconds = now * 0.001;
  try {
    drawCanvasBackground(ctx, activeScene.width, activeScene.height, activeScene.metrics.pad, idleSeconds);
    drawTimeScale(ctx, activeScene.width, activeScene.height, activeScene.metrics.pad);

    if (activeScene.kind !== "tree") {
      fruits = [];
      selectedFruitIndex = -1;
      drawMessage(ctx, activeScene.message, activeScene.width, activeScene.height);
      return;
    }

    fruits = Array.isArray(activeScene.fruits) ? activeScene.fruits : [];
    if (selectedFruitIndex >= fruits.length) {
      selectedFruitIndex = fruits.length - 1;
    }
    for (let i = 0; i < fruits.length; i += 1) {
      const fruit = fruits[i];
      fruit.renderX = fruit.x;
      fruit.renderY = fruit.y;
      fruit.renderR = Math.max(8, fruit.r || 10);
    }

    const introProgress = treeAnimationState.reducedMotion
      ? 1
      : clamp((now - treeAnimationState.introStartMs) / 2200, 0, 1);
    try {
      drawPainterlyTrunk(ctx, activeScene, introProgress, idleSeconds);
      drawAmbientPollen(ctx, activeScene, idleSeconds);

      for (let i = 0; i < fruits.length; i += 1) {
        const fruit = fruits[i];
        const pose = resolveFruitPose(fruit, introProgress, idleSeconds);
        fruit.renderX = pose.x;
        fruit.renderY = pose.y;
        fruit.renderR = Math.max(pose.radius, 8);
        fruit.renderOpacity = pose.opacity;
        fruit.renderBloom = pose.bloom;
        drawPainterlyBranch(ctx, activeScene.metrics.trunkX, fruit, pose, introProgress, idleSeconds);
      }

      for (let i = 0; i < fruits.length; i += 1) {
        const fruit = fruits[i];
        const pose = {
          x: fruit.renderX ?? fruit.x,
          y: fruit.renderY ?? fruit.y,
          radius: fruit.renderR ?? fruit.r,
          bloom: fruit.renderBloom ?? 1,
          opacity: fruit.renderOpacity ?? 1,
        };
        drawPainterlyFruit(ctx, fruit, pose, i === selectedFruitIndex, idleSeconds);
      }
      renderErrorFingerprint = "";
    } catch (error) {
      const fp = `${activeScene.fingerprint}:${String(error)}`;
      if (fp !== renderErrorFingerprint) {
        renderErrorFingerprint = fp;
        pushLogLine(`render fallback: ${error instanceof Error ? error.message : String(error)}`);
        console.error("tree render failed, fallback active", error);
      }
    }
  } catch (error) {
    const fp = `frame:${activeScene.fingerprint}:${String(error)}`;
    if (fp !== renderErrorFingerprint) {
      renderErrorFingerprint = fp;
      pushLogLine(`render frame guarded: ${error instanceof Error ? error.message : String(error)}`);
      console.error("tree frame failed, guarded fallback active", error);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(ratio, ratio);
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.fillStyle = uiState.theme === "light" ? "#f3f1e9" : "#101b2a";
    ctx.fillRect(0, 0, activeScene.width, activeScene.height);
    if (activeScene.kind === "tree") {
      fruits = activeScene.fruits || [];
      drawGuaranteedTree(ctx, activeScene);
    } else {
      fruits = [];
      drawMessage(ctx, activeScene.message || "Render error", activeScene.width, activeScene.height);
    }
  }
}

function startTreeAnimationLoop() {
  if (treeAnimationState.reducedMotion || treeAnimationState.rafId) return;
  const frameGap = 1000 / 60;
  const tick = (now) => {
    treeAnimationState.rafId = 0;
    if (activeScene?.kind !== "tree" || treeAnimationState.reducedMotion) return;
    if (!document.hidden && now - treeAnimationState.lastFrameMs >= frameGap) {
      renderTreeFrame(now);
      treeAnimationState.lastFrameMs = now;
    }
    treeAnimationState.rafId = requestAnimationFrame(tick);
  };
  treeAnimationState.rafId = requestAnimationFrame(tick);
}

function stopTreeAnimationLoop() {
  if (treeAnimationState.rafId) {
    cancelAnimationFrame(treeAnimationState.rafId);
  }
  treeAnimationState.rafId = 0;
  treeAnimationState.lastFrameMs = 0;
}

function drawTree(data) {
  lastTreeData = data;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width || canvas.clientWidth || 0;
  const height = rect.height || canvas.clientHeight || 0;
  if (!width || !height) return;
  const metrics = getCanvasMetrics(width, height);
  lastCanvasMetrics = metrics;
  activeScene = buildTreeScene(data, width, height, metrics);
  canvas.style.cursor = "grab";
  if (activeScene.kind === "tree") {
    setCanvasRenderMode("tree");
    setTreeEmptyOverlay("");
  } else {
    setCanvasRenderMode("empty");
    setTreeEmptyOverlay(activeScene.message || "No data");
    stopTreeAnimationLoop();
    fruits = [];
    selectedFruitIndex = -1;
    hideTooltip();
    return;
  }
  if (
    activeScene.kind === "message"
    && Array.isArray(data.entries)
    && data.entries.length > 0
  ) {
    const fullRange = resolveFullRange(data);
    viewState.userAdjusted = false;
    syncViewport(fullRange.start, fullRange.end, true);
    activeScene = buildTreeScene(data, width, height, metrics);
  }

  if (activeScene.fingerprint !== treeAnimationState.sceneFingerprint) {
    treeAnimationState.sceneFingerprint = activeScene.fingerprint;
    treeAnimationState.introStartMs = performance.now();
    treeAnimationState.primedScene = "";
  }
  renderTreeFrame(performance.now());
  if (uiState.activeView === "tree" && activeScene.kind === "tree" && !treeAnimationState.reducedMotion) {
    startTreeAnimationLoop();
  } else {
    stopTreeAnimationLoop();
  }
}

function findFruitAtPoint(x, y) {
  for (let i = 0; i < fruits.length; i += 1) {
    const fruit = fruits[i];
    const px = fruit.renderX ?? fruit.x;
    const py = fruit.renderY ?? fruit.y;
    const pr = fruit.renderR ?? fruit.r;
    const dx = x - px;
    const dy = y - py;
    if (dx * dx + dy * dy <= pr * pr) return i;
  }
  return -1;
}

function showTooltip(pageX, pageY, data) {
  if (!tooltip) return;
  tooltip.innerHTML = buildTooltipHtml(data);
  tooltip.classList.remove("hidden");
  const rect = tooltip.getBoundingClientRect();
  const left = clamp(pageX + 14, 8, window.innerWidth - rect.width - 8);
  const top = clamp(pageY + 14, 8, window.innerHeight - rect.height - 8);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hideTooltip() {
  tooltip.classList.add("hidden");
}

function getPointerRatioOnTree(event) {
  const rect = canvas.getBoundingClientRect();
  if (!lastCanvasMetrics) return 0.5;
  const y = event.clientY - rect.top;
  const span = Math.max(lastCanvasMetrics.trunkBottom - lastCanvasMetrics.trunkTop, 1);
  return clamp((y - lastCanvasMetrics.trunkTop) / span, 0, 1);
}

canvas.addEventListener("mousemove", (event) => {
  if (isPanning) {
    if (!lastCanvasMetrics) return;
    const spanPx = Math.max(lastCanvasMetrics.trunkBottom - lastCanvasMetrics.trunkTop, 1);
    const spanMin = viewState.viewEnd - viewState.viewStart;
    const deltaY = event.clientY - panStartY;
    const deltaMin = (deltaY / spanPx) * spanMin;
    setViewRange(panAnchorStart + deltaMin, panAnchorEnd + deltaMin);
    if (lastTreeData) drawTree(lastTreeData);
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const localX = event.clientX - rect.left;
  const localY = event.clientY - rect.top;

  const index = findFruitAtPoint(localX, localY);
  if (index < 0) {
    hideTooltip();
    return;
  }
  if (selectedFruitIndex !== index) {
    selectedFruitIndex = index;
    if (lastTreeData) drawTree(lastTreeData);
  }
  showTooltip(event.clientX, event.clientY, fruits[index].tooltip || fruits[index]);
});

canvas.addEventListener("mousedown", (event) => {
  if (event.button !== 0) return;
  isPanning = true;
  viewState.userAdjusted = true;
  panStartY = event.clientY;
  panAnchorStart = viewState.viewStart;
  panAnchorEnd = viewState.viewEnd;
  canvas.classList.add("panning");
  hideTooltip();
});

window.addEventListener("mouseup", () => {
  if (!isPanning) return;
  isPanning = false;
  canvas.classList.remove("panning");
});

canvas.addEventListener(
  "wheel",
  (event) => {
    if (!lastTreeData) return;
    event.preventDefault();
    viewState.userAdjusted = true;
    const factor = event.deltaY < 0 ? 0.86 : 1.16;
    zoomView(factor, getPointerRatioOnTree(event));
    drawTree(lastTreeData);
    hideTooltip();
  },
  { passive: false },
);

canvas.addEventListener("mouseleave", hideTooltip);
canvas.addEventListener("blur", hideTooltip);

canvas.addEventListener("keydown", (event) => {
  if (event.key === "+" || event.key === "=") {
    event.preventDefault();
    viewState.userAdjusted = true;
    zoomView(0.86, 0.5);
    if (lastTreeData) drawTree(lastTreeData);
    return;
  }
  if (event.key === "-" || event.key === "_") {
    event.preventDefault();
    viewState.userAdjusted = true;
    zoomView(1.16, 0.5);
    if (lastTreeData) drawTree(lastTreeData);
    return;
  }
  if (event.key === "Escape") {
    hideTooltip();
    return;
  }
  if (!fruits.length) return;

  if (["ArrowDown", "ArrowRight"].includes(event.key)) {
    event.preventDefault();
    selectedFruitIndex = (selectedFruitIndex + 1 + fruits.length) % fruits.length;
  } else if (["ArrowUp", "ArrowLeft"].includes(event.key)) {
    event.preventDefault();
    selectedFruitIndex = (selectedFruitIndex - 1 + fruits.length) % fruits.length;
  } else {
    return;
  }
  const fruit = fruits[selectedFruitIndex];
  if (lastTreeData) drawTree(lastTreeData);
  const rect = canvas.getBoundingClientRect();
  const px = fruit.renderX ?? fruit.x;
  const py = fruit.renderY ?? fruit.y;
  showTooltip(rect.left + px, rect.top + py, fruit.tooltip || fruit);
});

zoomInBtn?.addEventListener("click", () => {
  if (!lastTreeData) return;
  viewState.userAdjusted = true;
  zoomView(0.82, 0.5);
  drawTree(lastTreeData);
  hideTooltip();
});

zoomOutBtn?.addEventListener("click", () => {
  if (!lastTreeData) return;
  viewState.userAdjusted = true;
  zoomView(1.22, 0.5);
  drawTree(lastTreeData);
  hideTooltip();
});

resetViewBtn?.addEventListener("click", () => {
  viewState.userAdjusted = false;
  syncViewport(viewState.fullStart, viewState.fullEnd, true);
  if (lastTreeData) drawTree(lastTreeData);
  hideTooltip();
});

async function api(path, method = "GET", body = null) {
  const options = { method, headers: {} };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const raw = await response.text();
  let payload = {};
  try {
    payload = raw ? JSON.parse(raw) : {};
  } catch (error) {
    payload = { ok: response.ok, message: raw || "invalid response" };
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.message || `HTTP ${response.status}`);
  }
  return Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
}

function pushLogLine(text) {
  const content = logsPanel.textContent.trim();
  logsPanel.textContent = content ? `${content}\n${text}` : text;
  logsPanel.scrollTop = logsPanel.scrollHeight;
}

function nextSummaryRequestId() {
  summaryViewState.activeRequestId += 1;
  return summaryViewState.activeRequestId;
}

function isSummaryRequestActive(requestId) {
  return requestId === summaryViewState.activeRequestId;
}

function safeJsonParse(raw, fallback = {}) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function closeSummaryStreamConnection() {
  const connection = summaryViewState.streamConnection;
  if (connection) {
    try {
      connection.close();
    } catch (error) {
    }
  }
  summaryViewState.streamConnection = null;
}

function resolveSummaryDate() {
  return String(uiState.selectedDate || getTodayISO()).trim() || getTodayISO();
}

function setSummaryButtonsBusy(busy) {
  if (!summaryGenerateBtn || !summaryRegenerateBtn || !summaryCopyBtn) return;
  summaryGenerateBtn.disabled = busy;
  summaryRegenerateBtn.disabled = busy;
  summaryCopyBtn.disabled = busy || !summaryViewState.payload;
}

function setSummaryMeta(payload = null, dateText = "", options = {}) {
  if (!summaryViewMeta) return;
  const bits = [];
  const date = dateText || payload?.date || resolveSummaryDate();
  const generatedAt = String(payload?.generated_at || "").trim();
  if (date) bits.push(`日期 ${date}`);
  if (generatedAt) bits.push(`生成于 ${generatedAt}`);
  if (options.cached) bits.push("缓存命中");
  summaryViewMeta.textContent = bits.join(" · ");
}

function resetSummaryRenderBlocks() {
  summaryPhaseIndicator?.classList.add("hidden");
  if (summaryPhaseIndicator) summaryPhaseIndicator.textContent = "";
  summaryAiBlock?.classList.add("hidden");
  if (summaryAiText) summaryAiText.textContent = "";
  summaryAiCursor?.classList.add("hidden");
  summaryHighlightsBlock?.classList.add("hidden");
  if (summaryHighlightsList) summaryHighlightsList.innerHTML = "";
  summaryTimelineBlock?.classList.add("hidden");
  if (summaryTimelineList) summaryTimelineList.innerHTML = "";
}

function setSummaryNotice(kind = "", message = "") {
  if (!summaryViewEmpty || !summaryViewError || !summaryStreamArea) return;
  summaryViewEmpty.classList.add("hidden");
  summaryViewError.classList.add("hidden");
  summaryStreamArea.classList.remove("hidden");
  if (kind === "empty") {
    summaryStreamArea.classList.add("hidden");
    summaryViewEmpty.textContent = message || "当天无活动记录";
    summaryViewEmpty.classList.remove("hidden");
    return;
  }
  if (kind === "error") {
    summaryStreamArea.classList.add("hidden");
    summaryViewError.textContent = message || "日报加载失败";
    summaryViewError.classList.remove("hidden");
  }
}

function showSummaryPhase(payload = {}) {
  if (!summaryPhaseIndicator) return;
  const message = String(payload?.message || "处理中...").trim() || "处理中...";
  summaryPhaseIndicator.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <span class="summary-phase-dots" aria-hidden="true">
      <span></span><span></span><span></span>
    </span>
  `;
  summaryPhaseIndicator.classList.remove("hidden");
}

function appendSummaryToken(text) {
  const token = String(text || "");
  if (!token || !summaryAiText) return;
  summaryAiBlock?.classList.remove("hidden");
  summaryAiCursor?.classList.remove("hidden");
  summaryAiText.textContent += token;
  summaryViewState.tokenBuffer += token;
}

function revealStaggered(items, delayMs) {
  if (!Array.isArray(items) || !items.length) return;
  items.forEach((item, index) => {
    window.setTimeout(() => item.classList.add("visible"), delayMs * index);
  });
}

function renderSummaryHighlights(highlights, options = {}) {
  if (!summaryHighlightsBlock || !summaryHighlightsList) return;
  const items = Array.isArray(highlights) ? highlights.map((item) => String(item || "").trim()).filter(Boolean) : [];
  summaryHighlightsList.innerHTML = "";
  if (!items.length) {
    summaryHighlightsBlock.classList.add("hidden");
    return;
  }
  const nodes = [];
  for (const item of items) {
    const li = document.createElement("li");
    li.className = "summary-highlight-item";
    li.innerHTML = `<i aria-hidden="true"></i><span>${escapeHtml(item)}</span>`;
    summaryHighlightsList.appendChild(li);
    nodes.push(li);
  }
  summaryHighlightsBlock.classList.remove("hidden");
  if (options.animate === false || treeAnimationState.reducedMotion) {
    nodes.forEach((node) => node.classList.add("visible"));
  } else {
    revealStaggered(nodes, 200);
  }
}

function renderSummaryTimeline(segments, options = {}) {
  if (!summaryTimelineBlock || !summaryTimelineList) return;
  const items = Array.isArray(segments) ? segments : [];
  summaryTimelineList.innerHTML = "";
  if (!items.length) {
    summaryTimelineBlock.classList.add("hidden");
    return;
  }
  const nodes = [];
  for (const segment of items) {
    const start = escapeHtml(segment?.start || "--:--");
    const end = escapeHtml(segment?.end || "--:--");
    const category = String(segment?.main_category || "未分类");
    const description = escapeHtml(segment?.description || "");
    const article = document.createElement("article");
    article.className = "summary-timeline-item";
    article.innerHTML = `
      <div class="summary-timeline-time">${start} - ${end}</div>
      <div class="summary-timeline-body">
        <span class="summary-timeline-cat" style="background:${getCategoryColor(category)}">${escapeHtml(category)}</span>
        <p>${description}</p>
      </div>
    `;
    summaryTimelineList.appendChild(article);
    nodes.push(article);
  }
  summaryTimelineBlock.classList.remove("hidden");
  if (options.animate === false || treeAnimationState.reducedMotion) {
    nodes.forEach((node) => node.classList.add("visible"));
  } else {
    revealStaggered(nodes, 150);
  }
}

function normalizeSummaryPayload(payload = {}) {
  const normalized = payload && typeof payload === "object" ? { ...payload } : {};
  if (!Array.isArray(normalized.highlights)) normalized.highlights = [];
  if (!Array.isArray(normalized.timeline_segments)) normalized.timeline_segments = [];
  normalized.summary = String(normalized.summary || "").trim();
  return normalized;
}

function renderSummaryPayload(payload, options = {}) {
  const normalized = normalizeSummaryPayload(payload);
  const date = options.date || normalized.date || summaryViewState.date || resolveSummaryDate();
  if (!normalized.summary && summaryViewState.tokenBuffer) {
    normalized.summary = summaryViewState.tokenBuffer;
  }
  summaryViewState.date = date;
  summaryViewState.payload = normalized;
  summaryViewState.status = "ready";

  setSummaryNotice("", "");
  if (summaryStreamArea) summaryStreamArea.classList.remove("hidden");
  summaryPhaseIndicator?.classList.add("hidden");
  summaryAiBlock?.classList.remove("hidden");
  if (summaryAiText) {
    const preserveTyped = Boolean(options.preserveTypedText);
    if (!preserveTyped || !summaryAiText.textContent.trim()) {
      summaryAiText.textContent = normalized.summary || "暂无 AI 总结";
    }
  }
  summaryAiCursor?.classList.add("hidden");
  renderSummaryHighlights(normalized.highlights, { animate: options.animateLists !== false });
  renderSummaryTimeline(normalized.timeline_segments, { animate: options.animateLists !== false });
  setSummaryMeta(normalized, date, { cached: Boolean(options.cached) });
  setSummaryButtonsBusy(false);
}

async function sleep(ms) {
  await new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function typeSummaryText(text, requestId) {
  if (!summaryAiText) return;
  const content = String(text || "");
  summaryAiText.textContent = "";
  summaryAiBlock?.classList.remove("hidden");
  summaryAiCursor?.classList.remove("hidden");
  if (!content) return;

  if (treeAnimationState.reducedMotion) {
    summaryAiText.textContent = content;
    return;
  }
  const step = 2;
  for (let index = 0; index < content.length; index += step) {
    if (!isSummaryRequestActive(requestId)) return;
    summaryAiText.textContent += content.slice(index, index + step);
    await sleep(18);
  }
}

async function requestDailySummary(dateText) {
  const response = await fetch(`/api/daily-summary?date=${encodeURIComponent(dateText)}`);
  const raw = await response.text();
  const payload = safeJsonParse(raw, { message: raw || `HTTP ${response.status}` });
  if (response.status === 404 || payload?.error === "no_data") {
    return { status: "empty", payload: null, message: payload?.message || "当天无活动记录" };
  }
  if (!response.ok || payload?.ok === false) {
    throw new Error(payload?.message || payload?.error || `HTTP ${response.status}`);
  }
  const data = Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
  return { status: "ready", payload: normalizeSummaryPayload(data) };
}

async function generateDailySummary(dateText, force = false) {
  const response = await fetch("/api/daily-summary/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date: dateText, force }),
  });
  const raw = await response.text();
  const payload = safeJsonParse(raw, { message: raw || `HTTP ${response.status}` });
  if (response.status === 404 || payload?.error === "no_data") {
    return { status: "empty", payload: null, message: payload?.message || "当天无活动记录" };
  }
  if (!response.ok || payload?.ok === false) {
    throw new Error(payload?.message || payload?.error || `HTTP ${response.status}`);
  }
  const data = Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
  return { status: "ready", payload: normalizeSummaryPayload(data) };
}

async function loadSummaryForDate(dateText, options = {}) {
  if (!summaryViewSection) return;
  const date = String(dateText || "").trim() || getTodayISO();
  const forceFetch = Boolean(options.forceFetch);
  const useLoading = options.useLoading !== false;
  if (!forceFetch && summaryViewState.date === date && summaryViewState.status === "ready" && summaryViewState.payload) {
    renderSummaryPayload(summaryViewState.payload, { date, animateLists: false });
    return;
  }

  const requestId = nextSummaryRequestId();
  closeSummaryStreamConnection();
  summaryViewState.date = date;
  summaryViewState.status = "loading";
  summaryViewState.tokenBuffer = "";
  setSummaryButtonsBusy(true);
  setSummaryNotice("", "");
  resetSummaryRenderBlocks();
  setSummaryMeta(null, date);
  if (useLoading) {
    showSummaryPhase({ phase: "loading", message: "正在读取日报缓存..." });
  }

  try {
    const result = await requestDailySummary(date);
    if (!isSummaryRequestActive(requestId)) return;
    if (result.status === "empty") {
      summaryViewState.payload = null;
      summaryViewState.status = "empty";
      setSummaryNotice("empty", result.message || "当天无活动记录");
      setSummaryMeta(null, date);
      setSummaryButtonsBusy(false);
      return;
    }
    renderSummaryPayload(result.payload, { date, animateLists: false, cached: true });
  } catch (error) {
    if (!isSummaryRequestActive(requestId)) return;
    summaryViewState.payload = null;
    summaryViewState.status = "error";
    setSummaryNotice("error", `日报加载失败：${error instanceof Error ? error.message : String(error)}`);
    setSummaryButtonsBusy(false);
  }
}

function streamDailySummary(dateText, force, requestId) {
  if (typeof EventSource === "undefined") {
    return Promise.resolve({ status: "fallback", reason: "browser_no_eventsource" });
  }
  return new Promise((resolve) => {
    let settled = false;
    let receivedAny = false;
    const url = `/api/daily-summary/stream?date=${encodeURIComponent(dateText)}&force=${force ? "true" : "false"}`;
    const source = new EventSource(url);
    summaryViewState.streamConnection = source;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      if (summaryViewState.streamConnection === source) {
        closeSummaryStreamConnection();
      }
      resolve(result);
    };

    const ensureActive = () => isSummaryRequestActive(requestId) && summaryViewState.streamConnection === source;

    const bootstrapTimer = window.setTimeout(() => {
      if (!receivedAny && ensureActive()) {
        finish({ status: "fallback", reason: "stream_timeout" });
      }
    }, 4000);

    const onPhase = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      const payload = safeJsonParse(event.data, {});
      showSummaryPhase(payload);
      if (payload?.phase === "generating") {
        summaryAiBlock?.classList.remove("hidden");
        summaryAiCursor?.classList.remove("hidden");
      }
    };

    const onToken = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      const payload = safeJsonParse(event.data, {});
      appendSummaryToken(payload?.text || "");
    };

    const onHighlights = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      const payload = safeJsonParse(event.data, {});
      renderSummaryHighlights(payload?.highlights || [], { animate: true });
    };

    const onSegments = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      const payload = safeJsonParse(event.data, {});
      renderSummaryTimeline(payload?.timeline_segments || [], { animate: true });
    };

    const onCached = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      window.clearTimeout(bootstrapTimer);
      const payload = safeJsonParse(event.data, {});
      renderSummaryPayload(payload, { date: dateText, animateLists: false, cached: true });
      pushLogLine(`summary: cache hit for ${dateText}`);
      finish({ status: "ready" });
    };

    const onDone = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      window.clearTimeout(bootstrapTimer);
      const payload = safeJsonParse(event.data, {});
      if (!payload.summary && summaryViewState.tokenBuffer) {
        payload.summary = summaryViewState.tokenBuffer;
      }
      renderSummaryPayload(payload, { date: dateText, animateLists: true, preserveTypedText: true });
      pushLogLine(`summary: generated for ${dateText}${force ? " (force)" : ""}`);
      finish({ status: "ready" });
    };

    const onErrorEvent = (event) => {
      if (!ensureActive()) return;
      receivedAny = true;
      window.clearTimeout(bootstrapTimer);
      const payload = safeJsonParse(event.data, {});
      finish({ status: "fallback", reason: payload?.message || "stream_error" });
    };

    source.addEventListener("phase", onPhase);
    source.addEventListener("token", onToken);
    source.addEventListener("highlights", onHighlights);
    source.addEventListener("segments", onSegments);
    source.addEventListener("cached", onCached);
    source.addEventListener("done", onDone);
    source.addEventListener("error", onErrorEvent);
    source.onerror = () => {
      if (!ensureActive()) return;
      window.clearTimeout(bootstrapTimer);
      finish({ status: "fallback", reason: "stream_network_error" });
    };
  });
}

async function runGenerateFallback(date, force, requestId) {
  showSummaryPhase({
    phase: "generating",
    message: "流式不可用，切换为普通生成...",
  });
  try {
    const result = await generateDailySummary(date, force);
    if (!isSummaryRequestActive(requestId)) return;
    if (result.status === "empty") {
      summaryViewState.payload = null;
      summaryViewState.status = "empty";
      setSummaryNotice("empty", result.message || "当天无活动记录");
      setSummaryMeta(null, date);
      setSummaryButtonsBusy(false);
      pushLogLine(`summary: no data on ${date}`);
      return;
    }
    summaryViewState.tokenBuffer = "";
    await typeSummaryText(result.payload?.summary || "", requestId);
    if (!isSummaryRequestActive(requestId)) return;
    renderSummaryPayload(result.payload, {
      date,
      animateLists: true,
      preserveTypedText: true,
    });
    pushLogLine(`summary: generated for ${date}${force ? " (fallback)" : " (fallback)"}`);
  } catch (error) {
    if (!isSummaryRequestActive(requestId)) return;
    summaryViewState.status = "error";
    setSummaryNotice("error", `生成失败：${error instanceof Error ? error.message : String(error)}`);
    setSummaryButtonsBusy(false);
    pushLogLine(`summary generate failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

async function handleGenerateSummary(force = false) {
  if (!summaryViewSection) return;
  const date = resolveSummaryDate();
  const requestId = nextSummaryRequestId();
  closeSummaryStreamConnection();
  summaryViewState.date = date;
  summaryViewState.payload = null;
  summaryViewState.status = "streaming";
  summaryViewState.tokenBuffer = "";
  setSummaryButtonsBusy(true);
  setSummaryNotice("", "");
  resetSummaryRenderBlocks();
  setSummaryMeta(null, date);
  showSummaryPhase({
    phase: "parsing",
    message: force ? "正在重新生成日报..." : "正在生成日报...",
  });

  const streamResult = await streamDailySummary(date, force, requestId);
  if (!isSummaryRequestActive(requestId)) return;
  if (streamResult.status === "ready") {
    return;
  }
  await runGenerateFallback(date, force, requestId);
}

async function copyDailySummaryText() {
  if (!summaryViewState.payload) return;
  const payload = summaryViewState.payload;
  const date = payload?.date || summaryViewState.date || uiState.selectedDate || getTodayISO();
  const summaryText = String(payload?.summary || "").trim();
  const highlights = Array.isArray(payload?.highlights) ? payload.highlights : [];
  const lines = [`日报总结 ${date}`, "", summaryText || "暂无 AI 总结"];
  if (highlights.length) {
    lines.push("", "亮点：");
    highlights.forEach((item, index) => {
      lines.push(`${index + 1}. ${item}`);
    });
  }
  const output = lines.join("\n");
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(output);
    return;
  }
  const temp = document.createElement("textarea");
  temp.value = output;
  document.body.appendChild(temp);
  temp.select();
  document.execCommand("copy");
  document.body.removeChild(temp);
}

function initSummaryView() {
  if (!summaryViewSection) return;
  setSummaryButtonsBusy(false);
  resetSummaryRenderBlocks();
  setSummaryNotice("empty", "切换到日报视图后可加载缓存");
  setSummaryMeta(null, resolveSummaryDate());

  summaryGenerateBtn?.addEventListener("click", async () => {
    await handleGenerateSummary(false);
  });
  summaryRegenerateBtn?.addEventListener("click", async () => {
    await handleGenerateSummary(true);
  });
  summaryCopyBtn?.addEventListener("click", async () => {
    try {
      await copyDailySummaryText();
      pushLogLine("summary copied");
    } catch (error) {
      pushLogLine(`summary copy failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  });
}

function buildTreeQuery() {
  const query = new URLSearchParams();
  if (uiState.selectedDate) query.set("date", uiState.selectedDate);
  if (uiState.selectedTreeId) query.set("tree_id", uiState.selectedTreeId);
  return `/api/tree?${query.toString()}`;
}

function buildLogsQuery() {
  const query = new URLSearchParams();
  query.set("lines", "120");
  if (uiState.selectedDate) query.set("date", uiState.selectedDate);
  return `/api/logs?${query.toString()}`;
}

async function fetchTreeDataForDate(dateISO, treeId = "") {
  const query = new URLSearchParams();
  query.set("date", dateISO);
  if (treeId) query.set("tree_id", treeId);
  return api(`/api/tree?${query.toString()}`);
}

function buildFallbackStats(cards, dateValues) {
  const categoryCounts = {};
  for (const card of cards) {
    categoryCounts[card.category] = (categoryCounts[card.category] || 0) + 1;
  }
  const sorted = [...cards].sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? -1 : 1;
    return a.time < b.time ? -1 : 1;
  });
  const intervals = [];
  for (let i = 1; i < sorted.length; i += 1) {
    const prev = new Date(`${sorted[i - 1].date}T${sorted[i - 1].time}:00`).getTime();
    const next = new Date(`${sorted[i].date}T${sorted[i].time}:00`).getTime();
    if (Number.isFinite(prev) && Number.isFinite(next) && next > prev) {
      intervals.push((next - prev) / 1000);
    }
  }
  const avgInterval = intervals.length
    ? intervals.reduce((sum, value) => sum + value, 0) / intervals.length
    : 0;
  const rangeStart = dateValues.length ? dateValues[0] : "";
  const rangeEnd = dateValues.length ? dateValues[dateValues.length - 1] : "";
  return {
    total_count: cards.length,
    category_counts: categoryCounts,
    total_active_seconds: 0,
    avg_interval_seconds: Math.round(avgInterval),
    date_range: {
      start: rangeStart,
      end: rangeEnd,
    },
  };
}

async function loadCardsFallback(filters) {
  const dateValues = (() => {
    if (filters.date) return [filters.date];
    if (filters.date_from || filters.date_to) {
      const from = filters.date_from || filters.date_to;
      const to = filters.date_to || filters.date_from;
      return buildDateRangeValues(from, to);
    }
    return [uiState.selectedDate || getTodayISO()];
  })();

  const selectedCategories = new Set(parseCommaList(filters.categories));
  const selectedTreeIds = new Set(parseCommaList(filters.tree_ids));
  const needle = String(filters.search || "").trim().toLowerCase();
  const rows = [];
  const treeCatalog = new Map();
  const sequenceByMinute = new Map();

  for (const dateISO of dateValues) {
    const base = await fetchTreeDataForDate(dateISO);
    const trees = Array.isArray(base.trees) ? base.trees : [];
    for (const tree of trees) {
      treeCatalog.set(tree.id, tree);
    }

    const targetTreeIds = selectedTreeIds.size
      ? trees.map((tree) => tree.id).filter((id) => selectedTreeIds.has(id))
      : trees.map((tree) => tree.id);

    for (const treeId of targetTreeIds) {
      const treeDetail = await fetchTreeDataForDate(dateISO, treeId);
      const entries = Array.isArray(treeDetail.entries) ? treeDetail.entries : [];
      for (const entry of entries) {
        const key = `${dateISO}-${entry.time}`;
        const sequence = (sequenceByMinute.get(key) || 0) + 1;
        sequenceByMinute.set(key, sequence);

        const card = {
          id: `${toCardDateStamp(dateISO)}-${String(entry.time || "--:--").replace(":", "")}-${String(sequence).padStart(3, "0")}`,
          date: dateISO,
          time: entry.time || "--:--",
          category: entry.category || "未分类",
          summary: entry.summary || "",
          tree_id: treeId,
          tree_name: treeCatalog.get(treeId)?.name || treeId,
          source: "vl",
          confidence: 0,
          event_data: null,
          available_categories: [...uiState.categories],
        };
        rows.push(card);
      }
    }
  }

  const filtered = rows.filter((card) => {
    if (selectedCategories.size && !selectedCategories.has(card.category)) {
      return false;
    }
    if (selectedTreeIds.size && !selectedTreeIds.has(card.tree_id)) {
      return false;
    }
    if (!needle) return true;
    const haystack = `${card.date} ${card.time} ${card.category} ${card.summary}`.toLowerCase();
    return haystack.includes(needle);
  });

  const sortMode = String(filters.sort || "time_desc");
  filtered.sort((a, b) => {
    const aKey = `${a.date} ${a.time}`;
    const bKey = `${b.date} ${b.time}`;
    if (sortMode === "time_asc") {
      return aKey < bKey ? -1 : aKey > bKey ? 1 : 0;
    }
    return aKey > bKey ? -1 : aKey < bKey ? 1 : 0;
  });

  const page = Math.max(1, Number(filters.page || 1));
  const pageSize = clamp(Number(filters.page_size || 50), 10, 200);
  const start = (page - 1) * pageSize;
  const pageCards = filtered.slice(start, start + pageSize);

  return {
    cards: pageCards,
    total: filtered.length,
    page,
    page_size: pageSize,
    has_more: start + pageSize < filtered.length,
    stats: buildFallbackStats(filtered, dateValues),
    trees: [...treeCatalog.values()],
    categories: [...uiState.categories],
    fallback: true,
  };
}

function initFlowView() {
  if (!flowCanvas) return;
  if (!window.FlowView) {
    setFlowEmptyOverlay("FlowView script missing.");
    pushLogLine("flow: FlowView.js missing");
    return;
  }

  flowView = new window.FlowView(flowCanvas, {
    getCategoryColor: (category) => getCategoryColor(category),
    onHover: (node, pageX, pageY) => showTooltip(pageX, pageY, node),
    onLeave: () => hideTooltip(),
    onMessage: (message) => setFlowEmptyOverlay(message || ""),
  });
  setFlowEmptyOverlay("");

  flowZoomInBtn?.addEventListener("click", () => {
    if (!flowView) return;
    flowView.setZoom((flowView.getZoom?.() || 1) * 1.12);
  });

  flowZoomOutBtn?.addEventListener("click", () => {
    if (!flowView) return;
    flowView.setZoom((flowView.getZoom?.() || 1) * 0.9);
  });

  flowResetBtn?.addEventListener("click", () => {
    flowView?.resetView?.();
  });
}

function initCardsView() {
  if (!viewSwitcherMount || !cardsViewSection) return;
  if (!window.ViewSwitcher || !window.CardView) {
    pushLogLine("cards components missing");
    return;
  }

  cardView = new window.CardView(cardsViewSection, {
    apiRequest: api,
    getCategories: () => [...uiState.categories],
    getTrees: () => [...uiState.trees],
    getDefaultDate: () => uiState.selectedDate || getTodayISO(),
    fallbackLoader: async (filters) => {
      if (!cardFallbackWarned) {
        cardFallbackWarned = true;
        pushLogLine("cards api unavailable, fallback to /api/tree");
      }
      return loadCardsFallback(filters);
    },
    onNotify: (text, level = "info") => {
      const prefix = level === "error" ? "cards error" : "cards";
      pushLogLine(`${prefix}: ${text}`);
    },
    onViewTree: async (card) => {
      uiState.selectedDate = card.date || uiState.selectedDate || getTodayISO();
      uiState.selectedTreeId = card.tree_id || "";
      viewState.userAdjusted = false;
      await refreshTree().catch((error) => pushLogLine(`tree jump failed: ${error.message}`));
      setActiveView("tree", true);
    },
  });

  viewSwitcher = new window.ViewSwitcher(viewSwitcherMount, (view) => {
    setActiveView(view, false);
  }, {
    initialView: "tree",
  });
  setActiveView(viewSwitcher.getActiveView(), false);
}

async function refreshStatus(syncControls = false) {
  const data = await api("/api/status");
  const running = Boolean(data.running);
  setBadge(running);
  startBtn.disabled = running;
  stopBtn.disabled = !running;
  if (syncControls || !controlsHydrated) {
    if (data.start_time) startTimeInput.value = data.start_time;
    if (data.end_time) endTimeInput.value = data.end_time;
    if (data.interval_s) intervalInput.value = String(data.interval_s);
    if (Array.isArray(data.categories) && data.categories.length) {
      setCategories(data.categories);
    }
    controlsHydrated = true;
  }
}

async function refreshTree() {
  const requestSeq = ++treeRequestSeq;
  const data = await api(buildTreeQuery());
  if (requestSeq !== treeRequestSeq) {
    return;
  }
  treeDate.textContent = data.date || "";
  uiState.selectedDate = data.date || uiState.selectedDate;
  uiState.availableDates = data.date_options || [];
  renderDateDropdown();
  uiState.trees = data.trees || [];
  uiState.selectedTreeId = data.selected_tree_id || "";
  updateTreeSelect(uiState.trees, uiState.selectedTreeId);

  if (Array.isArray(data.categories) && data.categories.length) {
    setCategories(data.categories);
  }
  if (uiState.activeView === "summary") {
    loadSummaryForDate(uiState.selectedDate || getTodayISO(), { forceFetch: false, useLoading: false }).catch(() => {});
  }
  cardView?.applyMeta({
    categories: uiState.categories,
    trees: uiState.trees,
    selectedDate: uiState.selectedDate || getTodayISO(),
  });

  const fullRange = resolveFullRange(data);
  const selectionKey = `${data.date || ""}::${uiState.selectedTreeId || ""}`;
  const selectionChanged = selectionKey !== lastViewportSelectionKey;
  lastViewportSelectionKey = selectionKey;
  const shouldReset = selectionChanged || !viewState.initialized || !viewState.userAdjusted;
  syncViewport(fullRange.start, fullRange.end, shouldReset);

  const trees = Array.isArray(data.trees) ? data.trees : [];
  if (!trees.length) {
    setCanvasRenderMode("empty");
    setTreeEmptyOverlay("No Trees. Click New Tree to create one.");
    stopTreeAnimationLoop();
    if (resizeFrame) {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = null;
    }
    lastTreeData = null;
    lastCanvasMetrics = null;
    fruits = [];
    selectedFruitIndex = -1;
    activeScene = null;
    treeAnimationState.sceneFingerprint = "";
    treeAnimationState.primedScene = "";
    renderErrorFingerprint = "";
    hideTooltip();
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext("2d");
    if (ctx && rect.width && rect.height) {
      const ratio = window.devicePixelRatio || 1;
      const targetWidth = Math.max(1, Math.floor(rect.width * ratio));
      const targetHeight = Math.max(1, Math.floor(rect.height * ratio));
      if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
        canvas.width = targetWidth;
        canvas.height = targetHeight;
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    renderTreeList([]);
    if (flowView) {
      renderFlowFromTreeData({ entries: [] });
      if (uiState.activeView === "flow") {
        setFlowEmptyOverlay("No Trees. Click New Tree to create one.");
      }
    }
    return;
  }

  setCanvasRenderMode("tree");
  setTreeEmptyOverlay("");
  drawTree(data);
  renderTreeList(data.entries || []);
  cardView?.applyMeta({
    categories: uiState.categories,
    trees: uiState.trees,
    selectedDate: uiState.selectedDate || getTodayISO(),
  });
  if (flowView) {
    renderFlowFromTreeData(data);
    if (uiState.activeView === "flow") {
      setFlowEmptyOverlay("");
    }
  }
}

async function refreshLogs() {
  const data = await api(buildLogsQuery());
  logsPanel.textContent = (data.lines || []).join("\n");
  logsPanel.scrollTop = logsPanel.scrollHeight;
}

startBtn.addEventListener("click", async () => {
  try {
    const categories = parseCategories(categoriesInput.value);
    const result = await api("/api/start", "POST", {
      start_time: startTimeInput.value,
      end_time: endTimeInput.value,
      interval_s: Number.parseInt(intervalInput.value || "30", 10),
      categories,
      tree_id: uiState.selectedTreeId || "",
    });
    setCategories(result.categories || categories);
    viewState.userAdjusted = false;
    pushLogLine(`start: ${result.message || "requested"}`);
    await refreshStatus(true);
    await refreshTree();
  } catch (error) {
    pushLogLine(`start failed: ${error.message}`);
  }
});

stopBtn.addEventListener("click", async () => {
  try {
    const result = await api("/api/stop", "POST");
    pushLogLine(`stop: ${result.message || "requested"}`);
    await refreshStatus(false);
  } catch (error) {
    pushLogLine(`stop failed: ${error.message}`);
  }
});

manualBtn.addEventListener("click", async () => {
  manualBtn.disabled = true;
  pushLogLine("manual snapshot requested...");
  try {
    const result = await api("/api/manual", "POST", {
      tree_id: uiState.selectedTreeId || "",
    });
    pushLogLine(`manual: [${result.category || "未知"}] ${result.summary || "done"}`);
    await refreshTree();
    await refreshLogs();
  } catch (error) {
    pushLogLine(`manual failed: ${error.message}`);
  } finally {
    manualBtn.disabled = false;
  }
});

applyCategoriesBtn?.addEventListener("click", async () => {
  const categories = parseCategories(categoriesInput.value);
  if (!categories.length) {
    pushLogLine("preferences failed: categories cannot be empty");
    return;
  }
  try {
    const result = await api("/api/preferences", "POST", {
      interval_s: Number.parseInt(intervalInput.value || "30", 10),
      categories,
    });
    setCategories(result.categories || categories);
    pushLogLine(`preferences: interval=${result.interval_s}s categories=${(result.categories || []).join("/")}`);
    await refreshStatus(true);
    await refreshTree();
  } catch (error) {
    pushLogLine(`preferences failed: ${error.message}`);
  }
});

newTreeBtn?.addEventListener("click", async () => {
  const name = window.prompt("Tree name (optional):", "");
  try {
    const result = await api("/api/tree/create", "POST", {
      date: uiState.selectedDate || "",
      name: name || "",
    });
    uiState.selectedDate = result.date || uiState.selectedDate;
    uiState.selectedTreeId = result.tree?.id || "";
    viewState.userAdjusted = false;
    pushLogLine(`tree created: ${result.tree?.name || result.tree?.id || "new tree"}`);
    await refreshTree();
  } catch (error) {
    pushLogLine(`create tree failed: ${error.message}`);
  }
});

deleteTreeBtn?.addEventListener("click", async () => {
  if (!uiState.selectedTreeId) {
    pushLogLine("delete tree failed: no tree selected");
    return;
  }
  const ok = window.confirm("Delete selected tree and all its fruits?");
  if (!ok) return;
  try {
    const result = await api("/api/tree/delete", "POST", {
      date: uiState.selectedDate || "",
      tree_id: uiState.selectedTreeId,
    });
    if (result.ok === false) {
      throw new Error(result.message || "delete failed");
    }
    pushLogLine(`tree deleted: ${uiState.selectedTreeId}`);
    uiState.selectedTreeId = "";
    viewState.userAdjusted = false;
    await refreshTree();
    await refreshLogs();
  } catch (error) {
    pushLogLine(`delete tree failed: ${error.message}`);
  }
});

dateDropdownBtn?.addEventListener("click", () => {
  setDateMenuOpen(!uiState.dateMenuOpen);
});

settingsToggleBtn?.addEventListener("click", () => {
  setSettingsOpen(!uiState.settingsOpen);
});

settingsCloseBtn?.addEventListener("click", () => {
  setSettingsOpen(false);
});

settingsOverlay?.addEventListener("click", () => {
  setSettingsOpen(false);
});

document.addEventListener("click", (event) => {
  if (!dateDropdown || !uiState.dateMenuOpen) return;
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (!dateDropdown.contains(target)) {
    setDateMenuOpen(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (uiState.dateMenuOpen) {
    setDateMenuOpen(false);
    return;
  }
  if (uiState.settingsOpen) {
    setSettingsOpen(false);
  }
});

document.addEventListener("visibilitychange", () => {
  if (document.hidden) return;
  if (uiState.activeView === "tree" && activeScene?.kind === "tree" && !treeAnimationState.reducedMotion) {
    startTreeAnimationLoop();
  }
});

themeToggleBtn?.addEventListener("click", () => {
  applyTheme(uiState.theme === "light" ? "dark" : "light");
  if (uiState.activeView === "tree" && lastTreeData) {
    drawTree(lastTreeData);
  }
});

if (treeMotionMedia) {
  const onReduceMotionChange = (event) => {
    treeAnimationState.reducedMotion = Boolean(event.matches);
    if (uiState.activeView === "tree" && lastTreeData) {
      drawTree(lastTreeData);
    }
  };
  if (typeof treeMotionMedia.addEventListener === "function") {
    treeMotionMedia.addEventListener("change", onReduceMotionChange);
  } else if (typeof treeMotionMedia.addListener === "function") {
    treeMotionMedia.addListener(onReduceMotionChange);
  }
}

treeSelect?.addEventListener("change", async () => {
  uiState.selectedTreeId = treeSelect.value;
  viewState.userAdjusted = false;
  await refreshTree().catch((error) => pushLogLine(`tree switch failed: ${error.message}`));
  if (uiState.activeView === "cards") {
    await cardView?.loadCards({ tree_ids: uiState.selectedTreeId ? [uiState.selectedTreeId] : [], page: 1 });
  }
});

reloadHistoryBtn?.addEventListener("click", async () => {
  await refreshTree().catch((error) => pushLogLine(`reload failed: ${error.message}`));
  await refreshLogs().catch(() => {});
  if (uiState.activeView === "cards") {
    await cardView?.loadCards({ page: 1 }).catch(() => {});
  }
});

async function loadMonitors() {
  try {
    const response = await fetch("/api/monitors");
    const data = await response.json();
    if (data.ok && data.monitors) {
      monitorSelect.innerHTML = "";
      data.monitors.forEach((monitor) => {
        const option = document.createElement("option");
        option.value = monitor.index;
        option.textContent = `Display ${monitor.index} (${monitor.width}x${monitor.height})`;
        monitorSelect.appendChild(option);
      });
      if (data.current) {
        monitorSelect.value = data.current;
      }
    }
  } catch (error) {
    pushLogLine(`load monitors failed: ${error.message}`);
  }
}

async function loadMonitorPreview(monitorIndex) {
  try {
    monitorPreview.innerHTML = "<p style='padding: 1rem; text-align: center;'>Loading preview...</p>";
    monitorPreview.classList.remove("hidden");
    const response = await fetch(`/api/monitors/${monitorIndex}/preview`);
    const data = await response.json();
    if (data.ok && data.preview) {
      monitorPreview.textContent = "";
      const img = document.createElement("img");
      img.src = data.preview;
      img.alt = `Monitor ${monitorIndex} preview`;
      monitorPreview.appendChild(img);
    } else {
      monitorPreview.innerHTML = `<p style='padding: 1rem; text-align: center; color: var(--muted);'>Preview unavailable</p>`;
    }
  } catch (error) {
    monitorPreview.innerHTML = `<p style='padding: 1rem; text-align: center; color: var(--muted);'>Preview failed</p>`;
  }
}

monitorSelect?.addEventListener("change", async () => {
  const monitorIndex = parseInt(monitorSelect.value, 10);
  await loadMonitorPreview(monitorIndex);
});

monitorSelect?.addEventListener("focus", async () => {
  const monitorIndex = parseInt(monitorSelect.value, 10);
  await loadMonitorPreview(monitorIndex);
});

monitorSelect?.addEventListener("blur", async () => {
  const monitorIndex = parseInt(monitorSelect.value, 10);
  try {
    const response = await fetch("/api/monitors/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monitor_index: monitorIndex }),
    });
    const data = await response.json();
    if (data.ok) {
      pushLogLine(data.message || `Switched to monitor ${monitorIndex}`);
    } else {
      pushLogLine(data.message || `Failed to switch monitor`);
    }
  } catch (error) {
    pushLogLine(`monitor switch failed: ${error.message}`);
  }
  setTimeout(() => {
    monitorPreview.classList.add("hidden");
  }, 500);
});

window.addEventListener("resize", () => {
  if (lastTreeData) {
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => drawTree(lastTreeData));
  }
  if (flowResizeFrame) cancelAnimationFrame(flowResizeFrame);
  flowResizeFrame = requestAnimationFrame(() => flowView?.resize?.());
});

if (typeof ResizeObserver !== "undefined") {
  const observer = new ResizeObserver(() => {
    if (lastTreeData) {
      if (resizeFrame) cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => drawTree(lastTreeData));
    }
    if (flowResizeFrame) cancelAnimationFrame(flowResizeFrame);
    flowResizeFrame = requestAnimationFrame(() => flowView?.resize?.());
  });
  observer.observe(canvas);
  if (flowCanvas) {
    observer.observe(flowCanvas);
  }
}

async function boot() {
  ensureTooltipRichStyles();
  let savedTheme = "dark";
  try {
    savedTheme = localStorage.getItem("watcher_theme") || "dark";
  } catch (error) {
  }
  applyTheme(savedTheme);
  setSettingsOpen(false);
  setCategories(parseCategories(categoriesInput.value));
  renderDateDropdown();
  initSummaryView();
  await loadMonitors();
  try {
    await refreshStatus(true);
    await refreshTree();
    await refreshLogs();
    initFlowView();
    initCardsView();
  } catch (error) {
    pushLogLine(`boot failed: ${error.message}`);
  }
  setTimeout(() => {
    if (lastTreeData) drawTree(lastTreeData);
  }, 120);
  setTimeout(() => {
    if (lastTreeData) drawTree(lastTreeData);
  }, 800);
  pushLogLine(`ui build: ${UI_BUILD}`);
  setInterval(() => refreshStatus().catch(() => {}), 5000);
  setInterval(() => refreshTree().catch(() => {}), 300000);
  setInterval(() => {
    if (uiState.activeView === "logs") {
      refreshLogs().catch(() => {});
    }
  }, 5000);
  setInterval(() => {
    if (uiState.activeView === "cards") {
      cardView?.loadCards({ page: cardView?.state?.page || 1 }, { syncUrl: false }).catch(() => {});
    }
  }, 30000);
}

setBadge(false);
boot();
