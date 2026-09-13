import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const root = path.resolve(import.meta.dirname, "..");
const productionSnapshot = path.join(
  root,
  "legacy-desktop/01 - موقع Montessori/نسخة السيرفر الحقيقية",
);
const scanRoots = ["src", "messages", "public", productionSnapshot];
const textExtensions = new Set([".html", ".js", ".json", ".md", ".ts", ".tsx", ".txt", ".xml"]);
const forbidden = [
  /٧:٣٠[^\n]{0,100}٣:٠٠/,
  /7:30[^\n]{0,100}3:00/,
  /07:30[^\n]{0,100}15:00/,
  /8:00 AM (?:to|–|-) 2:00 PM/,
  /8:00 AM (?:to|–|-) 3:00 PM/,
  /8:00 AM (?:to|–|-) 12:00 PM/,
  /٨:٠٠[^\n]{0,50}٢:٠٠/,
  /٨:٠٠[^\n]{0,50}(?<![٠-٩])٣:٠٠/,
  /٨:٠٠[^\n]{0,50}١٢:٠٠/,
  /08:00[^\n]{0,50}14:00/,
  /08:00[^\n]{0,50}15:00/,
  /08:00[^\n]{0,50}12:00/,
  /من ٨:٣٠ صباح/,
  /from 8:30 AM/i,
  /(?:6-18 months|6-18 شهر|من 6 أشهر حتى 6 سنوات|from 6 months to 6 years)/i,
];

function filesIn(entry) {
  const absolute = path.isAbsolute(entry) ? entry : path.join(root, entry);
  const files = [];
  for (const item of fs.readdirSync(absolute, { withFileTypes: true })) {
    if (item.name === "node_modules" || item.name === "build") continue;
    const itemPath = path.join(absolute, item.name);
    if (item.isDirectory()) files.push(...filesIn(itemPath));
    else if (textExtensions.has(path.extname(item.name))) files.push(itemPath);
  }
  return files;
}

const conflicts = [];
for (const file of scanRoots.flatMap(filesIn)) {
  const content = fs.readFileSync(file, "utf8");
  if (forbidden.some((pattern) => pattern.test(content))) {
    conflicts.push(path.relative(root, file));
  }
}

assert.deepEqual(conflicts, [], `Conflicting official hours found in:\n${conflicts.join("\n")}`);

const facts = fs.readFileSync(path.join(root, "src/lib/site-facts.ts"), "utf8");
assert.match(facts, /opens: "08:00"/);
assert.match(facts, /closes: "13:00"/);

const bot = fs.readFileSync(path.join(root, "public/assets/bot.js"), "utf8");
assert.match(bot, /من ٨:٠٠ صباحًا حتى ١:٠٠ ظهرًا/);
assert.doesNotMatch(bot, /٧:٣٠|٣:٠٠|٨:٣٠|٢:٠٠/);

console.log("Verified one official schedule: Sunday-Thursday, 08:00-13:00.");
