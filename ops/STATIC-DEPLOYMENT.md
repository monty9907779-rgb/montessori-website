# Production Source

Repository: https://github.com/monty9907779-rgb/montessori-website.git, branch `main`.

`public/` is the canonical source for the static administration pages, including
`dashboard/`, `classes/`, and `whatsapp/`. Shared styling is in `assets/app-admin.css`.
Dashboard styling is only in `assets/dashboard.css`; WhatsApp controls and styles
are only in `assets/whatsapp-admin.js` and `assets/whatsapp-admin.css`.

Run `bash deploy.sh` from this repository. It packages these pages and their
reviewed assets, verifies checksums, backs up production, updates CSP without
removing existing grants, validates nginx, and rolls back if installation fails.
The release manifest is retained with the backup.

The only live webroot is `/var/www/montessori-ksa` on `187.127.79.242`.
The only active apex-domain nginx configuration is
`/etc/nginx/sites-enabled/montessori-ksa`. Never leave backup configuration files
inside `sites-enabled`; nginx loads every file there.

`legacy-desktop/`, the former `/root/deploy-montessori` package, and the old Vercel
deployment instructions are historical snapshots, not deployment sources.
Next.js is a separate development/marketing application and is not the server
currently serving this production domain. A GitHub push alone does not deploy nginx.

Public marketing and generated SEO content remain managed by their existing
publisher; this admin deployment does not replace them or modify Odoo data.
`/whatsapp/` is the authenticated admin page. `/wa/` and `/whatsapp.html` are public
contact links, not alternative admin dashboards.

CSS and JavaScript revalidate against the server. The service worker retains
only the offline fallback, never authenticated pages or API responses.
Verify live dashboard, classes, WhatsApp, reload/navigation, and mobile sizing
after every release. Do not report a build or Git push as live verification.
