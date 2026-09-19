#!/usr/bin/env python3
"""
Usage: python3 -c "import mapio" (library only -- no CLI)
Org-map I/O and the fact envelope -- the seam carved out of discover.py (stream S55, 2026-09-05).

Holds the three things every discovery module needs before it can record anything:

  * WHERE the map lives (MAP_DIR / DOC_DIR / INV_PATH, env-overridable for tests + benchmarks),
  * HOW a map is written (`_write_map` -- one rotated .bak generation per write; a build with
    --replace-population once reduced dev1's map from 1036 objects to 1 with no backup),
  * WHAT a recorded fact looks like (`wrap()` -- value/source/observed_at/verified, with
    `verified` in {"live","offline","could-not-check"}; never collapse could-not-check into
    false), plus the process-wide API call counter every build prints.

IMPORT CONTRACT: `discover.py` re-exports every name here, so `discover.MAP_DIR`,
`discover.wrap`, `discover.API_CALLS` etc. keep working for every existing consumer
(coverage.py, drift.py, processes.py, quality_center.py, recorder/handoff/coverage_link.py) and
for every test that monkeypatches them. Code that MOVES out of discover.py must read the
patchable names off the `discover` module (see transports.py `_D()`), not off this module, or a
test's monkeypatch would silently miss.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent            # tools/qforce-lite/discovery
QFL = HERE.parent                                   # tools/qforce-lite
ROOT = QFL.parent.parent                            # repo root

# MAP_DIR/DOC_DIR are overridable by env var ONLY so a before/after benchmark (or a test) can
# write a whole map somewhere harmless instead of over the shared one -- the defaults are
# unchanged and nothing in normal use sets them.
MAP_DIR = Path(os.environ.get("DISCOVER_MAP_DIR") or os.path.expanduser("~/.claude/state/org-map"))
DOC_DIR = Path(os.environ["DISCOVER_DOC_DIR"]) if os.environ.get("DISCOVER_DOC_DIR") else ROOT / "docs" / "org-map"
INV_PATH = ROOT / "docs" / "crt-train" / "org-inventory.json"

VALID_VERIFIED = {"live", "offline", "could-not-check"}


def _merge_org_level_from_disk(map_path, obj, baseline: dict | None = None) -> list:
    """Re-read the map that is on disk RIGHT NOW and put back every `org_level` key `obj` does not
    have. Returns the list of keys it rescued (empty is the normal case).

    Called from `_write_map` immediately before the write, so the window between reading and
    writing is microseconds instead of the ~89 s a `discover.py fetch` holds its map.

    `baseline` (optional) is the `org_level` as it was when `obj` was LOADED. With it, a key both
    sides changed can be told apart from a key only disk changed, and the collision is printed by
    name -- the whole point is that a lost key is never silent again. Without it the rule is the
    safe one: `obj` wins any key it actually carries."""
    map_path = Path(map_path)
    if not isinstance(obj, dict) or not map_path.exists():
        return []
    try:
        on_disk = json.loads(map_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []                      # an unreadable map is the backup's problem, not the merge's
    disk_level = (on_disk or {}).get("org_level")
    if not isinstance(disk_level, dict) or not disk_level:
        return []
    mine = obj.setdefault("org_level", {})
    if not isinstance(mine, dict):
        return []
    rescued, clobbered = [], []
    for key, value in disk_level.items():
        if key not in mine:
            mine[key] = value
            rescued.append(key)
        elif baseline is not None and mine[key] != value and baseline.get(key) == mine[key]:
            # `obj` never touched this key since it was loaded, but disk did -- disk is newer.
            mine[key] = value
            rescued.append(key)
        elif baseline is not None and mine[key] != value and baseline.get(key) != value:
            clobbered.append(key)
    if rescued:
        print(f"NOTE: {map_path.name}: merged {len(rescued)} org_level key(s) written by another "
              f"process while this map was held in memory: {', '.join(sorted(rescued))}",
              file=sys.stderr)
    if clobbered:
        print(f"WARNING: {map_path.name}: org_level key(s) {', '.join(sorted(clobbered))} were "
              f"changed BOTH here and on disk since this map was loaded -- this write keeps the "
              f"in-memory value and the on-disk one is lost. Re-run the tool that wrote it "
              f"(a canary target: `discover.py canary-target`; a floor: `discover.py calibrate`).",
              file=sys.stderr)
    return rescued


#: Top-level map keys written by exactly one tool and carried forward by every other writer:
#: `fail_fast` (calibrate), `last_verify` (a live verify), `coverage_built_at`/`coverage_totals`
#: (coverage). A key the incoming map sets itself always wins.
CARRIED_TOP_LEVEL_KEYS = ("fail_fast", "last_verify", "coverage_built_at", "coverage_totals")


def _write_map(map_path, obj, org_level_baseline: dict | None = None) -> None:
    """Every map write goes through here: the previous file is kept as <alias>.json.bak first.
    2026-09-05: a build with --replace-population reduced dev1's map from 1036 objects to 1 and
    there was no backup -- a 450 s / 2654-call rebuild was the only way back. Keeps ONE
    generation (the last good map), rotated on every write; restore = copy the .bak over.

    2026-09-06 (REVIEW-2026-09-06 §3, ORG-MAP-LAYERS.md): `fail_fast` (BACKLOG 62's per-org
    floor_ms/cutover_ms) is written ONLY by `discover.py calibrate` -- every other write path
    (`build`, `refresh`, `fetch`) never touches it, but neither did it carry it forward: a plain
    dict overwrite of the map file drops any key the new build didn't set. Both dev1 and slockard
    lost their calibration stamp this way. Carry `fail_fast` forward from the prior map (or its
    `.bak` if the live file was already stomped) when the incoming `obj` doesn't have one --
    additive only, never overwrites a `fail_fast` `obj` sets itself (a real `calibrate` run).

    2026-09-06 (the health90 race): `discover.py fetch` held that org's map IN MEMORY for ~89 s and
    its final write discarded an `org_level.canary` another process had written mid-flight. This is
    plain last-writer-wins on a whole-file replace, and `fail_fast` above is the same bug caught
    once for one key.

    CHOSEN FIX: re-read the on-disk map immediately before writing and merge back every
    `org_level.*` key the in-memory copy does not itself set. NOT a file lock, and the reason is
    the shape of the writers, not taste: the losing window is the whole 89 s a `fetch` holds the
    map, so a lock that is honest about that window has to be held for the entire fetch -- which
    would serialise every discovery run on the machine and turn a lost key into a stalled stream.
    A lock around the read-modify-write alone would be pure theatre: it closes a ~2 ms window and
    leaves the 89 s one wide open. Merging at write time closes the real window for the keys that
    actually collide (small, independent `org_level` facts written by different tools -- `canary`,
    `fail_fast`, a calibration stamp) and is honest about what it cannot do: a key BOTH sides
    changed is still last-writer-wins, and that case is PRINTED by name rather than swallowed.

    Object payloads are deliberately NOT merged: a `fetch`/`refresh` legitimately rewrites objects
    wholesale, and a merge there would resurrect deleted ones."""
    map_path = Path(map_path)
    _merge_org_level_from_disk(map_path, obj, baseline=org_level_baseline)
    # 2026-09-06 (N+3 close): `fail_fast` was the FIRST key of this class, not the only one.
    # `last_verify` (a live `verify`'s baseline, read by `verify --offline` in ci_local) was
    # dropped the same way by the recache's later writers (`diff --apply`, `coverage`), so
    # ci_local went red with "no prior LIVE verify on record" minutes after a live verify ran.
    # Every top-level key that only ONE tool writes is carried forward when the incoming map
    # does not set it -- additive only, never overwriting a value the writer set itself.
    missing = [k for k in CARRIED_TOP_LEVEL_KEYS if k not in obj]
    if missing:
        prior = None
        for candidate in (map_path, map_path.with_suffix(map_path.suffix + ".bak")):
            if candidate.exists():
                try:
                    prior = json.loads(candidate.read_text())
                except (OSError, json.JSONDecodeError):
                    prior = None
            if isinstance(prior, dict) and any(prior.get(k) for k in missing):
                for k in missing:
                    if prior.get(k):
                        obj[k] = prior[k]
                break
    if map_path.exists():
        try:
            shutil.copyfile(map_path, map_path.with_suffix(map_path.suffix + ".bak"))
        except OSError as exc:  # never block a build on the backup, but say so
            print(f"WARNING: could not back up {map_path.name}: {exc}", file=sys.stderr)
    map_path.write_text(json.dumps(obj, indent=1) + "\n")


# --------------------------------------------------------------------------------------------
# API-call accounting -- printed with every build, required by the plan's cost measurement.
# --------------------------------------------------------------------------------------------

class Counter:
    def __init__(self):
        self.n = 0

    def inc(self, k: int = 1) -> None:
        self.n += k


API_CALLS = Counter()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def wrap(value, source: str, verified: str = "live", observed_at: str | None = None) -> dict:
    assert verified in VALID_VERIFIED, verified
    return {"value": value, "source": source, "observed_at": observed_at or now_iso(), "verified": verified}


# --------------------------------------------------------------------------------------------
# org_level.canary -- the per-org known-good target the recorder's pre-flight canary drives
# (REVIEW-2026-09-06 Build-plan addendum (c)).
#
# WHY IT IS IN THE MAP. `tools/recorder/preflight/canary.py` hard-codes its known-good flow to the
# slockard zoo (`/lightning/n/Zoo_Base_Inputs`, label "Text"). On fsc7f, an org with no zoo, the
# canary correctly said so -- and then every flow of that night was COULD-NOT-CHECK for a reason
# that was about our fixture, not about the org. A known-good target is an ORG FACT, so it belongs
# in the org map beside every other org fact, read through the same reader and written through the
# same `_write_map` path (one rotated .bak per write) as everything else.
#
# SHAPE (all four fields are what the canary needs to make a claim):
#   org_level.canary = {
#       "path":     "/lightning/n/Zoo_Base_Inputs",   # where to go (URL-first, never a click path)
#       "label":    "Text",                            # the field to drive
#       "value":    "GZREC canary",                    # what to type (a run stamp is appended)
#       "expected": "GZREC canary",                    # what the read-back must equal, before the
#                                                      #   stamp is appended; None => equals `value`
#       "source": ..., "observed_at": ..., "verified": ...   # the standard `wrap()` envelope keys
#   }
# `verified` is "offline" when a human declared the target without driving it (the
# `discover.py canary-target` sub-command never touches an org) and "live" only once something has
# actually driven it -- so a declared-but-unproven target is never mistaken for a measured one.
# --------------------------------------------------------------------------------------------

CANARY_FIELDS = ("path", "label", "value", "expected")


def read_canary_target(mp: dict) -> dict | None:
    """The org map's `org_level.canary`, or None when the map has none (the caller then falls back
    to its own default and SAYS SO -- never silently). Returns a plain dict with the four fields
    plus the envelope keys; a malformed or partial entry (no path, or no label) returns None rather
    than a half-target, because a canary driven against half a target would report a failure that
    is really a config bug."""
    if not isinstance(mp, dict):
        return None
    entry = (mp.get("org_level") or {}).get("canary")
    if not isinstance(entry, dict):
        return None
    if not entry.get("path") or not entry.get("label"):
        return None
    out = {k: entry.get(k) for k in CANARY_FIELDS}
    out["expected"] = entry.get("expected") if entry.get("expected") is not None else entry.get("value")
    for k in ("source", "observed_at", "verified"):
        out[k] = entry.get(k)
    return out


def set_canary_target(mp: dict, path: str, label: str, value: str | None = None,
                      expected: str | None = None, source: str = "declared",
                      verified: str = "offline") -> dict:
    """Write `org_level.canary` into a map dict IN PLACE and return it. Does not touch disk -- the
    caller writes with `_write_map`, so the map's one-generation backup still happens on this write
    like on every other."""
    assert verified in VALID_VERIFIED, verified
    if not path or not label:
        raise ValueError("a canary target needs both a path and a label")
    mp.setdefault("org_level", {})["canary"] = {
        "path": path, "label": label, "value": value,
        "expected": expected if expected is not None else value,
        "source": source, "observed_at": now_iso(), "verified": verified,
    }
    return mp
