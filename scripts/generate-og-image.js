const sharp = require('sharp');
const fs = require('fs');

async function generateOgImage() {
  const svgBuffer = fs.readFileSync('./public/og-image.svg');

  await sharp(svgBuffer)
    .resize(1200, 630)
    .png()
    .toFile('./public/og-image.png');

  console.log('✅ og-image.png created successfully!');
}

generateOgImage().catch(console.error);
