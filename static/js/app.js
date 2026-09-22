// billow's Alpine components. Registered here rather than inline because
// `script-src` allows 'self' only, and named because the CSP build of Alpine
// reads component and method names out of the markup rather than expressions.

document.addEventListener("alpine:init", () => {
  // konspec app-shell/default. The class strings returned below are compiled
  // only because assets/css/app.css scans this file.
  Alpine.data("appShell", () => ({
    sidebar: true,
    nav: false,
    wide: false,
    tip: "",
    tipX: 0,
    tipY: 0,
    tipOn: false,

    init() {
      this.sidebar = localStorage.getItem("kon-sidebar") !== "0";
      const mq = window.matchMedia("(min-width: 1024px)");
      this.wide = mq.matches;
      mq.addEventListener("change", (e) => {
        this.wide = e.matches;
        if (e.matches) this.nav = false;
      });
      this.$watch("sidebar", (v) => localStorage.setItem("kon-sidebar", v ? "1" : "0"));
    },

    toggle() {
      if (this.wide) this.sidebar = !this.sidebar;
      else this.nav = !this.nav;
    },

    closeNav() {
      this.nav = false;
    },

    shortcut(event) {
      if (event.key === "[" && !/^(input|textarea|select)$/i.test(event.target.tagName)) this.toggle();
    },

    // One shared tooltip outside the sidebar: the rail clips its labels and
    // the nav is a scroll container, so one inside a row would be clipped.
    showTip(event) {
      if (this.sidebar || !this.wide) return;
      const r = event.currentTarget.getBoundingClientRect();
      this.tip = event.currentTarget.dataset.tip;
      this.tipX = this.$refs.rail.getBoundingClientRect().right + 8;
      this.tipY = r.top + r.height / 2;
      this.tipOn = true;
    },

    hideTip() {
      this.tipOn = false;
    },

    get trapped() {
      return !this.wide && this.nav;
    },

    get railRole() {
      return this.wide ? null : "dialog";
    },

    get railModal() {
      return this.trapped ? "true" : null;
    },

    get railClass() {
      return [this.sidebar ? "lg:w-64" : "lg:w-[68px]", this.nav ? "translate-x-0" : "max-lg:-translate-x-full"];
    },

    // Capped at the collapsed rail's content width: w-full alone resolves
    // against the rail mid-transition, stretching the brand across it.
    get brandBox() {
      return this.sidebar ? "" : "lg:w-full lg:max-w-11";
    },

    get brandWell() {
      return this.sidebar ? "" : "lg:h-10 lg:w-full";
    },

    get fade() {
      return this.sidebar ? "" : "lg:opacity-0";
    },

    get rule() {
      return this.sidebar ? "" : "lg:opacity-100";
    },

    get tipStyle() {
      return `left:${this.tipX}px; top:${this.tipY}px`;
    },

    get expanded() {
      return this.wide ? this.sidebar : this.nav;
    },

    get toggleLabel() {
      if (!this.wide) return "Open navigation";
      return this.sidebar ? "Collapse sidebar" : "Expand sidebar";
    },

    get toggleTitle() {
      return this.wide ? "Collapse sidebar  [" : "Open navigation  [";
    },
  }));

  // Handlers here take no arguments of their own, because the CSP build calls
  // a named handler with the event as its first argument.
  Alpine.data("accountMenu", () => ({
    open: false,

    items() {
      return [...this.$refs.menu.querySelectorAll("[role^=menuitem]")];
    },

    show(last) {
      this.open = true;
      this.$nextTick(() =>
        requestAnimationFrame(() => {
          const i = this.items();
          (last ? i[i.length - 1] : i[0])?.focus();
        }),
      );
    },

    close(toTrigger) {
      if (!this.open) return;
      this.open = false;
      if (toTrigger) this.$refs.trigger.focus();
    },

    move(step) {
      const i = this.items();
      const at = i.indexOf(document.activeElement);
      i[(at + step + i.length) % i.length]?.focus();
    },

    toggle() {
      if (this.open) this.close(false);
      else this.show(false);
    },

    showFirst() {
      this.show(false);
    },

    showLast() {
      this.show(true);
    },

    dismiss() {
      this.close(false);
    },

    escape(event) {
      if (!this.open) return;
      event.stopPropagation();
      this.close(true);
    },

    next() {
      this.move(1);
    },

    prev() {
      this.move(-1);
    },

    toFirst() {
      this.items()[0]?.focus();
    },

    toLast() {
      this.items().at(-1)?.focus();
    },
  }));

  // konspec auth-page/signin and auth-page/failed. The page renders the
  // alert only after a failed attempt, so its presence is the failed state.
  Alpine.data("signIn", () => ({
    show: false,
    busy: false,
    failed: false,
    edited: false,

    // A role="alert" present at first paint announces nothing, so on a
    // server-rendered failure moving focus to it is the announcement.
    init() {
      this.failed = Boolean(this.$refs.err);
      if (this.failed) this.$nextTick(() => this.$refs.err.focus());
    },

    reveal() {
      this.show = !this.show;
    },

    submitting() {
      this.busy = true;
    },

    edit() {
      this.edited = true;
    },

    get concealed() {
      return !this.show;
    },

    get passwordType() {
      return this.show ? "text" : "password";
    },

    get revealLabel() {
      return this.show ? "Hide password" : "Show password";
    },

    get revealStatus() {
      return this.show ? "Password is visible" : "";
    },

    get idleLabel() {
      return this.busy ? "invisible" : "";
    },

    get busyLabel() {
      return this.busy ? "" : "invisible";
    },

    get bad() {
      return this.failed && !this.edited;
    },

    get invalid() {
      return this.bad ? "true" : "false";
    },

    get fieldEdge() {
      return this.bad
        ? "border-red-600 focus-within:outline-red-600/15"
        : "border-zinc-200 focus-within:border-zinc-700 focus-within:outline-zinc-700/15";
    },
  }));

  // konspec form-page/two-column's unsaved-changes guard. Armed by input and
  // change only, so tabbing through a form to read it is not an edit.
  Alpine.data("formPage", () => ({
    dirty: false,
    leaving: false,

    arm(event) {
      if (event.target.matches("input, select, textarea")) this.dirty = true;
    },

    // Cancel is a real link, so it still works without JavaScript and is
    // only held back here when there is something to lose.
    cancel(event) {
      if (!this.dirty) return;
      event.preventDefault();
      this.leaving = true;
    },

    stay() {
      this.leaving = false;
    },

    discard() {
      this.dirty = false;
      window.location.href = this.$refs.cancel.href;
    },

    saveAndLeave() {
      this.leaving = false;
      this.$refs.form.requestSubmit();
    },

    get clean() {
      return !this.dirty;
    },

    // Cleared before the POST navigates, or the page would stop its own Save.
    send() {
      this.dirty = false;
    },

    // A Discard that reloads the page is itself the answer to "lose these
    // changes?", so the browser is not left to ask it again.
    drop() {
      this.dirty = false;
    },

    guard(event) {
      if (this.dirty) event.preventDefault();
    },
  }));

  // konspec alert/form-errors. A failed POST re-renders the page with the
  // summary already in it, where role="alert" announces nothing; the focus
  // move is what reads it out.
  Alpine.data("formErrors", () => ({
    init() {
      this.$el.focus();
    },
  }));

  // konspec form-page/line-items over a Django formset. A removed row is
  // marked and hidden rather than dropped, so a unit on file is deleted on
  // Save and a refused save can still show it.
  // MRP is printed on packaged Goods. One already typed stays in view, so
  // the refusal it causes can be answered by clearing it.
  Alpine.data("goodsOnly", () => ({
    service: false,
    filled: false,

    init() {
      const kind = this.$el.closest("form").elements.kind;
      const input = this.$el.querySelector("input");
      this.service = kind.value === "service";
      this.filled = input.value !== "";
      kind.addEventListener("change", () => (this.service = kind.value === "service"));
      input.addEventListener("input", () => (this.filled = input.value !== ""));
    },

    get applies() {
      return !this.service || this.filled;
    },
  }));

  Alpine.data("unitRows", () => ({
    shown: 0,
    exactRates: {},
    service: false,

    init() {
      this.shown = this.rows().length;
      this.exactRates = JSON.parse(this.$el.dataset.exactRates);
      const kind = this.$el.closest("form").elements.kind;
      this.service = kind.value === "service";
      kind.addEventListener("change", () => (this.service = kind.value === "service"));
    },

    // A Service is sold in one unit. Rows it already has stay in view, so
    // the refusal they cause can be answered by removing them.
    get applies() {
      return !this.service || this.shown > 0;
    },

    // Picking ft on an Item stocked in MTR fills in 0.3048. A rate the
    // Operator typed is left alone; one this filled in follows the unit.
    prefill(event) {
      const unit = event.target;
      if (!unit.name.endsWith("-code")) return;

      const rate = unit.closest("fieldset").querySelector('[name$="-rate"]');
      if (rate.value && rate.value !== rate.dataset.prefilled) return;

      const stock = unit.form.elements.stock_unit.value;
      rate.value = this.exactRates[unit.value]?.[stock] ?? "";
      rate.dataset.prefilled = rate.value;
    },

    rows() {
      return [...this.$refs.rows.querySelectorAll(":scope > fieldset:not([hidden])")];
    },

    get empty() {
      return this.shown === 0;
    },

    // TOTAL_FORMS counts every row ever issued, removed ones included, so a
    // new row never reuses the index of one waiting to be deleted.
    add() {
      const index = Number(this.$refs.total.value);
      const blank = this.$refs.blank.content.firstElementChild.outerHTML;
      const holder = document.createElement("div");
      holder.innerHTML = blank.replaceAll("__prefix__", index);
      const row = holder.firstElementChild;
      row.querySelector("legend").textContent = `Other unit ${index + 1}`;
      row.querySelector("button").setAttribute("aria-label", `Remove other unit ${index + 1}`);
      row.querySelector("[data-title]").textContent = `Unit ${index + 1}`;

      this.$refs.rows.append(row);
      this.$refs.total.value = index + 1;
      this.shown++;
      row.querySelector("select").focus();
    },

    // The pressed button is about to be hidden, and focus would drop to
    // <body>, so it moves to the next row's Remove, or to Add unit.
    remove(event) {
      const row = event.currentTarget.closest("fieldset");
      const rows = this.rows();
      const near = rows[rows.indexOf(row) + 1] || rows[rows.indexOf(row) - 1];

      const deleted = row.querySelector("[data-delete]");
      deleted.value = "on";
      // Removing a unit is an edit, so formPage's guard has to hear of it.
      deleted.dispatchEvent(new Event("change", { bubbles: true }));
      row.hidden = true;
      this.shown--;
      (near ? near.querySelector("button") : this.$refs.add).focus();
    },
  }));

  // konspec combobox/create over the Item form's Brand or Category. It posts
  // the id of a record on file, or a name to create; the server decides
  // whether a new one may be made. Emptying the box takes the record away,
  // since both are optional. A nested picker reads "Fittings > Tee" as Tee
  // under Fittings, written as the options are, "Fittings › Tee".
  Alpine.data("picker", () => ({
    open: false,
    typed: false,
    q: "",
    sel: "",
    fresh: "",
    ai: 0,
    options: [],
    canCreate: false,
    nested: false,
    kind: "",
    noun: "",
    plural: "",
    hint: "",

    init() {
      const data = this.$el.dataset;
      this.options = JSON.parse(document.getElementById(data.options).textContent);
      this.canCreate = data.canCreate === "true";
      this.nested = data.nested === "true";
      this.kind = data.kind;
      this.noun = data.noun;
      this.plural = data.plural;
      this.hint = data.help;
      this.sel = data.selected;
      this.fresh = data.fresh;
      if (this.fresh) this.sel = "";
      this.q = this.label;
    },

    get label() {
      const chosen = this.options.find((o) => String(o.id) === this.sel);
      return chosen ? chosen.name : this.fresh;
    },

    get term() {
      if (!this.nested) return this.q.trim();
      return this.q
        .split(/[›>]/)
        .map((s) => s.trim())
        .filter(Boolean)
        .join(" › ");
    },

    get found() {
      if (!this.typed) return this.options;
      const s = this.term.toLowerCase();
      return this.options.filter((o) => o.name.toLowerCase().includes(s));
    },

    // Offered only for a name no record has in any capitals, as the server
    // would refuse it.
    get creating() {
      const s = this.term.toLowerCase();
      return (
        this.canCreate &&
        this.typed &&
        s.length > 0 &&
        !this.options.some((o) => o.name.toLowerCase() === s)
      );
    },

    get list() {
      return this.creating
        ? [...this.found, { id: "__new", name: this.term, isNew: true }]
        : this.found;
    },

    get nothing() {
      return this.list.length === 0;
    },

    get count() {
      if (!this.open) return "";
      return this.found.length === 1
        ? `1 ${this.noun} matches`
        : `${this.found.length} ${this.plural} match`;
    },

    get help() {
      return this.fresh
        ? `New ${this.noun} — ${this.fresh} is created when the Item is saved.`
        : this.hint;
    },

    get activeId() {
      return this.open && this.list[this.ai] ? this.rowId(this.list[this.ai]) : null;
    },

    rowId(o) {
      return `${this.kind}-option-${o.id}`;
    },

    rowLabel(o) {
      return o.isNew ? `Add new ${this.noun}: “${o.name}”` : o.name;
    },

    rowClass(o, i) {
      return [i === this.ai ? "bg-zinc-100" : "", o.isNew ? "border-t border-zinc-100" : ""];
    },

    isSelected(o) {
      return !o.isNew && String(o.id) === this.sel;
    },

    scroll() {
      this.$nextTick(() => {
        const el = document.getElementById(this.activeId);
        if (el) el.scrollIntoView({ block: "nearest" });
      });
    },

    show() {
      if (this.open) return;
      this.open = true;
      this.typed = false;
      this.ai = Math.max(0, this.list.findIndex((o) => this.isSelected(o)));
      this.scroll();
    },

    close() {
      if (this.typed && this.term === "") {
        this.sel = "";
        this.fresh = "";
      }
      this.open = false;
      this.typed = false;
      this.q = this.label;
    },

    escape(event) {
      if (!this.open) return;
      event.stopPropagation();
      this.close();
      this.$refs.q.focus();
    },

    typing() {
      this.typed = true;
      this.open = true;
      this.ai = 0;
    },

    move(n) {
      if (!this.open) {
        this.show();
        return;
      }
      if (!this.list.length) return;
      this.ai = Math.min(this.list.length - 1, Math.max(0, this.ai + n));
      this.scroll();
    },

    down() {
      this.move(1);
    },

    up() {
      this.move(-1);
    },

    edge(end, event) {
      if (!this.open) return;
      event.preventDefault();
      if (!this.list.length) return;
      this.ai = end ? this.list.length - 1 : 0;
      this.scroll();
    },

    home(event) {
      this.edge(false, event);
    },

    end(event) {
      this.edge(true, event);
    },

    hover(i) {
      this.ai = i;
    },

    pickRow(o) {
      if (o.isNew) {
        this.sel = "";
        this.fresh = o.name;
      } else {
        this.sel = String(o.id);
        this.fresh = "";
      }
      this.open = false;
      this.typed = false;
      this.q = this.label;
      this.$refs.q.focus();
      // The hidden inputs change without an input event, and formPage's
      // unsaved-changes guard has to hear of it.
      this.$refs.q.dispatchEvent(new Event("change", { bubbles: true }));
    },

    enter(event) {
      if (!this.open) return;
      event.preventDefault();
      const o = this.list[this.ai];
      if (o) this.pickRow(o);
    },
  }));

  // konspec select/filter applies on change, with no Apply button.
  Alpine.data("filterSelect", () => ({
    apply() {
      this.$root.requestSubmit();
    },
  }));

  // konspec alert-dialog, for a write worth interrupting over.
  Alpine.data("confirmDialog", () => ({
    open: false,

    ask() {
      this.open = true;
    },

    cancel() {
      this.open = false;
    },
  }));

  // konspec dropdown/context-menu over the Customer directory. One menu
  // serves every row, so the row it is about is held as state and each row
  // carries its own name and URLs.
  Alpine.data("rowMenu", () => ({
    open: false,
    confirming: false,
    x: 0,
    y: 0,
    row: null,
    opener: null,

    items() {
      return [...this.$refs.menu.querySelectorAll("[role=menuitem]")];
    },

    // Height depends on which items the permissions left in, so the flip
    // upwards is measured a frame after x-show has displayed the panel.
    showAt(cx, cy, row, opener) {
      this.row = row;
      this.opener = opener;
      this.x = Math.max(8, Math.min(cx, window.innerWidth - 224));
      this.y = cy;
      this.open = true;
      this.$nextTick(() =>
        requestAnimationFrame(() => {
          const h = this.$refs.menu.offsetHeight;
          if (cy + h > window.innerHeight - 8) this.y = Math.max(8, cy - h);
          this.items()[0]?.focus();
        }),
      );
    },

    fromRow(event) {
      const row = event.currentTarget;
      this.showAt(event.clientX, event.clientY, row, row.querySelector("a"));
    },

    close(toOpener) {
      if (!this.open) return;
      this.open = false;
      if (toOpener) this.opener?.focus();
    },

    closeQuietly() {
      this.close(false);
    },

    // A left click on another row has to put the menu away too, not only a
    // click outside the table.
    dismiss(event) {
      if (this.open && !this.$refs.menu.contains(event.target)) this.close(false);
    },

    escape(event) {
      if (!this.open) return;
      event.stopPropagation();
      this.close(true);
    },

    move(step) {
      const i = this.items();
      const at = i.indexOf(document.activeElement);
      i[(at + step + i.length) % i.length]?.focus();
    },

    next() {
      this.move(1);
    },

    prev() {
      this.move(-1);
    },

    toFirst() {
      this.items()[0]?.focus();
    },

    toLast() {
      this.items().at(-1)?.focus();
    },

    // Focus goes back to the row's link first, so the dialog's trap has
    // somewhere to return it when it closes.
    askArchive() {
      this.close(true);
      this.confirming = true;
    },

    cancel() {
      this.confirming = false;
    },

    tint(row) {
      return (this.open || this.confirming) && this.row === row ? "[&>td]:bg-zinc-100" : "";
    },

    get menuLabel() {
      return this.row ? `Actions for ${this.row.dataset.name}` : "Row actions";
    },

    get menuStyle() {
      return `left: ${this.x}px; top: ${this.y}px`;
    },

    get name() {
      return this.row?.dataset.name ?? "";
    },

    get openUrl() {
      return this.row?.dataset.open;
    },

    get editUrl() {
      return this.row?.dataset.edit;
    },

    get actUrl() {
      return this.row?.dataset.act;
    },
  }));

  Alpine.data("dismissible", () => ({
    show: true,

    dismiss() {
      this.show = false;
    },
  }));

  // konspec radio/conditional's show condition, read off the checked radio
  // rather than bound with x-model, so the markup stays Django's own. It only
  // disables the GSTIN; CSS shows and hides it, with or without JavaScript.
  Alpine.data("gstAnswer", () => ({
    registered: false,

    init() {
      this.read();
    },

    read() {
      this.registered = this.$el.querySelector('input[value="True"]').checked;
    },

    get unregistered() {
      return !this.registered;
    },
  }));

  Alpine.data("logoPicker", () => ({
    name: "",
    detail: "",
    removing: false,
    depth: 0,

    // Taken off the page rather than passed in, so what the server rendered
    // for a visitor without JavaScript is also what this starts from.
    init() {
      this.name = this.$refs.name.textContent.trim();
      this.detail = this.$refs.detail.textContent.trim();
    },

    get zone() {
      return this.depth > 0 ? "border-zinc-700 bg-zinc-50" : "border-zinc-200 bg-zinc-100";
    },

    chosen() {
      const [file] = this.$refs.input.files;
      if (!file) return;

      this.removing = false;
      this.name = file.name;
      this.detail = readableSize(file.size);

      // A data URL rather than an object URL: `img-src` allows 'self' and
      // data:, and a blob: URL would be refused.
      const reader = new FileReader();
      reader.onload = () => (this.$refs.image.src = reader.result);
      reader.readAsDataURL(file);
    },

    // A depth rather than a flag: dragleave also fires as the pointer crosses
    // into a child of the zone, which would flicker a flag off.
    dragIn() {
      this.depth++;
    },

    dragOut() {
      this.depth--;
    },

    dropped(event) {
      this.depth = 0;
      const files = event.dataTransfer.files;
      if (!files.length) return;

      this.$refs.input.files = files;
      this.chosen();
    },
  }));
});

function readableSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// createIcons() leaves data-lucide on the <svg> it produces, so re-running it
// on every mutation would re-render every icon forever. Guarding on an
// un-hydrated element lets the loop settle.
(() => {
  let queued = false;
  const pending = () => document.querySelector("[data-lucide]:not(svg)");
  const draw = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (window.lucide && pending()) lucide.createIcons();
    });
  };
  document.addEventListener("DOMContentLoaded", draw);
  document.addEventListener("alpine:initialized", () => {
    draw();
    new MutationObserver(draw).observe(document.body, { childList: true, subtree: true });
  });
})();
