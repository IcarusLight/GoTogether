#!/usr/bin/env python3
"""Compose generated transparent layers; no car/VFX repainting or background removal."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import shutil, json, base64, hashlib

ROOT = Path(__file__).resolve().parent
PKG = ROOT if (ROOT/"design/roadster-rocket-silver-20261020/sources").exists() else ROOT / "package"
DES = PKG / "design/roadster-rocket-silver-20261020"
STATIC = PKG / "static/vehicles/roadsterRocket"
PREVIEW = PKG / "preview"
for p in (DES / "sources", DES / "aligned-2x", STATIC, PREVIEW, PKG / "demo"):
    p.mkdir(parents=True, exist_ok=True)
native = {
    "car": ROOT.parent/"generated_images/exec-bf88068b-eea8-4a61-8114-3342a048c6d8.png",
    "gas": ROOT.parent/"generated_images/exec-6341471c-92bb-4ac1-9701-25e59e9dab87.png",
    "shadow": ROOT.parent/"generated_images/exec-30648500-da17-4c28-9aea-12b9db0581a6.png",
}
for key, path in native.items():
    bundled=DES/"sources"/f"{key}-generated.png"
    if bundled.exists():
        native[key]=bundled
    else:
        shutil.copyfile(path, bundled)

def canvas():
    return Image.new("RGBA", (1280, 880))

def crop_content(im, threshold=1, margin=2):
    # Threshold locates the box only; source alpha is not thresholded or replaced.
    box = im.getchannel("A").point(lambda a: 255 if a > threshold else 0).getbbox()
    x0,y0,x1,y1=box
    box=(max(0,x0-margin),max(0,y0-margin),min(im.width,x1+margin),min(im.height,y1+margin))
    return im.crop(box), list(box)

car_src, car_box = crop_content(Image.open(native["car"]).convert("RGBA"))
car_scaled = car_src.resize((1200, round(car_src.height*1200/car_src.width)), Image.Resampling.LANCZOS)
car = canvas()
car.alpha_composite(car_scaled, (40, 160))

shadow_src, shadow_box = crop_content(Image.open(native["shadow"]).convert("RGBA"))
# Perspective shadow layer may be compressed independently of the rigid car.
shadow_scaled = shadow_src.resize((1160, 240), Image.Resampling.LANCZOS)
shadow_scaled.putalpha(shadow_scaled.getchannel("A").point(lambda a: round(a*.70)))
shadow = canvas()
shadow.alpha_composite(shadow_scaled, (58, 573))

gas_src, gas_box = crop_content(Image.open(native["gas"]).convert("RGBA"), threshold=2, margin=4)
gas = canvas()
jets = [
    # x, y, width, height, compositing opacity in the 640x440 coordinate system
    (109, 286, 82, 97, .34),
    (511, 247, 65, 88, .32),
]
for x,y,w,h,opacity in jets:
    plume=gas_src.resize((w*2,h*2),Image.Resampling.LANCZOS)
    plume.putalpha(plume.getchannel("A").point(lambda a: round(a*opacity)))
    gas.alpha_composite(plume, (x*2,y*2))

default=canvas()
for layer in (shadow,gas,car):
    default.alpha_composite(layer)
layers={"car":car,"shadow":shadow,"gas":gas,"default":default}
qa={}
for name,im in layers.items():
    im.save(DES/"aligned-2x"/f"{name}@2x.png")
    small=im.resize((640,440),Image.Resampling.LANCZOS)
    small.save(DES/f"{name}.png")
    small.save(STATIC/f"{name}.webp",lossless=True,exact=True,method=6)
    rgba=Image.open(STATIC/f"{name}.webp").convert("RGBA")
    assert rgba.tobytes()==small.tobytes(), name
    a=small.getchannel("A")
    corners=[a.getpixel(p) for p in [(0,0),(639,0),(0,439),(639,439)]]
    assert corners==[0,0,0,0]
    qa[name]={"size":[640,440],"mode":small.mode,"alpha_range":a.getextrema(),
              "nonzero_alpha_box":a.getbbox(),"transparent_corner_alpha":corners,
              "png_webp_rgba_identical":True,"webp_bytes":(STATIC/f"{name}.webp").stat().st_size,
              "png_sha256":hashlib.sha256((DES/f"{name}.png").read_bytes()).hexdigest()}

# Presentation preview, never a production asset.
regular="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
bold="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
def font(n,b=False): return ImageFont.truetype(bold if b else regular,n)
out=Image.new("RGB",(1440,1100),"#f0efeb")
d=ImageDraw.Draw(out)
d.text((54,31),"GOTOGETHER  /  VEHICLE COLLECTION",font=font(16,True),fill="#6a706e")
d.text((50,61),"ROADSTER ROCKET",font=font(54,True),fill="#16252a")
d.text((54,139),"银灰悬浮版 · 独立车身 / 地影 / 冷气流 · 640 × 440",font=font(22),fill="#64706e")
d.rounded_rectangle((48,199,885,778),radius=24,fill="#faf9f5")
d.rounded_rectangle((907,199,1392,778),radius=24,fill="#1d2932")
d.text((76,224),"01  浅色界面",font=font(18,True),fill="#67706c")
d.text((935,224),"02  深色界面",font=font(18,True),fill="#c5d1d3")
hero=default.resize((800,550),Image.Resampling.LANCZOS)
out.paste(hero,(64,202),hero)
dark=default.resize((480,330),Image.Resampling.LANCZOS)
out.paste(dark,(910,320),dark)
d.text((936,680),"同一套透明素材",font=font(20,True),fill="#e7eeeb")
d.text((936,716),"轻悬浮 · 短冷气流 · 无喷焰",font=font(16),fill="#9fadb0")
for i,(name,title) in enumerate([("car","A  车身"),("shadow","B  地面阴影"),("gas","C  冷气流")]):
    x=48+i*456
    d.rounded_rectangle((x,804,x+432,1044),radius=20,fill="#e3e6e3" if name!="gas" else "#33414a")
    color="#566461" if name!="gas" else "#d7e0df"
    d.text((x+24,821),title,font=font(17,True),fill=color)
    im=layers[name].resize((320,220),Image.Resampling.LANCZOS)
    if name=="car":
        out.paste(im,(x+56,826),im)
    elif name=="shadow":
        out.paste(im,(x+56,784),im)
    else:
        out.paste(im,(x+56,788),im)
d.text((54,1061),"透明素材预览  /  AI 绘制的二维游戏美术演绎，非官方资产或工程复刻",font=font(15),fill="#78817c")
out.save(PREVIEW/"Roadster-Rocket-预览.jpg",quality=94)
out.save(ROOT/"Roadster-Rocket-预览.jpg",quality=94)

# Four-up diagnostic including an actual transparency checkerboard.
qaout=Image.new("RGB",(1280,960),"#ececea")
qd=ImageDraw.Draw(qaout)
small=Image.open(DES/"default.png")
for i,(name,color) in enumerate([("LIGHT","#faf9f5"),("DARK","#202b35"),("ALPHA","#ffffff"),("180 PX","#faf9f5")]):
    x=(i%2)*640;y=(i//2)*480
    qd.rectangle((x,y,x+640,y+480),fill=color)
    if name=="ALPHA":
        for yy in range(y,y+480,16):
            for xx in range(x,x+640,16):
                if ((xx//16)+(yy//16))%2==0:
                    qd.rectangle((xx,yy,xx+15,yy+15),fill="#d8dcda")
    if name=="180 PX":
        thumb=small.resize((180,124),Image.Resampling.LANCZOS)
        qaout.paste(thumb,(x+230,y+160),thumb)
    else:
        qaout.paste(small,(x,y+20),small)
    qd.text((x+20,y+16),name,font=font(16,True),fill="#96a2a5" if name=="DARK" else "#55605c")
qaout.save(PREVIEW/"Roadster-Rocket-QA.jpg",quality=94)
qaout.save(ROOT/"Roadster-Rocket-QA.jpg",quality=94)

metadata={
 "created":"2026-10-20","vehicle_id":"roadsterRocket","appearance_id":"default",
 "canvas_1x":[640,440],"canvas_2x":[1280,880],
 "compositing_back_to_front":["shadow","gas","car"],
 "alpha":"Generated alpha preserved through crop, resampling and opacity compositing; no background keying.",
 "crop_box_thresholds_are_for_bounds_only":True,
 "native_sources":{k:{"size":list(Image.open(p).size),"filename":f"sources/{k}-generated.png"} for k,p in native.items()},
 "crop_boxes":{"car":car_box,"gas":gas_box,"shadow":shadow_box},
 "car_1x_placement":{"x":20,"y":80,"width":600,"height":car_scaled.height/2},
 "shadow_1x_placement":{"x":29,"y":286.5,"width":580,"height":120,"opacity":.70},
 "gas_1x_jets":jets,
 "artwork_type":"AI-generated 2D/2.5D visual interpretation of October 2026 Roadster Rocket. Not 3D model or engineering reference.",
 "design_references":[
 "https://www.tesla.com/roadster?redirect=no",
 "https://digitalassets.tesla.com/tesla-contents/image/upload/f_auto,q_auto/Roadster-03-Carousel-Slide-1-Desktop.jpg",
 "https://digitalassets.tesla.com/tesla-contents/image/upload/f_auto,q_auto/Roadster-02-Pilot-Desktop.jpg",
 "https://www.caranddriver.com/news/a74145531/tesla-roadster-revealed/"],
 "style_reference":"Previously created GoTogether black CT5 for camera / material style only.",
 "reference_photos_not_redistributed":True,
 "repository_modified":False,"deployment_performed":False,
}
(DES/"sources.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf8")
(DES/"export-qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf8")
if Path(__file__).resolve() != (PKG/"export_assets.py").resolve():
    shutil.copyfile(__file__,PKG/"export_assets.py")

# Self-contained offline layered CSS preview, no network calls.
encoded={key:base64.b64encode((STATIC/f"{key}.webp").read_bytes()).decode() for key in ["car","shadow","gas"]}
html='''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roadster Rocket · 分层悬浮预览</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f0efeb;color:#1c2c30;font:16px/1.6 system-ui,sans-serif}
main{max-width:1040px;margin:48px auto;padding:0 24px}h1{font-size:clamp(28px,5vw,48px);margin:4px 0}
.eyebrow{letter-spacing:.14em;font-size:12px;color:#697875}.sub{color:#687571}
.panel{background:#faf9f5;border-radius:28px;overflow:hidden;transition:background .2s}
.stage{position:relative;aspect-ratio:16/11;width:100%;isolation:isolate}
.layer,.hover-group{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none}
.shadow{animation:shadow 3.6s ease-in-out infinite;transform-origin:50% 82%}
.hover-group{animation:hover 3.6s ease-in-out infinite}.gas{animation:gas 2.2s ease-in-out infinite}
@keyframes hover{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.5%)}}
@keyframes shadow{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.83;transform:scale(.975,.94)}}
@keyframes gas{0%,100%{opacity:.82}50%{opacity:1}}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
button{border:1px solid #bdc7c3;border-radius:999px;background:transparent;color:inherit;padding:10px 18px;font:inherit;cursor:pointer}
button:focus-visible{outline:3px solid #427f9a;outline-offset:4px}.note{font-size:13px;color:#6d7976}
body.dark{background:#111a21;color:#e1ebe8}.dark .panel{background:#24313a}.dark .sub,.dark .note{color:#a0b2b4}
.paused .layer,.paused .hover-group{animation-play-state:paused}.no-gas .gas{visibility:hidden}
@media(prefers-reduced-motion:reduce){.layer,.hover-group{animation:none!important}}
</style><main><div class="eyebrow">GOTOGETHER / ASSET PREVIEW</div><h1>Roadster Rocket</h1>
<p class="sub">银灰悬浮版 · 同画布分层叠加，地影留在地面</p>
<div class="panel"><div class="stage" role="img" aria-label="银灰色 Roadster Rocket，车身水平轻悬浮，轮胎下方有独立软阴影和短白色冷气流">
<img class="layer shadow" src="data:image/webp;base64,__SHADOW__" alt="">
<div class="hover-group"><img class="layer gas" src="data:image/webp;base64,__GAS__" alt="">
<img class="layer car" src="data:image/webp;base64,__CAR__" alt=""></div></div></div>
<div class="controls"><button id="theme" type="button" aria-pressed="false">切换深色</button>
<button id="motion" type="button" aria-pressed="false">暂停动画</button>
<button id="gas" type="button" aria-pressed="false">隐藏气流</button></div>
<p class="note">离线预览，无需安装或联网。动画仅使用 CSS；系统启用减少动态效果时自动停用。
本文件是接入演示，未修改 GoTogether 项目。图像为二维游戏美术演绎，不代表实车结构或道路使用许可。</p></main>
<script>
for(const [id,cls,on,off] of [['theme','dark','切换浅色','切换深色'],['motion','paused','继续动画','暂停动画'],['gas','no-gas','显示气流','隐藏气流']]){
document.getElementById(id).addEventListener('click',e=>{const value=document.body.classList.toggle(cls);e.currentTarget.textContent=value?on:off;e.currentTarget.setAttribute('aria-pressed',String(value));});}
</script></html>'''
for key,value in encoded.items(): html=html.replace("__"+key.upper()+"__",value)
(PKG/"demo/Roadster-Rocket-悬浮演示.html").write_text(html,encoding="utf8")
print(json.dumps({"package":str(PKG),"preview":str(PREVIEW),"qa":qa},ensure_ascii=False,indent=2))
