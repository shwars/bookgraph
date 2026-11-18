"""Check this vault through the installed wikibook API; no extraction or LLM calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, default=Path.home()/'.codex/skills/wikibook')
    parser.add_argument('--rebuild-check', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.skill/'scripts'))
    import wiki
    wiki.configure(ROOT)
    provenance = json.loads((ROOT/'source/provenance.json').read_text(encoding='utf-8'))
    archive = ROOT/provenance['archive']
    fb2 = ROOT/provenance['fb2']
    assert digest(archive.read_bytes()) == provenance['archive_sha256'], 'Archive changed'
    assert digest(fb2.read_bytes()) == provenance['fb2_sha256'], 'FB2 changed'
    with zipfile.ZipFile(archive) as z:
        assert z.read(provenance['archive_member']) == fb2.read_bytes(), 'Extraction differs'
    manifest = wiki.load_manifest('bespridannica')
    # Reparse the immutable FB2 to verify the prepared contract independently.
    from fb2_sources import combine
    from fix_note_display import PATTERN
    fresh = combine([fb2], 'bespridannica', title='Бесприданница', series_order=1)
    for key in ('source_atomic_count','source_atomic_sha256','structural_title_atoms','notes'):
        assert manifest[key] == fresh[key], f'Source content differs: {key}'
    assert len(fresh['units']) == len(manifest['units'])
    for prepared, original in zip(manifest['units'],fresh['units']):
        expected = json.loads(json.dumps(original,ensure_ascii=False))
        for block in expected['blocks']:
            block['markdown'] = PATTERN.sub(r'[[\1]]',block['markdown'])
        assert prepared == expected, f'Prepared text or address differs: {prepared["id"]}'
    progress = json.loads((ROOT/'source/bespridannica/progress.json').read_text(encoding='utf-8'))
    notes = json.loads((ROOT/'source/bespridannica/notes-progress.json').read_text(encoding='utf-8'))['notes']
    classification = json.loads((ROOT/'source/bespridannica/classification.json').read_text(encoding='utf-8'))
    assert len(manifest['units']) == len(progress['units']) == 50
    assert Counter(x['classification'] for x in classification['units']) == dict(canon=44,cast=4,framing=1,editorial=1)
    assert {x['unit_id'] for x in classification['units']} == set(progress['units'])
    assert len(manifest['notes']) == len(notes) == 11
    for uid, row in list(progress['units'].items()) + list(notes.items()):
        assert all(row[k] for k in ('read','extracted','audited')), uid
        assert row['audit_date'] and row['audit_method'] and row['audit_summary'], uid
    errors, warnings, cards = wiki.validate()
    assert not errors, '\n'.join(errors)
    def authored():
        return {c['metadata']['entity_id']: re.sub(re.escape(wiki.GENERATED_START)+r'.*?'+re.escape(wiki.GENERATED_END),'',c['body'],flags=re.S) for c in wiki.cards()}
    def files():
        return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in (ROOT/'wiki').rglob('*') if p.is_file() and p.name != 'verification.bespridannica.md'}
    stable = None
    if args.rebuild_check:
        before = authored()
        wiki.build()
        assert authored() == before, 'First build changed authored content'
        first = files()
        wiki.build()
        assert authored() == before, 'Second build changed authored content'
        assert files() == first, 'Build is not byte-stable'
        stable = True
    errors, warnings, cards = wiki.validate()
    assert not errors, '\n'.join(errors)
    # Check links in navigation and reports too; core validation covers entity cards.
    pages = [ROOT/'README.md'] + list((ROOT/'wiki').rglob('*.md')) + list((ROOT/'source').rglob('*.md'))
    broken = []
    link_count = 0
    for page in pages:
        raw = page.read_text(encoding='utf-8')
        targets = [(s.split('|',1)[0], ROOT, True) for s in wiki.LINK_RE.findall(raw)]
        targets += [(m.group(1).strip('<>'),page.parent,False) for m in re.finditer(r'!?\[[^\]\n]*\]\(([^)\n]+)\)',raw)]
        for target, base, obsidian in targets:
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://',target):
                continue
            filename, _, anchor = unquote(target).partition('#')
            path = base/filename if filename else page
            if obsidian and not path.is_file():
                path = Path(str(path)+'.md')
            link_count += 1
            if not path.is_file():
                broken.append(f'{page.relative_to(ROOT)}: {target}')
            elif anchor.startswith('^') and not re.search(r'(?m)^\^'+re.escape(anchor[1:])+r'\s*$',path.read_text(encoding='utf-8')):
                broken.append(f'Missing block: {target}')
            elif anchor and not anchor.startswith('^') and path.suffix=='.md':
                headings=re.findall(r'(?m)^#{1,6}\s+(.+?)\s*$',path.read_text(encoding='utf-8'))
                slugs={re.sub(r'[^\w\s-]','',h.lower()).replace(' ','-') for h in headings}
                if anchor not in slugs and anchor not in headings:
                    broken.append(f'Missing heading: {target}')
    assert not broken, '\n'.join(broken)
    graph = json.loads((ROOT/'wiki/graph.json').read_text(encoding='utf-8'))
    facts = [f for c in cards for f in c['facts']]
    assert graph['facts'] == facts, 'Export facts differ from Markdown'
    assert {n['entity_id'] for n in graph['nodes']} == {c['metadata']['entity_id'] for c in cards}
    assert graph['edges'] == [f for f in facts if f.get('object')]
    expected_occurrences=[dict(event_id=c['metadata']['entity_id'],**o) for c in cards for o in c['occurrences']]
    assert graph['occurrences'] == expected_occurrences
    ids = {c['metadata']['entity_id'] for c in cards}
    assert 'Робинзон' in ids and 'Аркадий Счастливцев' not in ids
    for c in cards:
        if c['metadata']['first_source']=='hist' and c['metadata']['type']=='character':
            assert all(f['scope']!='canon' for f in c['facts']), c['metadata']['entity_id']
    counts = Counter(c['metadata']['type'] for c in cards)
    result = dict(cards=len(cards),types=dict(counts),facts=len(facts),edges=len(graph['edges']),occurrences=len(graph['occurrences']),units=50,notes=11,source_atoms=manifest['source_atomic_count'],checked_links=link_count,errors=errors,warnings=warnings,byte_stable=stable)
    if args.write_report:
        stability = 'Две последовательные сборки дали побайтово одинаковые файлы; ручной текст и факты сохранены.' if stable else 'В этом запуске повторяемость сборки не проверялась.'
        report = ['# Техническая проверка Бесприданницы','','Дата проверки: 13 ноября 2026.','','| Проверка | Результат |','|---|---|',f'| Единицы: чтение / извлечение / отдельный аудит | 50 / 50 / 50 |', '| Примечания: чтение / извлечение / отдельный аудит | 11 / 11 / 11 |',f'| Сохранённые атомы основного body | {manifest["source_atomic_count"]} |',f'| Карточки / факты / рёбра / появления | {len(cards)} / {len(facts)} / {len(graph["edges"])} / {len(graph["occurrences"])} |', f'| Проверенные локальные ссылки | {link_count} |','| Ошибки / предупреждения встроенного валидатора | 0 / '+str(len(warnings))+' |','| ZIP и FB2 | SHA-256 совпадают с реестром; FB2 побайтово равен члену ZIP |','| Markdown и экспорт | Сущности, факты, рёбра и появления совпадают |','','## Повторная сборка','',stability,'','## Типы карточек','']
        report += [f'- {k}: {v}.' for k,v in sorted(counts.items())]
        report += ['','Источник независимо повторно разобран FB2-парсером: атомы, заголовки, примечания, порядок и адреса совпадают; отличие Markdown ограничено документированной коррекцией 11 ссылок на примечания. Проверены ID, ссылки и блоки источника, стадии покрытия, отсутствие циклов before/causes, навигационные Markdown-ссылки и заголовки. Смысловые неопределённости находятся в [[wiki/audit.bespridannica|отдельном аудите]]. Встроенный валидатор не доказывает абсолютную смысловую полноту.','', 'Повторить: `python scripts/check_vault.py --rebuild-check --write-report`.']
        wiki.write_text(ROOT/'wiki/verification.bespridannica.md','\n'.join(report))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
