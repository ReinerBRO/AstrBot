(() => {
  function escapeRegExp(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function splitHighlighted(text, query) {
    const source = String(text || "");
    const keyword = String(query || "").trim();
    if (!keyword) {
      return [{ text: source, match: false }];
    }
    const regex = new RegExp(`(${escapeRegExp(keyword)})`, "ig");
    const output = [];
    let cursor = 0;
    source.replace(regex, (part, _group, offset) => {
      if (offset > cursor) {
        output.push({ text: source.slice(cursor, offset), match: false });
      }
      output.push({ text: part, match: true });
      cursor = offset + part.length;
      return part;
    });
    if (cursor < source.length) {
      output.push({ text: source.slice(cursor), match: false });
    }
    return output.length ? output : [{ text: source, match: false }];
  }

  function appendHighlighted(target, text, query) {
    const chunks = splitHighlighted(text, query);
    for (const chunk of chunks) {
      if (!chunk.match) {
        target.appendChild(document.createTextNode(chunk.text));
        continue;
      }
      const mark = document.createElement("mark");
      mark.textContent = chunk.text;
      mark.className = "cards-highlight";
      target.appendChild(mark);
    }
  }

  function sourceLabel(source) {
    const normalized = String(source || "vl").toLowerCase();
    if (normalized === "vl+event" || normalized === "fusion") return "VL+Event";
    if (normalized === "event") return "Event";
    return "VL";
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

  function activeDurationLabel(seconds) {
    const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
    if (!safe) return "-";
    if (safe < 3600) {
      return `${Math.max(1, Math.round(safe / 60))}m`;
    }
    const hours = Math.floor(safe / 3600);
    const mins = Math.round((safe % 3600) / 60);
    return mins > 0 ? `${hours}h${mins}m` : `${hours}h`;
  }

  class Card {
    constructor(data, handlers = {}) {
      this.data = { ...data };
      this.handlers = handlers;
      this.highlight = handlers.highlight || "";
      this.root = null;
      this.editing = false;
      this.busy = false;
      this.collapsed = true;
      this.onCardToggle = this.onCardToggle.bind(this);
      this.onCardKeydown = this.onCardKeydown.bind(this);
    }

    onCardToggle(event) {
      if (this.editing) return;
      const target = event.target;
      if (target instanceof Element) {
        if (target.closest("button,textarea,select,input,a,.log-card-editor")) {
          return;
        }
      }
      this.collapsed = !this.collapsed;
      this.render();
    }

    onCardKeydown(event) {
      if (this.editing) return;
      const target = event.target;
      if (target instanceof Element) {
        if (target.closest("button,textarea,select,input")) {
          return;
        }
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.collapsed = !this.collapsed;
        this.render();
      }
    }

    setData(next) {
      this.data = { ...this.data, ...next };
      this.render();
    }

    setHighlight(query) {
      this.highlight = query || "";
      this.render();
    }

    async copyToClipboard() {
      const line = `- ${this.data.time || "--:--"} [${this.data.category || "未分类"}] ${this.data.tree_id ? `{tree:${this.data.tree_id}} ` : ""}${this.data.summary || ""}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(line);
        return line;
      }
      const textArea = document.createElement("textarea");
      textArea.value = line;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      return line;
    }

    setBusy(value) {
      this.busy = Boolean(value);
      if (this.root) {
        this.root.classList.toggle("is-busy", this.busy);
      }
    }

    buildCategorySelect(selected) {
      const select = document.createElement("select");
      select.className = "cards-edit-category";
      const options = Array.isArray(this.data.available_categories) && this.data.available_categories.length
        ? this.data.available_categories
        : [this.data.category || "写代码", "研究", "娱乐"];
      const unique = [...new Set(options)];
      for (const category of unique) {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
      }
      select.value = selected || unique[0] || "";
      return select;
    }

    renderSummary(node) {
      node.innerHTML = "";
      appendHighlighted(node, this.data.summary || "", this.highlight);
    }

    render() {
      if (!this.root) {
        this.root = document.createElement("article");
        this.root.tabIndex = 0;
        this.root.setAttribute("role", "button");
        this.root.setAttribute("aria-expanded", "false");
        this.root.addEventListener("click", this.onCardToggle);
        this.root.addEventListener("keydown", this.onCardKeydown);
      }
      this.root.className = "log-card-item";
      const compactMode = this.collapsed && !this.editing;
      this.root.classList.toggle("is-collapsed", compactMode);
      this.root.classList.toggle("is-expanded", !compactMode);
      this.root.setAttribute("aria-expanded", compactMode ? "false" : "true");
      this.root.style.setProperty("--category-color", resolveCategoryColor(this.data.category));
      this.root.innerHTML = "";

      const categoryClass = `cards-cat-${String(this.data.category || "other").replace(/[^a-zA-Z0-9\u4e00-\u9fa5]+/g, "-").toLowerCase()}`;
      const topApp = this.data.event_data?.top_app || "Unknown";
      const activeSeconds = Number(this.data.event_data?.active_seconds || 0);
      const activeLabel = activeDurationLabel(activeSeconds);

      const header = document.createElement("header");
      header.className = "log-card-head";
      header.innerHTML = `
        <div class="log-card-head-main">
          <time>${escapeHtml(this.data.time || "--:--")}</time>
          <span class="log-card-category ${categoryClass}">${escapeHtml(this.data.category || "未分类")}</span>
          <span class="log-card-quick">${escapeHtml(topApp)} ${escapeHtml(activeLabel)}</span>
        </div>
        <div class="log-card-head-sub">
          <span class="log-card-date">${escapeHtml(this.data.date || "")}</span>
          <span class="log-card-tree">${escapeHtml(this.data.tree_name || this.data.tree_id || "No Tree")}</span>
          <span class="log-card-source">${escapeHtml(sourceLabel(this.data.source))} · ${Number(this.data.confidence || 0).toFixed(2)}</span>
        </div>
      `;

      const summary = document.createElement("p");
      summary.className = "log-card-summary";
      if (compactMode) {
        summary.classList.add("collapsed");
      }
      this.renderSummary(summary);

      const meta = document.createElement("div");
      meta.className = "log-card-meta";
      const clickCount = Number(this.data.event_data?.click_count || 0);
      meta.innerHTML = `
        <span>${clickCount}次点击</span>
        <span>置信度 ${Number(this.data.confidence || 0).toFixed(2)}</span>
        <span>${escapeHtml(sourceLabel(this.data.source))}</span>
        <span>ID: ${escapeHtml(this.data.id || "-")}</span>
      `;

      const actions = document.createElement("div");
      actions.className = "log-card-actions";
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "btn btn-ghost";
      copyBtn.textContent = "Copy";
      copyBtn.addEventListener("click", async () => {
        try {
          await this.copyToClipboard();
          this.handlers.onNotify?.("Card copied");
          await this.handlers.onCopy?.(this.data);
        } catch (error) {
          this.handlers.onNotify?.(`Copy failed: ${error instanceof Error ? error.message : String(error)}`, "error");
        }
      });

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn btn-ghost";
      editBtn.textContent = this.editing ? "Cancel" : "Edit";
      editBtn.addEventListener("click", () => {
        if (this.editing) {
          this.editing = false;
          this.render();
          return;
        }
        this.editing = true;
        this.collapsed = false;
        this.render();
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "btn btn-ghost";
      deleteBtn.textContent = "Delete";
      deleteBtn.addEventListener("click", async () => {
        const ok = window.confirm("Delete this card?");
        if (!ok) return;
        try {
          this.setBusy(true);
          await this.handlers.onDelete?.(this.data.id, this.data);
          this.handlers.onNotify?.("Card deleted");
        } catch (error) {
          this.handlers.onNotify?.(`Delete failed: ${error instanceof Error ? error.message : String(error)}`, "error");
        } finally {
          this.setBusy(false);
        }
      });

      const treeBtn = document.createElement("button");
      treeBtn.type = "button";
      treeBtn.className = "btn btn-ghost";
      treeBtn.textContent = "View Tree";
      treeBtn.disabled = !this.data.tree_id;
      treeBtn.addEventListener("click", () => {
        this.handlers.onViewTree?.(this.data);
      });

      actions.append(copyBtn, editBtn, deleteBtn, treeBtn);

      if (this.handlers.editable === false) {
        editBtn.disabled = true;
        deleteBtn.disabled = true;
      }

      this.root.append(header, summary, meta);

      if (this.editing) {
        const editor = document.createElement("div");
        editor.className = "log-card-editor";

        const textArea = document.createElement("textarea");
        textArea.value = this.data.summary || "";
        textArea.rows = 3;
        textArea.className = "cards-edit-summary";

        const categorySelect = this.buildCategorySelect(this.data.category || "");

        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.className = "btn btn-primary";
        saveBtn.textContent = "Save";
        saveBtn.addEventListener("click", async () => {
          const summaryValue = textArea.value.trim();
          const categoryValue = categorySelect.value;
          try {
            this.setBusy(true);
            const updated = await this.handlers.onEdit?.(
              this.data.id,
              {
                summary: summaryValue,
                category: categoryValue,
              },
              this.data,
            );
            if (updated && typeof updated === "object") {
              this.data = {
                ...this.data,
                ...updated,
              };
            } else {
              this.data.summary = summaryValue;
              this.data.category = categoryValue;
            }
            this.editing = false;
            this.render();
            this.handlers.onNotify?.("Card updated");
          } catch (error) {
            this.handlers.onNotify?.(`Update failed: ${error instanceof Error ? error.message : String(error)}`, "error");
          } finally {
            this.setBusy(false);
          }
        });

        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.className = "btn btn-ghost";
        cancelBtn.textContent = "Cancel";
        cancelBtn.addEventListener("click", () => {
          this.editing = false;
          this.render();
        });

        const editorActions = document.createElement("div");
        editorActions.className = "log-card-editor-actions";
        editorActions.append(saveBtn, cancelBtn);

        editor.append(textArea, categorySelect, editorActions);
        this.root.append(editor);
      }

      this.root.append(actions);
      this.setBusy(this.busy);
      return this.root;
    }
  }

  window.Card = Card;
})();
