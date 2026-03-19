(() => {
  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function splitList(value) {
    return [...new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean))];
  }

  function formatDateStamp(isoDate) {
    return String(isoDate || "").replace(/-/g, "");
  }

  function parseMinutes(timeText) {
    const text = String(timeText || "");
    if (!/^\d{2}:\d{2}$/.test(text)) return null;
    const [hText, mText] = text.split(":");
    const h = Number.parseInt(hText, 10);
    const m = Number.parseInt(mText, 10);
    if (!Number.isFinite(h) || !Number.isFinite(m)) return null;
    return h * 60 + m;
  }

  function timeBucket(timeText) {
    const minute = parseMinutes(timeText);
    if (minute === null) {
      return { key: "morning", label: "上午 (09:00-12:00)" };
    }
    if (minute < 12 * 60) {
      return { key: "morning", label: "上午 (09:00-12:00)" };
    }
    if (minute < 18 * 60) {
      return { key: "afternoon", label: "下午 (12:00-18:00)" };
    }
    return { key: "evening", label: "晚上 (18:00-24:00)" };
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function resolveCategoryColor(category) {
    const text = String(category || "").trim();
    if (text === "写代码") return "var(--work)";
    if (text === "研究") return "var(--research)";
    if (text === "娱乐") return "var(--fun)";
    return "var(--muted)";
  }

  function cardTimestamp(card) {
    if (!card?.date || !card?.time) return null;
    const timestamp = new Date(`${card.date}T${card.time}:00`).getTime();
    return Number.isFinite(timestamp) ? timestamp : null;
  }

  function intervalMinutes(prevCard, nextCard) {
    const prevTs = cardTimestamp(prevCard);
    const nextTs = cardTimestamp(nextCard);
    if (prevTs === null || nextTs === null) return null;
    const diff = Math.abs(nextTs - prevTs);
    return Math.max(0, Math.round(diff / 60000));
  }

  function formatGapLabel(minutes) {
    if (!Number.isFinite(minutes)) return "";
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (!mins) return `${hours}h`;
    return `${hours}h ${mins}min`;
  }

  function groupCardsByTime(cards) {
    const groups = [];
    const groupMap = new Map();

    for (const card of cards) {
      const bucket = timeBucket(card.time);
      if (!groupMap.has(bucket.key)) {
        const group = {
          key: bucket.key,
          label: bucket.label,
          cards: [],
          counts: {},
        };
        groups.push(group);
        groupMap.set(bucket.key, group);
      }
      const target = groupMap.get(bucket.key);
      target.cards.push(card);
      const category = card.category || "未分类";
      target.counts[category] = (target.counts[category] || 0) + 1;
    }

    for (const group of groups) {
      const major = Object.entries(group.counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "-";
      group.majorCategory = major;
    }

    return groups;
  }

  function fileDownload(content, name, type = "text/plain;charset=utf-8") {
    const blob = content instanceof Blob ? content : new Blob([content], { type });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  function toCSV(cards) {
    const header = ["id", "date", "time", "category", "summary", "tree_id", "source", "confidence"];
    const rows = cards.map((card) => [
      card.id || "",
      card.date || "",
      card.time || "",
      card.category || "",
      card.summary || "",
      card.tree_id || "",
      card.source || "",
      Number(card.confidence || 0).toFixed(2),
    ]);
    const all = [header, ...rows];
    return all
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
  }

  function toMarkdown(cards) {
    if (!cards.length) return "";
    return cards
      .map((card) => `- ${card.date || ""} ${card.time || "--:--"} [${card.category || "未分类"}] ${card.tree_id ? `{tree:${card.tree_id}} ` : ""}${card.summary || ""}`)
      .join("\n");
  }

  class CardView {
    constructor(container, options = {}) {
      this.container = container;
      this.apiRequest = typeof options.apiRequest === "function" ? options.apiRequest : this.defaultApiRequest;
      this.onNotify = typeof options.onNotify === "function" ? options.onNotify : () => {};
      this.onViewTree = typeof options.onViewTree === "function" ? options.onViewTree : () => {};
      this.getCategories = typeof options.getCategories === "function" ? options.getCategories : () => [];
      this.getTrees = typeof options.getTrees === "function" ? options.getTrees : () => [];
      this.getDefaultDate = typeof options.getDefaultDate === "function" ? options.getDefaultDate : () => "";
      this.fallbackLoader = typeof options.fallbackLoader === "function" ? options.fallbackLoader : null;

      this.filters = {
        date: "",
        date_from: "",
        date_to: "",
        categories: [],
        tree_ids: [],
        search: "",
        page: 1,
        page_size: 50,
        sort: "time_desc",
        ...this.readFiltersFromUrl(),
      };

      this.state = {
        loading: false,
        loaded: false,
        cards: [],
        total: 0,
        page: 1,
        page_size: 50,
        has_more: false,
        stats: null,
        backendMode: "api",
      };

      this.dom = {};
      this.filterBar = null;
      this.statsPanel = null;
      this.pagination = null;

      this.renderShell();
      this.initComponents();
      this.applyMeta();
    }

    readFiltersFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const output = {};
      if (params.get("date")) output.date = params.get("date");
      if (params.get("date_from")) output.date_from = params.get("date_from");
      if (params.get("date_to")) output.date_to = params.get("date_to");
      if (params.get("categories")) output.categories = splitList(params.get("categories"));
      if (params.get("tree_ids")) output.tree_ids = splitList(params.get("tree_ids"));
      if (params.get("search")) output.search = params.get("search");
      if (params.get("sort")) output.sort = params.get("sort");
      const page = Number.parseInt(params.get("page") || "1", 10);
      const pageSize = Number.parseInt(params.get("page_size") || "50", 10);
      if (Number.isFinite(page) && page > 0) output.page = page;
      if (Number.isFinite(pageSize) && pageSize > 0) output.page_size = clamp(pageSize, 10, 200);
      return output;
    }

    syncFiltersToUrl() {
      const url = new URL(window.location.href);
      const params = url.searchParams;
      const setOrDelete = (key, value) => {
        if (value === null || value === undefined || value === "") {
          params.delete(key);
          return;
        }
        params.set(key, String(value));
      };

      setOrDelete("date", this.filters.date);
      setOrDelete("date_from", this.filters.date_from);
      setOrDelete("date_to", this.filters.date_to);
      setOrDelete("categories", (this.filters.categories || []).join(","));
      setOrDelete("tree_ids", (this.filters.tree_ids || []).join(","));
      setOrDelete("search", this.filters.search);
      setOrDelete("sort", this.filters.sort);
      setOrDelete("page", this.filters.page > 1 ? this.filters.page : "");
      setOrDelete("page_size", this.filters.page_size !== 50 ? this.filters.page_size : "");

      window.history.replaceState({}, "", url);
    }

    renderShell() {
      if (!this.container) return;
      this.container.innerHTML = `
        <div class="cards-shell">
          <header class="cards-header">
            <div>
              <h2>Cards View</h2>
              <p class="small-muted">Search, filter and manage daily activity cards.</p>
            </div>
            <div class="cards-header-badges">
              <span class="cards-results" data-results>0 records</span>
              <span class="cards-mode" data-mode>API</span>
            </div>
          </header>
          <div class="cards-filter-mount" data-filter></div>
          <div class="cards-stats-mount" data-stats></div>
          <p class="cards-state" data-state>Ready.</p>
          <div class="cards-grid cards-timeline-mode" data-list></div>
          <div class="cards-pagination-mount" data-pagination></div>
        </div>
      `;

      this.dom.results = this.container.querySelector("[data-results]");
      this.dom.mode = this.container.querySelector("[data-mode]");
      this.dom.state = this.container.querySelector("[data-state]");
      this.dom.list = this.container.querySelector("[data-list]");
      this.dom.filter = this.container.querySelector("[data-filter]");
      this.dom.stats = this.container.querySelector("[data-stats]");
      this.dom.pagination = this.container.querySelector("[data-pagination]");
    }

    initComponents() {
      const FilterBar = window.FilterBar;
      const StatsPanel = window.StatsPanel;
      const Pagination = window.Pagination;
      if (!FilterBar || !StatsPanel || !Pagination) {
        this.dom.state.textContent = "Cards components are missing.";
        return;
      }

      this.filterBar = new FilterBar(this.dom.filter, (filters) => {
        this.loadCards(filters).catch((error) => {
          this.onNotify(`Cards load failed: ${error instanceof Error ? error.message : String(error)}`, "error");
        });
      }, {
        categories: this.getCategories(),
        trees: this.getTrees(),
        date: this.filters.date,
        date_from: this.filters.date_from,
        date_to: this.filters.date_to,
        categoriesSelected: this.filters.categories,
        tree_ids: this.filters.tree_ids,
        search: this.filters.search,
        sort: this.filters.sort,
        page_size: this.filters.page_size,
        onExport: () => this.exportCards().catch((error) => {
          this.onNotify(`Export failed: ${error instanceof Error ? error.message : String(error)}`, "error");
        }),
      });

      this.statsPanel = new StatsPanel(this.dom.stats);
      this.pagination = new Pagination(this.dom.pagination, (page) => {
        this.loadCards({ page }).catch((error) => {
          this.onNotify(`Page switch failed: ${error instanceof Error ? error.message : String(error)}`, "error");
        });
      });
    }

    applyMeta(meta = {}) {
      const categories = Array.isArray(meta.categories) ? meta.categories : this.getCategories();
      const trees = Array.isArray(meta.trees) ? meta.trees : this.getTrees();
      const selectedDate = typeof meta.selectedDate === "string" ? meta.selectedDate : this.getDefaultDate();
      if (!this.filters.date && selectedDate) {
        this.filters.date = selectedDate;
      }
      if (this.filterBar) {
        this.filterBar.setMeta({
          categories,
          trees,
          categoryCounts: this.state.stats?.category_counts || {},
        });
        this.filterBar.setFilters(this.filters, { silent: true });
      }
    }

    queryStringFromFilters(filters) {
      const params = new URLSearchParams();
      const add = (key, value) => {
        if (value === null || value === undefined || value === "") return;
        params.set(key, String(value));
      };
      add("date", filters.date);
      add("date_from", filters.date_from);
      add("date_to", filters.date_to);
      if (Array.isArray(filters.categories) && filters.categories.length) {
        add("categories", filters.categories.join(","));
      }
      if (Array.isArray(filters.tree_ids) && filters.tree_ids.length) {
        add("tree_ids", filters.tree_ids.join(","));
      }
      add("search", filters.search);
      add("sort", filters.sort);
      add("page", filters.page || 1);
      add("page_size", filters.page_size || 50);
      return params.toString();
    }

    normalizePayload(payload) {
      const cards = Array.isArray(payload?.cards) ? payload.cards : [];
      const total = Number(payload?.total || cards.length);
      const page = Number(payload?.page || this.filters.page || 1);
      const pageSize = Number(payload?.page_size || this.filters.page_size || 50);
      const hasMore = Boolean(payload?.has_more);
      return {
        cards,
        total,
        page,
        page_size: pageSize,
        has_more: hasMore,
        stats: payload?.stats || {
          total_count: total,
          category_counts: {},
          total_active_seconds: 0,
          avg_interval_seconds: 0,
          date_range: {
            start: this.filters.date_from || this.filters.date || "",
            end: this.filters.date_to || this.filters.date || "",
          },
        },
        categories: Array.isArray(payload?.categories) ? payload.categories : null,
        trees: Array.isArray(payload?.trees) ? payload.trees : null,
        fallback: Boolean(payload?.fallback),
      };
    }

    isCardsApiMissing(error) {
      const text = String(error instanceof Error ? error.message : error || "").toLowerCase();
      return text.includes("404") || text.includes("not found") || text.includes("/api/cards");
    }

    async fetchCards(filters) {
      try {
        const query = this.queryStringFromFilters(filters);
        const payload = await this.apiRequest(`/api/cards?${query}`);
        return this.normalizePayload(payload);
      } catch (error) {
        if (!this.fallbackLoader || !this.isCardsApiMissing(error)) {
          throw error;
        }
        const fallback = await this.fallbackLoader(filters);
        return this.normalizePayload({ ...fallback, fallback: true });
      }
    }

    setLoadingState(loading, message = "") {
      this.state.loading = loading;
      if (!this.dom.state) return;
      this.dom.state.classList.remove("error", "warning");
      if (loading) {
        this.dom.state.textContent = message || "Loading cards...";
        return;
      }
      if (message) {
        this.dom.state.textContent = message;
      }
    }

    updateSummary() {
      if (this.dom.results) {
        this.dom.results.textContent = `${this.state.total} records`;
      }
      if (this.dom.mode) {
        this.dom.mode.textContent = this.state.backendMode === "fallback" ? "Fallback" : "API";
        this.dom.mode.classList.toggle("fallback", this.state.backendMode === "fallback");
      }
    }

    buildGroupHeader(group) {
      const head = document.createElement("div");
      head.className = "cards-time-group";
      head.innerHTML = `<span>${escapeHtml(group.label)}</span><span>${group.cards.length}条 · 主要：${escapeHtml(group.majorCategory || "-")}</span>`;
      return head;
    }

    renderTimelineCard(cardData, prevCard, isLast) {
      const row = document.createElement("div");
      row.className = "cards-timeline-item";
      if (isLast) {
        row.classList.add("is-last");
      }

      const rail = document.createElement("div");
      rail.className = "cards-timeline-rail";

      const dot = document.createElement("i");
      dot.className = "cards-timeline-dot";
      dot.style.background = resolveCategoryColor(cardData.category);

      const line = document.createElement("i");
      line.className = "cards-timeline-line";

      const gap = document.createElement("span");
      gap.className = "cards-timeline-gap";
      const gapMin = intervalMinutes(prevCard, cardData);
      if (gapMin !== null && prevCard) {
        gap.textContent = formatGapLabel(gapMin);
        if (gapMin > 30) {
          line.classList.add("long-gap");
        }
      } else {
        gap.textContent = "";
      }

      rail.append(dot, line, gap);

      const body = document.createElement("div");
      body.className = "cards-timeline-body";
      const Card = window.Card;
      const card = new Card(cardData, {
        highlight: this.filters.search,
        editable: this.state.backendMode !== "fallback",
        onNotify: (text, level = "info") => this.onNotify(text, level),
        onCopy: () => Promise.resolve(),
        onEdit: (cardId, patch, current) => this.updateCard(cardId, patch, current),
        onDelete: (cardId) => this.deleteCard(cardId),
        onViewTree: (data) => this.onViewTree(data),
      });
      body.appendChild(card.render());

      row.append(rail, body);
      return row;
    }

    renderCards() {
      if (!this.dom.list) return;
      this.dom.list.innerHTML = "";
      if (!this.state.cards.length) {
        this.dom.state.textContent = "No cards found for current filters.";
        this.dom.state.classList.remove("error");
        this.dom.state.classList.add("warning");
        return;
      }

      this.dom.state.textContent = this.state.backendMode === "fallback"
        ? "Cards API not detected. Showing fallback cards from tree data."
        : "";
      this.dom.state.classList.toggle("warning", this.state.backendMode === "fallback");
      this.dom.state.classList.remove("error");

      const fragment = document.createDocumentFragment();
      const groups = groupCardsByTime(this.state.cards);

      for (const group of groups) {
        const block = document.createElement("section");
        block.className = "cards-time-group-block";
        block.appendChild(this.buildGroupHeader(group));

        const list = document.createElement("div");
        list.className = "cards-time-group-list";
        let prevCard = null;
        group.cards.forEach((item, index) => {
          const timelineCard = this.renderTimelineCard(item, prevCard, index === group.cards.length - 1);
          list.appendChild(timelineCard);
          prevCard = item;
        });

        block.appendChild(list);
        fragment.appendChild(block);
      }

      this.dom.list.appendChild(fragment);
    }

    async loadCards(nextFilters = {}, options = {}) {
      const merged = {
        ...this.filters,
        ...nextFilters,
      };
      if (!merged.date && !merged.date_from && !merged.date_to) {
        merged.date = this.getDefaultDate() || this.filters.date || "";
      }
      merged.page = Math.max(1, Number(merged.page || 1));
      merged.page_size = clamp(Number(merged.page_size || this.filters.page_size || 50), 10, 200);
      merged.categories = Array.isArray(merged.categories) ? merged.categories : splitList(merged.categories);
      merged.tree_ids = Array.isArray(merged.tree_ids) ? merged.tree_ids : splitList(merged.tree_ids);
      this.filters = merged;

      if (this.filterBar) {
        this.filterBar.setFilters(this.filters, { silent: true });
      }
      if (options.syncUrl !== false) {
        this.syncFiltersToUrl();
      }

      this.setLoadingState(true, "Loading cards...");
      try {
        const payload = await this.fetchCards(this.filters);
        this.state.cards = payload.cards;
        this.state.total = payload.total;
        this.state.page = payload.page;
        this.state.page_size = payload.page_size;
        this.state.has_more = payload.has_more;
        this.state.stats = payload.stats;
        this.state.backendMode = payload.fallback ? "fallback" : "api";
        this.state.loaded = true;

        this.updateSummary();
        this.statsPanel?.update(this.state.stats);
        this.filterBar?.setMeta({
          categories: payload.categories || this.getCategories(),
          trees: payload.trees || this.getTrees(),
          categoryCounts: this.state.stats?.category_counts || {},
        });
        this.pagination?.update(this.state.page, this.state.total, this.state.page_size);
        this.renderCards();
      } catch (error) {
        this.state.loaded = false;
        this.state.cards = [];
        this.state.total = 0;
        this.state.backendMode = "api";
        this.updateSummary();
        this.statsPanel?.update(null);
        this.pagination?.update(1, 0, this.filters.page_size || 50);
        if (this.dom.list) this.dom.list.innerHTML = "";
        if (this.dom.state) {
          this.dom.state.textContent = `Failed to load cards: ${error instanceof Error ? error.message : String(error)}`;
          this.dom.state.classList.add("error");
        }
        throw error;
      } finally {
        this.state.loading = false;
      }
    }

    async updateCard(cardId, patch, current) {
      if (this.state.backendMode === "fallback") {
        throw new Error("Cards API unavailable in fallback mode");
      }
      const payload = await this.apiRequest(`/api/cards/${encodeURIComponent(cardId)}`, "PUT", patch);
      const updated = payload?.card || payload || patch;
      this.state.cards = this.state.cards.map((item) => {
        if (item.id !== cardId) return item;
        return {
          ...item,
          ...current,
          ...patch,
          ...updated,
        };
      });
      this.renderCards();
      return updated;
    }

    async deleteCard(cardId) {
      if (this.state.backendMode === "fallback") {
        throw new Error("Cards API unavailable in fallback mode");
      }
      await this.apiRequest(`/api/cards/${encodeURIComponent(cardId)}`, "DELETE");
      const nextTotal = Math.max(0, this.state.total - 1);
      const maxPage = Math.max(1, Math.ceil(nextTotal / Math.max(this.state.page_size, 1)));
      const nextPage = clamp(this.state.page, 1, maxPage);
      await this.loadCards({ page: nextPage });
    }

    async exportCards() {
      const formatInput = window.prompt("Export format: markdown/json/csv", "markdown");
      const format = String(formatInput || "markdown").toLowerCase();
      if (!["markdown", "json", "csv"].includes(format)) {
        throw new Error("Unsupported format");
      }

      if (this.state.backendMode !== "fallback") {
        const response = await fetch("/api/cards/export", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            format,
            filters: this.filters,
          }),
        });
        if (response.ok) {
          const blob = await response.blob();
          const ext = format === "json" ? "json" : format === "csv" ? "csv" : "md";
          const name = `watcher-cards-${formatDateStamp(new Date().toISOString().slice(0, 10))}.${ext}`;
          fileDownload(blob, name, blob.type || "application/octet-stream");
          this.onNotify(`Exported ${this.state.total} cards (${format})`);
          return;
        }
      }

      const cards = this.state.cards || [];
      const baseName = `watcher-cards-${formatDateStamp(new Date().toISOString().slice(0, 10))}`;
      if (format === "json") {
        fileDownload(JSON.stringify(cards, null, 2), `${baseName}.json`, "application/json;charset=utf-8");
      } else if (format === "csv") {
        fileDownload(toCSV(cards), `${baseName}.csv`, "text/csv;charset=utf-8");
      } else {
        fileDownload(toMarkdown(cards), `${baseName}.md`, "text/markdown;charset=utf-8");
      }
      this.onNotify(`Exported ${cards.length} cards (${format}, local)`);
    }

    async defaultApiRequest(path, method = "GET", body = null) {
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
        payload = { message: raw || `HTTP ${response.status}` };
      }
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.message || `HTTP ${response.status}`);
      }
      return Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
    }
  }

  window.CardView = CardView;
})();
