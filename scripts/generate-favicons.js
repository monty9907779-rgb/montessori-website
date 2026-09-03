const sharp = require('sharp');
const fs = require('fs');

async function generateFavicons() {
  const svgBuffer = fs.readFileSync('./public/favicon.svg');

  // Generate favicon.ico (32x32)
  await sharp(svgBuffer)
    .resize(32, 32)
    .png()
    .toFile('./public/favicon-32.png');

  // Generate apple-touch-icon (180x180)
  await sharp(svgBuffer)
    .resize(180, 180)
    .png()
    .toFile('./public/apple-touch-icon.png');

  // Generate icon-192 (for manifest)
  await sharp(svgBuffer)
    .resize(192, 192)
    .png()
    .toFile('./public/icon-192.png');

  // Generate icon-512 (for manifest)
  await sharp(svgBuffer)
    .resize(512, 512)
    .png()
    .toFile('./public/icon-512.png');

  console.log('✅ All favicon sizes generated successfully!');
}

generateFavicons().catch(console.error);
