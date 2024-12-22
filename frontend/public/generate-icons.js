import sharp from 'sharp';
import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function generateIcons() {
  const inputSvg = await fs.readFile(join(__dirname, '../../images/whis_logo.svg'));
  const sizes = [180, 192, 512]; // 180px is specifically for iOS
  
  for (const size of sizes) {
    // Generate standard icon
    await sharp(inputSvg)
      .resize(size, size, {
        fit: 'contain',
        background: { r: 0, g: 0, b: 0, alpha: 0 }
      })
      .png({
        compressionLevel: 9,
        quality: 100,
        force: true
      })
      .toFile(join(__dirname, `apple-touch-icon${size === 180 ? '' : `-${size}x${size}`}.png`));

    // Generate precomposed version
    await sharp(inputSvg)
      .resize(size, size, {
        fit: 'contain',
        background: { r: 0, g: 0, b: 0, alpha: 0 }
      })
      .png({
        compressionLevel: 9,
        quality: 100,
        force: true
      })
      .toFile(join(__dirname, `apple-touch-icon${size === 180 ? '' : `-${size}x${size}`}-precomposed.png`));
  }

  console.log('Generated all iOS icon variants');
}

generateIcons().catch(console.error);