"""Shared map-loading helper for generate.py / datadriven.py / predict.py (P3,
docs/crt-train/ORG-DISCOVERY-PLAN.md "Consumers read the cache, and say when they didn't").

ONE tiny module so all three consumers apply IDENTICAL freshness/staleness rules instead of three
independently-drifting copies of the same "is this map fresh enough" logic. No org contact ever --
this is a pure filesystem/JSON read.

Rules (from the plan, verbatim):
  - default (no --map given): use the org's map automatically ONLY if younger than 24h; otherwise
    fall back to live with a printed reason -- never silently.
  - --map <path> given explicitly: always attempt to load that file. If it is older than 7 days,
    BLOCK (return blocked reason) unless --allow-stale is also passed -- a stale cache must never
    be mistaken for a fresh one (the tri-state rule applied to caching).
  - every caller must print the returned status line -- `map: <org> (built HH:MM, age Xh)` or
    `map: none -- live describe` -- so a reader can always tell which path produced a result.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

MAP_DIR = Path(os.path.expanduser("~/.claude/state/org-map"))
FRESH_SECONDS = 24 * 3600       # default auto-use cutoff
STALE_SECONDS = 7 * 24 * 3600   # hard block cutoff (without --allow-stale)


def default_map_path(org: str) -> Path:
    return MAP_DIR / f"{org}.json"


def map_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    return time.time() - path.stat().st_mtime


def resolve_map(org: str, map_arg: str | None, allow_stale: bool = False):
    """Returns (map_dict_or_None, status_line, blocked_reason_or_None).

    `map_dict_or_None` is the parsed org map, or None if this call should fall back to a live
    query. `blocked_reason_or_None` is set only when an EXPLICIT --map was given and is stale
    beyond the 7-day cutoff without --allow-stale -- callers should treat that as a hard error
    (non-zero exit), not a silent live fallback, per the plan's "map older than 7 days blocks
    generation unless --allow-stale."
    """
    explicit = map_arg is not None
    path = Path(map_arg) if explicit else default_map_path(org)

    if not path.exists():
        if explicit:
            return None, f"map: none ({path} missing) -- live describe", None
        return None, "map: none -- live describe", None

    age_s = time.time() - path.stat().st_mtime
    age_h = age_s / 3600.0
    built_local = time.strftime("%H:%M", time.localtime(path.stat().st_mtime))

    if not explicit and age_s >= FRESH_SECONDS:
        return (None,
                f"map: none -- {org} map is {age_h:.1f}h old (>24h, not auto-used; "
                f"pass --map {path} --allow-stale to force) -- live describe",
                None)

    if age_s >= STALE_SECONDS and not allow_stale:
        return (None,
                f"map: BLOCKED -- {org} map is {age_h / 24:.1f}d old (>7d); pass --allow-stale "
                f"to use it anyway, or rebuild with `discover.py build --org {org}`",
                f"stale ({age_h / 24:.1f}d, cutoff 7d)")

    try:
        mp = json.loads(path.read_text())
    except Exception as e:
        return None, f"map: none ({path} unreadable: {e}) -- live describe", None

    status = f"map: {org} (built {built_local}, age {age_h:.1f}h)"
    return mp, status, None
