(() => {
  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function pageList(page, totalPages) {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const list = [1];
    const start = clamp(page - 1, 2, totalPages - 1);
    const end = clamp(page + 1, 2, totalPages - 1);
    if (start > 2) list.push("...");
    for (let current = start; current <= end; current += 1) {
      list.push(current);
    }
    if (end < totalPages - 1) list.push("...");
    list.push(totalPages);
    return list;
  }

  class Pagination {
    constructor(container, onPageChange) {
      this.container = container;
      this.onPageChange = typeof onPageChange === "function" ? onPageChange : () => {};
      this.page = 1;
      this.total = 0;
      this.pageSize = 50;
      this.dom = {};
      this.render();
      this.update(1, 0, 50);
    }

    render() {
      if (!this.container) return;
      this.container.innerHTML = `
        <nav class="cards-pagination" aria-label="Cards Pagination">
          <button type="button" class="btn btn-ghost" data-action="prev">Prev</button>
          <div class="cards-pagination-pages" data-pages></div>
          <button type="button" class="btn btn-ghost" data-action="next">Next</button>
          <span class="cards-pagination-info" data-info></span>
        </nav>
      `;
      this.dom.root = this.container.querySelector(".cards-pagination");
      this.dom.prev = this.container.querySelector('[data-action="prev"]');
      this.dom.next = this.container.querySelector('[data-action="next"]');
      this.dom.pages = this.container.querySelector("[data-pages]");
      this.dom.info = this.container.querySelector("[data-info]");

      this.dom.prev?.addEventListener("click", () => this.go(this.page - 1));
      this.dom.next?.addEventListener("click", () => this.go(this.page + 1));
    }

    go(page) {
      const totalPages = this.totalPages();
      const nextPage = clamp(page, 1, Math.max(totalPages, 1));
      if (nextPage === this.page) return;
      this.onPageChange(nextPage);
    }

    totalPages() {
      return Math.max(1, Math.ceil(this.total / Math.max(this.pageSize, 1)));
    }

    renderPages() {
      if (!this.dom.pages) return;
      this.dom.pages.innerHTML = "";
      const totalPages = this.totalPages();
      for (const item of pageList(this.page, totalPages)) {
        if (item === "...") {
          const ellipsis = document.createElement("span");
          ellipsis.className = "cards-page-ellipsis";
          ellipsis.textContent = "...";
          this.dom.pages.appendChild(ellipsis);
          continue;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "cards-page-btn";
        if (item === this.page) {
          button.classList.add("active");
        }
        button.textContent = String(item);
        button.addEventListener("click", () => this.go(item));
        this.dom.pages.appendChild(button);
      }
    }

    update(page, total, pageSize) {
      this.page = Math.max(1, Number(page || 1));
      this.total = Math.max(0, Number(total || 0));
      this.pageSize = Math.max(1, Number(pageSize || 50));

      const totalPages = this.totalPages();
      this.page = clamp(this.page, 1, totalPages);
      if (this.dom.prev) this.dom.prev.disabled = this.page <= 1;
      if (this.dom.next) this.dom.next.disabled = this.page >= totalPages;
      if (this.dom.info) {
        this.dom.info.textContent = `Page ${this.page}/${totalPages} · ${this.total} items`;
      }
      this.renderPages();
    }
  }

  window.Pagination = Pagination;
})();
