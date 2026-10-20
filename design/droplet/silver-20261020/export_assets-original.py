"""Reproducible delivery export; no generation calls or app/database mutations.

Requires Pillow. Run: python export_assets.py
Only crops, proportionally resizes, pads and exports existing generated RGBA art.
It does not redraw the probe, create a replacement alpha mask, or add a shadow.
"""
from pathlib import Path
import hashlib
import json
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
scale = min(620 / crop.width, 420 / crop.height)
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
d.text((55, 90), 'MIRROR SILVER / HOVERING PROBE / GoTogether', font=small, fill='#66717b')
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
td.text((24, 350), 'Silver silhouette + needle tip remain readable.', font=small, fill='#626a70')
qa.paste(tile.convert('RGB'), (640, 440))
qd = ImageDraw.Draw(qa)
qd.text((24, 907), 'DROPLET / seamless mirror silver / rounded nose lower-left / needle tail upper-right', font=small, fill='#29343d')
qd.text((24, 942), 'QA: genuine alpha, soft hover shadow, no clipping, 180px silhouette', font=small, fill='#626a70')
qa.save(PREVIEW / 'droplet-contact-sheet.jpg', quality=94)

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

report = {'source': image_report(DESIGN / 'generated.png'),
          'png': image_report(DESIGN / 'default.png'),
          'webp': image_report(WEB / 'default.webp'),
          'cropBox': list(box), 'scaledSize': list(size), 'offset': list(offset),
          'resampling': 'Pillow LANCZOS', 'alphaPreserved': True,
          'webpEncoding': 'lossless, method=6, exact=True', 'pngWebpPixelIdentical': True,
          'allCanvasCornersTransparent': all(sprite.getpixel(p)[3] == 0 for p in [(0, 0), (639, 0), (0, 439), (639, 439)]),
          'alphaNote': 'Generated source has maximum alpha 254. Export retains alpha; it is not normalized or thresholded. The >10 threshold selects crop bounds only.',
          'visualChecks': ['light UI', 'dark UI', 'checkerboard', '180px width', 'full silhouette and needle tip visible', 'seamless reflective surface', 'small semitransparent hover shadow'],
          'verificationScope': 'Image export and visual QA only; no repository or database changes.'}
(DESIGN / 'export-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
