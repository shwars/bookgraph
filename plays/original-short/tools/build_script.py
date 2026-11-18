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
import scenes_a, scenes_d, scenes_e, scenes_f, scenes_g, scenes_h, scenes_i  # noqa: E402

RAW_SCENES = scenes_a.SCENES + [
    scenes_d.SCENE, scenes_e.SCENE, scenes_f.SCENE,
    scenes_g.SCENE, scenes_h.SCENE, scenes_i.SCENE,
]

DROPS = {
    "boulevard-morning": {"s1-07", "s1-11", "s1-15"},
    "arrival": {"s2-02", "s2-03", "s2-08", "s2-09"},
    "ideal": {"s3-02", "s3-03", "s3-08", "s3-18", "s3-21"},
    "efir": {"s4-03", "s4-09"},
    "half-million": {
        "s5-03", "s5-04", "s5-05", "s5-07", "s5-11", "s5-12",
        "s5-14", "s5-15", "s5-19", "s5-20", "s5-21", "s5-22",
        "s5-26", "s5-27", "s5-28", "s5-29", "s5-32", "s5-34", "s5-36",
        "s5-43", "s5-46", "s5-53", "s5-54", "s5-55",
        "s5-57", "s5-58", "s5-60", "s5-61", "s5-65", "s5-66", "s5-67", "s5-68",
        "s5-69", "s5-71",
    },
    "dinner": {"s6-04", "s6-05", "s6-07", "s6-13", "s6-25", "s6-29", "s6-32", "s6-36"},
    "funny-man": {"s7-03", "s7-08", "s7-13"},
    "coin-toss": {
        "s8-03", "s8-04", "s8-05", "s8-06", "s8-08", "s8-09", "s8-10", "s8-11",
        "s8-15", "s8-16", "s8-17", "s8-18", "s8-19", "s8-21", "s8-24", "s8-27",
        "s8-31", "s8-33", "s8-39", "s8-43", "s8-45", "s8-47", "s8-49",
        "s8-52", "s8-58",
    },
    "thing": {
        "s9-03", "s9-05", "s9-06", "s9-09", "s9-10", "s9-11", "s9-12", "s9-13",
        "s9-14", "s9-15", "s9-19", "s9-23", "s9-25", "s9-26", "s9-27", "s9-29",
        "s9-32", "s9-33", "s9-37", "s9-39a", "s9-44",
    },
}

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
        enter = None
        if spec.get("enter_cue"):
            enter = by_id[spec["enter_cue"]]["at"] - 0.4
            keyframes.append({"at": 0, "x": start_x, "y": spec["y"],
                              "asset": f"{aid}-{spec['pose']}"})
            keyframes.append({"at": round(enter, 1), "x": start_x})
            keyframes.append({"at": round(enter + 1.8, 1), "x": spec["x"]})
        else:
            keyframes.append({"at": 0, "x": spec["x"], "y": spec["y"],
                              "asset": f"{aid}-{spec['pose']}"})
        for cue_id, offset, emotion in spec["poses"]:
            if cue_id not in by_id:
                continue
            at = round(by_id[cue_id]["at"] + offset, 1)
            if at <= keyframes[-1]["at"]:
                at = round(keyframes[-1]["at"] + 0.2, 1)
            keyframes.append({"at": at, "asset": f"{aid}-{emotion}"})
        gestures = []
        for kind, cue_id, offset, duration in spec["gestures"]:
            if cue_id not in by_id:
                continue
            gestures.append({"kind": kind, "at": round(by_id[cue_id]["at"] + offset, 1),
                             "duration": duration})
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
                if spec.get("enter_cue") in mapping:
                    spec["enter_cue"] = mapping[spec["enter_cue"]]
                spec["poses"] = [(mapping.get(cid, cid), off, emo)
                                 for cid, off, emo in spec["poses"]]
                spec["gestures"] = [(kind, mapping.get(cid, cid), off, dur)
                                    for kind, cid, off, dur in spec["gestures"]]
        scenes.append(build_scene(raw))
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
        "adaptation_notes": [
            "Сокращённая сценическая версия четырёх действий. Сохранены ключевые сюжетные и цитатные реплики; экспозиция, комические линии и часть монологов сокращены.",
            "Текст героев взят из предоставленного издания. В длинных репликах сделаны купюры; они отмечены в поле adaptation у каждой реплики.",
            "Связки рассказчика пересказывают ремарки и места действия. Новых фактов они не добавляют; источники указаны у каждой связки.",
            "Визуальный стиль — акварель по фильму «Жестокий романс» (1984). Это художественное оформление, а не каноническое описание внешности.",
            "Ключевые предметы — монета, кольцо, пистолет — не выносятся отдельными куклами: на них указывают жестом и словом. Выстрел обозначен ремаркой и жестом.",
            "Спектакль идёт без звука. Цыганский хор в финале обозначен ремаркой; пушечный выстрел и выстрел Карандышева — сценическими знаками.",
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
