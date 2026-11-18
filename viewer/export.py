"""Build the offline viewer from Markdown through the installed wikibook engine."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

BOOK = 'bespridannica'
WIKILINK = re.compile(r'!?\[\[([^\]\n]+)\]\]')
FRONT = re.compile(r'\A---\n.*?\n---\n', re.S)
FACTS = re.compile(r'(?ms)^## Структурированные факты\s*\n+~~~yaml\n.*?\n~~~\s*$')


def strip_frontmatter(text):
    return FRONT.sub('', text)


def summary(card):
    # Use authored prose, excluding artwork and the generated navigation.
    body = re.sub(r'<!-- illustrations:start -->.*?<!-- illustrations:end -->', '', card['body'], flags=re.S)
    body = body.split('<!-- wiki:generated:start -->')[0]
    paragraphs = re.split(r'\n\s*\n', body)
    for paragraph in paragraphs:
        if paragraph.strip() and not paragraph.lstrip().startswith(('#', '[[', '!', '<!--', '|', '~~~')):
            return paragraph.strip()
    return next((str(f['value']) for f in card['facts'] if f['predicate'] == 'description' and 'value' in f), 'Описание пока отсутствует.')


def dependency(fact):
    """Project requires without changing the canonical statement or its ID."""
    return dict(id=fact['fact_id'], source=fact['object'] if fact['predicate'] == 'requires' else fact['subject'],
                target=fact['subject'] if fact['predicate'] == 'requires' else fact['object'],
                kind=fact['predicate'], fact_ids=[fact['fact_id']], scope=fact['scope'],
                truth_status=fact['truth_status'], label={'causes':'причина', 'requires':'условие',
                'prevents':'препятствие', 'before':'раньше'}[fact['predicate']])


def export(root, skill, rebuild=True):
    root, skill = Path(root).resolve(), Path(skill).resolve()
    sys.path.insert(0, str(skill/'scripts'))
    wiki = importlib.import_module('wiki')
    wiki.configure(root)
    errors, warnings, cards = wiki.validate()
    if errors:
        raise ValueError('\n'.join(errors))
    if rebuild:
        authored = {c['metadata']['entity_id']: re.sub(r'<!-- wiki:generated:start -->.*?<!-- wiki:generated:end -->', '', c['body'], flags=re.S) for c in cards}
        wiki.build()
        errors, warnings, cards = wiki.validate()
        if errors:
            raise ValueError('\n'.join(errors))
        for c in cards:
            if re.sub(r'<!-- wiki:generated:start -->.*?<!-- wiki:generated:end -->', '', c['body'], flags=re.S) != authored[c['metadata']['entity_id']]:
                raise ValueError('Build modified authored text: '+str(c['path']))
    facts = {f['fact_id']: f for c in cards for f in c['facts']}
    by_id = {c['metadata']['entity_id']: c for c in cards}
    pages, addresses, nodes = {}, {}, []
    inputs = []
    for base in ('wiki', 'source'):
        inputs.extend((root/base).rglob('*.md'))
    for path in sorted(inputs):
        rel = path.relative_to(root).as_posix()
        body = strip_frontmatter(path.read_text(encoding='utf-8'))
        key = rel[:-3]
        pages[key] = {'title': next((line[2:] for line in body.splitlines() if line.startswith('# ')), path.stem), 'body': FACTS.sub('', body).strip(), 'path':rel}
        for anchor in re.findall(r'(?m)^\^([\w-]+)\s*$', body):
            addresses[key+'#^'+anchor] = {'page': key, 'block': anchor}
    classified = json.loads((root/f'source/{BOOK}/classification.json').read_text(encoding='utf-8'))
    labels = {u['unit_id']:u for u in classified['units']}
    manifest = wiki.load_manifest(BOOK)
    units = []
    for unit in manifest['units']:
        units.append({'id':unit['id'], 'title':labels[unit['id']]['label'], 'source_title':unit['title'], 'classification':labels[unit['id']]['classification'],
                      'page':unit['path'][:-3], 'blocks':[{'id':b['id'], 'text':b['text'], 'markdown':b['markdown']} for b in unit['blocks']]})
    notes = manifest['notes']
    for n in notes:
        addresses[f'source/{BOOK}/notes#^{n["id"]}'] = {'page':f'source/{BOOK}/notes', 'block':n['id']}
    for c in cards:
        meta = dict(c['metadata'])
        eid, v = meta['entity_id'], meta.get('viewer', {})
        if v.get('layer') not in {'story','mentioned','literary','editorial'}:
            raise ValueError('Missing viewer.layer: '+eid)
        if meta['type']=='character':
            if v.get('gender') not in {'male','female','unknown'} or v.get('importance') not in {'main','secondary','episodic'}:
                raise ValueError('Missing gender/importance: '+eid)
            if v['gender']!='unknown' and not v.get('gender_sources'):
                raise ValueError('Gender without evidence: '+eid)
        if meta['type']=='event':
            if v.get('time_group') not in {'main','prehistory','unknown','editorial'}:
                raise ValueError('Missing timeline group: '+eid)
            if v['time_group']=='main' and not isinstance(v.get('time_rank'),(int,float)):
                raise ValueError('Missing relative rank: '+eid)
        rel = c['path'].relative_to(root).as_posix()
        stem = c['path'].stem
        face = root/'wiki/protagonists/images'/f'{stem}.face_neutral.png'
        art = root/'wiki/protagonists/images'/f'{stem}.charsheet.png'
        own = c['facts']
        refs = list(dict.fromkeys(s for f in own for s in f['sources']))
        participants = list(dict.fromkeys(f['object'] for f in own if f['predicate']=='participates'))
        places = list(dict.fromkeys(f['object'] for f in own if f['predicate']=='located_at'))
        # Preserve all places, preferring the most specific named stage location for a single lane.
        place_priority={'Кофейная Гаврилы':0,'Дом Огудаловых':0,'Квартира Карандышева':0,'Бульвар Бряхимова':1,'Волга':2,'Бряхимов':3}
        places.sort(key=lambda p:place_priority.get(p,1))
        nodes.append({**meta, 'id':eid, 'path':rel, 'page':rel[:-3], 'summary':summary(c), 'body':pages[rel[:-3]]['body'],
                      'fact_ids':[f['fact_id'] for f in own], 'sources':refs, 'participants':participants, 'places':places,
                      'occurrences':c['occurrences'], 'portrait':face.relative_to(root).as_posix() if face.exists() else None,
                      'art':art.relative_to(root).as_posix() if art.exists() else None})
    relations = {}
    dependencies = []
    for f in facts.values():
        target = f.get('object')
        if not target or target not in by_id:
            continue
        src_type = by_id[f['subject']]['metadata']['type']
        dst_type = by_id[target]['metadata']['type']
        if f['predicate']=='related_to' and src_type==dst_type=='character':
            if not f.get('label') or not f.get('relation_type'):
                raise ValueError('Unlabelled relationship: '+f['fact_id'])
            # Different accounts share a line; contradictory truth states remain visible as separate lines.
            status_group=f['truth_status'] if f['truth_status'] in {'disputed','refuted','unknown'} else 'affirmed'
            key=(f['subject'],target,f['relation_type'],f['label'],f['scope'],status_group)
            if key not in relations:
                relations[key]={'id':f['fact_id'],'source':f['subject'],'target':target,'kind':f['relation_type'],
                                'label':f['label'],'scope':f['scope'],'truth_status':f['truth_status'],'fact_ids':[]}
            relations[key]['fact_ids'].append(f['fact_id'])
            if f['truth_status']=='confirmed': relations[key]['truth_status']='confirmed'
        elif src_type==dst_type=='event' and f['predicate'] in {'causes','requires','prevents','before'}:
            dependencies.append(dependency(f))
    # The compiled graph must have exactly the facts just read from canonical Markdown.
    graph=json.loads((root/'wiki/graph.json').read_text(encoding='utf-8'))
    if {f['fact_id']:f for f in graph['facts']} != facts:
        raise ValueError('graph.json is stale; rebuild the wiki first')
    known_paths={str(p.relative_to(root).as_posix()):p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '.work' not in p.parts}
    aliases={}
    for n in nodes:
        aliases[n['id']]=n['page']
        for name in n.get('aliases',[]): aliases.setdefault(name,n['page'])
    def validate_link(raw, owner):
        target=unquote(raw.split('|',1)[0])
        if re.match(r'https?://',target): return
        path,_,anchor=target.partition('#')
        path=aliases.get(path,path).removesuffix('.md') if path else owner
        if path in pages:
            if anchor.startswith('^') and path+'#'+anchor not in addresses:
                raise ValueError('Unknown block: '+target+' in '+owner)
            return
        if path in known_paths or path+'.md' in known_paths:return
        raise ValueError('Unresolved link: '+target+' in '+owner)
    for key,page in pages.items():
        for match in WIKILINK.finditer(page['body']):validate_link(match[1],key)
    for f in facts.values():
        for source in f['sources']:
            for match in WIKILINK.finditer(source): validate_link(match[1],by_id[f['subject']]['path'].relative_to(root).as_posix()[:-3])
    for n in nodes:
        for source in n['viewer'].get('gender_sources',[])+n['viewer'].get('time_sources',[]):
            for match in WIKILINK.finditer(source):validate_link(match[1],n['page'])
    digest=hashlib.sha256()
    for p in sorted(inputs):digest.update(p.relative_to(root).as_posix().encode());digest.update(p.read_bytes())
    return {'schema_version':1,'book_id':BOOK,'title':'Бесприданница','author':'А. Н. Островский',
            'exported_at':datetime.now(timezone(timedelta(hours=3))).isoformat(timespec='seconds'),
            'input_sha256':digest.hexdigest(),'nodes':nodes,'facts':facts,'relations':list(relations.values()),'dependencies':dependencies,
            'pages':pages,'addresses':addresses,'aliases':aliases,'units':units,'notes':notes,'warnings':warnings}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--skill',type=Path,default=Path.home()/'.codex/skills/wikibook')
    args=parser.parse_args()
    data=export(args.root,args.skill)
    out=args.root.resolve()/'viewer/data.js'
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    out.write_text('// Generated from Markdown. Run python viewer/export.py to update.\nwindow.BOOKGRAPH_DATA = '+payload+';\n',encoding='utf-8')
    print(f'Exported {len(data["nodes"])} entities, {len(data["relations"])} relationships, {len(data["dependencies"])} event edges; {out.stat().st_size:,} bytes')

if __name__=='__main__':main()
