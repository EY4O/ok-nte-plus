"""Turn Character Ascend Scan results into farming targets for the daily tasks.

CharacterAscendScanTask records, for each character, the materials its next ascension
needs and the Source lines the game lists for them. This module reads those lines and
says which task and setting farm each material:

- Anomaly Hunt sources map to an AnomalyHunter target (追猎目标).
- Characters still below their level cap need character EXP: AnomalyTask on
  经验与甲硬币 / 角色经验.
- "Anomaly Drop" items (the Whispers / Silhouette / Numeral family) come from anomalies
  in the world. No task targets them, so they are reported for manual farming.
- "Open Material Selection Box", "Craft" and shop exchanges ("Hunter Exchange") are
  not farming routes and are skipped.

Farming is sized by the raw shortfall only. Material Conversion is never considered as a
way to cover a deficit; the builder farms raw materials instead.

Pure functions only, so the plan can be previewed before anything is written.
"""

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.tasks.AnomalyHunter import AnomalyHunter
from src.tasks.AnomalyTask import AnomalyTask

ASCEND_MAP_PATH = Path("configs") / "CharacterAscendMap.json"

KIND_HUNT = "hunt"
KIND_EXP = "exp"
KIND_ANOMALY_DROP = "anomaly_drop"
KIND_SELECTION_BOX = "selection_box"
KIND_CRAFT = "craft"
KIND_EXCHANGE = "exchange"
KIND_UNKNOWN = "unknown"

# Preference when a material lists several sources: a task that can target it first.
_KIND_RANK = {KIND_HUNT: 0, KIND_ANOMALY_DROP: 1, KIND_UNKNOWN: 2, KIND_EXCHANGE: 3,
              KIND_CRAFT: 4, KIND_SELECTION_BOX: 5}

# English names the game shows, squashed to lowercase letters, to AnomalyHunter targets.
# "Serenetti" is the game's spelling of Serenity; the English UI calls Sound King
# "Beat King".
HUNT_ALIASES = {
    "beatking": AnomalyHunter.TARGET_SOUND_KING,
    "soundking": AnomalyHunter.TARGET_SOUND_KING,
    "headlessrider": AnomalyHunter.TARGET_HEADLESS_RIDER,
    "serenetti": AnomalyHunter.TARGET_SERENITY,
    "serenity": AnomalyHunter.TARGET_SERENITY,
    "blacktome": AnomalyHunter.TARGET_BLACK_BOOK,
    "blackbook": AnomalyHunter.TARGET_BLACK_BOOK,
    "seaprisoner": AnomalyHunter.TARGET_SEA_PRISONER,
    "nestboundbird": AnomalyHunter.TARGET_NEST_BIRD,
    "nestbird": AnomalyHunter.TARGET_NEST_BIRD,
    "swallowtail": AnomalyHunter.TARGET_SPOTTED_BUTTERFLY,
    "spottedbutterfly": AnomalyHunter.TARGET_SPOTTED_BUTTERFLY,
}
# The Chinese target names are accepted as they are.
for _target in AnomalyHunter.HUNTER_TARGETS:
    HUNT_ALIASES[_target] = _target

# 'Anomaly Hunt "Serenetti"', 'Anomaly Hunt"Serenetti"', 'Anomaly Hunt: Sea Prisoner'.
HUNT_MATCH = re.compile(r"^\s*(?:Anomaly\s*Hunt|异象追猎)\s*[:：]?\s*(.+?)\s*$", re.I)
ANOMALY_DROP_MATCH = re.compile(r"^\s*Anomaly\s*Drop\s*$|异象掉落", re.I)
SELECTION_BOX_MATCH = re.compile(r"Material\s*Selection\s*Box|自选", re.I)
CRAFT_MATCH = re.compile(r"^\s*Craft\s*$|合成|制作", re.I)
# Shops: "Hunter Exchange", "Lost Exchange".
EXCHANGE_MATCH = re.compile(r"Exchange\s*$|兑换", re.I)
# OCR misreads such as "Headless Rlder" still resolve, but not unrelated names.
FUZZY_CUTOFF = 0.8


@dataclass(frozen=True)
class Source:
    kind: str
    raw: str
    target: str | None = None


@dataclass
class FarmStep:
    """One thing to farm and which task setting does it."""

    kind: str
    task: str | None
    config: dict
    material: str | None = None
    deficit: int = 0
    characters: list = field(default_factory=list)
    source: str | None = None


def _squash(text: str) -> str:
    return re.sub(r"[^a-z一-鿿]", "", text.lower())


def hunt_target(name: str) -> str | None:
    """AnomalyHunter target for a hunt name as the game prints it, or None."""
    key = _squash(name)
    if not key:
        return None
    if key in HUNT_ALIASES:
        return HUNT_ALIASES[key]
    close = difflib.get_close_matches(key, HUNT_ALIASES, n=1, cutoff=FUZZY_CUTOFF)
    return HUNT_ALIASES[close[0]] if close else None


