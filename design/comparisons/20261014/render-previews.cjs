// Render the selected raster lineup. The earlier comparison and SVG drafts remain historical.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
const root = __dirname;
const vehicles = JSON.parse(fs.readFileSync(path.join(root, 'sources.json'), 'utf8')).items;
const width = 1500, height = 790;
const text = (x, y, value, size = 20, color = '#263d35') => `<text x="${x}" y="${y}" font-family="Microsoft YaHei, sans-serif" font-size="${size}" fill="${color}">${value}</text>`;
async function main() {
  const overlays = [];
  let board = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#f6f4ed"/>`;
  board += text(48, 48, 'GOTOGETHER  /  VEHICLE STUDY 02', 15, '#6d806e');
  board += text(48, 95, '豪华，运动，还有老伙计。', 34);
  board += text(48, 132, '当前采用：透明图片方案    /    三蹦子 v2 · 大货斗、旧漆、开放式车头', 18, '#6d806e');
  {
    const top = 190;
    for (let col = 0; col < vehicles.length; col++) {
      const v = vehicles[col], left = 48 + col * 474;
      board += `<rect x="${left}" y="${top}" width="456" height="329" rx="16" fill="#e4ebd8"/>`;
      board += text(left + 20, top + 304, v.name, 20);
      const source = path.join(root, v.raster);
      const img = await sharp(source).resize(420, 260, {fit:'contain',background:'#00000000'}).png().toBuffer();
      overlays.push({input:img,left:left + 18,top:top + 12});
    }
  }
  board += text(48, 567, '停车位尺寸预览（每辆 180 × 139 px 图框）', 20);
  for (let col = 0; col < vehicles.length; col++) {
    const v = vehicles[col], left = 48 + col * 474;
    board += `<rect x="${left}" y="591" width="456" height="160" rx="12" fill="#e4ebd8"/>`;
    const img = await sharp(path.join(root, v.raster)).resize(180,139,{fit:'contain',background:'#00000000'}).png().toBuffer();
    overlays.push({input:img,left:left+138,top:601});
  }
  board += '</svg>';
  await sharp(Buffer.from(board)).composite(overlays).png().toFile(path.join(root, 'selected-lineup-v2.png'));
  for (const v of vehicles) {
    const m = await sharp(path.join(root,v.raster)).metadata();
    console.log(`${v.id}: PNG ${m.width}x${m.height}, alpha=${m.hasAlpha}`);
  }
  console.log('Created selected-lineup-v2.png.');
}
main().catch(error => {console.error(error);process.exitCode = 1;});
