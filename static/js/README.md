# Vendored JavaScript

Checked in rather than installed, for the same reason the font beside it is:
the production image holds no npm, and a page that has to reach a CDN to become
interactive is a page that breaks when someone else's server does.

Both files are the published minified builds, copied out of the npm tarball
and otherwise untouched, bar the trailing newline the repo's hooks add. To
upgrade, replace the file and record the new version here.

| File            | Package     | Version | Source                            |
| --------------- | ----------- | ------- | --------------------------------- |
| `htmx.min.js`   | `htmx.org`  | 2.0.10  | `package/dist/htmx.min.js`        |
| `alpine.min.js` | `alpinejs`  | 3.17.3  | `package/dist/cdn.min.js`         |
