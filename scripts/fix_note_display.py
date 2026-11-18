"""Repair the existing importer's triple-bracket note display, preserving text/IDs."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r'\[\[\[(source/bespridannica/notes#\^[^|\]]+\|[^\]]+)\]\]\]')

def main():
    path = ROOT/'source/bespridannica/manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    fixes = []
    for unit in manifest['units']:
        page = ROOT/unit['path']
        raw = page.read_text(encoding='utf-8')
        for block in unit['blocks']:
            old = block['markdown']
            new = PATTERN.sub(r'[[\1]]', old)
            if old != new:
                assert old in raw
                raw = raw.replace(old, new)
                block['markdown'] = new
                fixes.append(dict(unit_id=unit['id'],block_id=block['id'],old_markdown=old,new_markdown=new))
        if raw != page.read_text(encoding='utf-8'):
            page.write_text(raw,encoding='utf-8',newline='\n')
    if fixes:
        assert len(fixes)==11, 'Unexpected source note structure'
        path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        (path.parent/'display-normalization.json').write_text(json.dumps({'reason':'Исходные квадратные скобки вокруг ссылки создавали тройные скобки при импорте; исправлена только отображаемая Markdown-ссылка. Оригинал, text, atom_index, ID, порядок и хеши атомов неизменны.','changes':fixes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Normalized {len(fixes)} source-note displays; originals and atom text unchanged.')

if __name__=='__main__':
    main()
