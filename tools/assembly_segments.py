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
It also lists the segments in Resources/kanji/{KANJI_ID}.asset.
Covers sets A, B and C and the tutorial example 四. Add a kanji by adding its groups to G
(and to IDS) and checking tools/assembly_preview.png.
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, re, sys
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
 # Sets B and C (Task 1.9, 19 October): groups from the "Assembly" column of
 # Tabla_Autoria_Kanji_Fase2.md
 '山':[('centre peak',[[(256,100),(256,380)]]),
       ('base with sides',[[(112,190),(112,450)],[(112,398),(400,398)],[(400,190),(400,450)]])],
 '門':[('left leaf',[[(107,122),(107,455)],[(107,122),(230,122),(230,252)],[(107,182),(230,182)],[(107,250),(230,250)]]),
       ('right leaf',[[(288,122),(288,252)],[(288,122),(412,122),(412,435),(335,452)],[(288,182),(412,182)],[(288,250),(412,250)]])],
 '女':[('く',[[(237,100),(150,330)],[(165,320),(416,448)]]),
       ('ノ',[[(371,211),(335,305),(256,384),(90,448)]]),
       ('一',[[(77,205),(435,205)]])],
 '手':[('three horizontals',[[(109,134),(390,102)],[(102,220),(416,220)],[(77,316),(435,316)]]),
       ('hooked vertical',[[(257,141),(257,442),(166,454)]])],
 '雨':[('top bar',[[(77,132),(435,132)]]),
       ('frame',[[(113,205),(113,458)],[(113,205),(413,205),(413,442),(333,454)],[(253,141),(253,454)]]),
       ('four drops',[[(147,262),(224,307)],[(147,343),(218,390)],[(294,262),(369,307)],[(288,343),(365,390)]])],
 '人':[('left stroke',[[(250,109),(235,260),(180,360),(77,442)]]),
       ('right stroke',[[(262,230),(320,350),(435,442)]])],
 '足':[('口 upper',[[(128,115),(128,243)],[(128,115),(397,115),(397,243)],[(128,243),(397,243)]]),
       ('middle',[[(260,243),(260,415)],[(260,326),(407,326)]]),
       ('foot',[[(160,284),(140,370),(77,448)],[(160,340),(200,400),(256,428),(435,437)]])],
 '牛':[('horns',[[(160,109),(130,200),(102,256)],[(134,179),(410,179)]]),
       ('body',[[(77,326),(435,326)],[(259,96),(259,460)]])],
 '肉':[('冂 outer',[[(109,154),(109,461)],[(109,154),(406,154),(406,435),(333,450)]]),
       ('inner strokes',[[(271,96),(240,200),(154,275)],[(236,205),(352,282)],[(269,269),(230,350),(147,403)],[(250,333),(352,403)]])],
 '花':[('艹 grass',[[(79,143),(430,143)],[(192,96),(192,198)],[(323,96),(323,198)]]),
       ('亻',[[(198,211),(150,280),(70,339)],[(156,256),(156,461)]]),
       ('匕',[[(416,250),(275,320)],[(275,205),(275,420),(300,430),(400,430),(430,371)]])],
 # The 10 reserve kanji that are a first substitute (Task 1.10, 19 October):
 # groups defined here from stroke order, pending Sebas's review
 '土':[('十',[[(102,237),(410,237)],[(256,96),(256,420)]]),
       ('base',[[(77,429),(435,429)]])],
 '米':[('two dots',[[(115,122),(173,211)],[(397,122),(339,218)]]),
       ('cross',[[(79,262),(433,262)],[(256,96),(256,461)]]),
       ('two sweeps',[[(250,280),(165,370),(77,429)],[(262,280),(345,370),(435,429)]])],
 '木':[('cross',[[(83,207),(429,207)],[(256,96),(256,461)]]),
       ('two sweeps',[[(250,240),(170,340),(70,403)],[(262,240),(345,340),(435,403)]])],
 '耳':[('frame',[[(83,131),(429,131)],[(160,147),(160,372)],[(352,147),(352,461)]]),
       ('bars',[[(175,218),(337,218)],[(175,307),(337,307)],[(77,407),(435,378)]])],
 '口':[('left, top and right',[[(122,134),(122,448)],[(122,150),(390,150),(390,448)]]),
       ('bottom',[[(140,402),(372,402)]])],
 '貝':[('目 box',[[(143,122),(143,355)],[(143,122),(371,122),(371,355)],[(143,201),(371,201)],[(143,276),(371,276)],[(143,348),(371,348)]]),
       ('legs',[[(211,384),(90,448)],[(294,384),(422,448)]])],
 '金':[('roof',[[(252,100),(220,140),(155,200),(85,248)],[(260,100),(288,140),(358,200),(425,245)]]),
       ('body',[[(180,230),(345,230)],[(105,307),(407,307)],[(256,230),(256,435)],[(86,435),(426,435)]]),
       ('two dots',[[(147,339),(185,410)],[(365,339),(320,410)]])],
 '川':[('left',[[(134,115),(134,330),(110,410),(77,454)]]),
       ('middle',[[(262,134),(262,422)]]),
       ('right',[[(397,115),(397,461)]])],
 '水':[('centre hook',[[(256,96),(256,429),(171,442)]]),
       ('side strokes',[[(79,208),(211,198),(170,290),(77,410)],[(416,173),(307,256)],[(266,170),(290,215),(311,260),(335,330),(380,380),(435,422)]])],
 '糸':[('幺 top',[[(224,96),(115,179),(205,243)],[(346,141),(205,280)],[(83,296),(384,282)],[(326,230),(435,333)]]),
       ('小 bottom',[[(256,325),(256,461)],[(186,352),(83,435)],[(320,352),(429,435)]])],
}
# Hard overrides: (kanji, group index, x0, y0, x1, y1) -- pixels inside the box go to that group.
OVR=[('車',2,241,0,269,512),          # the vertical stays whole through the bars
     ('月',0,130,100,182,470),         # left stroke of the frame
     ('月',0,352,100,400,470),         # right stroke of the frame
     ('石',0,140,0,200,255),           # the slash crosses the mouth's top-left corner
     ('手',1,243,140,272,470),         # the vertical stays whole through the horizontals
     ('雨',1,240,140,267,460),         # the centre vertical stays whole through the top bar
     ('牛',1,243,90,275,470),          # the vertical stays whole through the horns' bar
     ('女',2,0,189,512,219),           # 一 stays whole where く and ノ cross it
     ('肉',0,94,155,418,187),          # the frame's top bar stays whole where the inner ノ crosses it
     ('米',1,241,90,271,465),          # the vertical stays whole where the sweeps leave it
     ('木',0,241,90,271,465),
     ('水',0,239,90,274,440),
     ('水',1,275,160,300,290),         # the right stroke where it leaves the vertical
     ('耳',0,145,140,177,378),         # both verticals of the frame stay whole
     ('耳',0,333,140,369,465),
     ('土',1,0,413,512,446),           # the base stays whole under the vertical
     ('口',0,104,130,139,450),         # both sides of 口 stay whole; the bottom fits between them
     ('口',0,372,130,408,450)]
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

