# Vendored JavaScript

Checked in rather than installed, for the same reason the font beside it is:
the production image holds no npm, and a page that has to reach a CDN to become
interactive is a page that breaks when someone else's server does.

Both files are the published minified builds, copied out of the npm tarball
and otherwise untouched, bar the trailing newline the repo's hooks add. To
upgrade, replace the file and record the new version here.

| File            | Package         | Version | Source                     |
| --------------- | --------------- | ------- | -------------------------- |
| `htmx.min.js`   | `htmx.org`      | 2.0.10  | `package/dist/htmx.min.js` |
| `alpine.min.js` | `@alpinejs/csp` | 3.17.3  | `package/dist/cdn.min.js`  |

Alpine is the CSP build, not the ordinary one: `script-src` in settings allows
`'self'` and nothing else, and stock Alpine evaluates every expression with
`new Function`, which that header forbids. The difference is in what an
attribute may hold — `x-data="dropdown"` naming a component registered with
`Alpine.data()`, and `x-on:click="toggle"` naming one of its methods, rather
than a JavaScript expression written in the markup. Registering those
components needs a file of our own served from this directory, since an inline
`<script>` is forbidden by the same header. That file is `app.js`, which is
billow's own code rather than a vendored build.