def parse_source(text: str) -> Source:
    raw = (text or "").strip()
    if SELECTION_BOX_MATCH.search(raw):
        return Source(KIND_SELECTION_BOX, raw)
    if ANOMALY_DROP_MATCH.search(raw):
        return Source(KIND_ANOMALY_DROP, raw)
    if CRAFT_MATCH.search(raw):
        return Source(KIND_CRAFT, raw)
    if EXCHANGE_MATCH.search(raw):
        return Source(KIND_EXCHANGE, raw)
    if found := HUNT_MATCH.match(raw):
        target = hunt_target(found.group(1))
        if target is not None:
            return Source(KIND_HUNT, raw, target)
    return Source(KIND_UNKNOWN, raw)


def best_source(sources: list) -> Source | None:
    """The most useful route among a material's Source lines, or None if there are none."""
    parsed = [parse_source(s) for s in sources or []]
    if not parsed:
        return None
    return min(parsed, key=lambda s: _KIND_RANK[s.kind])


def _hunt_config(target: str) -> dict:
    return {AnomalyHunter.CONF_HUNTER_TARGET: target}


def _exp_config() -> dict:
    return {AnomalyTask.CONF_TASK_TYPE: AnomalyTask.TASK_EXP_COIN,
            AnomalyTask.CONF_EXP_TARGET: AnomalyTask.EXP_CHAR}


def material_steps(records: list) -> list:
    """Materials still short across the given characters, one step per material.

    The inventory is shared, so for several characters the shortfall is the combined
    need minus what is owned once, not the sum of each character's own deficit.
    """
    by_name: dict = {}
    for record in records:
        if record.get("status") != "ascend":
            continue
        for m in record.get("materials") or []:
            name = m.get("name")
            if not name:
                continue
            entry = by_name.setdefault(name, {"have": m.get("have") or 0, "need": 0,
                                              "sources": [], "characters": []})
            entry["need"] += m.get("need") or 0
            entry["characters"].append(record.get("name"))
            entry["sources"] += [s for s in m.get("sources") or []
                                 if s not in entry["sources"]]

    steps = []
    for name, entry in by_name.items():
        deficit = max(0, entry["need"] - entry["have"])
        if deficit == 0:
            continue
        source = best_source(entry["sources"])
        kind = source.kind if source else KIND_UNKNOWN
        if kind == KIND_HUNT:
            task, config = AnomalyHunter.__name__, _hunt_config(source.target)
        else:
            task, config = None, {}
        steps.append(FarmStep(kind=kind, task=task, config=config, material=name,
                              deficit=deficit, characters=entry["characters"],
                              source=source.raw if source else None))
    return steps


def exp_step(records: list) -> FarmStep | None:
    """Character EXP for everyone still below their level cap."""
    names = [r.get("name") for r in records if r.get("status") == "level_up"]
    if not names:
        return None
    return FarmStep(kind=KIND_EXP, task=AnomalyTask.__name__, config=_exp_config(),
                    characters=names)


def build_plan(records: list) -> list:
    """Every farming step for the given characters: materials first, then EXP."""
    steps = material_steps(records)
    if (step := exp_step(records)) is not None:
        steps.append(step)
    return steps


def load_ascend_map(path: Path = ASCEND_MAP_PATH) -> dict:
    """Scan results keyed by character name; empty if the scan has not run."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


# Daily Routine entries whose settings the builder writes. AnomalyTask and AnomalyHunter
# share one exclusive slot there, so a profile runs one of them per day; which one is
# left to the Daily Routine tab.
ROUTINE_ANOMALY = "daily_anomaly"
ROUTINE_HUNTER = "daily_anomaly_hunter"


def hunt_steps(steps: list) -> list:
    """Hunt steps, largest shortfall first: the choices for the hunter target."""
    return sorted((s for s in steps if s.kind == KIND_HUNT), key=lambda s: -s.deficit)


def routine_changes(hunt: FarmStep | None, exp: FarmStep | None) -> dict:
    """Daily Routine settings to write, keyed by routine entry id."""
    changes = {}
    if hunt is not None:
        changes[ROUTINE_HUNTER] = dict(hunt.config)
    if exp is not None:
        changes[ROUTINE_ANOMALY] = dict(exp.config)
    return changes


def preview_changes(current: dict, changes: dict) -> list:
    """(entry id, setting, before, after) for every setting the apply would change."""
    rows = []
    for task_id, values in changes.items():
        before = current.get(task_id) or {}
        for key, after in values.items():
            if before.get(key) != after:
                rows.append((task_id, key, before.get(key), after))
    return rows
