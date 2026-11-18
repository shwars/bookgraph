"""Catalog and receive illustration assets; generation uses built-in image_gen."""
import argparse
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
MOODS=['neutral','happy','sad','surprised','angry','disgusted']
PRIMARY={'Лариса Огудалова','Харита Огудалова','Паратов','Карандышев','Кнуров','Вожеватов'}
STYLE='Traditional finely painted watercolor book illustration, translucent pigment washes, subtle granulation and fine sepia pencil contours, precise expressive facial anatomy, restrained late-19th-century palette. Natural adult proportions, recognizable faces, no caricature, no anime, no 3D, no photographic collage. Consistent costume and identity throughout the collection.'
CAST=[
('Лариса Огудалова','Larisa Ogudalova','Larisa Guzeeva','young adult woman, oval face, large gray-blue eyes, dark eyebrows, dark center-parted braided updo; pale sage-blue full-length 1870s dress, white ruffled lace collar and cuffs, small pale flower at chest'),
('Карандышев','Yuly Karandyshev','Andrey Myagkov','slender awkward man in his thirties, recognizable gentle Myagkov face, receding curly light-brown hair, small round wire spectacles, short moustache; modest light beige three-piece 1870s suit, dark waistcoat and tie, black boots'),
('Паратов','Sergey Paratov','Nikita Mikhalkov','confident handsome broad-shouldered man in his thirties, recognizable young Mikhalkov face, receding light-brown hair, thick light moustache; immaculate ivory-white three-piece 1870s suit, waistcoat, white peaked cap, dark tie and polished black boots'),
('Харита Огудалова','Kharita Ogudalova','Alisa Freindlich','mature middle-aged widow visibly around 55, mother of an adult daughter, distinctly recognizable mature Alisa Freindlich face and striking eyes, visible fine forehead lines, eye wrinkles, nasolabial folds, mature jaw and neck, graying auburn-brown hair in elaborate high period updo; elegant boldly fashionable burgundy/plum full-length 1870s gown, fitted bodice, restrained lace, cameo brooch. She is resourceful, socially practiced and shrewd, NOT a young pretty woman, NOT Larisa with different clothes'),
('Кнуров','Moky Knurov','Alexey Petrenko','wealthy older stout man, recognizable broad Petrenko face, heavy brows, gray-brown beard and moustache; dark charcoal 1870s frock coat and waistcoat, watch chain, white shirt, dark tie, black boots'),
('Вожеватов','Vasily Vozhevatov','Viktor Proskurin','young slim businessman, recognizable young Proskurin face, narrow lively eyes and angular nose, tidy dark-brown period hair and small moustache; smart dark olive-gray European 1870s three-piece suit, bow tie, watch chain, black boots'),
('Робинзон','Arkady Schastlivtsev nicknamed Robinson','Georgy Burkov','middle-aged dishevelled provincial actor, recognizable Burkov face with fleshy cheeks, slightly drooping eyelids and shaggy brown hair; worn brown checked period suit under a travel cloak, battered soft high hat, frayed cuffs, black boots'),
('Гаврило','Gavrilo the cafe proprietor','Alexander Pyatkov','stout broad-faced cafe proprietor, recognizable young Pyatkov face and light-brown hair, modest moustache; 1870s white shirt, dark waistcoat, dark trousers, long off-white service apron, black shoes'),
('Иван','Ivan the cafe servant','Borislav Brondukov','small wiry adult servant, recognizable Brondukov face, pointed nose, expressive eyes, thin moustache and short dark hair; plain white high-collared shirt, dark service waistcoat, dark trousers and black shoes'),
('Илья','Ilya the Romani musician','Dmitry Buzylyov-Kretso','adult Romani musician, recognizable Buzylyov face, dark curly hair, expressive dark eyes and small dark moustache; dark 1870s caftan over deep red shirt, narrow sash and black boots; guitar can be held close without obscuring the face'),
('Евфросинья Потаповна','Efrosinya Potapovna','Tatyana Pankova','elderly practical aunt, recognizable Pankova face, small wrinkled features and gray hair under a modest dark kerchief; simple full-length dark-brown 1870s house dress with gray apron, worn black shoes'),
('Голос с улицы — зовущий Илью','Unnamed street caller summoning Ilya',None,'original artistic interpretation of an unnamed adult male street caller, medium build, chestnut hair and moustache, modest ochre 1870s shirt, dark waistcoat, brown trousers, black boots. His age, facial details and costume are artistic invention because the play gives only a voice; do not claim a verified movie actor for this figure')]
PLACES={
'Бряхимов':'Wide establishing view of a fictional 1870s Russian merchant town on the high Volga bank, inspired by old Kostroma seen in the film: white stucco merchant houses, pale ochre facades, pitched roofs, small church domes and wooden river piers. This is a fictional town interpretation, no exact historical reconstruction.',
'Бульвар Бряхимова':'Playable theatrical background on a high Volga-bank boulevard, wrought-iron low railing in the back, vast river and far forests beyond, leafy trees on the left, cafe entrance on the right, two small outdoor tables at the sides, empty central acting space.',
'Волга':'Wide Volga river landscape near an 1870s provincial merchant town, low mist, remote wooded shore and simple wooden piers near the lower edges, water and sky dominate, no readable ship names, open staging space.',
'Деревня Карандышева':'Imagined modest Russian country estate and village in the 1870s, small timber manor, birch grove, rough country lane, meadow and wooden fence; quiet unpretentious rural refuge, no claim that this imagined visit occurred.',
'Дом Огудаловых':'Playable interior of the Ogudalov drawing room, two doors with one centered in back and one on the left, tall window on right, respectable but slightly worn period furniture, upright piano with guitar nearby, pale floral wallpaper and restrained lace curtains. Empty central acting space.',
'Заболотье':'Imagined remote wooded Russian district of Zabolotye, dirt lane past modest wooden houses into deep forest, grassy clearing in front and birches, no identifiable real location, 1870s atmosphere.',
'Италия':'Imagined late-19th-century Italian landscape used as an evocative contrast to the Russian countryside: sun-washed stucco villa, cypress trees, distant warm hills, stone terrace with open foreground. No characters and no modern objects.',
'Кавказ':'Evocative late-19th-century Caucasus mountain-road landscape, rocky winding path, distant blue mountain ridges and sparse stone buildings. No wedding, crime or persons: the book gives only a mentioned destination, not an exact location.',
'Квартира Карандышева':'Playable modest pretentious 1870s study, inexpensive carpet hung over sofa with antique pistols and daggers displayed on it, mismatched ambitious furniture, three doors, cheap decorative objects, empty central acting floor. Mood of aspiration and awkward thrift.',
'Кофейная Гаврилы':'Playable provincial 1870s cafe interior adjoining a Volga boulevard, wooden counter, shelves of bottles and porcelain teapots, plain small tables set to edges, door and tall windows facing river, timber floor and empty central foreground.',
'Москва':'Evocative 1870s Moscow street with low merchant houses and distant old church domes, stone pavement, no modern vehicles, period gas lanterns and ample empty foreground. General historical artistic setting, no specific unverified address.',
'Нижний':'Evocative 1870s Nizhny fair riverside, merchant fair arcades, wooden piers and remote confluence landscape, no modern signage or vehicles, open foreground. A mentioned destination rather than an enacted book scene.',
'Остров Робинзона':'Small empty island in a wide Russian river, sandy shore, willow thicket, driftwood and distant wooded bank, usable clear foreground. No shipwreck or ocean: the play describes a river island, not a tropical Robinson Crusoe island.',
'Париж':'Evocative Paris in the 1870s, elegant boulevard, cream stone Haussmann facades and gas street lamps, leafy promenade and open foreground. Absolutely NO Eiffel Tower, automobiles or electric advertising; no specific fair buildings claimed.',
'Петербург':'Evocative 1870s Saint Petersburg embankment, broad Neva water, granite parapet and classical facades, old gas lamps, no modern vehicles or skyline additions, empty foreground.',
'Трактир Париж':'Playable interior of a modest provincial Russian 1870s tavern named Paris, simple wooden tables at sides, worn plaster, bar counter and samovar, gas lamps, empty central space. This is NOT the city of Paris. Do not paint readable lettering.',
'Щелыково':'Evocative 1870s Russian wooden country manor in a leafy park, pale timber facade, modest porch with columns, birches and garden path, open foreground. An artistic editorial setting for Ostrovsky writing, not a fictional scene with book characters.'}

