"""Reproducible delivery export; no generation calls or app/database mutations.

Requires Pillow. Run: python export_assets.py
Only crops, proportionally resizes, pads and exports existing generated RGBA art.
It does not redraw the probe, create a replacement alpha mask, or add a shadow.
"""
from pathlib import Path
import hashlib
import json
import math
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT = Path(__file__).resolve().parent
DESIGN = ROOT / 'design/droplet-silver-20261020'
WEB = ROOT / 'static/vehicles/droplet'
PREVIEW = ROOT / 'preview'
for directory in (DESIGN, WEB, PREVIEW):
    directory.mkdir(parents=True, exist_ok=True)

original = Image.open(DESIGN / 'generated.png').convert('RGBA')
alpha = original.getchannel('A')
meaningful = alpha.point(lambda v: 255 if v > 10 else 0).getbbox()
if meaningful is None:
    raise ValueError('Empty source image')
box = (max(0, meaningful[0] - 24), max(0, meaningful[1] - 24),
       min(original.width, meaningful[2] + 24), min(original.height, meaningful[3] + 24))
crop = original.crop(box)
scale = min(560 / crop.width, 420 / crop.height)
size = (round(crop.width * scale), round(crop.height * scale))
offset = ((640 - size[0]) // 2, (440 - size[1]) // 2)
sprite = Image.new('RGBA', (640, 440), (0, 0, 0, 0))
sprite.alpha_composite(crop.resize(size, Image.Resampling.LANCZOS), offset)
sprite.save(DESIGN / 'default.png', optimize=True)
sprite.save(WEB / 'default.webp', lossless=True, method=6, exact=True)

font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
font = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
small = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()

# Presentation backdrops are separate from the transparent production asset.
preview = Image.new('RGBA', (1280, 850), '#f2f0e9')
d = ImageDraw.Draw(preview)
d.text((55, 48), 'DROPLET', font=font, fill='#222b34')
d.text((55, 90), 'COMPACT ROUND EDITION / MIRROR SILVER / GoTogether', font=small, fill='#66717b')
d.line((55, 128, 1225, 128), fill='#cccac4', width=1)
preview_scale = 1180 / 640
large = crop.resize((round(size[0] * preview_scale), round(size[1] * preview_scale)), Image.Resampling.LANCZOS)
preview.alpha_composite(large, (50 + round(offset[0] * preview_scale), 12 + round(offset[1] * preview_scale)))
d.text((55, 790), 'Transparent 2.5D sprite  |  640 x 440  |  PNG + lossless WebP', font=small, fill='#66717b')
preview.convert('RGB').save(PREVIEW / 'droplet-preview.jpg', quality=94)

qa = Image.new('RGB', (1280, 1000), '#f2f0e9')
for x, y, color, label in [(0, 0, '#f4f3ef', 'Light UI'), (640, 0, '#20262c', 'Dark UI'), (0, 440, None, 'Alpha checker')]:
    bg = Image.new('RGBA', (640, 440), color or '#ffffff')
    bd = ImageDraw.Draw(bg)
    if color is None:
        for yy in range(0, 440, 20):
            for xx in range(0, 640, 20):
                if (xx // 20 + yy // 20) % 2 == 0:
                    bd.rectangle((xx, yy, xx + 19, yy + 19), fill='#d9dde1')
    bg.alpha_composite(sprite)
    bd.text((24, 18), label, font=small, fill='#f2f4f7' if color == '#20262c' else '#29343d')
    qa.paste(bg.convert('RGB'), (x, y))
tile = Image.new('RGBA', (640, 440), '#f4f3ef')
td = ImageDraw.Draw(tile)
td.text((24, 18), '180px display width', font=small, fill='#29343d')
thumb = sprite.resize((180, 124), Image.Resampling.LANCZOS)
tile.alpha_composite(thumb, (55, 120))
dark = Image.new('RGBA', (240, 200), '#20262c')
dark.alpha_composite(thumb, (30, 38))
tile.alpha_composite(dark, (330, 82))
td.text((55, 280), 'Light', font=small, fill='#29343d')
td.text((360, 280), 'Dark', font=small, fill='#29343d')
td.text((24, 350), 'Fuller bulb + shorter taper remain readable.', font=small, fill='#626a70')
qa.paste(tile.convert('RGB'), (640, 440))
qd = ImageDraw.Draw(qa)
qd.text((24, 907), 'DROPLET / mirror silver / horizontal / fuller rounded bulb / short pointed tail', font=small, fill='#29343d')
qd.text((24, 942), 'QA: genuine alpha, soft hover shadow, no clipping, 180px silhouette', font=small, fill='#626a70')
qa.save(PREVIEW / 'droplet-contact-sheet.jpg', quality=94)

before_path = DESIGN / 'history/default-v2.png'
if before_path.exists():
    comparison = Image.new('RGBA', (1280, 540), '#f4f3ef')
    cd = ImageDraw.Draw(comparison)
    cd.text((30, 25), 'BEFORE / long horizontal taper', font=small, fill='#626a70')
    cd.text((670, 25), 'AFTER / shorter + rounder', font=small, fill='#29343d')
    cd.line((640, 20, 640, 510), fill='#d4d5d5', width=1)
    comparison.alpha_composite(Image.open(before_path).convert('RGBA'), (0, 65))
    comparison.alpha_composite(sprite, (640, 65))
    cd.text((30, 510), 'Same 640 x 440 canvas; geometry redesigned, not merely scaled down.', font=small, fill='#626a70')
    comparison.convert('RGB').save(PREVIEW / 'droplet-before-after.jpg', quality=94)

decoded = Image.open(WEB / 'default.webp').convert('RGBA')
assert decoded.size == (640, 440)
assert decoded.getchannel('A').getextrema()[0] == 0
assert all(channel.getbbox() is None for channel in ImageChops.difference(decoded, sprite).split())

def image_report(path):
    im = Image.open(path)
    a = im.getchannel('A')
    h = a.histogram()
    return {'size': list(im.size), 'mode': im.mode, 'bytes': path.stat().st_size,
            'alphaRange': list(a.getextrema()), 'transparentPixels': h[0],
            'partialAlphaPixels': sum(h[1:255]), 'opaquePixels': h[255],
            'alphaAbove10BBox': list(a.point(lambda v: 255 if v > 10 else 0).getbbox()),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def horizontal_axis_report(im):
    # Read-only geometry measurement. This threshold never alters exported alpha.
    a = im.getchannel('A')
    columns = []
    for x in range(im.width):
        ys = [y for y in range(im.height) if a.getpixel((x, y)) > 200]
        if ys:
            columns.append((x, (min(ys) + max(ys)) / 2))
    mx = sum(x for x, _ in columns) / len(columns)
    my = sum(y for _, y in columns) / len(columns)
    slope = sum((x-mx)*(y-my) for x,y in columns) / sum((x-mx)**2 for x,y in columns)
    body_bbox = a.point(lambda v: 255 if v > 200 else 0).getbbox()
    return {'method': 'Least-squares line through midpoints of high-alpha (>200) body columns; approximate raster QA, not CAD certification',
            'axisAngleDegrees': round(math.degrees(math.atan(slope)), 3),
            'centerlineYRange': [min(y for _, y in columns), max(y for _, y in columns)],
            'bodyBBox': list(body_bbox),
            'bodyLengthHeightRatio': round((body_bbox[2] - body_bbox[0]) / (body_bbox[3] - body_bbox[1]), 3),
            'centerlineYRangePixels': max(y for _, y in columns) - min(y for _, y in columns)}

report = {'source': image_report(DESIGN / 'generated.png'),
          'png': image_report(DESIGN / 'default.png'),
          'webp': image_report(WEB / 'default.webp'),
          'cropBox': list(box), 'scaledSize': list(size), 'offset': list(offset),
          'resampling': 'Pillow LANCZOS', 'alphaPreserved': True,
          'webpEncoding': 'lossless, method=6, exact=True', 'pngWebpPixelIdentical': True,
          'allCanvasCornersTransparent': all(sprite.getpixel(p)[3] == 0 for p in [(0, 0), (639, 0), (0, 439), (639, 439)]),
          'alphaNote': 'Export retains generated alpha; it is not normalized or thresholded. The >10 threshold selects crop bounds only; >200 is measurement only.',
          'horizontalAxisQA': {'source': horizontal_axis_report(original), 'sprite': horizontal_axis_report(sprite)},
          'visualChecks': ['light UI', 'dark UI', 'checkerboard', '180px width', 'full silhouette and short pointed tail visible', 'horizontal nose-left tail-right orientation', 'fuller rounded bulb with shorter taper', 'seamless reflective surface', 'small semitransparent hover shadow'],
          'verificationScope': 'Image export and visual QA only; no repository or database changes.'}
(DESIGN / 'export-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
