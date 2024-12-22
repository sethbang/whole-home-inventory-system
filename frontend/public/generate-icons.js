import sharp from 'sharp';
import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function generateIcons() {
  const sizes = [192, 512];
  const inputSvg = await fs.readFile(join(__dirname, '../../images/whis_logo.svg'));
  
  for (const size of sizes) {
    await sharp(inputSvg)
      .resize(size, size)
      .png()
      .toFile(join(__dirname, `apple-touch-icon-${size}x${size}.png`));
  }
}

generateIcons().catch(console.error);