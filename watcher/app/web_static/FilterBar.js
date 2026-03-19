(() => {
  function splitList(value) {
    return [...new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean))];
  }

  function toISODate(date) {
    return date.toISOString().slice(0, 10);
  }

  function todayISO() {
    return toISODate(new Date());
  }

  function shiftDate(baseISO, delta) {
    const value = new Date(`${baseISO}T00:00:00`);
    if (Number.isNaN(value.getTime())) return baseISO;
    value.setDate(value.getDate() + delta);
    return toISODate(value);
  }

  class FilterBar {
    constructor(container, onFilterChange, options = {}) {
      this.container = container;
      this.onFilterChange = typeof onFilterChange === "function" ? onFilterChange : () => {};
      this.onExport = typeof options.onExport === "function" ? options.onExport : null;
      this.categoryOptions = Array.isArray(options.categories) ? options.categories : [];
      this.treeOptions = Array.isArray(options.trees) ? options.trees : [];
      this.categoryCounts = options.categoryCounts || {};
      this.searchDebounceMs = 300;
      this.searchTimer = 0;
      this.filters = {
        date: options.date || "",
        date_from: options.date_from || "",
        date_to: options.date_to || "",
        categories: Array.isArray(options.categoriesSelected) ? options.categoriesSelected : [],
        tree_ids: Array.isArray(options.tree_ids) ? options.tree_ids : [],
        search: options.search || "",
        sort: options.sort || "time_desc",
        page_size: Number.isFinite(options.page_size) ? options.page_size : 50,
      };
      this.dom = {};
      this.render();
      this.syncUi();
    }

    render() {
      if (!this.container) return;
      this.container.innerHTML = `
        <section class="cards-filter-bar" aria-label="Cards Filters">
          <div class="cards-filter-row cards-filter-row-main">
            <label class="cards-field">
              Date
              <input type="date" data-field="date" />
            </label>
            <label class="cards-field">
              From
              <input type="date" data-field="date_from" />
            </label>
            <label class="cards-field">
              To
              <input type="date" data-field="date_to" />
            </label>
            <label class="cards-field">
              Tree
              <select data-field="tree_id"></select>
            </label>
            <label class="cards-field">
              Sort
              <select data-field="sort">
                <option value="time_desc">Newest First</option>
                <option value="time_asc">Oldest First</option>
              </select>
            </label>
            <label class="cards-field cards-search-field">
              Search
              <input type="search" data-field="search" placeholder="Search summary/category/time" />
            </label>
          </div>
          <div class="cards-filter-row cards-filter-row-quick">
            <div class="cards-quick-group" role="group" aria-label="Date Shortcuts">
              <button type="button" class="btn btn-ghost cards-quick" data-quick="today">Today</button>
              <button type="button" class="btn btn-ghost cards-quick" data-quick="yesterday">Yesterday</button>
              <button type="button" class="btn btn-ghost cards-quick" data-quick="week">Last 7 Days</button>
            </div>
            <div class="cards-action-group">
              <button type="button" class="btn btn-ghost" data-action="reset">Reset Filters</button>
              <button type="button" class="btn btn-primary" data-action="export">Export</button>
            </div>
          </div>
          <div class="cards-category-group" data-field="categories" role="group" aria-label="Category Filters"></div>
        </section>
      `;

      const root = this.container.querySelector(".cards-filter-bar");
      this.dom.root = root;
      this.dom.date = root.querySelector('input[data-field="date"]');
      this.dom.dateFrom = root.querySelector('input[data-field="date_from"]');
      this.dom.dateTo = root.querySelector('input[data-field="date_to"]');
      this.dom.tree = root.querySelector('select[data-field="tree_id"]');
      this.dom.sort = root.querySelector('select[data-field="sort"]');
      this.dom.search = root.querySelector('input[data-field="search"]');
      this.dom.categories = root.querySelector('[data-field="categories"]');
      this.dom.reset = root.querySelector('[data-action="reset"]');
      this.dom.export = root.querySelector('[data-action="export"]');
      this.dom.quick = [...root.querySelectorAll(".cards-quick")];

      this.dom.date?.addEventListener("change", () => {
        this.filters.date = this.dom.date.value;
        if (this.filters.date) {
          this.filters.date_from = "";
          this.filters.date_to = "";
        }
        this.emitChange({ page: 1 });
      });

      this.dom.dateFrom?.addEventListener("change", () => {
        this.filters.date_from = this.dom.dateFrom.value;
        if (this.filters.date_from) {
          this.filters.date = "";
        }
        this.emitChange({ page: 1 });
      });

      this.dom.dateTo?.addEventListener("change", () => {
        this.filters.date_to = this.dom.dateTo.value;
        if (this.filters.date_to) {
          this.filters.date = "";
        }
        this.emitChange({ page: 1 });
      });

      this.dom.tree?.addEventListener("change", () => {
        const value = this.dom.tree.value;
        this.filters.tree_ids = value ? [value] : [];
        this.emitChange({ page: 1 });
      });

      this.dom.sort?.addEventListener("change", () => {
        this.filters.sort = this.dom.sort.value;
        this.emitChange({ page: 1 });
      });

      this.dom.search?.addEventListener("input", () => {
        this.filters.search = this.dom.search.value.trim();
        window.clearTimeout(this.searchTimer);
        this.searchTimer = window.setTimeout(() => this.emitChange({ page: 1 }), this.searchDebounceMs);
      });

      this.dom.reset?.addEventListener("click", () => {
        this.reset();
      });

      this.dom.export?.addEventListener("click", () => {
        if (this.onExport) {
          this.onExport(this.getFilters());
        }
      });

      this.dom.quick.forEach((button) => {
        button.addEventListener("click", () => {
          const type = button.dataset.quick || "today";
          const today = todayISO();
          if (type === "today") {
            this.filters.date = today;
            this.filters.date_from = "";
            this.filters.date_to = "";
          } else if (type === "yesterday") {
            this.filters.date = shiftDate(today, -1);
            this.filters.date_from = "";
            this.filters.date_to = "";
          } else {
            this.filters.date = "";
            this.filters.date_from = shiftDate(today, -6);
            this.filters.date_to = today;
          }
          this.syncUi();
          this.emitChange({ page: 1 });
        });
      });

      this.renderCategoryFilters();
      this.renderTreeOptions();
    }

    renderTreeOptions() {
      if (!this.dom.tree) return;
      const current = this.filters.tree_ids?.[0] || "";
      this.dom.tree.innerHTML = "";
      const allOption = document.createElement("option");
      allOption.value = "";
      allOption.textContent = "All Trees";
      this.dom.tree.appendChild(allOption);
      for (const tree of this.treeOptions) {
        const option = document.createElement("option");
        option.value = tree.id;
        option.textContent = tree.name ? `${tree.name} (${tree.count || 0})` : tree.id;
        this.dom.tree.appendChild(option);
      }
      this.dom.tree.value = current;
    }

    renderCategoryFilters() {
      if (!this.dom.categories) return;
      this.dom.categories.innerHTML = "";
      const selected = new Set(this.filters.categories || []);
      for (const category of this.categoryOptions) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "cards-category-chip";
        button.dataset.category = category;
        if (selected.has(category)) {
          button.classList.add("active");
        }
        const count = Number(this.categoryCounts?.[category] || 0);
        button.innerHTML = `<span>${category}</span><b>${count}</b>`;
        button.addEventListener("click", () => {
          if (selected.has(category)) {
            selected.delete(category);
          } else {
            selected.add(category);
          }
          this.filters.categories = [...selected];
          this.renderCategoryFilters();
          this.emitChange({ page: 1 });
        });
        this.dom.categories.appendChild(button);
      }
    }

    setMeta(meta = {}) {
      if (Array.isArray(meta.categories)) {
        this.categoryOptions = meta.categories;
      }
      if (Array.isArray(meta.trees)) {
        this.treeOptions = meta.trees;
      }
      if (meta.categoryCounts && typeof meta.categoryCounts === "object") {
        this.categoryCounts = meta.categoryCounts;
      }
      const selectedSet = new Set(this.categoryOptions);
      this.filters.categories = (this.filters.categories || []).filter((item) => selectedSet.has(item));
      this.renderTreeOptions();
      this.renderCategoryFilters();
      this.syncUi();
    }

    setFilters(nextFilters = {}, options = {}) {
      const silent = Boolean(options.silent);
      this.filters = {
        ...this.filters,
        ...nextFilters,
        categories: Array.isArray(nextFilters.categories)
          ? nextFilters.categories
          : this.filters.categories,
        tree_ids: Array.isArray(nextFilters.tree_ids) ? nextFilters.tree_ids : this.filters.tree_ids,
      };
      if (typeof nextFilters.categories === "string") {
        this.filters.categories = splitList(nextFilters.categories);
      }
      if (typeof nextFilters.tree_ids === "string") {
        this.filters.tree_ids = splitList(nextFilters.tree_ids);
      }
      this.syncUi();
      if (!silent) {
        this.emitChange({ page: 1 });
      }
    }

    syncUi() {
      if (this.dom.date) this.dom.date.value = this.filters.date || "";
      if (this.dom.dateFrom) this.dom.dateFrom.value = this.filters.date_from || "";
      if (this.dom.dateTo) this.dom.dateTo.value = this.filters.date_to || "";
      if (this.dom.sort) this.dom.sort.value = this.filters.sort || "time_desc";
      if (this.dom.search) this.dom.search.value = this.filters.search || "";
      if (this.dom.tree) {
        const treeValue = (this.filters.tree_ids || [""])[0] || "";
        this.dom.tree.value = treeValue;
      }
      this.renderCategoryFilters();
    }

    reset() {
      this.filters = {
        date: "",
        date_from: "",
        date_to: "",
        categories: [],
        tree_ids: [],
        search: "",
        sort: "time_desc",
        page_size: this.filters.page_size || 50,
      };
      this.syncUi();
      this.emitChange({ page: 1 });
    }

    getFilters() {
      const payload = {
        date: this.filters.date || "",
        date_from: this.filters.date_from || "",
        date_to: this.filters.date_to || "",
        categories: [...(this.filters.categories || [])],
        tree_ids: [...(this.filters.tree_ids || [])],
        search: this.filters.search || "",
        sort: this.filters.sort || "time_desc",
        page_size: Number(this.filters.page_size || 50),
      };
      return payload;
    }

    emitChange(extra = {}) {
      const filters = {
        ...this.getFilters(),
        ...extra,
      };
      this.onFilterChange(filters);
    }
  }

  window.FilterBar = FilterBar;
})();
