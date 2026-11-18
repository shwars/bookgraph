"""Link existing generated artwork into manual card sections and write a gallery."""
import json,re,sys
from pathlib import Path
from PIL import Image
from illustration_catalog import ROOT,CAST,PRIMARY,MOODS
sys.path.insert(0,str(Path.home()/'.codex/skills/wikibook/scripts'))
import wiki
wiki.configure(ROOT)

START='<!-- illustrations:start -->'
END='<!-- illustrations:end -->'
ACTORS_RU=dict(zip([c[2] for c in CAST],['Лариса Гузеева','Андрей Мягков','Никита Михалков','Алиса Фрейндлих','Алексей Петренко','Виктор Проскурин','Георгий Бурков','Александр Пятков','Борислав Брондуков','Дмитрий Бузылёв-Крэцо','Татьяна Панкова','']))
MOODS_RU=dict(zip(MOODS,['Нейтральное','Радость','Печаль','Удивление','Гнев','Отвращение']))

def link(path,label):return f'[[{path}|{label}]]'
def embed(path,width=600):return f'![[{path}|{width}]]'

def main():
    manifest=json.loads((ROOT/'work/illustrations/manifest.json').read_text(encoding='utf-8'))
    assets=manifest['assets'];ready=[];errors=[]
    for a in assets:
        p=ROOT/a['target']
        if not p.exists():continue
        im=Image.open(p)
        if min(im.size)<400:errors.append(f'Too small: {a["target"]}')
        if a['transparent'] and (im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0):errors.append(f'Missing alpha: {a["target"]}')
        if a['kind'] in ['day','evening'] and im.width*9!=im.height*16:errors.append(f'Not 16:9: {a["target"]}')
        ready.append(a)
    assert not errors,'\n'.join(errors)
    cards={c['metadata']['entity_id']:c for c in wiki.cards()}
    cast={c[0]:c for c in CAST}
    gallery=['# Акварельные иллюстрации Бесприданницы','',f'Готово {len(ready)} из {len(assets)} ожидаемых PNG. Акварельные интерпретации внешности актёров «Жестокого романса» (1984), с учётом книжных ролей и возраста. Художественные изображения не являются новыми доказательствами канона.','', '## Персонажи','']
    for entity in dict.fromkeys(a['entity'] for a in assets):
        found={a['kind']:a for a in ready if a['entity']==entity}
        if not found:continue
        card=cards[entity]
        body=[START,'## Иллюстрации — художественная интерпретация','']
        if entity in cast:
            actor=ACTORS_RU[cast[entity][2]]
            body+=['Акварельный образ по фильму «Жестокий романс» (1984). Визуальный ориентир: '+actor+'. Возраст, социальное положение и характер соотнесены с описанием в wiki. Костюм и отдельные детали — художественная интерпретация.' if actor else 'Придуманный визуальный образ безымянного голоса с улицы. Возраст и внешность в пьесе не описаны; соответствие конкретному актёру фильма не установлено.','']
            if 'charsheet' in found:body += [embed(found['charsheet']['target'],720),'',link(found['charsheet']['target'],'Лист персонажа в полном разрешении'), '']
            if 'front_neutral' in found:body += [embed(found['front_neutral']['target'],300),'']
            body+=['| Настроение | Ростовая фигурка, PNG с альфа-каналом | Лицо, PNG с альфа-каналом |','|---|---|---|']
            for mood in MOODS if entity in PRIMARY else ['neutral']:
                f=found.get('front_'+mood);p=found.get('face_'+mood)
                if f or p:body.append(f'| {MOODS_RU[mood]} | '+(link(f['target'],'Открыть') if f else 'Ещё не готово')+' | '+(link(p['target'],'Открыть') if p else 'Ещё не готово')+' |')
            gallery+=[f'### {entity}','',wiki.link(card),'']
            if 'charsheet' in found:gallery += [embed(found['charsheet']['target'],640),'']
        else:
            body+=['Художественный сценический фон. Для мест, лишь упомянутых в пьесе или редакционном аппарате, это воображаемая обстановка, без утверждения о точной исторической реконструкции или состоявшемся посещении героями.','']
            for kind,label in [('day','День'),('evening','Вечер')]:
                if kind in found:body += [f'### {label}', '',embed(found[kind]['target'],720),'']
        body += [END,'']
        section='\n'.join(body)
        raw=card['path'].read_text(encoding='utf-8')
        if START in raw:raw=re.sub(re.escape(START)+r'.*?'+re.escape(END)+'\n*',lambda _:section+'\n',raw,flags=re.S)
        else:raw=raw.replace(wiki.GENERATED_START,section+'\n'+wiki.GENERATED_START,1)
        wiki.write_text(card['path'],raw)
    gallery+=['## Места','']
    for entity in dict.fromkeys(a['entity'] for a in assets if a['kind'] in ['day','evening']):
        found=[a for a in ready if a['entity']==entity]
        if found:
            gallery += [f'### {entity}','',wiki.link(cards[entity]),'']
            for a in found:gallery += ['День' if a['kind']=='day' else 'Вечер', '', embed(a['target'],720),'']
    gallery += ['## Визуальные референсы','', '[Фильм и актёрский состав — Мосфильм](https://www.mosfilm.ru/cinema/films/zhestokiy-romans/). [Соответствие актёров и ролей](https://wink.ru/movies/zhestokiy-romans-year-1984/cast). Дополнительные малые роли сверены по [Кинопоиску](https://www.kinopoisk.ru/film/45314/cast/). [Референс Ларисы](https://aif.ru/culture/gallery/yarkie_roli_larisy_guzeevoy); [референс Хариты Игнатьевны](https://aif.ru/culture/book/mat-bespridannicy-iz-pesy-ostrovskogo-cyganka-chto-skryval-dramaturg). Страницы служат источниками оформления и атрибуции ролей, не историческими источниками литературного канона.','', 'Производственные реестры: [[work/illustrations/manifest.json|ожидаемые изображения]] и [[work/illustrations/jobs.json|промпты атласов и фонов]].']
    wiki.write_text(ROOT/'wiki/illustrations.bespridannica.md','\n'.join(gallery))
    (ROOT/'work/illustrations/status.json').write_text(json.dumps(dict(expected=len(assets),ready=len(ready),missing=[a['target'] for a in assets if not (ROOT/a['target']).exists()],checks=errors),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Linked',len(ready),'/',len(assets),'illustrations; size/alpha/aspect checks pass')

if __name__=='__main__':main()
