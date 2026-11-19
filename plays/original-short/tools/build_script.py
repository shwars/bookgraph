"""Build script.json from the editable scene modules."""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(HERE))

from script_common import CHARACTERS, HEIGHTS  # noqa: E402
import scenes_a, scenes_d, scenes_e, scenes_f, scenes_g, scenes_h_split, scenes_i  # noqa: E402

RAW_SCENES = scenes_a.SCENES + [
    scenes_d.SCENE, scenes_e.SCENE, scenes_f.SCENE,
    scenes_g.SCENE, *scenes_h_split.SCENES, scenes_i.SCENE,
]

DROPS = {}
CPS = 28.0
FIRST_CUE = 3.0
TAIL = 2.8


def split_cues(cues: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Split very long bubbles at a sentence boundary; return id remapping."""
    result, mapping = [], {}
    for cue in cues:
        text = cue["text"]
        if len(text) <= 220 or cue["speaker"] == "narrator":
            result.append(cue)
            continue
        if "‖" in text:
            first, second = text.split("‖", 1)
        else:
            breaks = [m.end() for m in re.finditer(r"(?<=[.!?])\s+", text)]
            if not breaks:
                breaks = [m.end() for m in re.finditer(r"(?<=[;])\s+", text)]
            if not breaks:
                breaks = [m.end() for m in re.finditer(r"(?<=[,])\s+", text)]
            target = len(text) * 0.52
            breaks = [pos for pos in breaks if len(text) * 0.32 <= pos <= len(text) * 0.72]
            if breaks:
                point = min(breaks, key=lambda pos: abs(pos - target))
                first, second = text[:point], text[point:]
            else:
                spaces = [m.start() for m in re.finditer(r"\s+", text)
                          if len(text) * 0.32 <= m.start() <= len(text) * 0.72]
                point = min(spaces, key=lambda pos: abs(pos - target)) if spaces else int(target)
                first, second = text[:point], text[point:]
        first, second = first.strip().rstrip(",;:"), second.strip()
        if second and second[0].islower():
            second = second[0].upper() + second[1:]
        if len(first) < 40 or len(second) < 40:
            result.append(cue)
            continue
        mapping[cue["id"]] = cue["id"] + "-a"
        for suffix, part, gap in (("-a", first, cue.get("gap", 0.6)), ("-b", second, 0.45)):
            item = dict(cue)
            item["id"] = cue["id"] + suffix
            item["text"] = part
            item["gap"] = gap
            item["adaptation"] = cue["adaptation"] + " Одна длинная реплика разделена на две для читаемости."
            result.append(item)
    return result, mapping


def timed(scene: dict) -> dict:
    t = FIRST_CUE
    for index, cue in enumerate(scene["cues"]):
        gap = 0 if index == 0 else float(cue.get("gap", 0.6))
        t += gap
        text_len = len(cue["text"])
        dur = cue.get("fixed") or max(2.5, text_len / CPS + 1.6)
        dur = round(dur + 0.049, 1)
        cue["at"] = round(t + 0.049, 1)
        cue["duration"] = dur
        t = cue["at"] + dur
    scene["duration"] = round(math.ceil((t + TAIL) * 10) / 10, 1)
    return scene


def build_actors(scene: dict) -> list[dict]:
    by_id = {c["id"]: c for c in scene["cues"]}
    out = []
    for spec in scene["actors"]:
        aid = spec["id"]
        start_x = -0.18 if spec["x"] <= 0.5 else 1.18
        keyframes = []

        def add(at: float, **values) -> None:
            at = max(0.0, round(at, 1))
            while any(abs(frame["at"] - at) < 0.05 for frame in keyframes):
                at = round(at + 0.1, 1)
            keyframes.append({"at": at, **values})

        add(0, x=start_x if spec.get("enter_cue") else spec["x"],
            y=spec["y"], asset=f"{aid}-{spec['pose']}")
        enter = None
        if spec.get("enter_cue") and spec["enter_cue"] in by_id:
            enter = by_id[spec["enter_cue"]]["at"] - 0.4
            add(enter, x=start_x)
            add(enter + 1.8, x=spec["x"])
        if spec.get("exit_cue") and spec["exit_cue"] in by_id:
            exit_cue = by_id[spec["exit_cue"]]
            add(exit_cue["at"] + exit_cue["duration"] + 0.2, x=start_x)
        if spec.get("reenter_cue") and spec["reenter_cue"] in by_id:
            reenter = by_id[spec["reenter_cue"]]["at"] - 0.4
            add(reenter, x=start_x)
            add(reenter + 1.8, x=spec["x"])
        for cue_id, offset, x_value, y_value in spec["moves"]:
            if cue_id not in by_id:
                continue
            values = {"x": x_value}
            if y_value is not None:
                values["y"] = y_value
            add(by_id[cue_id]["at"] + offset, **values)
        for cue_id, offset, emotion in spec["poses"]:
            if cue_id not in by_id:
                continue
            add(by_id[cue_id]["at"] + offset, asset=f"{aid}-{emotion}")
        gestures = []
        for kind, cue_id, offset, duration in spec["gestures"]:
            if cue_id not in by_id:
                continue
            gestures.append({"kind": kind, "at": round(by_id[cue_id]["at"] + offset, 1),
                             "duration": duration})
        keyframes.sort(key=lambda frame: frame["at"])
        out.append({
            "id": aid,
            "asset": f"{aid}-{spec['pose']}",
            "height": HEIGHTS[aid],
            "z": spec["z"],
            "keyframes": keyframes,
            "gestures": gestures,
        })
    return out


def build_scene(raw: dict) -> dict:
    scene = timed({**raw, "cues": [dict(c) for c in raw["cues"]]})
    scene["actors"] = build_actors(scene)
    for cue in scene["cues"]:
        cue.pop("gap", None)
        cue.pop("fixed", None)
    if "caption" in scene:
        scene["caption"] = dict(scene["caption"])
    return scene


def main() -> None:
    scenes = []
    for raw in RAW_SCENES:
        drop = DROPS.get(raw["id"], set())
        raw["cues"] = [c for c in raw["cues"] if c["id"] not in drop]
        raw["cues"], mapping = split_cues(raw["cues"])
        if mapping:
            for spec in raw["actors"]:
                for key in ("enter_cue", "exit_cue", "reenter_cue"):
                    if spec.get(key) in mapping:
                        spec[key] = mapping[spec[key]]
                spec["poses"] = [(mapping.get(cid, cid), off, emo)
                                 for cid, off, emo in spec["poses"]]
                spec["gestures"] = [(kind, mapping.get(cid, cid), off, dur)
                                    for kind, cid, off, dur in spec["gestures"]]
                spec["moves"] = [(mapping.get(cid, cid), off, xv, yv)
                                 for cid, off, xv, yv in spec["moves"]]
        scenes.append(build_scene(raw))

    # Close-up blocks are time ranges, not per-cue flags: a narrator line or a
    # pause between cues must not drop the shot back to the wide stage.
    closeups = {
        "ideal": [
            ("s3-01", "s3-09e", ["larisa", "karandyshev"]),
            ("s3-17", "s3-20", ["larisa", "karandyshev"]),
        ],
        "efir": [
            ("s4-01a", "s4-12", ["knurov", "harita"]),
        ],
        "half-million": [
            ("s5-16", "s5-25", ["paratov", "larisa"]),
            ("s5-31", "s5-42b", ["paratov", "larisa"]),
        ],
        "funny-man": [
            ("s7-09", "s7-15", ["karandyshev"]),
        ],
        "coin-toss": [
            ("s8-02", "s8-16", ["knurov", "vozhevatov"]),
        ],
        "engagement": [
            ("s8-18", "s8-30", ["paratov", "larisa"]),
            ("s8-38", "s8-42", ["paratov", "larisa"]),
        ],
        "thing": [
            ("s9-02", "s9-07", ["larisa"]),
            ("s9-18", "s9-27", ["larisa", "karandyshev"]),
            ("s9-36", "s9-39d", ["larisa", "karandyshev"]),
        ],
    }
    for scene in scenes:
        specs = closeups.get(scene["id"], [])
        ids = [cue["id"] for cue in scene["cues"]]
        segments = []
        for start, end, cast in specs:
            if start not in ids or end not in ids:
                continue
            first, last = ids.index(start), ids.index(end)
            start_at = scene["cues"][first]["at"]
            if last + 1 < len(scene["cues"]):
                end_at = scene["cues"][last + 1]["at"]
            else:
                end_at = scene["duration"]
            segments.append({
                "from": start,
                "to": end,
                "start": round(start_at, 2),
                "end": round(end_at, 2),
                "cast": list(cast),
            })
            for cue in scene["cues"][first:last + 1]:
                if cue["speaker"] != "narrator":
                    cue["closeup"] = list(cast)
        if segments:
            scene["closeups"] = segments

    faces_path = HERE / "faces.json"
    faces = json.loads(faces_path.read_text(encoding="utf-8")) if faces_path.is_file() else {}

    story = {
        "version": 1,
        "title": "Бесприданница",
        "subtitle": "Драма в четырёх действиях. Сокращённая сценическая версия",
        "end_title": "Занавес",
        "stage": {"width": 1516, "height": 680, "chars_per_second": CPS,
                  "curtain_seconds": 2.2},
        "presentation": {
            "logical_size": [1600, 900],
            "theme": {"paper": "#f4e8d0", "ink": "#392a20",
                      "gold": "#bf9652", "curtain": "#6e2433"},
        },
        "characters": CHARACTERS,
        "faces": faces,
        "adaptation_notes": [
            "Сокращённая сценическая версия четырёх действий. Диалоги сохранены целыми обменами: если оставлен вопрос, оставлен и ответ; комические и фоновые линии сокращены целыми блоками.",
            "Текст героев взят из предоставленного издания. В длинных монологах сделаны купюры; они отмечены в поле adaptation у каждой реплики.",
            "Связки рассказчика пересказывают ремарки и места действия. Новых фактов они не добавляют; источники указаны у каждой связки.",
            "Визуальный стиль — акварель по фильму «Жестокий романс» (1984). Это художественное оформление, а не каноническое описание внешности.",
            "Ключевые предметы — монета, кольцо, пистолет — не выносятся отдельными куклами: на них указывают жестом и словом. Выстрел обозначен ремаркой и жестом.",
            "Спектакль идёт без звука. Цыганский хор в финале обозначен ремаркой; пушечный выстрел и выстрел Карандышева — сценическими знаками.",
            "Важные диалоги идут в портретном режиме: крупные лица говорящего и слушающего, полные фигурки приглушены. Портреты — те же акварельные образы, не новые факты.",
            "Источники: source/bespridannica/bychapter/section-XX#^bYYYY. Полная таблица сцен и купюр — в coverage.md; издание и хеш — в README.md.",
        ],
        "scenes": scenes,
    }
    (PROJECT / "script.json").write_text(
        json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    total = sum(s["duration"] for s in scenes)
    print(json.dumps({"scenes": len(scenes), "cues": sum(len(s["cues"]) for s in scenes),
                      "seconds": round(total, 1), "minutes": round(total / 60, 1)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
