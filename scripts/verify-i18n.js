const fs = require("fs");
const path = require("path");

const messagesDir = path.join(process.cwd(), "messages");
const localeFiles = ["ar.json", "en.json"];

function readJson(fileName) {
  const filePath = path.join(messagesDir, fileName);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function flattenKeys(value, prefix = "") {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenKeys(item, `${prefix}[${index}]`));
  }

  if (value && typeof value === "object") {
    return Object.keys(value).flatMap((key) =>
      flattenKeys(value[key], prefix ? `${prefix}.${key}` : key)
    );
  }

  return [prefix];
}

function findEmptyStrings(value, prefix = "") {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => findEmptyStrings(item, `${prefix}[${index}]`));
  }

  if (value && typeof value === "object") {
    return Object.keys(value).flatMap((key) =>
      findEmptyStrings(value[key], prefix ? `${prefix}.${key}` : key)
    );
  }

  return typeof value === "string" && value.trim().length === 0 ? [prefix] : [];
}

const [ar, en] = localeFiles.map(readJson);
const arKeys = new Set(flattenKeys(ar));
const enKeys = new Set(flattenKeys(en));

const missingInAr = [...enKeys].filter((key) => !arKeys.has(key));
const missingInEn = [...arKeys].filter((key) => !enKeys.has(key));
const emptyValues = [
  ...findEmptyStrings(ar).map((key) => `ar:${key}`),
  ...findEmptyStrings(en).map((key) => `en:${key}`),
];

if (missingInAr.length || missingInEn.length || emptyValues.length) {
  console.error("i18n verification failed.");
  if (missingInAr.length) console.error("Missing in ar:", missingInAr.join(", "));
  if (missingInEn.length) console.error("Missing in en:", missingInEn.join(", "));
  if (emptyValues.length) console.error("Empty values:", emptyValues.join(", "));
  process.exit(1);
}

console.log(`i18n verified: ${arKeys.size} locale keys match across ar/en.`);
