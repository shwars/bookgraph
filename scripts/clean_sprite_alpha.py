"""Refine generated halo alpha; preserve RGB painting and native crop resolution."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from illustration_catalog import ROOT

def main():
    jobs=json.loads((ROOT/'work/illustrations/jobs.json').read_text(encoding='utf-8'))
    records=[]
    # Solid subject interiors cluster at alpha 252-255; generated glow is translucent.
    # Always start from archived original atlases so reruns are idempotent.
    lut=[0 if a<=235 else min(255,round((a-235)*255/18)) for a in range(256)]
    for job in jobs:
        if job['type'] not in ['grid6','grid2']:continue
        raw=ROOT/'work/illustrations/atlases'/f'{job["id"]}.png'
        if not raw.exists():continue
        im=Image.open(raw).convert('RGBA')
        cols,rows=(3,2) if job['type']=='grid6' else (2,1)
        w,h=im.size
        for i,target in enumerate(job['targets']):
            x,y=i%cols,i//cols
            cell=im.crop((round(x*w/cols),round(y*h/rows),round((x+1)*w/cols),round((y+1)*h/rows)))
            before=cell.getchannel('A');alpha=before.point(lut)
            # Remove only canvas-edge residue; figures have explicit safe margins.
            if '.front_' in target:
                draw=ImageDraw.Draw(alpha)
                draw.rectangle((0,0,cell.width-1,1),fill=0);draw.rectangle((0,cell.height-2,cell.width-1,cell.height-1),fill=0)
                draw.rectangle((0,0,1,cell.height-1),fill=0);draw.rectangle((cell.width-2,0,cell.width-1,cell.height-1),fill=0)
            detached_cleanup=None
            if '.front_' in target and job['entity'] in ['Гаврило','Евфросинья Потаповна']:
                # Visual review found a small fragment of the adjacent portrait
                # at the far right of these two atlas cells. Bound the connected
                # central figure, retaining a native-pixel margin for soft edges.
                binary=alpha.point(lambda a:255 if a else 0)
                y=cell.height//2
                candidates=[x for x in range(cell.width) if binary.getpixel((x,y))]
                seed=min(candidates,key=lambda x:abs(x-cell.width//2))
                ImageDraw.floodfill(binary,(seed,y),128)
                component=binary.point(lambda a:255 if a==128 else 0)
                left,top,right,bottom=component.getbbox()
                bounds=(max(0,left-8),max(0,top-8),min(cell.width,right+8),min(cell.height,bottom+8))
                confined=Image.new('L',cell.size,0);confined.paste(alpha.crop(bounds),bounds[:2]);alpha=confined
                detached_cleanup=dict(method='Remove detached neighboring-cell fragment outside central figure bounds plus 8px margin',bounds=list(bounds))
            assert min(cell.size)>=400 and alpha.getbbox() is not None
            cell.putalpha(alpha)
            dest=ROOT/target;dest.parent.mkdir(parents=True,exist_ok=True);cell.save(dest)
            records.append(dict(path=target,size=list(cell.size),original_alpha=list(before.getextrema()),final_alpha=list(alpha.getextrema()),opaque_pixels=alpha.histogram()[255],detached_cleanup=detached_cleanup))
    (ROOT/'work/illustrations/alpha-cleanup.json').write_text(json.dumps(dict(method='Alpha-only monotone remap 235..253 -> 0..255; RGB unchanged; no scaling. Generated atlas originals preserved.',files=records),ensure_ascii=False,indent=2),encoding='utf-8')
    # QA composite uses smaller previews only; final PNGs remain at native resolution.
    identities=['Лариса Огудалова','Харита Огудалова','Карандышев','Паратов','Кнуров','Вожеватов']
    canvas=Image.new('RGB',(1500,1000),'#344957');draw=ImageDraw.Draw(canvas)
    font_path=Path('C:/Windows/Fonts/segoeui.ttf')
    font=ImageFont.truetype(str(font_path),24) if font_path.exists() else ImageFont.load_default()
    for i,name in enumerate(identities):
        x=(i%3)*500;y=(i//3)*500
        for kind,box in [('front',(x+35,y+55,190,420)),('face',(x+245,y+85,235,340))]:
            p=ROOT/'wiki/protagonists/images'/f'{name}.bespridannica.{kind}_neutral.png'
            if p.exists():
                im=Image.open(p).convert('RGBA');im=im.crop(im.getchannel('A').getbbox());im.thumbnail((box[2],box[3]));canvas.paste(im,(box[0],box[1]),im)
        draw.text((x+15,y+10),name,fill='white',font=font)
    canvas.save(ROOT/'work/illustrations/alpha-qa.png')
    print('Cleaned',len(records),'sprites; RGB and resolution preserved')

if __name__=='__main__':main()
