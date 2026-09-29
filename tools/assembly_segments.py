#!/usr/bin/env python3
"""
assembly_segments.py -- cut each kanji into its assembly groups (spec 5.3).

Written 30 September 2026 for the demo. The segments are cut from the SAME
Noto Sans CJK JP face the Learning Board renders (the repository .otf), so
stacking the segments rebuilds the board glyph pixel for pixel.

How: the glyph is rendered at 512 px; every ink pixel goes to the group whose
hand-placed centre lines are nearest; a few boxes (OVR) settle crossings, so
a stroke that runs through another stays whole. Group count per kanji must
match assemblyGroups in the content contract (kanji_content.json).

Output (written where Unity reads it, like the contract):
  unity-client/Assets/Resources/assembly/{KANJI_ID}_FULL.png
  unity-client/Assets/Resources/assembly/{KANJI_ID}_SEG{n}.png   (n = slot order)
  unity-client/Assets/Resources/assembly/{KANJI_ID}_SEG{n}_CARD.png  (cropped, for the answer card)
White ink, alpha = coverage, 512x512, full frame: the presenter tints them.

    python tools/assembly_segments.py            # write PNGs + preview
Covers set A and the tutorial example 四. Add a kanji by adding its groups to G
(and to IDS) and checking tools/assembly_preview.png.
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, sys
import pathlib
REPO=pathlib.Path(__file__).resolve().parent.parent
F=str(REPO/'unity-client'/'Assets'/'Fonts'/'NotoSansCJKjp-Regular.otf')
SIZE=512
# groups: list of (name, [polylines]); polylines are lists of points in 512-space
G={
 '四':[('frame',[[(108,131),(108,451)],[(108,140),(405,140),(405,448)],[(108,406),(405,406)]]),
       ('inside',[[(210,160),(198,256),(138,331)],[(293,160),(293,300),(310,318),(370,318),(380,246)]])],
 '月':[('frame',[[(155,118),(150,280),(80,450)],[(155,128),(370,128),(370,430),(280,445)]]),
       ('bars',[[(190,226),(335,226)],[(190,322),(335,322)]])],
 '車':[('top bar',[[(90,143),(423,143)]]),
       ('box',[[(134,200),(134,331)],[(134,200),(379,200),(379,331)],[(134,331),(379,331)],[(134,266),(379,266)]]),
       ('bottom bar + vertical',[[(78,390),(436,390)],[(255,95),(255,462)]])],
 '火':[('left dot',[[(150,195),(100,295)]]),
       ('right dot',[[(400,183),(345,293)]]),
       ('person',[[(254,100),(254,260),(90,455)],[(254,260),(420,455)]])],
 '竹':[('left',[[(156,96),(83,268)],[(150,188),(255,188)],[(170,188),(170,460)]]),
       ('right',[[(308,96),(238,268)],[(300,188),(438,188)],[(364,188),(364,440),(290,455)]])],
 '石':[('top',[[(82,138),(430,138)],[(220,138),(185,215),(150,280),(78,356)]]),
       ('mouth',[[(169,256),(169,460)],[(169,270),(390,270),(390,460)],[(169,416),(390,416)]])],
}
# Hard overrides: (kanji, group index, x0, y0, x1, y1) -- pixels inside the box go to that group.
OVR=[('車',2,241,0,269,512),          # the vertical stays whole through the bars
     ('月',0,130,100,182,470),         # left stroke of the frame
     ('月',0,352,100,400,470),         # right stroke of the frame
     ('石',0,140,0,200,255)]           # the slash crosses the mouth's top-left corner
# at crossings (equal distance) the LAST group listed wins, so verticals stay whole
def glyph(ch):
    im=Image.new('L',(SIZE,SIZE),0); ImageDraw.Draw(im).text((SIZE//2,SIZE//2),ch,font=ImageFont.truetype(F,400),fill=255,anchor='mm')
    return np.array(im)
def segdist(px,py,a,b):
    ax,ay=a; bx,by=b; dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    t=np.clip(((px-ax)*dx+(py-ay)*dy)/L,0,1) if L>0 else 0
    return np.hypot(px-(ax+t*dx),py-(ay+t*dy))
def split(ch):
    a=glyph(ch); ys,xs=np.nonzero(a>8)
    D=[]
    for name,polys in G[ch]:
        d=np.full(xs.shape,1e9)
        for pl in polys:
            for p,q in zip(pl,pl[1:]): d=np.minimum(d,segdist(xs,ys,p,q))
        D.append(d)
    D=np.stack(D)  # groups x pixels
    # tie -> last group: argmin over reversed
    idx=len(D)-1-np.argmin(D[::-1]-1e-6*np.arange(len(D))[:,None][::-1],axis=0)
    for k,g,x0,y0,x1,y1 in OVR:
        if k==ch:
            sel=(xs>=x0)&(xs<=x1)&(ys>=y0)&(ys<=y1); idx[sel]=g
    masks=[]
    for g in range(len(D)):
        m=np.zeros_like(a); sel=idx==g; m[ys[sel],xs[sel]]=a[ys[sel],xs[sel]]; masks.append(m)
    return a,masks,D.min(0).max()

IDS={'月':'KANJI_TSUKI','車':'KANJI_KURUMA','火':'KANJI_HI','竹':'KANJI_TAKE','石':'KANJI_ISHI','四':'KANJI_YON'}

def main():
    import os
    out=REPO/'unity-client'/'Assets'/'Resources'/'assembly'
    os.makedirs(out,exist_ok=True)
    contract=json.load(open(REPO/'unity-client'/'Assets'/'Resources'/'kanji_content.json',encoding='utf-8'))
    groups={k['id']:k['assemblyGroups'] for k in contract['kanji']}
    cols=[(220,50,50),(40,110,220),(30,150,60)]
    tiles=[]
    for ch,kid in IDS.items():
        if len(G[ch])!=groups[kid]:
            raise SystemExit(f"{ch}: {len(G[ch])} groups here, contract says {groups[kid]}")
        a,masks,_=split(ch)
        def save(m,name):
            rgba=np.zeros((SIZE,SIZE,4),np.uint8); rgba[...,:3]=255; rgba[...,3]=m
            Image.fromarray(rgba,'RGBA').save(out/f'{name}.png',optimize=True)
        save(a,f'{kid}_FULL')
        for i,m in enumerate(masks):
            save(m,f'{kid}_SEG{i+1}')
            # Card version: the segment alone, cropped square with a margin, so
            # the piece reads large on the answer card.
            ys,xs=np.nonzero(m>8)
            cx,cy=(xs.min()+xs.max())/2,(ys.min()+ys.max())/2
            half=max(xs.max()-xs.min(),ys.max()-ys.min())/2*1.18+6
            box=[int(cx-half),int(cy-half),int(cx+half),int(cy+half)]
            rgba=np.zeros((SIZE,SIZE,4),np.uint8); rgba[...,:3]=255; rgba[...,3]=m
            Image.fromarray(rgba,'RGBA').crop(box).resize((256,256),Image.LANCZOS).save(out/f'{kid}_SEG{i+1}_CARD.png',optimize=True)
        rgb=np.full((SIZE,SIZE,3),255,np.uint8)
        for g,m in enumerate(masks):
            al=(m/255.0)[...,None]; rgb=(rgb*(1-al)+np.array(cols[g])*al).astype(np.uint8)
        t=Image.fromarray(rgb); ImageDraw.Draw(t).text((6,4),ch+'  '+' | '.join(n for n,_ in G[ch]),fill='black',font=ImageFont.truetype(F,26))
        tiles.append(t)
    sheet=Image.new('RGB',(SIZE*3,SIZE*((len(tiles)+2)//3)),'white')
    for i,t in enumerate(tiles): sheet.paste(t,((i%3)*SIZE,(i//3)*SIZE))
    sheet.save(REPO/'tools'/'assembly_preview.png')
    print(f"{len(IDS)} kanji -> {out}")

if __name__=='__main__':
    main()
