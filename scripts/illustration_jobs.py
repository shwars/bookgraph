"""Prepare image_gen jobs and split approved atlases without upscaling."""
import argparse,json,shutil
from pathlib import Path
from PIL import Image
from illustration_catalog import ROOT,CAST,PRIMARY,MOODS,STYLE

def prepare():
    manifest=json.loads((ROOT/'work/illustrations/manifest.json').read_text(encoding='utf-8'))
    assets=manifest['assets']; jobs=[]
    for a in assets:
        if a['kind']=='charsheet':
            jobs.append(dict(id=a['id'],entity=a['entity'],type='copy',targets=[a['target']],prompt=a['prompt'],refs=a['refs'],transparent=False,deps=[]))
    for ident,eng,actor,desc in CAST:
        base=next(a for a in assets if a['entity']==ident and a['kind']=='charsheet')
        ref='D:/GIT/bookgraph/'+base['target']
        who=f'{eng}; {actor} as in A Cruel Romance (1984).' if actor else eng+'. Artistic interpretation of an unnamed book voice.'
        common=STYLE+' '+who+' '+desc+'. Use the reference sheet as the EXACT identity, age, face, costume and watercolor-style anchor. Preserve identity across every cell. '
        if ident in PRIMARY:
            for kind in ['front','face']:
                destinations=[next(a['target'] for a in assets if a['entity']==ident and a['kind']==kind+'_'+m) for m in MOODS]
                composition=('exactly ONE FRONT-FACING COMPLETE HEAD-TO-TOE standing adult figure with both hands, feet, shoes and hat fully visible and a clear 8 percent margin inside its cell. NO additional portrait or second figure within a cell' if kind=='front' else 'exactly ONE large front-facing HEAD AND SHOULDERS PORTRAIT, complete hair and hat inside its cell, face large and centered. NO whole body or second face')
                prompt=common+'Create ONE production SPRITE ATLAS, landscape canvas ideally 3072x2048, or at least 1536x1024. EXACTLY THREE EQUAL COLUMNS and TWO EQUAL ROWS, six invisible identical rectangular cells occupying the full canvas. DO NOT TRIM CANVAS. Each cell contains '+composition+'. Cells must NEVER overlap. Row-major emotion order is top-left NEUTRAL calm; top-middle HAPPY smiling; top-right SAD sorrowful; bottom-left SURPRISED; bottom-middle ANGRY controlled anger; bottom-right DISGUSTED restrained distaste. This is one and the same person six times, same age and costume. Every subject fully isolated in its own cell, no lines or dividers. Actual transparent alpha background across the WHOLE canvas and between cells; watercolor texture ONLY INSIDE the subject. Absolutely no cream paper, rectangular glow, halo, vignette, shadows, floor, checkerboard, text, emotion labels or decorative marks. Each figure at least 400 pixels tall, each cell at least 500 pixels wide. Natural mature expressions matching the character, no comic exaggeration.'
                jobs.append(dict(id=base['id']+'-'+kind,entity=ident,type='grid6',targets=destinations,prompt=prompt,refs=[ref],transparent=True,deps=[base['id']]))
        else:
            targets=[next(a['target'] for a in assets if a['entity']==ident and a['kind']==kind+'_neutral') for kind in ['front','face']]
            prompt=common+'Create ONE transparent sprite ATLAS in exactly TWO EQUAL COLUMNS, ONE ROW, landscape canvas at least 1536x1024. LEFT HALF: exactly one complete FRONT-FACING HEAD-TO-TOE neutral standing figure, all hair/hat, hands, feet and shoes inside the half with 8 percent margin. RIGHT HALF: exactly one large front-facing neutral HEAD AND SHOULDERS portrait of the same person. Keep the halves separate with generous transparent spacing and no overlap. Only neutral expression, no other moods. TRUE transparent alpha background everywhere outside subjects; no paper, no glow, no halo, no shadow, no labels, no lines, no checkerboard. Preserve the full canvas dimensions; DO NOT TRIM. Each half at least 600px wide and 800px high.'
            jobs.append(dict(id=base['id']+'-neutral',entity=ident,type='grid2',targets=targets,prompt=prompt,refs=[ref],transparent=True,deps=[base['id']]))
    for a in assets:
        if a['kind'] not in ['day','evening']:continue
        day=next(x for x in assets if x['entity']==a['entity'] and x['kind']=='day')
        prompt=a['prompt']+' Keep all essential staging details inside a centered 16:9 safe area. Output a landscape composition, ideally 1792x1008 or 1536x864; if canvas is 1536x1024 the central 1536x864 will be used without scaling.'
        jobs.append(dict(id=a['id'],entity=a['entity'],type='background',targets=[a['target']],prompt=prompt,refs=a['refs'],transparent=False,deps=[] if a['kind']=='day' else [day['id']]))
    (ROOT/'work/illustrations/jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
    for j in jobs:
        (ROOT/'work/illustrations/prompts'/f'{j["id"]}.txt').write_text(j['prompt'],encoding='utf-8')
    print('Prepared',len(jobs),'generation jobs for',len(assets),'final PNGs')

def receive(ident,source):
    jobs=json.loads((ROOT/'work/illustrations/jobs.json').read_text(encoding='utf-8'));j=next(j for j in jobs if j['id']==ident)
    src=Path(source); im=Image.open(src)
    raw=ROOT/'work/illustrations/atlases'/f'{ident}.png';raw.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,raw)
    results=[]
    if j['type']=='copy':
        target=ROOT/j['targets'][0];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target);results.append((j['targets'][0],im.size))
    elif j['type'] in ['grid6','grid2']:
        assert im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0,'Missing real alpha'
        cols,rows=(3,2) if j['type']=='grid6' else (2,1)
        w,h=im.size;assert w//cols>=400 and h//rows>=400, f'Insufficient native cell resolution: {im.size}'
        for i,target in enumerate(j['targets']):
            x,y=i%cols,i//cols
            cell=im.crop((round(x*w/cols),round(y*h/rows),round((x+1)*w/cols),round((y+1)*h/rows)))
            assert min(cell.size)>=400
            dest=ROOT/target;dest.parent.mkdir(parents=True,exist_ok=True);cell.save(dest);results.append((target,cell.size))
    else:
        w,h=im.size;tw=(min(w,h*16//9)//16)*16;th=tw*9//16
        assert tw>=400 and th>=400
        x=(w-tw)//2;y=(h-th)//2
        dest=ROOT/j['targets'][0];dest.parent.mkdir(parents=True,exist_ok=True);im.crop((x,y,x+tw,y+th)).convert('RGB').save(dest);results.append((j['targets'][0],(tw,th)))
    receipt=dict(id=ident,entity=j['entity'],generated_source=str(src),atlas=str(raw.relative_to(ROOT)),mode='built-in image_gen; Pillow crops authorized by user; no upscaling',files=[dict(path=p,width=s[0],height=s[1]) for p,s in results])
    (ROOT/'work/illustrations/receipts'/f'{ident}.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--receive',nargs=2);a=p.parse_args()
    if a.prepare:prepare()
    if a.receive:receive(*a.receive)
