# Vendored JavaScript

Checked in rather than installed, for the same reason the fonts beside it are:
the production image holds no npm, and a page that has to reach a CDN to become
interactive is a page that breaks when someone else's server does.

These are the published minified builds, copied out of the npm tarball
and otherwise untouched, bar the trailing newline the repo's hooks add. To
upgrade, replace the file and record the new version here.

| File                     | Package              | Version | Source                           |
| ------------------------ | -------------------- | ------- | -------------------------------- |
| `htmx.min.js`            | `htmx.org`           | 2.0.10  | `package/dist/htmx.min.js`       |
| `alpine.min.js`          | `@alpinejs/csp`      | 3.17.3  | `package/dist/cdn.min.js`        |
| `alpine-focus.min.js`    | `@alpinejs/focus`    | 3.17.3  | `package/dist/cdn.min.js`        |
| `alpine-collapse.min.js` | `@alpinejs/collapse` | 3.17.3  | `package/dist/cdn.min.js`        |
| `lucide.min.js`          | `lucide`             | 1.47.0  | `package/dist/umd/lucide.min.js` |

The one edit: the `//# sourceMappingURL=lucide.min.js.map` line is removed
from `lucide.min.js`. The map is 4 MB and not vendored, and the manifest
storage `collectstatic` uses in production fails on a reference to a file that
is not there.

The two Alpine plugins are the stock builds, not CSP ones — neither package
publishes one, and neither needs it: they evaluate their attribute through
Alpine's own evaluator, which is the CSP one. They register themselves on
`alpine:init`, so they load before Alpine core. The fonts in `static/fonts/`
come from konspec-ui (`assets/fonts/`).

Alpine is the CSP build, not the ordinary one: `script-src` in settings allows
`'self'` and nothing else, and stock Alpine evaluates every expression with
`new Function`, which that header forbids. The difference is in what an
attribute may hold — `x-data="dropdown"` naming a component registered with
`Alpine.data()`, and `x-on:click="toggle"` naming one of its methods, rather
than a JavaScript expression written in the markup. Registering those
components needs a file of our own served from this directory, since an inline
`<script>` is forbidden by the same header. That file is `app.js`, which is
billow's own code rather than a vendored build.