def catalog():
    assets=[]
    sheet='D:/GIT/bookgraph/wiki/protagonists/images/Лариса Огудалова.bespridannica.charsheet.png'
    for ident,eng,actor,description in CAST:
        stem=ident+'.bespridannica'
        identity=f'{eng}, recognizably portrayed by {actor} at the time of the 1984 Soviet film A Cruel Romance (Жестокий романс).' if actor else eng+'. No verified film casting; this design is expressly an artistic interpretation.'
        identity+=' '+description+'. '
        folder='wiki/protagonists/images/'
        refs=[sheet] if ident!='Лариса Огудалова' else ['D:/GIT/bookgraph/work/illustrations/references/larisa-film.jpg']
        prompt=STYLE+' '+identity+' Create ONE opaque warm ivory watercolor-paper character design sheet, landscape. Three complete head-to-toe poses: front neutral, three-quarter conversational gesture, expressive sorrowful gesture; plus six distinct close-up head expressions: neutral, happy, sad, surprised, angry, disgusted. Consistent actor likeness and costume, no other people, no environmental scene. Keep shoes, hands and hats completely inside frame. Generous spacing, no overlap. Small emotion labels permitted. Input sheet, if supplied, is STYLE REFERENCE ONLY: do not copy its female subject, use the actor and costume specified here.'
        if ident not in PRIMARY:
            prompt=prompt.replace('Three complete head-to-toe poses: front neutral, three-quarter conversational gesture, expressive sorrowful gesture; plus six distinct close-up head expressions: neutral, happy, sad, surprised, angry, disgusted.','Three complete head-to-toe neutral poses: front, three-quarter and side; plus one large neutral head portrait. ONLY neutral expression, no emotional variants.').replace('Small emotion labels permitted.','No text or labels.')
        assets.append(dict(id=f'c{len(assets):03d}',entity=ident,kind='charsheet',target=folder+stem+'.charsheet.png',prompt=prompt,transparent=False,refs=refs))
        for kind in ['front','face']:
            for mood in MOODS:
                expression={'neutral':'calm neutral resting expression, relaxed attentive gaze','happy':'warm genuinely happy smile, soft bright eyes','sad':'restrained sadness, downturned mouth and moist eyes, no melodramatic distortion','surprised':'clear surprise, raised eyebrows and slightly parted lips','angry':'controlled anger, brows lowered and firm mouth, dignified','disgusted':'distinct restrained disgust, slight nose wrinkle and averted mouth'}[mood]
                composition='Exactly ONE complete FRONT-FACING FULL-LENGTH ADULT FIGURE, entire head, hat if worn, hands, feet and shoes visible with 8 percent clear margins. Same standing height and costume silhouette as identity sheet; natural readable gesture matching emotion. No extra portrait, no second figure, no props except specified clothing or Ilya guitar. Portrait composition.' if kind=='front' else 'Exactly ONE large front-facing CLOSE-UP HEAD AND NECK portrait, shoulders included lightly, complete hair and hat if any inside frame, expressive face centered. No whole body, no second face, no panel or collage. Square composition.'
                prompt=STYLE+' '+identity+composition+' Emotion: '+expression+'. Reference character sheet is the exact identity/costume/style anchor; preserve this same person. TRUE TRANSPARENT BACKGROUND, actual alpha channel. Watercolor texture only within the painted subject, clean softly painted cutout edges. No paper rectangle, no white/gray backdrop, no checkerboard, no floor, no cast shadow, no border, no text, no labels, no watermark.'
                assets.append(dict(id=f'c{len(assets):03d}',entity=ident,kind=kind+'_'+mood,target=folder+stem+'.'+kind+'_'+mood+'.png',prompt=prompt,transparent=True,refs=['D:/GIT/bookgraph/'+folder+stem+'.charsheet.png']))
    graph=json.loads((ROOT/'wiki/graph.json').read_text(encoding='utf-8'))
    for ident,description in PLACES.items():
        node=next(n for n in graph['nodes'] if n['type']=='place' and n['entity_id']==ident)
        stem=Path(node['path']).stem
        for time in ['day','evening']:
            target='wiki/places/images/'+stem+'.'+time+'.png'
            prompt=STYLE+' Create ONE WIDE 16:9 landscape watercolor theatre background, no border, full bleed, no people or human silhouettes, no text, no labels, no modern objects. '+description+' Fixed eye-level perspective and carefully readable geometry, suitable for overlaying puppet characters. '+('DAY version: soft clear summer daylight, subtle warm shadows, quiet natural colors. Establish a fixed layout for a matching evening version.' if time=='day' else 'EVENING version of the supplied DAY background: preserve the EXACT same camera, architecture, furniture, landscape, object positions and framing. Change ONLY lighting to gentle twilight, blue-violet shadows and warm light in the existing windows and lanterns. Do not add or remove architecture, people or objects.')
            refs=[sheet] if time=='day' else ['D:/GIT/bookgraph/wiki/places/images/'+stem+'.day.png']
            assets.append(dict(id=f'p{len(assets):03d}',entity=ident,kind=time,target=target,prompt=prompt,transparent=False,refs=refs))
    return [a for a in assets if a['entity'] in PRIMARY or a['kind'] in ['charsheet','front_neutral','face_neutral','day','evening']]

