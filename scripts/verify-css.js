const fs = require("fs");
const path = require("path");
const postcss = require("postcss");

const cssFiles = [
  path.join(process.cwd(), "src", "app", "globals.css"),
];

for (const filePath of cssFiles) {
  const source = fs.readFileSync(filePath, "utf8");
  postcss.parse(source, { from: filePath });
}

console.log(`CSS verified: ${cssFiles.length} stylesheet parsed successfully.`);
