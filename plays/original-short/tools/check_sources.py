"""Check that every quoted cue really comes from its declared source blocks.

Narrator bridges are paraphrases and are checked only for a valid address.
Quoted cues are split at ellipses; every fragment must occur in the concatenated
source text after removing stage directions and punctuation. A small allowlist
records two obvious source typos that were corrected for the stage.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
SCRIPT = PROJECT / "script.json"
CHAPTERS = REPO / "source" / "bespridannica" / "bychapter"
CPS = 28.0

# Cues where the provided edition has an obvious typo; the stage text uses the
# normal reading and the adaptation field says so.
EDITORIAL = {"s4-18", "s9-22"}


def clean(text: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("…", " ").replace("...", " ")
    text = re.sub(r"[«»\"“”„']", " ", text)
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"[–—‒]", " ", text)
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def load_blocks() -> dict[str, str]:
    blocks: dict[str, str] = {}
    for path in sorted(CHAPTERS.glob("section-*.md")):
        section = path.stem.replace("section-", "")
        lines = path.read_text(encoding="utf-8").splitlines()
        current: list[str] = []
        for line in lines:
            match = re.fullmatch(r"\^b(\d{4})", line.strip())
            if match:
                blocks[f"{section}#^b{match.group(1)}"] = " ".join(current)
                current = []
            elif line.strip() and not line.startswith("#") and not line.startswith("[["):
                current.append(line.strip())
    return blocks


def main() -> None:
    story = json.loads(SCRIPT.read_text(encoding="utf-8"))
    blocks = load_blocks()
    problems: list[str] = []
    corrections: list[str] = []
    checked = 0
    for scene in story["scenes"]:
        for cue in scene["cues"]:
            addresses = []
            for source in cue["sources"]:
                match = re.search(r"section-(\d+)#\^(b\d{4})$", source)
                if not match:
                    problems.append(f"{cue['id']}: bad address {source}")
                    continue
                key = f"{match.group(1)}#^{match.group(2)}"
                if key not in blocks:
                    problems.append(f"{cue['id']}: missing block {source}")
                else:
                    addresses.append(blocks[key])
            if cue["speaker"] == "narrator":
                continue
            if cue["id"] in EDITORIAL:
                corrections.append(cue["id"])
                continue
            haystack = clean(" ".join(addresses))
            raw_parts = [p for p in re.split(r"…|\.\.\.", cue["text"]) if p.strip()]
            for part in raw_parts:
                needle = clean(part)
                if len(needle) < 4:
                    continue
                if needle not in haystack:
                    problems.append(f"{cue['id']}: fragment not found: {part[:90]!r}")
            checked += 1
            needed = len(cue["text"]) / CPS + 1.0
            if cue["duration"] + 0.01 < needed:
                problems.append(f"{cue['id']}: short duration {cue['duration']} < {needed:.1f}")
            if cue["at"] + cue["duration"] > scene["duration"] - 2.4:
                problems.append(f"{cue['id']}: too close to closing curtain")
    print(json.dumps({"checked": checked, "editorial_corrections": corrections,
                      "problems": problems[:40], "problem_count": len(problems)},
                     ensure_ascii=False, indent=2))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
