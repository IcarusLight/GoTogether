"""Re-export generated artwork only; no AI calls and no application/database changes.

Requires Pillow. Run from any directory: python export_assets.py
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT = Path(__file__).resolve().parent
DESIGN = ROOT / 'design/mazda929-black-20261020'
WEB = ROOT / 'static/vehicles/mazda929'
PREVIEW = ROOT / 'preview'
for directory in (DESIGN, WEB, PREVIEW):
    directory.mkdir(parents=True, exist_ok=True)

original = Image.open(DESIGN / 'generated.png').convert('RGBA')
alpha = original.getchannel('A')
body = alpha.point(lambda v: 255 if v > 10 else 0).getbbox()
if body is None:
    raise ValueError('Empty source image')
# Include 24 source pixels around the meaningful silhouette/contact shadow.
box = (max(0, body[0] - 24), max(0, body[1] - 24),
       min(original.width, body[2] + 24), min(original.height, body[3] + 24))
crop = original.crop(box)
scale = min(620 / crop.width, 420 / crop.height)
size = (round(crop.width * scale), round(crop.height * scale))
offset = ((640 - size[0]) // 2, (440 - size[1]) // 2)
sprite = Image.new('RGBA', (640, 440), (0, 0, 0, 0))
sprite.alpha_composite(crop.resize(size, Image.Resampling.LANCZOS), offset)
sprite.save(DESIGN / 'default.png', optimize=True)
sprite.save(WEB / 'default.webp', lossless=True, method=6, exact=True)

font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
font = ImageFont.truetype(str(font_path), 23) if font_path.exists() else ImageFont.load_default()
small = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()

# Presentation and QA backgrounds are not baked into the production sprite.
preview = Image.new('RGBA', (1280, 850), '#f2f0e9')
pdraw = ImageDraw.Draw(preview)
pdraw.text((55, 48), 'MAZDA 929 HC', font=font, fill='#1f252b')
pdraw.text((55, 84), 'BLACK CLASSIC / LATE 1980s / GoTogether', font=small, fill='#626a70')
pdraw.line((55, 120, 1225, 120), fill='#cccac4', width=1)
preview_scale = 1180 / 640
large = crop.resize((round(size[0] * preview_scale), round(size[1] * preview_scale)), Image.Resampling.LANCZOS)
preview.alpha_composite(large, (50 + round(offset[0] * preview_scale), 30 + round(offset[1] * preview_scale)))
pdraw.text((55, 777), 'Transparent sprite  |  640 x 440  |  PNG + lossless WebP', font=small, fill='#626a70')
preview.convert('RGB').save(PREVIEW / 'mazda929-preview.jpg', quality=94)

qa = Image.new('RGB', (1280, 1000), '#f2f0e9')
for x, y, color, label in [
    (0, 0, '#f4f3ef', 'Light UI'),
    (640, 0, '#20262c', 'Dark UI'),
    (0, 440, None, 'Alpha checker')]:
    bg = Image.new('RGBA', (640, 440), color or '#ffffff')
    d = ImageDraw.Draw(bg)
    if color is None:
        for yy in range(0, 440, 20):
            for xx in range(0, 640, 20):
                if (xx // 20 + yy // 20) % 2 == 0:
                    d.rectangle((xx, yy, xx + 19, yy + 19), fill='#d9dde1')
    bg.alpha_composite(sprite)
    d.text((24, 18), label, font=small, fill='#f2f4f7' if color == '#20262c' else '#29343d')
    qa.paste(bg.convert('RGB'), (x, y))

tile = Image.new('RGBA', (640, 440), '#f4f3ef')
d = ImageDraw.Draw(tile)
d.text((24, 18), '180px display width', font=small, fill='#29343d')
thumb = sprite.resize((180, 124), Image.Resampling.LANCZOS)
tile.alpha_composite(thumb, (55, 120))
dark = Image.new('RGBA', (240, 200), '#20262c')
dark.alpha_composite(thumb, (30, 38))
tile.alpha_composite(dark, (330, 82))
d.text((55, 280), 'Light', font=small, fill='#29343d')
d.text((360, 280), 'Dark', font=small, fill='#29343d')
d.text((24, 350), 'Use a visible UI label for model identification.', font=small, fill='#626a70')
qa.paste(tile.convert('RGB'), (640, 440))
d = ImageDraw.Draw(qa)
d.text((24, 907), 'MAZDA 929 HC / black / front three-quarter / generated interpretation', font=small, fill='#29343d')
d.text((24, 942), 'QA: real alpha, retained contact shadow, no clipped body, readable small-size silhouette', font=small, fill='#626a70')
qa.save(PREVIEW / 'mazda929-contact-sheet.jpg', quality=94)

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

report = {
    'source': image_report(DESIGN / 'generated.png'),
    'png': image_report(DESIGN / 'default.png'),
    'webp': image_report(WEB / 'default.webp'),
    'cropBox': list(box), 'scaledSize': list(size), 'offset': list(offset),
    'resampling': 'Pillow LANCZOS', 'alphaPreserved': True,
    'webpEncoding': 'lossless, method=6, exact=True', 'pngWebpPixelIdentical': True,
    'allCanvasCornersTransparent': all(sprite.getpixel(p)[3] == 0 for p in [(0,0),(639,0),(0,439),(639,439)]),
    'visualChecks': ['light background', 'dark background', 'checkerboard background', '180px width',
                     'whole car not clipped', 'boxy HC sedan body, not rounded HD', 'period headlamps and wheels'],
    'verificationScope': 'Image export and visual review only; application integration not performed.'
}
(DESIGN / 'export-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
