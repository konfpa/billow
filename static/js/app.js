// billow's Alpine components. Registered here rather than inline because
// `script-src` allows 'self' only, and named because the CSP build of Alpine
// reads component and method names out of the markup rather than expressions.

document.addEventListener("alpine:init", () => {
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
