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

    get brandBox() {
      return this.sidebar ? "" : "lg:w-full";
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

  Alpine.data("dismissible", () => ({
    show: true,

    dismiss() {
      this.show = false;
    },
  }));

  Alpine.data("logoPicker", () => ({
    name: "",
    detail: "",
    removing: false,
    dragging: false,

    // Taken off the page rather than passed in, so what the server rendered
    // for a visitor without JavaScript is also what this starts from.
    init() {
      this.name = this.$refs.name.textContent.trim();
      this.detail = this.$refs.detail.textContent.trim();
    },

    get zone() {
      return this.dragging ? "border-accent bg-accent-soft" : "";
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

    dragOn() {
      this.dragging = true;
    },

    // dragleave also fires as the pointer crosses into a child of the zone,
    // which would flicker the highlight off over every element inside it.
    dragOff(event) {
      if (event.currentTarget.contains(event.relatedTarget)) return;
      this.dragging = false;
    },

    dropped(event) {
      this.dragging = false;
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
