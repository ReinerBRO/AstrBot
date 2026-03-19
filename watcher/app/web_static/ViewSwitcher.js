(() => {
  const STORAGE_KEY = "watcher_view_mode";
  const VALID_VIEWS = ["tree", "cards", "flow", "summary", "logs"];

  function normalizeView(view) {
    return VALID_VIEWS.includes(view) ? view : "tree";
  }

  class ViewSwitcher {
    constructor(container, onViewChange, options = {}) {
      this.container = container;
      this.onViewChange = typeof onViewChange === "function" ? onViewChange : () => {};
      this.views = options.views || [
        { id: "tree", label: "Tree", icon: "🌳" },
        { id: "cards", label: "Cards", icon: "📋" },
        { id: "flow", label: "Flow", icon: "🔀" },
        { id: "summary", label: "Summary", icon: "📊" },
        { id: "logs", label: "Logs", icon: "📄" },
      ];
      this.activeView = normalizeView(options.initialView || this.resolveInitialView());
      this.buttons = new Map();
      this.handlePopState = this.handlePopState.bind(this);
      this.render();
      window.addEventListener("popstate", this.handlePopState);
    }

    resolveInitialView() {
      const params = new URLSearchParams(window.location.search);
      const fromUrl = normalizeView(params.get("view") || "");
      if (fromUrl !== "tree" || (params.get("view") || "").trim() === "tree") {
        return fromUrl;
      }
      try {
        const saved = localStorage.getItem(STORAGE_KEY) || "";
        if (VALID_VIEWS.includes(saved)) {
          return saved;
        }
      } catch (error) {
      }
      return "tree";
    }

    render() {
      if (!this.container) return;
      this.container.innerHTML = "";
      const shell = document.createElement("div");
      shell.className = "view-switcher";
      shell.setAttribute("role", "tablist");
      shell.setAttribute("aria-label", "Display mode");

      for (const view of this.views) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "view-switcher-btn";
        button.dataset.view = view.id;
        button.setAttribute("role", "tab");
        button.innerHTML = `<span class="icon" aria-hidden="true">${view.icon || ""}</span><span>${view.label}</span>`;
        button.addEventListener("click", () => this.setActiveView(view.id));
        this.buttons.set(view.id, button);
        shell.appendChild(button);
      }

      this.container.appendChild(shell);
      this.syncButtonState();
    }

    handlePopState() {
      const params = new URLSearchParams(window.location.search);
      const fromUrl = normalizeView(params.get("view") || "");
      this.setActiveView(fromUrl, { silent: false, syncUrl: false });
    }

    syncButtonState() {
      for (const [viewId, button] of this.buttons.entries()) {
        const active = viewId === this.activeView;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
        button.tabIndex = active ? 0 : -1;
      }
    }

    syncStorage() {
      try {
        localStorage.setItem(STORAGE_KEY, this.activeView);
      } catch (error) {
      }
    }

    syncUrl() {
      const url = new URL(window.location.href);
      url.searchParams.set("view", this.activeView);
      window.history.replaceState({}, "", url);
    }

    getActiveView() {
      return this.activeView;
    }

    setActiveView(view, options = {}) {
      const nextView = normalizeView(view);
      const { silent = false, syncUrl = true } = options;
      const changed = this.activeView !== nextView;
      this.activeView = nextView;
      this.syncButtonState();
      this.syncStorage();
      if (syncUrl) {
        this.syncUrl();
      }
      if (changed || !silent) {
        this.onViewChange(this.activeView);
      }
    }
  }

  window.ViewSwitcher = ViewSwitcher;
})();
