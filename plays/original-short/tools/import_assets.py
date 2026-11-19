"""Import the verified wiki illustrations into the self-contained theater project.

Reads (never modifies) work/illustrations/manifest.json, copies the selected
sprites, sheets, prompts and references, writes sheet metadata, and rebuilds the
asset section of assets/manifest.json. Run from the repository root or anywhere;
paths are derived from this file's location.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
WORK = REPO / "work" / "illustrations"
WIKI_IMAGES = REPO / "wiki" / "protagonists" / "images"

PROFILE = "zhestokiy-romans-watercolor-v1"
GENERATOR = "Codex built-in image_gen (GPT Images); atlas cut and alpha cleanup with Pillow"

# slug -> (wiki entity_id, emotions)
CHARACTERS = {
    "larisa": ("Лариса Огудалова", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "harita": ("Харита Огудалова", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "paratov": ("Паратов", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "karandyshev": ("Карандышев", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "knurov": ("Кнуров", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "vozhevatov": ("Вожеватов", ["neutral", "happy", "sad", "surprised", "angry", "disgusted"]),
    "robinson": ("Робинзон", ["neutral"]),
    "ilya": ("Илья", ["neutral"]),
    "gavrilo": ("Гаврило", ["neutral"]),
    "ivan": ("Иван", ["neutral"]),
    "evfrosinya": ("Евфросинья Потаповна", ["neutral"]),
}

# slug -> (wiki entity_id, kind, source filename stem)
PLACES = {
    "boulevard-day": ("Бульвар Бряхимова", "day", "Бульвар Бряхимова.bespridannica.day.png"),
    "boulevard-evening": ("Бульвар Бряхимова", "evening", "Бульвар Бряхимова.bespridannica.evening.png"),
    "ogudalova-day": ("Дом Огудаловых", "day", "Дом Огудаловых.bespridannica.day.png"),
    "karandyshev-evening": ("Квартира Карандышева", "evening", "Квартира Карандышева.bespridannica.evening.png"),
}

CAST_BLOCK = {
    "Лариса Огудалова": "section-02#^b0002",
    "Харита Огудалова": "section-02#^b0001",
    "Кнуров": "section-02#^b0003",
    "Вожеватов": "section-02#^b0004",
    "Карандышев": "section-02#^b0005",
    "Паратов": "section-02#^b0006",
    "Робинзон": "section-02#^b0007",
    "Гаврило": "section-02#^b0008",
    "Иван": "section-02#^b0009",
    "Илья": "section-22#^b0010",
    "Евфросинья Потаповна": "section-22#^b0001",
}

ARTISTIC = {
    "Лариса Огудалова": [
        "Молодая незамужняя девушка; в тексте сказано «одета богато, но скромно».",
        "Тёмные косы, светлое платье и общая пластика — художественная отсылка к фильму «Жестокий романс» (1984), не книжная реконструкция.",
    ],
    "Харита Огудалова": [
        "Вдова средних лет, мать взрослой дочери; выглядит заметно старше Ларисы.",
        "Возраст около 50–55 — художественный выбор, не точная дата из текста.",
    ],
    "Паратов": [
        "Барин старше тридцати, уверенный и эффектный.",
        "Белый костюм — отсылка к фильму; в первом выходе пьеса называет чёрный сюртук.",
    ],
    "Карандышев": [
        "Молодой небогатый чиновник; очки и скромный костюм — визуальная интерпретация.",
        "Самолюбие и напряжённость переданы позой, без превращения в пожилого человека.",
    ],
    "Кнуров": [
        "Пожилой состоятельный делец, сдержанный и тяжёлый силуэт.",
        "Дорогой тёмный костюм — визуальная интерпретация при отсутствии точного описания одежды.",
    ],
    "Вожеватов": [
        "Очень молодой представитель торговой фирмы, европейский костюм.",
        "Наблюдательность и расчётливость переданы позой.",
    ],
    "Робинзон": [
        "Провинциальный актёр Аркадий Счастливцев; поношенный театрально-дорожный вид.",
        "Костюм — художественная интерпретация, не книжное описание.",
    ],
    "Илья": [
        "Музыкант с гитарой; возраст и орнаменты одежды — визуальная интерпретация.",
        "Точного описания внешности в тексте нет.",
    ],
    "Гаврило": [
        "Содержатель кофейной; костюм служит роли.",
        "Точный возраст книгой не задан.",
    ],
    "Иван": [
        "Слуга в кофейной; не смешивать с Иваном Петровичем Семёновским из фильма.",
        "Точное описание внешности в тексте отсутствует.",
    ],
    "Евфросинья Потаповна": [
        "Практичная тётка Карандышева, простая домашняя одежда.",
        "Возраст и черты лица — визуальная интерпретация, не книжное описание.",
    ],
}


def load_work():
    return json.loads((WORK / "manifest.json").read_text(encoding="utf-8"))


def local_reference(source: str, asset_id: str, slug: str) -> str:
    """Copy one reference into the project and return its project-relative path."""
    path = Path(source)
    if path.is_file():
        target_dir = PROJECT / "assets" / "references"
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{asset_id}-{path.name}"
        target = target_dir / name
        shutil.copy2(path, target)
        return target.relative_to(PROJECT).as_posix()
    # The sheet reference of a pose is replaced by the local sheet copy by the caller.
    return ""


def main() -> None:
    work = load_work()
    (PROJECT / "assets" / "prompts").mkdir(parents=True, exist_ok=True)
    entries = {(a["entity"], a["kind"]): a for a in work["assets"]}
    assets: dict[str, dict] = {}
    sheet_meta: dict[str, dict] = {}
    copied_refs: dict[str, str] = {}

    for slug, (entity, emotions) in CHARACTERS.items():
        sheet_src = entries[(entity, "charsheet")]
        sheet_dir = PROJECT / "assets" / "characters" / "sheets" / slug
        sheet_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / sheet_src["target"], sheet_dir / "sheet.png")
        shutil.copy2(WORK / "prompts" / f"{sheet_src['id']}.txt", sheet_dir / "prompt.txt")
        sheet_refs = []
        for ref in sheet_src.get("refs", []):
            local = copied_refs.get(ref)
            if not local:
                local = local_reference(ref, sheet_src["id"], slug)
                copied_refs[ref] = local
            if local:
                sheet_refs.append(local)
        sheet_meta[slug] = {
            "entity_id": entity,
            "profile": PROFILE,
            "version": 1,
            "image": "sheet.png",
            "sources": [
                f"wiki/protagonists/{entity}.bespridannica.md",
                f"source/bespridannica/bychapter/{CAST_BLOCK[entity]}",
            ],
            "generator": GENERATOR,
            "prompt_file": "prompt.txt",
            "reference_files": sheet_refs,
            "artistic_choices": ARTISTIC[entity],
        }
        (sheet_dir / "sheet.json").write_text(
            json.dumps(sheet_meta[slug], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        for emotion in emotions:
            source = entries[(entity, f"front_{emotion}")]
            image_dir = PROJECT / "assets" / "characters" / slug
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{emotion}.png"
            shutil.copy2(REPO / source["target"], image_path)
            prompt_name = f"{slug}-{emotion}.txt"
            shutil.copy2(WORK / "prompts" / f"{source['id']}.txt", PROJECT / "assets" / "prompts" / prompt_name)
            assets[f"{slug}-{emotion}"] = {
                "file": f"assets/characters/{slug}/{emotion}.png",
                "kind": "character",
                "anchor": [0.5, 1],
                "head_anchor": [0.5, 0.04],
                "sheet": f"assets/characters/sheets/{slug}/sheet.png",
                "sheet_metadata": f"assets/characters/sheets/{slug}/sheet.json",
                "sheet_origin": {
                    "entity_id": entity,
                    "profile": PROFILE,
                    "version": 1,
                    "path": f"wiki/protagonists/images/{Path(sheet_src['target']).name}",
                },
                "provenance": {
                    "generator": GENERATOR,
                    "prompt_file": f"assets/prompts/{prompt_name}",
                    "references": [f"assets/characters/sheets/{slug}/sheet.png"],
                },
            }

    faces: dict[str, dict[str, str]] = {}
    for slug, (entity, emotions) in CHARACTERS.items():
        faces[slug] = {}
        for emotion in emotions:
            source = entries[(entity, f"face_{emotion}")]
            face_dir = PROJECT / "assets" / "faces"
            face_dir.mkdir(parents=True, exist_ok=True)
            face_path = face_dir / f"{slug}-{emotion}.png"
            shutil.copy2(REPO / source["target"], face_path)
            prompt_name = f"{slug}-face-{emotion}.txt"
            shutil.copy2(WORK / "prompts" / f"{source['id']}.txt", PROJECT / "assets" / "prompts" / prompt_name)
            faces[slug][emotion] = f"assets/faces/{slug}-{emotion}.png"

    for slug, (entity, kind, filename) in PLACES.items():
        source = entries[(entity, kind)]
        image_path = PROJECT / "assets" / "backgrounds" / f"{slug}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / source["target"], image_path)
        prompt_name = f"{slug}.txt"
        shutil.copy2(WORK / "prompts" / f"{source['id']}.txt", PROJECT / "assets" / "prompts" / prompt_name)
        refs = []
        for ref in source.get("refs", []):
            if kind == "evening" and "places/images" in ref:
                # The evening image uses the day anchor: keep a local copy.
                local = copied_refs.get(ref)
                if not local:
                    local = local_reference(ref, source["id"], slug)
                    copied_refs[ref] = local
                if local:
                    refs.append(local)
            elif "protagonists/images" in ref:
                refs.append("assets/characters/sheets/larisa/sheet.png")
        assets[slug] = {
            "file": f"assets/backgrounds/{slug}.png",
            "kind": "background",
            "provenance": {
                "generator": GENERATOR,
                "prompt_file": f"assets/prompts/{prompt_name}",
                "references": refs,
            },
        }

    manifest_path = PROJECT / "assets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"] = assets
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (PROJECT / "tools" / "asset-report.json").write_text(
        json.dumps({"characters": len(CHARACTERS), "sprites": sum(len(v[1]) for v in CHARACTERS.values()),
                    "backgrounds": len(PLACES), "assets": len(assets),
                    "faces": sum(len(v) for v in faces.values())}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROJECT / "tools" / "faces.json").write_text(
        json.dumps(faces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"assets": len(assets), "backgrounds": len(PLACES),
                      "characters": len(CHARACTERS),
                      "faces": sum(len(v) for v in faces.values())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
