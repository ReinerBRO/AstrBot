(() => {
  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function parseMinutes(timeText, fallback = 0) {
    const text = String(timeText || "");
    if (!/^\d{2}:\d{2}$/.test(text)) return fallback;
    const [hText, mText] = text.split(":");
    const h = Number.parseInt(hText, 10);
    const m = Number.parseInt(mText, 10);
    if (!Number.isFinite(h) || !Number.isFinite(m)) return fallback;
    return clamp(h, 0, 23) * 60 + clamp(m, 0, 59);
  }

  function formatHHMM(minutes) {
    let value = minutes % (24 * 60);
    if (value < 0) value += 24 * 60;
    const h = Math.floor(value / 60);
    const m = value % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  function dedupeCategories(categories, entries) {
    const ordered = [];
    for (const category of categories || []) {
      const text = String(category || "").trim();
      if (text && !ordered.includes(text)) ordered.push(text);
    }
    for (const entry of entries || []) {
      const text = String(entry.category || "").trim();
      if (text && !ordered.includes(text)) ordered.push(text);
    }
    return ordered.length ? ordered : ["写代码", "研究", "娱乐"];
  }

  function laneOffsetByIndex(index) {
    if (index <= 0) return -1;
    if (index === 1) return 1;
    const step = Math.floor((index - 2) / 2) + 2;
    return index % 2 === 0 ? step : -step;
  }

  function formatGapLabel(minutes) {
    const value = Math.max(0, Math.round(Number(minutes) || 0));
    if (value < 60) return `${value}m`;
    const hour = Math.floor(value / 60);
    const min = value % 60;
    return min ? `${hour}h ${min}m` : `${hour}h`;
  }

  function pathRoundedRect(ctx, x, y, width, height, radius) {
    const r = Math.max(0, Math.min(radius, width / 2, height / 2));
    if (typeof ctx.roundRect === "function") {
      ctx.beginPath();
      ctx.roundRect(x, y, width, height, r);
      return;
    }
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
  }

  class FlowView {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.options = options;
      this.entries = [];
      this.categories = [];
      this.nodes = [];
      this.edges = [];
      this.visibleNodeIndices = [];
      this.visibleEdgeIndices = [];
      this.laneX = new Map();

      this.zoom = 1.15;
      this.minZoom = 0.75;
      this.maxZoom = 4.2;
      this.offsetY = 0;
      this.selectedIndex = -1;
      this.hoverIndex = -1;
      this.message = "";

      this.metrics = {
        width: 0,
        height: 0,
        padTop: 56,
        padBottom: 36,
        padLeft: 84,
        padRight: 36,
        baseMinMinute: 9 * 60,
        baseMaxMinute: 18 * 60,
        minuteSpan: 1,
        scaleY: 1,
        timelineX: 0,
        minNodeGap: 20,
      };

      this.drag = {
        active: false,
        pending: false,
        startClientY: 0,
        startOffsetY: 0,
      };

      this.handleMouseMove = this.handleMouseMove.bind(this);
      this.handleMouseDown = this.handleMouseDown.bind(this);
      this.handleMouseUp = this.handleMouseUp.bind(this);
      this.handleMouseLeave = this.handleMouseLeave.bind(this);
      this.handleWheel = this.handleWheel.bind(this);
      this.handleClick = this.handleClick.bind(this);
      this.attachEvents();
      this.resize();
    }

    attachEvents() {
      if (!this.canvas) return;
      this.canvas.addEventListener("mousemove", this.handleMouseMove);
      this.canvas.addEventListener("mousedown", this.handleMouseDown);
      this.canvas.addEventListener("mouseleave", this.handleMouseLeave);
      this.canvas.addEventListener("wheel", this.handleWheel, { passive: false });
      this.canvas.addEventListener("click", this.handleClick);
      window.addEventListener("mouseup", this.handleMouseUp);
    }

    detachEvents() {
      if (!this.canvas) return;
      this.canvas.removeEventListener("mousemove", this.handleMouseMove);
      this.canvas.removeEventListener("mousedown", this.handleMouseDown);
      this.canvas.removeEventListener("mouseleave", this.handleMouseLeave);
      this.canvas.removeEventListener("wheel", this.handleWheel);
      this.canvas.removeEventListener("click", this.handleClick);
      window.removeEventListener("mouseup", this.handleMouseUp);
    }

    destroy() {
      this.detachEvents();
    }

    getCategoryColor(category) {
      if (typeof this.options.getCategoryColor === "function") {
        return this.options.getCategoryColor(category);
      }
      return "#9ba8bb";
    }

    isLightTheme() {
      return document.documentElement.getAttribute("data-theme") === "light";
    }

    palette() {
      if (this.isLightTheme()) {
        return {
          bgTop: "rgba(245, 250, 255, 0.96)",
          bgBottom: "rgba(231, 241, 252, 0.98)",
          timeline: "rgba(66, 101, 138, 0.52)",
          majorGrid: "rgba(86, 119, 154, 0.28)",
          minorGrid: "rgba(104, 136, 170, 0.14)",
          axisText: "rgba(33, 66, 98, 0.88)",
          laneText: "rgba(30, 59, 89, 0.96)",
          nodeStroke: "rgba(245, 251, 255, 0.98)",
          labelText: "rgba(26, 61, 95, 0.86)",
          labelBg: "rgba(246, 251, 255, 0.92)",
          labelBorder: "rgba(90, 123, 157, 0.34)",
          switchText: "rgba(120, 84, 25, 0.95)",
          switchBg: "rgba(255, 237, 198, 0.88)",
          switchBorder: "rgba(216, 166, 77, 0.44)",
        };
      }
      return {
        bgTop: "rgba(16, 26, 38, 0.96)",
        bgBottom: "rgba(10, 18, 28, 0.98)",
        timeline: "rgba(186, 211, 236, 0.44)",
        majorGrid: "rgba(170, 197, 224, 0.24)",
        minorGrid: "rgba(156, 185, 214, 0.12)",
        axisText: "rgba(194, 217, 240, 0.9)",
        laneText: "rgba(222, 236, 250, 0.96)",
        nodeStroke: "rgba(9, 16, 24, 0.95)",
        labelText: "rgba(208, 226, 244, 0.9)",
        labelBg: "rgba(10, 19, 30, 0.88)",
        labelBorder: "rgba(162, 191, 221, 0.3)",
        switchText: "rgba(252, 219, 152, 0.98)",
        switchBg: "rgba(68, 47, 15, 0.72)",
        switchBorder: "rgba(243, 190, 99, 0.42)",
      };
    }

    setMessage(message = "") {
      this.message = String(message || "");
      if (typeof this.options.onMessage === "function") {
        this.options.onMessage(this.message);
      }
    }

    setData(entries, categories) {
      this.entries = Array.isArray(entries) ? entries : [];
      this.categories = dedupeCategories(categories, this.entries);
      this.buildFlowGraph(this.entries, this.categories);
      if (!this.nodes.length) {
        this.setMessage("No activity entries for this tree yet.");
      } else {
        this.setMessage("");
      }
      this.render();
    }

    buildFlowGraph(entries = this.entries, categories = this.categories) {
      const sorted = [...entries]
        .map((entry, index) => {
          const minute = parseMinutes(entry.time, 9 * 60);
          return {
            ...entry,
            _index: index,
            minute,
          };
        })
        .sort((a, b) => a.minute - b.minute || a._index - b._index);

      const lanes = dedupeCategories(categories, sorted);
      const laneMap = new Map(lanes.map((category, laneIndex) => [category, laneIndex]));

      this.nodes = sorted.map((entry, index) => {
        const lane = laneMap.get(entry.category) ?? 0;
        return {
          id: `${entry.time || "--:--"}-${index}`,
          index,
          minute: entry.minute,
          time: entry.time || formatHHMM(entry.minute),
          category: entry.category || "未分类",
          summary: entry.summary || "",
          source: entry.source || "",
          confidence: Number(entry.confidence || 0),
          topApp: entry.top_app || entry.topApp || entry.event_data?.top_app || "",
          clickCount: Number(entry.click_count || entry.event_data?.click_count || 0),
          activeSeconds: Number(entry.active_seconds || entry.event_data?.active_seconds || 0),
          lane,
          x: 0,
          y: 0,
          color: this.getCategoryColor(entry.category),
        };
      });

      this.edges = [];
      for (let i = 1; i < this.nodes.length; i += 1) {
        const from = this.nodes[i - 1];
        const to = this.nodes[i];
        this.edges.push({
          fromIndex: i - 1,
          toIndex: i,
          type: from.lane === to.lane ? "same" : "switch",
          gapMinutes: Math.max(0, to.minute - from.minute),
        });
      }

      const minutes = this.nodes.map((node) => node.minute);
      const minMinute = minutes.length ? Math.min(...minutes) : 9 * 60;
      const maxMinute = minutes.length ? Math.max(...minutes) : 18 * 60;
      this.metrics.baseMinMinute = minMinute - 10;
      this.metrics.baseMaxMinute = Math.max(maxMinute + 10, this.metrics.baseMinMinute + 1);
      this.metrics.minuteSpan = Math.max(1, this.metrics.baseMaxMinute - this.metrics.baseMinMinute);

      this.computeLaneX(lanes);
    }

    computeLaneX(categories) {
      this.laneX.clear();
      const laneCount = Math.max(1, categories.length);
      const { width, padLeft, padRight } = this.metrics;
      const innerWidth = Math.max(120, width - padLeft - padRight);
      const centerX = padLeft + innerWidth * 0.5;
      const offsets = [];
      for (let index = 0; index < laneCount; index += 1) {
        offsets.push(laneOffsetByIndex(index));
      }
      const maxOffset = Math.max(1, ...offsets.map((value) => Math.abs(value)));
      const spacing = laneCount <= 1
        ? 0
        : Math.min(160, innerWidth / (maxOffset * 2 + 0.75));

      categories.forEach((_category, index) => {
        const offset = offsets[index] ?? 0;
        this.laneX.set(index, centerX + offset * spacing);
      });
      this.metrics.timelineX = centerX;
    }

    minuteToY(minute) {
      const { padTop, baseMinMinute, scaleY, offsetY } = this.metrics;
      return padTop + (minute - baseMinMinute) * scaleY + offsetY;
    }

    yToMinute(y) {
      const { padTop, baseMinMinute, scaleY, offsetY } = this.metrics;
      return baseMinMinute + (y - padTop - offsetY) / Math.max(scaleY, 0.001);
    }

    clampOffsetY() {
      const { height, padTop, padBottom, minuteSpan } = this.metrics;
      const viewportHeight = Math.max(1, height - padTop - padBottom);
      const contentHeight = minuteSpan * this.metrics.scaleY;
      const minOffset = Math.min(0, viewportHeight - contentHeight) - 4;
      const maxOffset = 4;
      this.offsetY = clamp(this.offsetY, minOffset, maxOffset);
      this.metrics.offsetY = this.offsetY;
    }

    resize() {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      this.metrics.width = Math.max(1, rect.width || this.canvas.clientWidth || 0);
      this.metrics.height = Math.max(1, rect.height || this.canvas.clientHeight || 0);
      const targetW = Math.max(1, Math.floor(this.metrics.width * ratio));
      const targetH = Math.max(1, Math.floor(this.metrics.height * ratio));
      if (this.canvas.width !== targetW || this.canvas.height !== targetH) {
        this.canvas.width = targetW;
        this.canvas.height = targetH;
      }
      this.updateScale();
      this.computeLaneX(this.categories);
      this.render();
    }

    updateScale() {
      const { height, padTop, padBottom, minuteSpan } = this.metrics;
      const drawable = Math.max(1, height - padTop - padBottom);
      this.metrics.scaleY = (drawable / Math.max(minuteSpan, 1)) * this.zoom;
      this.clampOffsetY();
    }

    setZoom(scale) {
      this.zoom = clamp(Number(scale) || 1, this.minZoom, this.maxZoom);
      this.updateScale();
      this.render();
    }

    getZoom() {
      return this.zoom;
    }

    resetView() {
      this.zoom = 1.15;
      this.offsetY = 0;
      this.selectedIndex = -1;
      this.hoverIndex = -1;
      this.updateScale();
      this.render();
    }

    updateNodeLayout() {
      const laneLastY = new Map();
      let lastGlobalY = Number.NEGATIVE_INFINITY;
      this.visibleNodeIndices = [];

      for (const node of this.nodes) {
        node.x = this.laneX.get(node.lane) ?? this.metrics.timelineX;
        const baseY = this.minuteToY(node.minute);
        const laneY = laneLastY.get(node.lane) ?? Number.NEGATIVE_INFINITY;
        node.y = Math.max(
          baseY,
          laneY + this.metrics.minNodeGap,
          lastGlobalY + this.metrics.minNodeGap * 0.5,
        );
        laneLastY.set(node.lane, node.y);
        lastGlobalY = node.y;
        if (this.isVisibleY(node.y, 40)) {
          this.visibleNodeIndices.push(node.index);
        }
      }

      this.visibleEdgeIndices = [];
      for (let i = 0; i < this.edges.length; i += 1) {
        const edge = this.edges[i];
        const from = this.nodes[edge.fromIndex];
        const to = this.nodes[edge.toIndex];
        if (!from || !to) continue;
        const minY = Math.min(from.y, to.y);
        const maxY = Math.max(from.y, to.y);
        if (maxY >= -48 && minY <= this.metrics.height + 48) {
          this.visibleEdgeIndices.push(i);
        }
      }
    }

    isVisibleY(y, pad = 0) {
      return y >= -pad && y <= this.metrics.height + pad;
    }

    render() {
      if (!this.canvas) return;
      const ctx = this.canvas.getContext("2d");
      if (!ctx) return;
      const ratio = window.devicePixelRatio || 1;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      ctx.scale(ratio, ratio);

      this.updateNodeLayout();
      this.drawBackground(ctx);
      this.drawTimeline(ctx);
      this.drawLaneHeaders(ctx);
      this.drawEdges(ctx);
      this.drawDurationLabels(ctx);
      this.drawSwitchLabels(ctx);
      this.drawNodes(ctx);
    }

    drawBackground(ctx) {
      const { width, height } = this.metrics;
      const palette = this.palette();
      const bg = ctx.createLinearGradient(0, 0, 0, height);
      bg.addColorStop(0, palette.bgTop);
      bg.addColorStop(1, palette.bgBottom);
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, width, height);
    }

    drawTimeline(ctx) {
      const { timelineX, width, height, padTop, padBottom, padLeft, padRight, baseMinMinute, baseMaxMinute } = this.metrics;
      const palette = this.palette();
      const scaleY = this.metrics.scaleY;
      const majorStep = scaleY >= 4.5 ? 60 : scaleY >= 2.4 ? 120 : 180;
      const minorStep = majorStep / 2;

      ctx.strokeStyle = palette.timeline;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.moveTo(timelineX, padTop - 4);
      ctx.lineTo(timelineX, height - padBottom + 4);
      ctx.stroke();

      const firstTick = Math.ceil(baseMinMinute / minorStep) * minorStep;
      let lastLabelY = Number.NEGATIVE_INFINITY;
      ctx.font = '600 10px "IBM Plex Mono", monospace';
      ctx.fillStyle = palette.axisText;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      for (let minute = firstTick; minute <= baseMaxMinute; minute += minorStep) {
        const y = this.minuteToY(minute);
        if (y < padTop - 24 || y > height - padBottom + 24) continue;
        const isMajor = minute % majorStep === 0;
        ctx.strokeStyle = isMajor ? palette.majorGrid : palette.minorGrid;
        ctx.setLineDash(isMajor ? [2.5, 6] : [2, 10]);
        ctx.beginPath();
        ctx.moveTo(padLeft, y);
        ctx.lineTo(width - padRight, y);
        ctx.stroke();
        ctx.setLineDash([]);

        if (isMajor && Math.abs(y - lastLabelY) >= 20) {
          lastLabelY = y;
          ctx.fillText(formatHHMM(minute), 12, y);
        }
      }
    }

    drawLaneHeaders(ctx) {
      const { padTop } = this.metrics;
      const palette = this.palette();
      ctx.font = '700 11px "IBM Plex Mono", monospace';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (const [lane, x] of this.laneX.entries()) {
        const category = this.categories[lane] || `Lane ${lane + 1}`;
        const y = padTop - 14;
        const width = Math.max(64, ctx.measureText(category).width + 20);
        const height = 20;
        pathRoundedRect(ctx, x - width / 2, y - height / 2, width, height, 999);
        ctx.fillStyle = this.isLightTheme()
          ? "rgba(92, 132, 170, 0.14)"
          : "rgba(122, 172, 231, 0.14)";
        ctx.fill();
        ctx.strokeStyle = this.isLightTheme()
          ? "rgba(112, 145, 180, 0.42)"
          : "rgba(166, 195, 225, 0.32)";
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = palette.laneText;
        ctx.fillText(category, x, y + 0.5);
      }
    }

    drawEdges(ctx) {
      const palette = this.palette();
      for (const edgeIndex of this.visibleEdgeIndices) {
        const edge = this.edges[edgeIndex];
        const from = this.nodes[edge.fromIndex];
        const to = this.nodes[edge.toIndex];
        if (!from || !to) continue;

        ctx.lineWidth = edge.type === "same" ? 1.7 : 2.15;
        ctx.strokeStyle = edge.type === "same"
          ? palette.majorGrid
          : palette.switchBorder;
        ctx.beginPath();
        if (edge.type === "same") {
          ctx.moveTo(from.x, from.y);
          ctx.lineTo(to.x, to.y);
        } else {
          const controlY = (from.y + to.y) / 2;
          const bend = (to.x - from.x) * 0.55;
          ctx.moveTo(from.x, from.y);
          ctx.bezierCurveTo(
            from.x + bend,
            controlY,
            to.x - bend,
            controlY,
            to.x,
            to.y,
          );
        }
        ctx.stroke();
      }
    }

    drawDurationLabels(ctx) {
      const palette = this.palette();
      let lastY = Number.NEGATIVE_INFINITY;
      ctx.font = '600 9px "IBM Plex Mono", monospace';
      ctx.fillStyle = palette.labelText;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (const edgeIndex of this.visibleEdgeIndices) {
        const edge = this.edges[edgeIndex];
        if (edge.gapMinutes < 20) continue;
        const from = this.nodes[edge.fromIndex];
        const to = this.nodes[edge.toIndex];
        if (!from || !to) continue;
        const x = (from.x + to.x) * 0.5;
        const y = (from.y + to.y) / 2;
        if (Math.abs(y - lastY) < 24) continue;
        lastY = y;
        const text = formatGapLabel(edge.gapMinutes);
        const textWidth = ctx.measureText(text).width;
        pathRoundedRect(ctx, x - textWidth / 2 - 6, y - 8, textWidth + 12, 16, 999);
        ctx.fillStyle = palette.labelBg;
        ctx.fill();
        ctx.strokeStyle = palette.labelBorder;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = palette.labelText;
        ctx.fillText(text, x, y);
      }
    }

    drawSwitchLabels(ctx) {
      const palette = this.palette();
      let lastY = Number.NEGATIVE_INFINITY;
      ctx.font = '700 9px "IBM Plex Mono", monospace';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (const edgeIndex of this.visibleEdgeIndices) {
        const edge = this.edges[edgeIndex];
        if (edge.type !== "switch" || edge.gapMinutes < 8) continue;
        const from = this.nodes[edge.fromIndex];
        const to = this.nodes[edge.toIndex];
        if (!from || !to) continue;
        const midY = (from.y + to.y) / 2;
        if (Math.abs(midY - lastY) < 26) continue;
        lastY = midY;
        const label = `-> ${to.category}`;
        const textWidth = ctx.measureText(label).width;
        const x = (from.x + to.x) / 2;
        const y = midY - 10;
        pathRoundedRect(ctx, x - textWidth / 2 - 6, y - 8, textWidth + 12, 16, 999);
        ctx.fillStyle = palette.switchBg;
        ctx.fill();
        ctx.strokeStyle = palette.switchBorder;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = palette.switchText;
        ctx.fillText(label, x, y);
      }
    }

    drawNodes(ctx) {
      const palette = this.palette();

      for (const index of this.visibleNodeIndices) {
        const node = this.nodes[index];
        const selected = index === this.selectedIndex;
        const hovered = index === this.hoverIndex;
        const radius = selected ? 7.4 : hovered ? 6.3 : 5.4;
        const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius * 2.6);
        glow.addColorStop(0, this.isLightTheme() ? "rgba(95, 146, 206, 0.3)" : "rgba(215, 236, 255, 0.26)");
        glow.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius * 2.6, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = node.color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.lineWidth = selected ? 2.3 : 1.35;
        ctx.strokeStyle = selected ? palette.timeline : palette.nodeStroke;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    hitTest(localX, localY) {
      for (let i = this.visibleNodeIndices.length - 1; i >= 0; i -= 1) {
        const index = this.visibleNodeIndices[i];
        const node = this.nodes[index];
        const dx = localX - node.x;
        const dy = localY - node.y;
        if (dx * dx + dy * dy <= 9 * 9) {
          return index;
        }
      }
      return -1;
    }

    showHover(index, event) {
      const node = this.nodes[index];
      if (!node || typeof this.options.onHover !== "function") return;
      this.options.onHover({
        time: node.time,
        category: node.category,
        summary: node.summary,
        color: node.color,
        clickCount: node.clickCount,
        topApp: node.topApp,
        activeSeconds: node.activeSeconds,
        source: node.source,
        confidence: node.confidence,
      }, event.clientX, event.clientY);
    }

    handleMouseMove(event) {
      if (this.drag.pending && !this.drag.active) {
        const delta = Math.abs(event.clientY - this.drag.startClientY);
        if (delta > 3) {
          this.drag.active = true;
          this.drag.pending = false;
          this.canvas.classList.add("is-panning");
          if (this.hoverIndex >= 0) {
            this.hoverIndex = -1;
            if (typeof this.options.onLeave === "function") {
              this.options.onLeave();
            }
          }
        }
        return;
      }

      if (this.drag.active) {
        const delta = event.clientY - this.drag.startClientY;
        this.offsetY = this.drag.startOffsetY + delta;
        this.metrics.offsetY = this.offsetY;
        this.clampOffsetY();
        this.render();
        return;
      }

      const rect = this.canvas.getBoundingClientRect();
      const index = this.hitTest(event.clientX - rect.left, event.clientY - rect.top);
      if (index !== this.hoverIndex) {
        this.hoverIndex = index;
        this.render();
      }
      if (index >= 0) {
        this.showHover(index, event);
      } else if (typeof this.options.onLeave === "function") {
        this.options.onLeave();
      }
    }

    handleMouseDown(event) {
      if (event.button !== 0) return;
      this.drag.pending = true;
      this.drag.active = false;
      this.drag.startClientY = event.clientY;
      this.drag.startOffsetY = this.offsetY;
    }

    handleMouseUp() {
      const wasDragging = this.drag.active;
      this.drag.active = false;
      this.drag.pending = false;
      if (wasDragging) {
        this.canvas.classList.remove("is-panning");
      }
    }

    handleMouseLeave() {
      this.hoverIndex = -1;
      if (typeof this.options.onLeave === "function") {
        this.options.onLeave();
      }
      this.render();
    }

    handleWheel(event) {
      event.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const localY = event.clientY - rect.top;
      const anchorMinute = this.yToMinute(localY);
      const factor = event.deltaY < 0 ? 1.11 : 0.9;
      const nextZoom = clamp(this.zoom * factor, this.minZoom, this.maxZoom);
      if (Math.abs(nextZoom - this.zoom) < 0.0001) return;

      this.zoom = nextZoom;
      this.updateScale();
      const anchoredY = this.minuteToY(anchorMinute);
      this.offsetY += localY - anchoredY;
      this.metrics.offsetY = this.offsetY;
      this.clampOffsetY();
      this.render();
    }

    handleClick(event) {
      const rect = this.canvas.getBoundingClientRect();
      const index = this.hitTest(event.clientX - rect.left, event.clientY - rect.top);
      this.selectedIndex = index;
      this.render();
      if (index >= 0 && typeof this.options.onSelect === "function") {
        this.options.onSelect(this.nodes[index]);
      }
    }
  }

  window.FlowView = FlowView;
})();
