import json, os, re, unicodedata
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H = 1200, 630
PAPER, INK, MUTED, WHITE = (247,245,240), (33,31,27), (126,120,108), (255,255,255)
FR, AR = 'fonts/fraunces.ttf', 'fonts/archivo.ttf'
def font(p, s, w=400, o=None):
    f = ImageFont.truetype(p, s)
    try:
        f.set_variation_by_axes([{b'Weight':w, b'Optical Size':o or s, b'Width':100}.get(a['name'], a['default']) for a in f.get_variation_axes()])
    except Exception: pass
    return f
def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower().replace('&','and').replace("'",'')
    return re.sub(r'-+','-', re.sub(r'[^a-z0-9]+','-', s)).strip('-')
def hx(h): h = h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def ink(c): r,g,b = [v/255 for v in c]; return INK if 0.2126*r+0.7152*g+0.0722*b > 0.55 else WHITE
def lin(v): v/=255; return ((v+0.055)/1.055)**2.4 if v>0.04045 else v/12.92
def oklab(r,g,b):
    R,G,B = lin(r),lin(g),lin(b)
    l=(0.4122214708*R+0.5363325363*G+0.0514459929*B)**(1/3); m=(0.2119034982*R+0.6806995451*G+0.1073969566*B)**(1/3); s=(0.0883024619*R+0.2817188376*G+0.6299787005*B)**(1/3)
    return [0.2104542553*l+0.793617785*m-0.0040720468*s, 1.9779984951*l-2.428592205*m+0.4505937099*s, 0.0259040371*l+0.7827717662*m-0.808675766*s]
paints = json.load(open('paints-fixed.json')); N = len(paints)
OKM = np.array([oklab(*hx(p['hex'])) for p in paints]); OL = OKM[:,0]; OC = np.hypot(OKM[:,1], OKM[:,2]); OH = np.degrees(np.arctan2(OKM[:,2], OKM[:,1]))%360
BR = [p['brand'] for p in paints]
def dmatch(i):
    dh = np.abs(OH-OH[i])%360; dh = np.radians(np.where(dh>180,360-dh,dh))
    return 190*np.sqrt(((OL-OL[i])/1.3)**2 + (OC-OC[i])**2 + 4*(2*np.sqrt(np.maximum(OC*OC[i],0))*np.sin(dh/2))**2)
BL = "FARROW & BALL  ·  LITTLE GREENE  ·  CRAIG & ROSE  ·  DULUX  ·  JOHNSTONE'S  ·  VALSPAR  ·  LICK  ·  CROWN  ·  COAT"
def build(i, out):
    p=paints[i]; c=hx(p['hex']); d=dmatch(i); best={}
    for k in range(N):
        b=BR[k]
        if b!=p['brand'] and (b not in best or d[k]<d[best[b]]): best[b]=k
    picks=sorted(best.values(), key=lambda k:d[k])[:4]
    im=Image.new('RGB',(W,H),PAPER); dr=ImageDraw.Draw(im)
    dr.text((60,46),'Pick any colour, find the',font=font(FR,44,800,48),fill=INK)
    dr.text((60,98),'paint — across every UK brand',font=font(FR,44,800,48),fill=INK)
    dr.text((60,162),BL,font=font(FR,16,600,14),fill=MUTED)
    dr.rounded_rectangle([60,210,350,510],radius=10,fill=c); li=ink(c)
    dr.text((80,236),'YOUR COLOUR',font=font(AR,14,700),fill=li); dr.text((80,470),p['hex'].upper(),font=font(AR,22,600),fill=li)
    dr.text((372,340),'→',font=font(AR,30,600),fill=MUTED)
    cols=[(434,776),(797,1139)]; rows=[(211,349),(371,509)]
    for n,k in enumerate(picks):
        x0,x1=cols[n%2]; y0,y1=rows[n//2]; q=paints[k]
        dr.rounded_rectangle([x0,y0,x1,y1],radius=10,fill=WHITE)
        st=Image.new('RGB',(91,y1-y0),hx(q['hex'])); mk=Image.new('L',(x1-x0,y1-y0),0)
        ImageDraw.Draw(mk).rounded_rectangle([0,0,x1-x0-1,y1-y0-1],radius=10,fill=255)
        im.paste(st,(x0,y0),mk.crop((0,0,91,y1-y0)))
        dr.text((x0+106,y0+32),q['name'],font=font(FR,22,700,24),fill=INK); dr.text((x0+106,y0+62),q['brand'].upper(),font=font(AR,12,600),fill=MUTED)
    fl=font(FR,28,800,30); dr.text((60,585),'PaintDial',font=fl,fill=INK); dx=60+dr.textlength('PaintDial',font=fl)+11
    dr.ellipse([dx,597,dx+14,611],fill=c); fu=font(AR,17,400); u='paintdial.co.uk'
    dr.text((1140-dr.textlength(u,font=fu),592),u,font=fu,fill=MUTED); im.save(out,'JPEG',quality=82,optimize=True)
if __name__=='__main__':
    os.makedirs('site/share',exist_ok=True)
    for n,p in enumerate(paints):
        build(n,'site/share/'+slug(p['brand'])+'-'+slug(p['name'])+'.jpg')
        if (n+1)%500==0: print(f'  {n+1}/{N}')
    print('regenerated',N,'images')
