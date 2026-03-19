(() => {
  const STORAGE_KEY = "watcher_cards_stats_collapsed";

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatHours(seconds) {
    const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
    if (safe < 3600) {
      return `${Math.round(safe / 60)}m`;
    }
    return `${(safe / 3600).toFixed(1)}h`;
  }

  function formatInterval(seconds) {
    const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
    if (!safe) return "-";
    if (safe < 60) return `${Math.round(safe)}s`;
    return `${(safe / 60).toFixed(1)}min`;
  }

  class StatsPanel {
    constructor(container) {
      this.container = container;
      this.collapsed = false;
      this.stats = null;
      this.dom = {};
      this.restoreCollapsed();
      this.render();
      this.update(null);
    }

    restoreCollapsed() {
      try {
        this.collapsed = localStorage.getItem(STORAGE_KEY) === "1";
      } catch (error) {
        this.collapsed = false;
      }
    }

    saveCollapsed() {
      try {
        localStorage.setItem(STORAGE_KEY, this.collapsed ? "1" : "0");
      } catch (error) {
      }
    }

    render() {
      if (!this.container) return;
      this.container.innerHTML = `
        <section class="cards-stats-panel" aria-label="Cards Statistics">
          <header class="cards-stats-head">
            <h3>Stats</h3>
            <button type="button" class="btn btn-ghost cards-stats-toggle" aria-expanded="true">Collapse</button>
          </header>
          <div class="cards-stats-body">
            <div class="cards-stats-bars" data-bars></div>
            <p class="cards-stats-summary" data-summary></p>
          </div>
        </section>
      `;

      const root = this.container.querySelector(".cards-stats-panel");
      this.dom.root = root;
      this.dom.body = root.querySelector(".cards-stats-body");
      this.dom.toggle = root.querySelector(".cards-stats-toggle");
      this.dom.bars = root.querySelector("[data-bars]");
      this.dom.summary = root.querySelector("[data-summary]");

      this.dom.toggle?.addEventListener("click", () => {
        this.collapsed = !this.collapsed;
        this.syncCollapsed();
        this.saveCollapsed();
      });

      this.syncCollapsed();
    }

    syncCollapsed() {
      if (!this.dom.body || !this.dom.toggle) return;
      this.dom.body.classList.toggle("hidden", this.collapsed);
      this.dom.toggle.textContent = this.collapsed ? "Expand" : "Collapse";
      this.dom.toggle.setAttribute("aria-expanded", this.collapsed ? "false" : "true");
    }

    renderBars(categoryCounts = {}, total = 0) {
      if (!this.dom.bars) return;
      this.dom.bars.innerHTML = "";
      const entries = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
      if (!entries.length || total <= 0) {
        const empty = document.createElement("p");
        empty.className = "cards-stats-empty";
        empty.textContent = "No category distribution yet.";
        this.dom.bars.appendChild(empty);
        return;
      }

      for (const [category, count] of entries) {
        const ratio = count / total;
        const row = document.createElement("article");
        row.className = "cards-stats-row";
        row.innerHTML = `
          <div class="cards-stats-track"><i style="width: ${(ratio * 100).toFixed(2)}%"></i></div>
          <div class="cards-stats-labels">
            <span>${escapeHtml(category)}</span>
            <b>${count}条 (${Math.round(ratio * 100)}%)</b>
          </div>
        `;
        this.dom.bars.appendChild(row);
      }
    }

    update(stats) {
      this.stats = stats || null;
      const total = Number(stats?.total_count || 0);
      const totalActive = formatHours(Number(stats?.total_active_seconds || 0));
      const avgInterval = formatInterval(Number(stats?.avg_interval_seconds || 0));

      this.renderBars(stats?.category_counts || {}, total);
      if (this.dom.summary) {
        this.dom.summary.textContent = `活跃 ${totalActive} · 平均间隔 ${avgInterval} · 共${total}条`;
      }
    }
  }

  window.StatsPanel = StatsPanel;
})();