def main():
    p=argparse.ArgumentParser();p.add_argument('--init',action='store_true');p.add_argument('--receive',nargs=2,metavar=('ASSET_ID','GENERATED_FILE'));args=p.parse_args()
    manifest=ROOT/'work/illustrations/manifest.json'
    if args.init:
        assets=catalog()
        manifest.write_text(json.dumps({'style':'Акварель; внешность актёров Жестокого романса (1984); художественное оформление отдельно от канона','characters':len(CAST),'places':len(PLACES),'assets':assets},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for a in assets: (ROOT/'work/illustrations/prompts'/f'{a["id"]}.txt').write_text(a['prompt'],encoding='utf-8')
        print('Cataloged',len(assets),'assets')
    if args.receive:
        ident,source=args.receive
        a=next(a for a in json.loads(manifest.read_text(encoding='utf-8'))['assets'] if a['id']==ident)
        dest=ROOT/a['target'];dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists(): shutil.copyfile(source,dest)
        (ROOT/'work/illustrations/receipts').mkdir(exist_ok=True)
        (ROOT/'work/illustrations/receipts'/f'{ident}.json').write_text(json.dumps({'id':ident,'entity':a['entity'],'target':a['target'],'generated_source':source,'mode':'built-in image_gen'},ensure_ascii=False,indent=2),encoding='utf-8')
        print(ident, a['target'])

if __name__=='__main__':main()
