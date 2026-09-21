# UI

billow's UI is built with **konspec-ui** (https://konfpa.github.io/konspec-ui): copy-paste HTML components on stock Tailwind v4, Alpine and htmx. Every template, class list and Alpine component follows it.

## Before writing markup

1. Read https://konfpa.github.io/konspec-ui/llms.txt in full — the stack, tokens and the numbered rules. The rules are binding here.
2. Find the component in its list. Fetch its markup from `/r/<component>/<variant>.html` and copy it **verbatim**, keeping the root's `data-kui="<component>/<variant>"`. Prefer a `django` variant when one exists. Fetch `/r/<component>.json` when you need the rules or which variant to take.
3. Change only the content: labels, template variables, URLs, form field names.
4. If no component or variant fits, stop and ask. Never invent a component, variant, token or layout.

## billow-specific adaptations

These are the only places a pasted variant may differ from the registry.

- **Strict CSP, so no inline Alpine.** `script-src` is `'self'` only and billow runs the CSP build of Alpine, which cannot evaluate expressions in attributes. Move every variant's inline `x-data` object, handlers and expressions into a named `Alpine.data()` component in `static/js/app.js`. The markup then names that component and its methods or getters (`x-data="appShell"`, `x-on:click="toggle"`, `x-bind:class="railClass"`). Keep the class lists and structure as copied. Never add `'unsafe-eval'` or inline `<script>`.
- **Vendored, never CDN.** Alpine plugins, Lucide and fonts are checked in under `static/js/` and `static/fonts/`, and recorded in `static/js/README.md`. The demo's CDN `<script>` and font URLs are replaced with `{% static %}` paths. Plugins load before Alpine core.
- **Class names in Python or JS are compiled only if Tailwind scans the file.** `assets/css/app.css` lists every scanned directory with `@source`, and the Dockerfile `assets` stage must copy the same directories. A class that only appears in an unscanned file renders unstyled, with no error.
- **Django forms.** Render fields through `templates/forms/field.html`, which is the konspec `field/django` markup. Widget classes and `aria-*` attributes are set in `apps/core/forms.py` (`StyledForm`), not per template.
- **Markup the tests pin.** Several tests assert exact strings: attribute order on inputs, `aria-label="Main"`, `id="messages"`, and user-facing copy. Run `pytest` after every change and keep what they assert, unless the change deliberately updates the test.

## Checking a change

`npm run build`, then `pytest`, then look at the page at desktop width and at 390px.
