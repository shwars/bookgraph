"""Shared data helpers for the abridged Bespridannica stage script."""
from __future__ import annotations

CHARACTERS = {
    "larisa": {"name": "Лариса", "entity_id": "Лариса Огудалова", "color": "#6f8798"},
    "harita": {"name": "Харита Игнатьевна", "entity_id": "Харита Огудалова", "color": "#8a5560"},
    "paratov": {"name": "Паратов", "entity_id": "Паратов", "color": "#40596b"},
    "karandyshev": {"name": "Карандышев", "entity_id": "Карандышев", "color": "#77664b"},
    "knurov": {"name": "Кнуров", "entity_id": "Кнуров", "color": "#4a4944"},
    "vozhevatov": {"name": "Вожеватов", "entity_id": "Вожеватов", "color": "#557563"},
    "robinson": {"name": "Робинзон", "entity_id": "Робинзон", "color": "#8a6746"},
    "ilya": {"name": "Илья", "entity_id": "Илья", "color": "#8b5a3c"},
    "gavrilo": {"name": "Гаврило", "entity_id": "Гаврило", "color": "#6b5b45"},
    "ivan": {"name": "Иван", "entity_id": "Иван", "color": "#6f6252"},
    "evfrosinya": {"name": "Евфросинья Потаповна", "entity_id": "Евфросинья Потаповна", "color": "#7c5f55"},
    "narrator": {"name": "Рассказчик", "color": "#6b5947"},
}

# Actor height in logical stage pixels and default x for each scene are set per scene.
HEIGHTS = {
    "larisa": 320, "harita": 322, "paratov": 342, "karandyshev": 330,
    "knurov": 338, "vozhevatov": 328, "robinson": 326, "ilya": 324,
    "gavrilo": 330, "ivan": 318, "evfrosinya": 316,
}


def S(section: str, block: str) -> str:
    """Return the real block address used in script sources."""
    return f"source/bespridannica/bychapter/section-{section}#^{block}"


def cue(cid: str, speaker: str, text: str, sources: list[str], adaptation: str,
        gap: float = 0.6, fixed: float | None = None) -> dict:
    return {"id": cid, "speaker": speaker, "text": text, "sources": sources,
            "adaptation": adaptation, "gap": gap, "fixed": fixed}


def actor(aid: str, x: float, pose: str = "neutral", z: int = 2,
          enter_cue: str | None = None, exit_cue: str | None = None,
          reenter_cue: str | None = None,
          poses: list[tuple[str, float, str]] | None = None,
          gestures: list[tuple[str, str, float, float]] | None = None,
          moves: list[tuple[str, float, float, float | None]] | None = None,
          y: float = 0.94) -> dict:
    return {"id": aid, "x": x, "pose": pose, "z": z, "enter_cue": enter_cue,
            "exit_cue": exit_cue, "reenter_cue": reenter_cue,
            "poses": poses or [], "gestures": gestures or [],
            "moves": moves or [], "y": y}
