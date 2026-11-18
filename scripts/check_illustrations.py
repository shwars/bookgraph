"""Audit the completed artwork set and make day/evening contact sheets for review."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from illustration_catalog import ROOT,CAST,PRIMARY,MOODS

def main():
    m=json.loads((ROOT/'work/illustrations/manifest.json').read_text(encoding='utf-8'))
    assets=m['assets'];errors=[];records=[]
    for a in assets:
        path=ROOT/a['target']
        if not path.exists():errors.append('Missing: '+a['target']);continue
        im=Image.open(path)
        if min(im.size)<400:errors.append('Too small: '+a['target'])
        if a['transparent']:
            if im.mode!='RGBA':errors.append('Not RGBA: '+a['target'])
            else:
                alpha=im.getchannel('A')
                if alpha.getextrema()[0]!=0:errors.append('No transparency: '+a['target'])
                if '.front_' in a['target']:
                    borders=[alpha.crop((0,0,im.width,1)),alpha.crop((0,im.height-1,im.width,im.height)),alpha.crop((0,0,1,im.height)),alpha.crop((im.width-1,0,im.width,im.height))]
                    if any(b.getextrema()[1]!=0 for b in borders):errors.append('Canvas border residue: '+a['target'])
                if not alpha.getbbox():errors.append('Empty sprite: '+a['target'])
        if a['kind'] in ['day','evening'] and im.width*9!=im.height*16:errors.append('Not 16:9: '+a['target'])
        records.append(dict(path=a['target'],width=im.width,height=im.height,mode=im.mode))
    assert len(assets)==130
    for ident,*_ in CAST:
        present={a['kind'] for a in assets if a['entity']==ident}
        expected={'charsheet'}|{k+'_'+m for k in ['front','face'] for m in (MOODS if ident in PRIMARY else ['neutral'])}
        if present!=expected:errors.append('Wrong mood scope: '+ident)
        card=ROOT/'wiki/protagonists'/f'{ident}.bespridannica.md'
        text=card.read_text(encoding='utf-8')
        for a in assets:
            if a['entity']==ident and (ROOT/a['target']).exists() and a['target'] not in text:errors.append('Unlinked: '+a['target'])
    place_names=list(dict.fromkeys(a['entity'] for a in assets if a['kind']=='day'))
    assert len(place_names)==17
    for name in place_names:
        pair=[a for a in assets if a['entity']==name]
        if len(pair)!=2:errors.append('Wrong place pair: '+name)
        if all((ROOT/a['target']).exists() for a in pair):
            if Image.open(ROOT/pair[0]['target']).size!=Image.open(ROOT/pair[1]['target']).size:errors.append('Different pair dimensions: '+name)
            card=next(p for p in (ROOT/'wiki/places').glob('*.md') if p.name.startswith(name+'.'))
            text=card.read_text(encoding='utf-8')
            for a in pair:
                if a['target'] not in text:errors.append('Unlinked: '+a['target'])
    qa=ROOT/'work/illustrations/qa';qa.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',25)
    # Review every final sprite, including the secondary cast, against a dark surface.
    for index,(name,*_) in enumerate(CAST,1):
        moods=MOODS if name in PRIMARY else ['neutral']
        out=Image.new('RGB',(len(moods)*320,810),'#344957');draw=ImageDraw.Draw(out)
        draw.text((12,8),name,fill='white',font=font)
        for column,mood in enumerate(moods):
            draw.text((column*320+12,48),mood,fill='white',font=font)
            for kind,top,height in [('front',95,440),('face',555,240)]:
                a=next(a for a in assets if a['entity']==name and a['kind']==kind+'_'+mood)
                im=Image.open(ROOT/a['target']).convert('RGBA')
                im=im.crop(im.getchannel('A').getbbox());im.thumbnail((295,height))
                out.paste(im,(column*320+(320-im.width)//2,top),im)
        out.save(qa/f'characters-{index:02d}.jpg',quality=92)
    for page in range((len(place_names)+3)//4):
        group=place_names[page*4:(page+1)*4]
        out=Image.new('RGB',(1600,len(group)*490),'#e9e4da');draw=ImageDraw.Draw(out)
        for row,name in enumerate(group):
            for col,kind in enumerate(['day','evening']):
                a=next(a for a in assets if a['entity']==name and a['kind']==kind)
                draw.text((col*800+20,row*490+5),name+' — '+('день' if col==0 else 'вечер'),fill='#2f3339',font=font)
                if (ROOT/a['target']).exists():
                    im=Image.open(ROOT/a['target']).convert('RGB');im.thumbnail((780,439));out.paste(im,(col*800+10,row*490+43))
        out.save(qa/f'places-{page+1:02d}.jpg',quality=90)
    report=dict(expected=130,ready=len(records),characters=12,character_files=96,place_pairs=17,place_files=34,minimum_side=min((min(r['width'],r['height']) for r in records),default=0),errors=errors,files=records)
    (ROOT/'work/illustrations/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
