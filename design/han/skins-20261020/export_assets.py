from PIL import Image, ImageDraw, ImageFont, ImageChops
from pathlib import Path
import json, hashlib
root=Path(__file__).resolve().parent
sources={'default':root/'sources/han-red-source.png','didi':root/'sources/han-didi-source.png'}
ims={k:Image.open(p).convert('RGBA') for k,p in sources.items()}
w=max(im.width for im in ims.values());h=max(im.height for im in ims.values())
for k,im in ims.items():
 canvas=Image.new('RGBA',(w,h),(0,0,0,0));canvas.alpha_composite(im,(0,0));ims[k]=canvas
boxes=[im.getchannel('A').point(lambda v:255 if v>10 else 0).getbbox() for im in ims.values()]
# Freeze the common frame from v1 so the red export is unchanged.
box=(28,145,1494,918)
scale=min(620/(box[2]-box[0]),420/(box[3]-box[1]))
scaled_size=(round((box[2]-box[0])*scale),round((box[3]-box[1])*scale))
offset=((640-scaled_size[0])//2,(440-scaled_size[1])//2)
sprites={}
for k,im in ims.items():
 sprite=Image.new('RGBA',(640,440),(0,0,0,0));sprite.alpha_composite(im.crop(box).resize(scaled_size,Image.Resampling.LANCZOS),offset)
 sprite.save(root/f'png/han-{k}.png',optimize=True)
 sprite.save(root/f'static/vehicles/han/{k}.webp',lossless=True,method=6,exact=True)
 sprites[k]=sprite
# Contact sheet: light/dark/checker plus native 180px tiles.
qa=Image.new('RGB',(1280,1500),'#f4f3ef');draw=ImageDraw.Draw(qa)
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(fontpath,22);small=ImageFont.truetype(fontpath,18)
for col,(k,sprite) in enumerate(sprites.items()):
 for row,color in enumerate(['#f4f3ef','#20262c',None]):
  bg=Image.new('RGBA',(640,440),color or '#ffffff')
  if color is None:
   d=ImageDraw.Draw(bg)
   for yy in range(0,440,20):
    for xx in range(0,640,20):
     if (xx//20+yy//20)%2==0:d.rectangle((xx,yy,xx+19,yy+19),fill='#d9dde1')
  bg.alpha_composite(sprite)
  qa.paste(bg.convert('RGB'),(col*640,row*440))
  draw.text((col*640+20,row*440+15),('Red / default' if k=='default' else 'Pearl white + Didi / didi'),font=font,fill='#ecf0f3' if row==1 else '#263440')
 thumb=sprite.resize((180,124),Image.Resampling.LANCZOS)
 tile=Image.new('RGBA',(640,180),'#f4f3ef');tile.alpha_composite(thumb,(20,40))
 dark=Image.new('RGBA',(180,124),'#20262c');dark.alpha_composite(thumb);tile.alpha_composite(dark,(230,40))
 qa.paste(tile.convert('RGB'),(col*640,1320));draw.text((col*640+20,1330),'180px display width (light / dark)',font=small,fill='#263440')
qa.save(root/'preview/han-contact-sheet.jpg',quality=94)
# Compact display preview, 2 x 640px assets on light neutral, separate from source alpha.
preview=Image.new('RGBA',(1280,480),'#f4f3ef')
d=ImageDraw.Draw(preview)
for n,(k,sprite) in enumerate(sprites.items()):
 preview.alpha_composite(sprite,(n*640,20));d.text((n*640+22,15),'Han EV - '+('Red' if k=='default' else 'Didi concept skin'),font=font,fill='#263440')
preview.convert('RGB').save(root/'preview/han-two-variants.jpg',quality=94)
report={'canvas':[640,440],'source_normalized_canvas':[w,h],'common_crop':box,'common_scaled_size':scaled_size,'common_offset':offset,'webp':'lossless, method=6, exact=True','assets':{}}
for k,sprite in sprites.items():
 p=root/f'static/vehicles/han/{k}.webp';check=Image.open(p)
 assert check.size==(640,440) and check.mode=='RGBA' and check.getchannel('A').getextrema()==(0,255)
 assert ImageChops.difference(check,sprite).getbbox() is None
 a=check.getchannel('A');hist=a.histogram()
 report['assets'][k]={'bytes':p.stat().st_size,'alphaExtrema':a.getextrema(),'transparentPixels':hist[0],'partialAlphaPixels':sum(hist[1:255]),'opaquePixels':hist[255],'alphaAbove10BBox':a.point(lambda v:255 if v>10 else 0).getbbox(),'pngMatchesWebpExactly':True}
# Silhouette overlap at opaque-ish threshold; includes small generation changes, not a pixel-identity claim.
a=sprites['default'].getchannel('A').point(lambda v:255 if v>220 else 0);b=sprites['didi'].getchannel('A').point(lambda v:255 if v>220 else 0)
inter=sum(1 for x,y in zip(a.getdata(),b.getdata()) if x and y);union=sum(1 for x,y in zip(a.getdata(),b.getdata()) if x or y)
report['highAlphaSilhouetteIoU']=inter/union
(root/'docs/export-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
