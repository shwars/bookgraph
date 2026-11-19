"""Split the night into two scenes: the coin toss and the engagement."""
from script_common import actor
from scenes_h import SCENE

COIN_IDS = {f"s8-{i:02d}" for i in range(1, 17)}

COIN = {
    **SCENE,
    "id": "coin-toss",
    "title": "Орел или решетка",
    "actors": [
        actor("knurov", .18, z=2,
              moves=[("s8-02", 0, .22, None), ("s8-10", 0, .28, None)]),
        actor("vozhevatov", .38, z=2,
              poses=[("s8-15", 0, "neutral"), ("s8-16", 0, "happy")],
              moves=[("s8-02", 0, .42, None), ("s8-12", 0, .48, None)]),
    ],
    "cues": [c for c in SCENE["cues"] if c["id"] in COIN_IDS],
}

ENGAGEMENT = {
    **SCENE,
    "id": "engagement",
    "title": "Обручение",
    "actors": [
        actor("paratov", .58, z=3, enter_cue="s8-18", exit_cue="s8-43",
              gestures=[("recoil", "s8-41", 0.2, 1.2)],
              moves=[("s8-20", 0, .52, None), ("s8-30", 0, .58, None),
                     ("s8-42", 0, .50, None)]),
        actor("larisa", .76, z=3, enter_cue="s8-18",
              poses=[("s8-18", 0, "sad"), ("s8-39", 0, "surprised"),
                     ("s8-47", 0, "surprised"), ("s8-50", 0, "sad")],
              gestures=[("recoil", "s8-38", 0.2, 1.4)],
              moves=[("s8-18", 0, .70, None), ("s8-27", 0, .64, None),
                     ("s8-42", 0, .58, None)]),
        actor("knurov", .12, z=2, enter_cue="s8-43",
              moves=[("s8-54", 0, .20, None)]),
        actor("vozhevatov", .30, z=2, enter_cue="s8-43",
              moves=[("s8-44", 0, .36, None)]),
        actor("robinson", .90, z=2, enter_cue="s8-43"),
    ],
    "cues": [c for c in SCENE["cues"] if c["id"] not in COIN_IDS and c["id"] not in {"s8-17"}],
}
ENGAGEMENT.pop("caption", None)

SCENES = [COIN, ENGAGEMENT]
