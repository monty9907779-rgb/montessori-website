const legacyPlatformBaseUrl = (
  process.env.NEXT_PUBLIC_ODOO_URL || "https://odoo.montessori-ksa.com"
).replace(/\/+$/, "");

/**
 * The legacy Odoo app owns authentication and the parent portal.
 * Keep that integration as a URL boundary instead of mixing Python routes
 * into the Next.js marketing application.
 */
export const parentPortalUrl = `${legacyPlatformBaseUrl}/portal-login`;
