const fs = require("fs");
const path = require("path");

const publicDir = path.join(process.cwd(), "public");
const requiredFiles = [
  "favicon.ico",
  "favicon.svg",
  "favicon-32.png",
  "apple-touch-icon.png",
  "icon-192.png",
  "icon-512.png",
  "og-image.png",
  "robots.txt",
  "sitemap.xml",
  "site.webmanifest",
  ".well-known/security.txt",
];

const missing = requiredFiles.filter((fileName) => {
  const filePath = path.join(publicDir, fileName);
  return !fs.existsSync(filePath) || fs.statSync(filePath).size === 0;
});

if (missing.length > 0) {
  console.error("Missing or empty public assets:", missing.join(", "));
  process.exit(1);
}

const manifest = JSON.parse(fs.readFileSync(path.join(publicDir, "site.webmanifest"), "utf8"));
const manifestIcons = new Set((manifest.icons || []).map((icon) => icon.src));
const expectedIcons = new Set(["/icon-192.png", "/icon-512.png"]);
const missingManifestIcons = [...expectedIcons].filter((src) => !manifestIcons.has(src));

if (!manifest.name || !manifest.short_name || missingManifestIcons.length > 0) {
  console.error("Manifest verification failed.");
  if (!manifest.name) console.error("Missing manifest name.");
  if (!manifest.short_name) console.error("Missing manifest short_name.");
  if (missingManifestIcons.length) {
    console.error("Missing manifest icons:", missingManifestIcons.join(", "));
  }
  process.exit(1);
}

const robots = fs.readFileSync(path.join(publicDir, "robots.txt"), "utf8");
const sitemap = fs.readFileSync(path.join(publicDir, "sitemap.xml"), "utf8");

if (!robots.includes("Sitemap:") || !sitemap.includes("<urlset")) {
  console.error("robots.txt or sitemap.xml verification failed.");
  process.exit(1);
}

console.log(`Public assets verified: ${requiredFiles.length} required files present.`);