IDS={'月':'KANJI_TSUKI','車':'KANJI_KURUMA','火':'KANJI_HI','竹':'KANJI_TAKE','石':'KANJI_ISHI','四':'KANJI_YON',
     '山':'KANJI_YAMA','門':'KANJI_MON','女':'KANJI_ONNA','手':'KANJI_TE','雨':'KANJI_AME',
     '人':'KANJI_HITO','足':'KANJI_ASHI','牛':'KANJI_USHI','肉':'KANJI_NIKU','花':'KANJI_HANA',
     '土':'KANJI_TSUCHI','米':'KANJI_KOME','木':'KANJI_KI','耳':'KANJI_MIMI','口':'KANJI_KUCHI',
     '貝':'KANJI_KAI','金':'KANJI_KIN','川':'KANJI_KAWA','水':'KANJI_MIZU','糸':'KANJI_ITO'}

def write_asset(kid,names):
    """List the segments in the kanji's asset: AssemblyPlan only counts a kanji
    as authored (segments_authored) when its asset lists them."""
    path=REPO/'unity-client'/'Assets'/'Resources'/'kanji'/f'{kid}.asset'
    text=path.read_text(encoding='utf-8')
    block='  assemblySegments:\n'+''.join(
        f'  - segmentId: {kid}_SEG{i+1}\n    description: {n}\n'
        f'    slotPosition: {{x: 0, y: 0, z: 0}}\n    segmentAsset: {{fileID: 0}}\n' for i,n in enumerate(names))
    new,count=re.subn(r'  assemblySegments:.*?\n(?=  targetReadingAudio:)',lambda _:block,text,flags=re.S)
    if count!=1: raise SystemExit(f'{path.name}: assemblySegments not found')
    path.write_text(new,encoding='utf-8',newline='\n')

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
        write_asset(kid,[n for n,_ in G[ch]])
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
