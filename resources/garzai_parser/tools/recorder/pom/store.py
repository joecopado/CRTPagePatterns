"""store -- read/write/merge the page object records (one JSON file per page key).

Usage (library): from pom.store import Store; s = Store(); rec = s.get(key); s.merge_session(session_dict)

Two session step shapes are read (`normalise_step`): the recorder's DOM events
(`event: {kind: nav|click|type|change|key, url, target, context}`) and the KEPT sessions
`up.py --op kw --session NAME` writes (`event: {kind: "kw", host: <page url>, control_family:
"kw-driven"}`, the action and family read off `chosen.kw`).

Layout (user, 2026-09-05 -- partitioned by org, beside that org's metadata cache, never mixed):
  Salesforce   ~/.claude/state/org-map/<alias>/pom/<slug>.json   render docs/org-map/<alias>-pom.md
  other apps   ~/.claude/state/apps/<host>/pom/<slug>.json        render docs/recorder/pom/<host>.md
Tests point `Store(state_root=..., docs_root=...)` at a scratch tree.

Record schema -- docs/recorder/POM.md. The short version:
  page      key/partition/pattern/object/action/record_type/layout_hash, first_seen, last_seen, visits
  l0        the last observed index (source: v3 | v1 | session), captured_at, bytes
  elements  {element_id: {family, label, container, attrs, ladder:[rung...], effects:{class: n},
             leads_to:{page key: n}, opens:{modal/panel title: n}, states:{name: {label, enabled?}},
             last_seen, source?, folded_from?}}
             -- WHAT a control is called here is decided in ONE place, `identify_control`, which
             every writer calls before it writes (F70, 2026-09-19): a driven `--op kw` step knows
             no tag or attrs, so without it the same control got a second id and the truth split
             between the two halves. `source: driven` marks an element minted with no shape yet;
             `folded_from` names an id the migration merged away.
  links     {target page key: {via: [element_id...], n}}  -- where this page's controls GO, and
             which control goes there. The target may be in ANOTHER PARTITION: Copado CI/CD's
             `Commit Changes` on a Salesforce User Story page leads to
             `na.devops.copado.com|/en/commit/{id}`, an Angular app on its own host. The partition
             rule does not bend for it (AI-POM-HANDOFF.md fact 2); the LINK is what crosses.
  states    {state name: {entered_via: [element_id...], elements: [element_id...], n_seen, last_seen}}
             -- a page is not one control set. `Dependency Analysis` is disabled with no row
             ticked and enabled after one is; `Explain Changes` opens a panel that is `Thinking...`,
             then streaming (a `Stop` button), then done (a `Copy` button). The default state is
             called "default" and is never written.
  rung      {kw, args, kwargs, name?, body?, why, score, n_verified, n_failed, n_unverified,
             last_verdict, last_seen, failure_signal, origin: session|seed|repair|l0}
  rung_stats host/org-level {family: {kw: {won, failed}}} merged from lessons.jsonl
  patterns  names of library keywords that applied here
  flows     {flow_name: [step numbers]}
  predictions {action_ref: {predicted, observed, status, confirmations, mismatches, field_families,
             last_seen}} -- the org map's quick-action rendering prediction, and whether the live
             DOM confirmed it (S37). A CONFIRMED prediction is what the next session reads before
             the click, so the first candidate is right on the first visit of the day.
Everything is merged, never overwritten: a second visit adds counts.
"""
from __future__ import annotations

import glob
import json
import os
import re
import time
from typing import Any, Iterable

try:                                  # package import (tests, CLI) or flat sys.path (server)
    from . import keys as K
    from . import match as M
    from . import scope as SCOPE
except ImportError:                   # pragma: no cover
    import keys as K  # type: ignore
    import match as M  # type: ignore
    import scope as SCOPE  # type: ignore

STABLE_ATTRS = ("name", "aria-label", "title", "data-testid", "data-test-id", "item", "field",
                "field-label", "data-target-selection-name", "placeholder", "id")
# `_ngcontent-ng-<hash>` / `_nghost-ng-<hash>` (Angular view encapsulation) and `data-v-<hash>`
# (Vue scoped styles) are per-BUILD markers: they change on every release of the app. They are
# framework-universal, like the Aura `\d+:\d+` and `lgcp-` shapes already here. Measured 2026-09-12
# on robotic.copado.com, an Angular app: the Artifacts tab's identity xpath was built on
# `@_ngcontent-ng-c540179591` and resolved 0 elements live.
UNSTABLE_VALUE = re.compile(
    r"^\d+:\d+$|^[a-f0-9]{16,}$|^lgcp-|^input-\d+$|^_ngcontent-|^_nghost-|^data-v-[0-9a-f]{6,}$")
VERIFIED = {"VERIFIED-PASS", "PASS-GUARDED"}


def now() -> float:
    return time.time()


def _iso(ts: float | None) -> str | None:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts)) if ts else None


def stable_attrs(attrs: dict | None) -> dict:
    out = {}
    for k in STABLE_ATTRS:
        v = (attrs or {}).get(k)
        if v and isinstance(v, str) and not UNSTABLE_VALUE.match(v):
            out[k] = v
    return out


def element_id(family: str | None, label: str | None, container: str | None, attrs: dict | None,
               drop_container: bool = False, tag: str | None = None) -> str:
    """Structural identity of a control on a page: family + label + container + best stable attr +
    the real HTML tag. Not a counter, not a hash of position -- the same control gets the same id
    on the next visit.

    THE TAG JOINS THE IDENTITY (D20, 2026-09-20; F122). Before this, a `button` and an `a` that
    agreed on family/label/container/attr collided at this function's return value and silently
    became one element -- the second write's tag overwriting the first's, against this docstring's
    own promise and the `tag=` doctrine (`ClickItem` silently finds nothing without an explicit
    `tag=`, and it must be the REAL HTML tag). Measured on the live store, 2026-09-19: 349 elements
    are `family=button` with `tag=a`, and 10 of 2,221 distinct keys occur with more than one tag
    across records -- exactly the fold this closes. `tag` defaults to `None` (an empty trailing
    segment) so a caller that does not know the shape yet (a driven `--op kw` step) still mints a
    stable id; `identify_control`'s label/family fallback -- not a string match on this id -- is
    what still finds that element again later, shaped or not. Existing on-disk keys are re-keyed by
    `migrate_keys.py --steps tag`, never silently orphaned.

    `drop_container` omits the container from the identity, for a SINGLE-SURFACE app
    (keys.SINGLE_SURFACE_HOSTS) where the "container" is not structure at all but whatever prose
    happened to surround the control on that visit.

    MEASURED 2026-09-12, robotic.copado.com: the container was the chat/message node text, so ONE
    tab button existed SEVEN times --

        button|Artifacts|
        button|Artifacts|Explorer|
        button|Artifacts|Arguments|
        button|Artifacts|Planning and Task Tracking|
        button|Artifacts|Deployed - Ready for Testing: Vehicle__c Object and Configur|
        button|Artifacts|Success - Vehicle__c Object and Configuration Deployed|
        button|Artifacts|(X) Build/Validation Failure Report|

    385 of 701 elements (55%) carried run/story text in their key, 138 labels occurred more than
    once, and **34 of the 37 live VERIFIED-PASS verdicts were attached to ids that can never recur**
    -- only the 3 with an EMPTY container were durable. The docstring's promise above was measured
    FALSE for that page, which is the whole point of the page-object asset: never relearn a known
    page. Scoped to single-surface hosts so the 144-capture Salesforce corpus is untouched, where a
    container genuinely IS structure (a section, a legend, a related-list card)."""
    sa = stable_attrs(attrs)
    attr = ""
    for k in STABLE_ATTRS:
        if k in sa:
            attr = f"{k}={sa[k]}"
            break
    norm = lambda s: re.sub(r"\s+", " ", (s or "")).strip().strip("*").strip()[:60]
    parts = [family or "generic", norm(label), "" if drop_container else norm(container), attr,
             (tag or "")]
    return "|".join(parts)


# THE SENTINEL, not a state name. A session step whose `state` is this named NO state; it is what
# `merge_session` tests against before filing a member. Keeping it distinct from BASE_STATE is B1's
# fix: one word meant both "no state" and "the page itself", and the writer and the reader each
# picked a different one (0 records named `default`, 18 named `page`, 106 of 198 capture-index
# entries keyed `default` and unreachable -- docs/audit/challenge-2026-09-19b/scope-held-out.md).
DEFAULT_STATE = "default"
# THE ONE NAME of the base state, everywhere: records, capture index, writers, readers.
BASE_STATE = SCOPE.BASE_STATE
is_base_state = SCOPE.is_base_state
# A step that carries an ELEMENT. `verify` is here and deliberately NOT in LEADS_TO_KINDS: a
# VerifyText proves a label was on the page, it never took you anywhere.
ELEMENT_KINDS = ("click", "type", "change", "key", "verify")
# The implicit "this click went somewhere" inference runs on these step kinds only; an EXPLICIT
# `step["effect"]` is honoured on any step that produces an element.
LEADS_TO_KINDS = ("click", "type", "key")
EFFECT_KINDS = ("nav", "modal", "panel", "state")


def kw_step_kind_family(kw: str | None) -> tuple[str | None, str | None]:
    """(event kind, control family) for a keyword NAME -- snake_case or CamelCase.

    A `--op kw --session NAME` step records only the keyword it ran; there is no DOM event behind
    it, so the shape of the action has to be read off the keyword. Unknown keyword -> (None, None),
    which registers the page visit and nothing else: a guessed family would put a wrong rung in
    front of a real one.
    """
    flat = re.sub(r"[^a-z]", "", (kw or "").lower())
    if not flat:
        return None, None
    if flat in ("goto", "openbrowser", "navigate", "navigateto"):
        return "nav", None
    if flat.startswith("verify"):
        return "verify", "text"
    if flat in ("picklist", "combobox", "selectfrom", "selectlist"):
        return "change", "combobox"
    if flat in ("clickcheckbox", "setcheckbox"):
        return "change", "checkbox"
    if flat.startswith("type") or flat in ("inputtext", "settext", "settextfield"):
        return "type", "input"
    if flat.startswith("click"):
        return "click", "button"
    return None, None


def normalise_step(step: dict) -> dict:
    """A kept session written by `up.py --op kw --session NAME` in the shape merge_session reads.

    MEASURED 2026-09-15 on `docs/recorder/sessions/cicd-demo/df26-commit-experience-2026-09-15.json`:
    35 steps, every one silently skipped as "no url". `--op kw` writes
    `event = {kind: "kw", control_family: "kw-driven", host: <the full page URL>,
    synthetic: "op-kw-session"}` (tools/interop/up.py) -- the URL is under `host`, the kind is the
    literal string `kw`, and there is no `target`/`context` because no DOM event happened. That
    is the shape a LIVE drive produces, so it is the shape the store has to accept; anything else
    means the day's recording lands nowhere. The keyword name carries the action and the family
    (`kw_step_kind_family`) and `chosen.args[0]` carries the label. Any other step shape is
    returned untouched.
    """
    ev = step.get("event") or {}
    if ev.get("kind") != "kw":
        return step
    ev = dict(ev)
    chosen = step.get("chosen") or {}
    kind, family = kw_step_kind_family(chosen.get("kw"))
    args = chosen.get("args") or []
    label = str(args[0]) if args else ""
    # `url` = the page the keyword ran ON (written by up.py since 2026-09-15); older kept files
    # only carry `host`, which is the page it landed on -- the best available then.
    ev["url"] = ev.get("url") or ev.get("host")
    ev["kind"] = kind or "kw"
    if ev.get("ts") is None and isinstance(step.get("ts"), (int, float)):
        ev["ts"] = step["ts"]
    if kind in ELEMENT_KINDS and label:
        ev["target"] = {"tag": None, "text": label, "attrs": {}}
        ev["context"] = {"family": family, "labels": [label],
                         "interactive": {"tag": None, "text": label, "attrs": {}},
                         "container": {"kind": "kw-driven", "label": ""}}
    out = dict(step)
    out["event"] = ev
    return out


def step_effect(step: dict, this_key: str | None, next_key: str | None,
                landed_key: str | None = None) -> tuple[str | None, str | None]:
    """(kind, target) for one step -- what did acting on this control DO?

    An explicit `step["effect"] = {"kind": nav|modal|panel|state, "target": ...}` wins, because
    only the driver knows that a click opened a modal rather than navigating. Otherwise the
    inference: the step LANDED on a different page key (`event.landed_url` when the driver
    recorded it, else the next step's own page), so it was a nav there.

    Returns (None, None) when nothing can be said -- the third state, never a guessed "nav".
    """
    eff = step.get("effect") or {}
    kind, target = eff.get("kind"), eff.get("target")
    if kind in ("modal", "panel", "state") and target:
        return kind, target
    if kind == "nav" and target:
        return "nav", target
    dest = landed_key or next_key
    if dest and this_key and dest != this_key:
        return "nav", dest
    return None, None


def step_enabled(step: dict, attrs: dict | None) -> bool | None:
    """Tri-state: True/False only on a real signal (an explicit `step["enabled"]`, or a
    disabled/aria-disabled attribute on the target). No signal -> None, and the caller writes
    nothing rather than claiming a control was enabled."""
    v = step.get("enabled")
    if isinstance(v, bool):
        return v
    a = attrs or {}
    if str(a.get("aria-disabled") or "").lower() == "true":
        return False
    if "disabled" in a and a.get("disabled") not in (None, False, "false"):
        return False
    return None


def same_control_id(rec: dict, eid: str, family: str | None, label: str | None,
                    container: str | None) -> str:
    """The id an already-known control has when its LABEL moved but the control did not.

    Measured 2026-09-15 on na.devops.copado.com: `Dependency Analysis` becomes
    `Dependency Analysis (2)` once it has run. `element_id` puts the label in the identity, so the
    relabelled button would become a SECOND element with an empty ladder -- the page object would
    forget the verified locator exactly when the page changed state. `pom.match` already owns the
    rule that a trailing live count is not part of a label; this reuses that normaliser (never a
    second copy of it) and additionally demands an equal container and a compatible family, so two
    genuinely different controls that merely normalise alike are never merged. A control whose RAW
    label is already identical is left alone: those are different elements by container/attrs.
    """
    els = rec.get("elements") or {}
    if eid in els:
        return eid
    want = M.norm_label(label)
    if not want:
        return eid
    wc = M.norm_label(container)
    for other_id, e in els.items():
        if (e.get("label") or "") == (label or ""):
            continue
        if M.norm_label(e.get("label")) != want or M.norm_label(e.get("container")) != wc:
            continue
        if not M.families_compatible(family, e.get("family")):
            continue
        return other_id
    return eid


# ------------------------------------------------- TWO WRITERS, ONE CONTROL (F70, 2026-09-19)
# A control DRIVEN through `merge_session` (`--op kw`) carries no DOM shape: the keyword name is
# all there is, so `normalise_step` mints `button|Object Fields||` -- family read off the keyword,
# tag null, container empty. The capture writer parses the SAME live control and mints
# `link|Object Fields|Tabs|id=customTab__item` -- family link, tag `a`, the real attrs. Nothing
# folded the two, so the store held one control twice and each half carried half the truth:
#
#   button|Object Fields||                      tag null, family button, opens {object-fields: 1},
#                                               ladder: click_text PASS-GUARDED  <- the BEHAVIOUR
#   link|Object Fields|Tabs|id=customTab__item  tag "a", family link, source capture, no opens
#
# Measured 2026-09-19 on copado-trial's Data Template page: 11 of 13 pre-existing controls got a
# twin (docs/recorder/evidence/datatemplate-states-filled-2026-09-19.md 6b, ledger F70). It is not
# tidiness: CLAUDE.md is explicit that `ClickItem` silently finds nothing without the REAL tag, and
# a reader that follows `opens` gets the untagged, mis-familied half.
#
# THE FIX IS `identify_control` BELOW, NOT A FOLD: all three writers ask it what a control is
# CALLED on this page before they write, so the second name is never minted. `fold_driven_twins` /
# `migrate_twins.py` exist ONLY to clean up the twins the old writers already put on disk.
#
# The fold classes are deliberately NARROWER than `match.families_compatible` (which exists for a
# tolerant lookup, where a wrong hit costs a re-derive). A fold DESTROYS an identity, so two
# controls merge only inside one class, and an unknown family matches only itself.
DRIVEN = "driven"
TWIN_FAMILY_CLASS = {
    "button": "click", "link": "click", "tab": "click", "menuitem": "click", "a": "click",
    "click": "click",
    "input": "type", "input_field": "type", "textarea": "type", "lookup": "type", "search": "type",
    "picklist": "choice", "combobox": "choice", "dropdown": "choice", "select": "choice",
}
# Fields the surviving element may take from the folded one -- only where its own is EMPTY, and
# never a narrative field (`note`, `verdict`, `source`): a capture-stamp placeholder's note says
# "its shape has never been captured", which becomes a lie the moment the real shape lands.
FOLD_FILL_FIELDS = ("label", "family", "container", "tag", "attrs", "shape", "shadow_depth")


def twin_families_compatible(a: str | None, b: str | None) -> bool:
    """True only when two families are the same, or map to the same fold class. A missing family on
    EITHER side is False -- the third state is "do not fold", never a guessed merge."""
    fa, fb = (a or "").casefold(), (b or "").casefold()
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    ca = TWIN_FAMILY_CLASS.get(fa)
    return bool(ca) and ca == TWIN_FAMILY_CLASS.get(fb)


def is_shapeless(el: dict | None) -> bool:
    """A control the store knows only by name: no real HTML tag and no stable attribute. That is
    exactly what a `--op kw` driven step and a capture-stamp placeholder produce."""
    if el is None:
        return False
    return not el.get("tag") and not stable_attrs(el.get("attrs"))


def identify_control(rec: dict, label: str | None, family: str | None, attrs: dict | None = None,
                     tag: str | None = None, container: str | None = "",
                     drop_container: bool = False, exclude: str | None = None) -> str:
    """**THE id for this control on this page.** Every writer calls this BEFORE it writes.

    The fix for F70 is not another fold: it is that the three writers stop disagreeing about what
    a control is CALLED. `merge_session` (a driven `--op kw` step), `apply_capture_stamp` (the
    capture path) and `review_table.writeback` all resolve through here, so a control written by
    any of them in any order lands on ONE element that ends up holding the tag, the attrs, the
    `opens`/`leads_to` and the verdicts together.

    The rule is the store's one match rule (`pom.match`): the label normalised (whitespace, case,
    a trailing live count -- `Dependency Analysis (2)` is the same button as `Dependency Analysis`)
    and the family in one compatibility class (`TWIN_FAMILY_CLASS`). Two narrowings, each paid for:

    * **Exactly one candidate, or it mints.** `match.find_control` breaks a tie by verified rungs
      because a wrong hit on a READ costs a re-derive; a wrong hit on a WRITE merges two real
      controls forever. A page with three `Edit` buttons cannot say which one was driven, so the
      driven step keeps its own id and `migrate_twins.py` REPORTS the ambiguity.
    * **Two SHAPED controls are never merged.** When the caller brings a tag or a stable attribute
      and the candidate has one too, they are two structural identities (`button|Edit|Deployment
      Options|` and `button|Edit|Main Object Filter|`) and stay two. The match only ever joins a
      shapeless half to a shaped one -- which is exactly the driven/captured split.

    An UNKNOWN family on either side matches on the label alone, as the capture stamp always has:
    the stamp names a control it has never seen the shape of, so `None` there means "not known",
    not "not a button". (`twin_families_compatible` keeps saying False for a missing family --
    that is the MIGRATION's rule, where a fold is destructive and an unknown must not be guessed
    at.) `exclude` lets `fold_driven_twins` ask the same question of an element already in the
    record ("what else is this control called here?") without matching itself.
    """
    els = rec.get("elements") or {}
    base = element_id(family, label, container, attrs, drop_container, tag)
    if base in els and base != exclude:
        return base
    relabelled = same_control_id(rec, base, family, label, container)
    if relabelled in els and relabelled != exclude:
        return relabelled
    want = M.norm_label(label)
    if not want:
        return base
    caller_shaped = bool(tag) or bool(stable_attrs(attrs))
    hits = [i for i, e in els.items()
            if i != exclude and M.norm_label(e.get("label")) == want
            and (twin_families_compatible(family, e.get("family"))
                 if (family and e.get("family")) else True)
            and not (caller_shaped and not is_shapeless(e))]
    if len(hits) != 1:
        return base
    if caller_shaped and hits[0] != base and exclude is None:
        # The store knew this control only by NAME and the caller brings its shape. Keep ONE
        # element and give it the id the shape earns: `button|Object Fields||` becomes
        # `link|Object Fields|Tabs|id=customTab__item`, with every `links[].via` and state
        # membership re-pointed. This is a RENAME of one element, not a merge of two -- and it is
        # what makes identification idempotent: without it the next capture of the same page would
        # find a now-SHAPED element under a shapeless id, decline to claim it, and mint the twin
        # all over again. The id also stops lying about the tag, which `ClickItem` needs.
        rename_element(rec, hits[0], base)
        return base
    return hits[0]


def rename_element(rec: dict, old_id: str, new_id: str) -> str:
    """Move one element to a new id and re-point every reference to it. No merge: if `new_id` is
    already taken the record is left alone and `old_id` comes back (the caller is then looking at
    two real controls, which `identify_control` never merges)."""
    els = rec.get("elements") or {}
    if old_id not in els or new_id in els or old_id == new_id:
        return old_id
    el = els.pop(old_id)
    el["renamed_from"] = sorted(set((el.get("renamed_from") or []) + [old_id]))
    els[new_id] = el
    for link in (rec.get("links") or {}).values():
        via = link.get("via") or []
        if old_id in via:
            link["via"] = list(dict.fromkeys([new_id if v == old_id else v for v in via]))
    for st in (rec.get("states") or {}).values():
        for name in ("entered_via", "elements"):
            lst = st.get(name) or []
            if old_id in lst:
                st[name] = list(dict.fromkeys([new_id if v == old_id else v for v in lst]))
    return new_id


def _merge_ladders(dst: dict, src: dict) -> None:
    """Rung-by-rung, counters SUMMED -- the driven half is where the VERIFIED rungs live
    (`click_text` PASS-GUARDED on the Data Template tabs), so a fold that dropped them would throw
    away the only live evidence on the page. A capture rung has no `_key`; `rung_key` computes the
    same identity for both writers."""
    ladder = dst.setdefault("ladder", [])
    index = {(r.get("_key") or rung_key(r)): r for r in ladder}
    for r in src.get("ladder") or []:
        k = r.get("_key") or rung_key(r)
        cur = index.get(k)
        if cur is None:
            cur = dict(r)
            cur["_key"] = k
            ladder.append(cur)
            index[k] = cur
            continue
        for c in ("n_verified", "n_failed", "n_unverified"):
            cur[c] = int(cur.get(c) or 0) + int(r.get(c) or 0)
        if (r.get("last_seen") or "") >= (cur.get("last_seen") or ""):
            for f in ("last_verdict", "last_seen", "failure_signal"):
                if r.get(f) is not None:
                    cur[f] = r[f]
    dst["ladder"] = order_ladder(ladder)


def fold_element(rec: dict, src_id: str, dst_id: str) -> bool:
    """Move everything the twin `src_id` knows onto `dst_id`, re-point every reference, delete it.

    Carried: `opens`, `leads_to`, `effects` (counts bumped), `n_seen` (summed), `evidence` (unioned),
    the ladder (rung counters summed), per-element `states` membership and `overrides`, and any
    FOLD_FILL_FIELDS the survivor is missing. Re-pointed: every `links[].via` and every
    `states[].entered_via` / `states[].elements` entry -- a state whose opener was the driven twin
    would otherwise name a control that no longer exists. `folded_from` records the id that went,
    so the fold is never silent."""
    els = rec.get("elements") or {}
    src, dst = els.get(src_id), els.get(dst_id)
    if src is None or dst is None or src_id == dst_id:
        return False
    for field in ("opens", "leads_to", "effects"):
        for k, v in (src.get(field) or {}).items():
            _bump(dst.setdefault(field, {}), k, int(v or 0))
    dst["n_seen"] = int(dst.get("n_seen") or 0) + int(src.get("n_seen") or 0)
    ev = sorted(set((dst.get("evidence") or []) + (src.get("evidence") or [])))
    if ev:
        dst["evidence"] = ev
    _merge_ladders(dst, src)
    for name, seen_as in (src.get("states") or {}).items():
        dst.setdefault("states", {}).setdefault(name, seen_as)
    for o in src.get("overrides") or []:
        _append_unique(dst.setdefault("overrides", []), o)
    for f in FOLD_FILL_FIELDS:
        if not dst.get(f) and src.get(f):
            dst[f] = src[f]
    if (src.get("last_seen") or "") > (dst.get("last_seen") or ""):
        dst["last_seen"] = src["last_seen"]
    dst["folded_from"] = sorted(set((dst.get("folded_from") or []) + [src_id]))
    for link in (rec.get("links") or {}).values():
        via = link.get("via") or []
        if src_id in via:
            link["via"] = list(dict.fromkeys([dst_id if v == src_id else v for v in via]))
    for st in (rec.get("states") or {}).values():
        for name in ("entered_via", "elements"):
            lst = st.get(name) or []
            if src_id in lst:
                st[name] = list(dict.fromkeys([dst_id if v == src_id else v for v in lst]))
    del els[src_id]
    return True


def fold_driven_twins(rec: dict) -> list[dict]:
    """MIGRATION ONLY: the twins already on disk, from before every writer went through
    `identify_control`. Nothing in the write path calls this -- new writes cannot produce a twin,
    so this exists to clean up what the old writers left (`migrate_twins.py`).

    The survivor is decided by `identify_control` itself, asked of the shapeless element with
    `exclude=<itself>`: "what else is this control called here?". An answer that is the element's
    own id means nothing else matches, and nothing is folded. Returns one row per fold
    (`{"from", "into", "label", "family", "into_family"}`)."""
    folded = []
    for src_id in list((rec.get("elements") or {}).keys()):
        src = (rec.get("elements") or {}).get(src_id)
        if src is None or not is_shapeless(src):
            continue
        dst_id = identify_control(rec, src.get("label"), src.get("family"),
                                  attrs=src.get("attrs"), tag=src.get("tag"),
                                  container=src.get("container") or "", exclude=src_id)
        dst = (rec.get("elements") or {}).get(dst_id)
        if dst is None or dst_id == src_id or not dst.get("tag"):
            continue
        dst_family = dst.get("family")
        if fold_element(rec, src_id, dst_id):
            folded.append({"from": src_id, "into": dst_id, "label": src.get("label"),
                           "family": src.get("family"), "into_family": dst_family})
    return folded


def _md(s) -> str:
    """A page key contains `|`, which ends a markdown table cell. Escape it, or the render eats
    the rest of the row silently -- exactly the class of failure no_silent_truncation.py names."""
    return str(s if s is not None else "").replace("|", "\\|")


def leads_to_cell(e: dict) -> str:
    bits = [f"-> {k} ×{v}" for k, v in sorted((e.get("leads_to") or {}).items())]
    bits += [f"opens {k} ×{v}" for k, v in sorted((e.get("opens") or {}).items())]
    return ", ".join(bits)


def _bump(d: dict, key: str, by: int = 1) -> None:
    d[key] = int(d.get(key) or 0) + by


def _append_unique(lst: list, v) -> None:
    if v is not None and v not in lst:
        lst.append(v)


def page_state(rec: dict, name: str) -> dict:
    return rec.setdefault("states", {}).setdefault(
        name, {"entered_via": [], "elements": [], "n_seen": 0, "last_seen": None})


# --------------------------------------------------------------------- the CAPTURE STATE STAMP
UNKNOWN_ENTERED_VIA = "unknown"
# A state you LEAVE by dismissing it. A tab is not one: you do not close a tab to reach another.
OVERLAY_KINDS = ("modal", "panel")
CLOSER_LABELS = ("close", "cancel", "cancel and close", "dismiss", "x", "close this window")


def _norm_label(s: str | None) -> str:
    return " ".join(str(s or "").split()).casefold()


def _scope_for_capture(rec: dict, state: str | None, capture_path: str | None,
                       id_map: dict | None, driven_tab: str | None = None,
                       base_path: str | None = None) -> tuple[dict | None, set, str | None]:
    """(scopes by FINAL element id, chrome ids to keep OUT of the state, note).

    THE ONE PLACE scope is computed (2026-09-19). Both capture writers -- `pom_asset.build_record`
    and `review_table.writeback` -- reach it through `apply_capture_stamp`, so the two cannot
    disagree about what "inside this state" means.

    `id_map` maps the RAW id a capture's control mints (`element_id(family,label,container,attrs)`)
    to the id the record actually files it under, because `identify_control` may fold a control
    onto an element the store already holds under another name (F70's twin fold). Two raw controls
    can fold onto ONE element -- one inside the subtree and one outside; `own` wins, because the
    member demonstrably IS in the state's own container.

    Returns `(None, set(), note)` for COULD-NOT-CHECK: no capture to read, or a subtree the ladder
    refuses to guess at. The caller then writes no `scope` key at all -- never `own` by default.
    """
    if not capture_path or not os.path.exists(capture_path):
        return None, set(), "no capture behind this stamp"
    try:
        html = open(capture_path, errors="replace").read()
    except OSError as e:                                    # pragma: no cover - unreadable file
        return None, set(), "capture unreadable: %s" % e
    kind = ((rec.get("states") or {}).get(state or "") or {}).get("kind")
    # The inline-edit rung needs the page's own base capture to diff against; `find_base_capture`
    # picks it out of the same crawl directory by its header, and a caller that already knows the
    # path (migrate_scope has the whole capture index) hands it in.
    base_html = None
    if base_path is None and capture_path:
        base_path = SCOPE.find_base_capture(capture_path)
    if base_path and os.path.exists(base_path) and \
            os.path.abspath(base_path) != os.path.abspath(capture_path):
        try:
            base_html = open(base_path, errors="replace").read()
        except OSError:                                     # pragma: no cover - unreadable file
            base_html = None
    raw = SCOPE.scopes_for_capture(html, state=state, kind=kind,
                                   element_id=element_id, stable_attrs=stable_attrs,
                                   driven_tab=driven_tab, base_html=base_html)
    chrome_raw = SCOPE.transient_ids(html, element_id=element_id, stable_attrs=stable_attrs)
    m = id_map or {}
    chrome = {m.get(k, k) for k in chrome_raw}
    if raw is None:
        return None, chrome, "the state's own subtree could not be resolved in this capture"
    out: dict = {}
    for k, v in raw.items():
        fid = m.get(k, k)
        if out.get(fid) != SCOPE.OWN:
            out[fid] = v
    return out, chrome, None


def apply_capture_stamp(store: "Store", rec: dict, eids: list[str], *, state: str | None,
                        entered_via: str | None, host_url: str | None, org: str | None = None,
                        stamp: str | None = None, evidence: str | None = None,
                        capture_path: str | None = None, id_map: dict | None = None) -> dict:
    """Land one capture's state stamp -- the ONE writer both pom_asset.build_record and
    review_table.writeback go through, so the two cannot drift.

    The user's decision (2026-09-18): "What a capture lacks is a stamp saying which page state it
    was taken in and which control got it there. Add that one field and every capture becomes a
    state." Before this, `build_record` and `writeback` wrote `states`/`links`/`opens`/`leads_to`
    NEVER -- not once across 3,394 controls -- so 76 pages were recorded as one flat control set
    and 20 of 25 routed modals had no route to them (docs/audit/pom-states-and-modals-2026-09-18.md
    G1/G2, section 3 W2 and W3).

    Two shapes, and the difference is the whole point:

    * **routed** modal (`host_url` resolves to a DIFFERENT page key -- a quick action,
      `/lightning/o/<Obj>/new`): the modal's own page key holds its controls FLAT, and the HOST
      page gets the `links` edge plus `opens`/`leads_to` on the opening control. No state is
      written on the modal's own key -- that is exactly the defect the audit named at 20:08
      (`fsc7f|/lightning/o/Account/new` carrying a state literally called `New Account` with
      `entered_via` empty: a state nobody can enter, and still no link from the list view).
    * **in-page** modal / panel / tab state (`host_url` is this same page, or absent): the state
      is written HERE, with the opening control in `entered_via` and the capture's controls as its
      members.

    An `entered_via` of `unknown` (nothing could be derived) still files the controls and still
    names the state, and marks the state `entered_via_unknown` so `audit_states.py` reports it
    under `states_with_no_opening_control` rather than letting it pass as complete. Third state,
    stated -- never a guessed opener.

    Returns what it did, so the caller can print it.
    """
    out = {"state": SCOPE.normalize_state(state), "entered_via": entered_via or UNKNOWN_ENTERED_VIA,
           "host_url": host_url or "", "wrote": [], "gap": None}
    stamp = stamp or _iso(now())
    known_via = bool(entered_via) and entered_via != UNKNOWN_ENTERED_VIA
    named_state = not is_base_state(state)
    this_key = (rec.get("page") or {}).get("key")

    host_key, host_rec = None, None
    if known_via and host_url:
        hk = store.key_for(host_url, org)
        if hk.get("host"):
            host_key = hk["key"]
            host_rec = rec if host_key == this_key else store._open(hk)

    routed = bool(host_key) and host_key != this_key
    if routed:
        # the opening control lives on the HOST page. Look it up by visible label; a capture of the
        # host may never have been built, in which case the control is recorded with what is
        # actually known (its label) and NOTHING is invented about its shape -- a fabricated
        # family/tag would put a guessed rung in front of a real one.
        # WRITER 2 of 3 (F70): the capture path asks `identify_control` what this control is called
        # on the host page, so a stamp never mints a second name for a control already there.
        els = host_rec.setdefault("elements", {})
        eid = identify_control(host_rec, entered_via, None)
        if eid not in els:
            els[eid] = {"family": None, "label": entered_via, "container": "", "attrs": {},
                        "tag": None, "ladder": [], "effects": {}, "n_seen": 0,
                        "source": "capture-stamp", "verdict": "COULD-NOT-CHECK",
                        "evidence": [evidence] if evidence else [],
                        "note": "named by a capture's state stamp as the control that opens "
                                "%s; its shape has never been captured" % (state or this_key)}
        el = els[eid]
        el["n_seen"] = (el.get("n_seen") or 0) + 1
        el["last_seen"] = stamp
        opens_title = state if named_state else ((rec.get("page") or {}).get("title") or this_key)
        _bump(el.setdefault("opens", {}), opens_title)
        _bump(el.setdefault("leads_to", {}), this_key)
        link = host_rec.setdefault("links", {}).setdefault(
            this_key, {"via": [], "n": 0, "opens": opens_title})
        link["opens"] = link.get("opens") or opens_title
        _append_unique(link["via"], eid)
        link["n"] = (link.get("n") or 0) + 1
        host_rec["last_seen"] = stamp
        if host_rec is not rec:
            store.put(host_rec)
        out["wrote"] += ["links[%s] on %s" % (this_key, host_key), "opens on %r" % entered_via]
        out["host_key"] = host_key
        return out

    # THE BASE STATE IS A STATE (2026-09-19). Until now a capture of the page itself wrote nothing
    # at all, so copado-trial's Data Template held 4 base-state members while its landing capture
    # parsed 180 controls: a step "on the hierarchy of that general page" had almost nothing to
    # resolve against, and the page's own controls lived only inside the tab and modal states that
    # had leaked them. The base state is entered by NAVIGATING to the page, so it never takes an
    # `entered_via` -- the old `page` state's opener was `button|Dismiss||`, a toast dismissal.
    state_name = state if named_state else BASE_STATE
    # The label the state was entered via is what picks the right tabset on a two-tabset record
    # page -- 36 of 60 held-out captures have two selected tabs and no tab state on one of them
    # could be scoped before (held-out audit 2026-09-19). The state's own name is the fallback: the
    # crawler names a tab state after the tab.
    scopes, chrome, scope_note = _scope_for_capture(
        rec, state_name, capture_path, id_map,
        driven_tab=(entered_via if known_via else None) or (state if named_state else None))

    ps = page_state(rec, state_name)
    ps["n_seen"] = (ps.get("n_seen") or 0) + 1
    ps["last_seen"] = stamp
    if not named_state:
        ps.setdefault("kind", "page")
    # `eids` is a capture's control list in DOM order and two controls can fold onto ONE element
    # (F70's twin fold), so every count below is over the UNIQUE members -- a per-occurrence count
    # reported 8 own controls where the page has 7.
    uniq = list(dict.fromkeys(eids))
    filed = 0
    for eid in uniq:
        # A TOAST IS NOT A MEMBER OF ANYTHING. `button|Dismiss|Just so you know|` was a member of
        # NINE states on the probe page and outside every one of their subtrees: a transient
        # notification that happened to be on screen when the capture was taken. The element is
        # still recorded; it is simply never filed under a state.
        if eid in chrome:
            continue
        _append_unique(ps["elements"], eid)
        filed += 1
        el = (rec.get("elements") or {}).get(eid)
        if el is None:
            continue
        seen_as = {"label": el.get("label")}
        if scopes is not None and eid in scopes:
            seen_as["scope"] = scopes[eid]
        el.setdefault("states", {})[state_name] = seen_as
    if scopes is not None:
        ps["scope_from"] = evidence or os.path.basename(capture_path or "")
    elif scope_note:
        ps["scope_unknown"] = scope_note
    if known_via and named_state:
        cand = identify_control(rec, entered_via, None)
        via_eid = cand if cand in (rec.get("elements") or {}) else None
        # A CLOSER IS NOT AN OPENER (2026-09-19). `object-fields` had
        # `button|Close|GarzAI slockard cred Preview|title=Close` in its `entered_via`: the crawler
        # returned to the tab by CLOSING the Preview modal, and the store read that as "this
        # control opens object-fields". The rule is deliberately NARROW -- a closing LABEL on a
        # control that is `own` in an OVERLAY state (modal/panel). Both halves are needed: the
        # Preview button is `own` in the `details` TAB and genuinely opens the modal, so "own in
        # another state" alone would have filed a real opener as a closer (measured, first run).
        closes = None
        if via_eid and _norm_label(entered_via) in CLOSER_LABELS:
            for other, s in ((rec["elements"][via_eid].get("states") or {})).items():
                if other == state_name or (s or {}).get("scope") != SCOPE.OWN:
                    continue
                if ((rec.get("states") or {}).get(other) or {}).get("kind") in OVERLAY_KINDS:
                    closes = other
                    break
        if closes:
            _append_unique(page_state(rec, closes).setdefault("closed_via", []), via_eid)
            out["wrote"].append("closed_via[%s] += %r (not an opener of %s)"
                                % (closes, via_eid, state_name))
            if not ps["entered_via"]:
                ps["entered_via_unknown"] = True
                out["gap"] = ("state %r was entered by closing %r -- no opening control is known; "
                              "audit_states.py names it under states_with_no_opening_control"
                              % (state_name, closes))
        else:
            _append_unique(ps["entered_via"], via_eid or entered_via)
            if via_eid:
                _bump((rec["elements"][via_eid]).setdefault("opens", {}), state_name)
            ps.pop("entered_via_unknown", None)
    elif named_state:
        ps["entered_via_unknown"] = True
        out["gap"] = ("state %r has no opening control -- audit_states.py names it under "
                      "states_with_no_opening_control" % state)
    out["state"] = state_name
    out["wrote"].append("states[%s] += %d control(s)" % (state_name, filed))
    if chrome:
        out["chrome_not_filed"] = sorted(chrome & set(uniq))
    out["scope"] = ("COULD-NOT-CHECK: %s" % scope_note if scopes is None else
                    {"own": sum(1 for e in uniq if scopes.get(e) == SCOPE.OWN),
                     "shell": sum(1 for e in uniq if scopes.get(e) == SCOPE.SHELL),
                     "absent": sum(1 for e in uniq if e not in scopes)})
    return out


def absorb_stamp_placeholder(rec: dict, eid: str, label: str | None) -> str:
    """Fold a `capture-stamp` placeholder into the REAL element once a capture parses that control.

    `apply_capture_stamp` has to name the opening control on a HOST page that may never have been
    captured, so it records what it actually knows -- the visible label -- as an element with no
    family, tag or ladder. When the host page IS captured later, the parser mints a different id
    from the real shape and the store ends up holding the control TWICE: one entry with the
    verified ladder and no `opens`, one with the `opens` and no way to click it. A reader looking
    up "New" gets whichever it hits first, and both answers are half right -- this codebase's
    signature failure in miniature.

    CAUGHT LIVE 2026-09-18 on slockard's Account list view, by building the routed New Account
    modal and then the list view itself into a scratch store: `button|New|Accounts|title=New`
    (2 rungs, no opens) beside `generic|New||` (opens `New Account`, 0 rungs). Everything the
    placeholder carries -- `opens`, `leads_to`, its `n_seen`, and every `links[].via` and state
    membership pointing at it -- moves onto the real element, and the placeholder is deleted.
    Returns `eid`, so the caller can use it inline.

    F70 (2026-09-19) did NOT add a second fold here. A placeholder only exists because
    `apply_capture_stamp` may have to name a control on a page nothing has captured yet; every
    writer now asks `identify_control` what a control is called before it writes, so the
    driven/captured split this used to be widened to cover cannot be minted in the first place.
    The body moved onto the shared `fold_element`, which also carries the ladder.
    """
    els = rec.get("elements") or {}
    tgt = els.get(eid)
    if tgt is None:
        return eid
    for pid, p in list(els.items()):
        if pid == eid or p.get("source") != "capture-stamp":
            continue
        if _norm_label(p.get("label")) != _norm_label(label):
            continue
        fold_element(rec, pid, eid)
    return eid


def note_layout_hash(rec: dict, layout_hash: str | None, record_type: str | None) -> None:
    """Record WHICH LAYOUT this visit rendered, as a fact on the page (D17, user 2026-09-19).

    Until today the hash was a key SEGMENT, so a page rendered under two org-map builds was two
    records and the question "which layout is this record about" never had to be asked. Now one
    record accumulates every rendering, so it has to answer: `page.layout_hash` is the most recent
    one and `page.layout_hashes` is the set, each with the record type it was rendered for, when it
    was first and last seen, and how many visits landed on it.

    That set is the evidence a reader needs to tell a page whose layout genuinely changed from one
    that never moved -- the fact the old key destroyed by splitting the record instead of noting
    the change. It is never used as identity: nothing keys, paths or looks a record up by it.
    """
    if not layout_hash:
        return
    page = rec.setdefault("page", {})
    page["layout_hash"] = layout_hash
    seen = page.setdefault("layout_hashes", {})
    entry = seen.setdefault(layout_hash, {"record_type": record_type,
                                          "first_seen": _iso(now()), "n": 0})
    entry["n"] = (entry.get("n") or 0) + 1
    entry["last_seen"] = _iso(now())
    if record_type and not entry.get("record_type"):
        entry["record_type"] = record_type


def rung_key(c: dict) -> str:
    return json.dumps({"kw": c.get("kw") or c.get("name"), "args": c.get("args"), "kwargs": c.get("kwargs")},
                      sort_keys=True, default=str)


class Store:
    def __init__(self, state_root: str | None = None, docs_root: str | None = None):
        self.state_root = state_root or K.STATE
        self.docs_root = docs_root or os.getcwd()
        self.org_map_dir = os.path.join(self.state_root, "org-map")
        self.apps_dir = os.path.join(self.state_root, "apps")

    # ------------------------------------------------------------------ paths
    def key_for(self, url: str, org: str | None = None) -> dict:
        pk = K.page_key(url, org=org)
        if pk["salesforce"] and pk["alias"]:
            pk["store_dir"] = os.path.join(self.org_map_dir, pk["alias"], "pom")
        else:
            pk["store_dir"] = os.path.join(self.apps_dir, pk["host"] or "unknown-host", "pom")
        pk["path"] = os.path.join(pk["store_dir"], pk["slug"] + ".json")
        return pk

    def partitions(self) -> list[dict]:
        out = []
        for d in sorted(glob.glob(os.path.join(self.org_map_dir, "*", "pom"))):
            out.append({"kind": "org", "name": os.path.basename(os.path.dirname(d)), "dir": d})
        for d in sorted(glob.glob(os.path.join(self.apps_dir, "*", "pom"))):
            out.append({"kind": "host", "name": os.path.basename(os.path.dirname(d)), "dir": d})
        return out

    def records(self, partition: str | None = None) -> list[dict]:
        out = []
        for p in self.partitions():
            if partition and p["name"] != partition:
                continue
            for f in sorted(glob.glob(os.path.join(p["dir"], "*.json"))):
                if os.path.basename(f).startswith("_"):
                    continue
                try:
                    with open(f) as fh:
                        rec = json.load(fh)
                    rec["_path"] = f
                    out.append(rec)
                except Exception:
                    continue
        return out

    # ---------------------------------------------------------------- get/put
    def get(self, key_or_url: str, org: str | None = None) -> dict | None:
        pk = self.key_for(key_or_url, org) if "://" in key_or_url else None
        path = pk["path"] if pk else self._path_for_key(key_or_url)
        if not path or not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def _path_for_key(self, key: str) -> str | None:
        partition = key.split("|", 1)[0]
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("_")[:180]
        for base in (os.path.join(self.org_map_dir, partition, "pom"), os.path.join(self.apps_dir, partition, "pom")):
            p = os.path.join(base, slug + ".json")
            if os.path.exists(p):
                return p
        kinds = {p["name"]: p["kind"] for p in self.partitions()}
        base_dir = self.org_map_dir if kinds.get(partition, "host" if ("." in partition or partition == "unknown-host") else "org") == "org" else self.apps_dir
        return os.path.join(base_dir, partition, "pom", slug + ".json")

    def put(self, rec: dict) -> str:
        path = rec["_path"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        body = {k: v for k, v in rec.items() if not k.startswith("_")}
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(body, f, indent=1, sort_keys=True, default=str)
        os.replace(tmp, path)
        return path

    def _open(self, pk: dict) -> dict:
        rec = None
        if os.path.exists(pk["path"]):
            with open(pk["path"]) as f:
                rec = json.load(f)
        if not rec:
            rec = {"page": {k: pk[k] for k in ("key", "partition", "alias", "host", "salesforce", "pattern",
                                                 "object", "action", "record_type", "app", "layout_hash")},
                   "first_seen": _iso(now()), "last_seen": None, "visits": 0,
                   "l0": None, "elements": {}, "rung_stats": {}, "patterns": [], "flows": {},
                   "predictions": {}, "links": {}, "states": {}}
        rec.setdefault("predictions", {})
        rec.setdefault("links", {})
        rec.setdefault("states", {})
        note_layout_hash(rec, pk.get("layout_hash"), pk.get("record_type"))
        rec["_path"] = pk["path"]
        rec["_render"] = pk["render"]
        return rec

    # ------------------------------------------------------------------ merge
    def merge_session(self, session: dict, flow_name: str | None = None) -> dict:
        """Every step with a target becomes/updates an element on its page; every candidate becomes
        a rung with history. Returns {pages: n, elements: n, rungs: n, skipped: [...]}."""
        org = session.get("org")
        stats = {"pages": set(), "elements": 0, "rungs": 0, "skipped": [], "dropped_hostless": 0,
                 "links": 0, "opens": 0, "states": 0, "twins_attached": 0}
        flow_name = flow_name or session.get("name")
        open_recs: dict[str, dict] = {}
        steps = [normalise_step(s) for s in session.get("steps", [])]
        # PRE-PASS: every step's page key, so a step can see where the NEXT one landed. A click
        # whose successor is on another key NAVIGATED there -- possibly into another PARTITION
        # (`Commit Changes` on a cicd-demo User Story -> na.devops.copado.com|/en/commit/{id}).
        step_keys: list[str | None] = []
        for s in steps:
            u = ((s.get("event") or {}).get("url"))
            k = self.key_for(u, org) if u else None
            step_keys.append(k["key"] if (k and k.get("host")) else None)
        for idx, step in enumerate(steps):
            ev = step.get("event") or {}
            url = ev.get("url")
            if not url:
                stats["skipped"].append((step.get("n"), "no url"))
                continue
            pk = self.key_for(url, org)
            if not pk.get("host"):
                # about:blank and friends: the frontdoor unwrap found no destination -> not a page
                stats["dropped_hostless"] += 1
                continue
            rec = open_recs.get(pk["path"]) or self._open(pk)
            open_recs[pk["path"]] = rec
            rec["last_seen"] = _iso(ev.get("ts", 0) / 1000 if ev.get("ts", 0) > 1e11 else ev.get("ts") or now())
            rec["visits"] = rec.get("visits", 0) + (1 if ev.get("kind") == "nav" else 0)
            rec.setdefault("flows", {}).setdefault(flow_name, [])
            # The flow's step list is also the REPLAY MARKER: a step number already in it means
            # this exact session step has been merged before, so its link/open/state counts must
            # not be counted twice (the structure below is additive and idempotent either way).
            replayed = step.get("n") in rec["flows"][flow_name]
            if not replayed:
                rec["flows"][flow_name].append(step.get("n"))
            stats["pages"].add(pk["key"])
            if ev.get("kind") not in ELEMENT_KINDS:
                continue
            ctx = ev.get("context") or {}
            tgt = ev.get("target") or {}
            labels = ctx.get("labels") or []
            label = (labels[0] if labels else "") or (ctx.get("interactive") or {}).get("text") or tgt.get("text") or ""
            container = (ctx.get("container") or {}).get("label") or ""
            attrs = dict((ctx.get("interactive") or {}).get("attrs") or {})
            attrs.update(tgt.get("attrs") or {})
            family = ctx.get("family") or tgt.get("tag")
            # WRITER 1 of 3 (F70). A DRIVEN step carries no DOM shape -- `--op kw` knows the
            # keyword and nothing else -- so this path used to mint `button|Object Fields||` while
            # the capture writer minted `link|Object Fields|Tabs|id=customTab__item` for the same
            # control, and the truth split in half: the behaviour (`opens`, the verified rung) sat
            # on the untagged copy, which `ClickItem` can never resolve. `identify_control` is the
            # one place that decides what a control is CALLED here, so the driven step lands on the
            # element the store already holds; when nothing matches it mints and says `source:
            # driven`, so the next writer with a real shape fills the SAME element in.
            shapeless = not tgt.get("tag") and not stable_attrs(attrs)
            eid = identify_control(rec, label, family, attrs=attrs, tag=tgt.get("tag"),
                                   container=container)
            minted = eid not in rec["elements"]
            if not minted and eid != element_id(family, label, container, attrs):
                stats["twins_attached"] += 1
            el = rec["elements"].setdefault(eid, {"family": ctx.get("family") or tgt.get("tag"),
                                                  "label": label, "container": container,
                                                  "attrs": stable_attrs(attrs), "tag": tgt.get("tag"),
                                                  "shadow_depth": tgt.get("shadow_depth"),
                                                  "ladder": [], "effects": {}, "n_seen": 0, "last_seen": None})
            if minted and shapeless:
                el["source"] = DRIVEN
            el["n_seen"] += 1
            el["last_seen"] = rec["last_seen"]
            stats["elements"] += 1
            # ---------------------------------------------------------------- where it LEADS
            # Until now `effects` was a counter by CLASS: it said a click navigated, never WHERE.
            # The user's question (2026-09-15): "How would you know to look at this when we're
            # interacting with Copado CI/CD ... would you say this button leads you to this page
            # object here?" -- so the destination is stored on the button and on the page.
            landed = ev.get("landed_url")
            landed_key = None
            if landed:
                lk = self.key_for(landed, org)
                landed_key = lk["key"] if lk.get("host") else None
            nxt = step_keys[idx + 1] if idx + 1 < len(step_keys) else None
            kind, target = step_effect(
                step, pk["key"],
                nxt if ev.get("kind") in LEADS_TO_KINDS else None, landed_key)
            if kind == "nav" and target and str(target).startswith("http"):
                # an explicit nav target given as a URL is stored as the PAGE KEY it resolves to,
                # never the raw URL (a record id in a link is a link nothing can look up)
                tk = self.key_for(str(target), org)
                target = tk["key"] if tk.get("host") else target
            if kind in ("modal", "panel") and target and landed_key and landed_key != pk["key"]:
                # a modal that moves the URL (a Lightning quick action: /lightning/action/quick/...)
                # is BOTH an `opens` on the control and a link to its own page key
                if not replayed:
                    _bump(el.setdefault("opens", {}), target)
                    _bump(el.setdefault("leads_to", {}), landed_key)
                link = rec.setdefault("links", {}).setdefault(landed_key, {"via": [], "n": 0, "opens": target})
                _append_unique(link["via"], eid)
                if not replayed:
                    link["n"] += 1
                    stats["links"] += 1
                    stats["opens"] += 1
                kind = None
            if kind == "nav" and target:
                if not replayed:
                    _bump(el.setdefault("leads_to", {}), target)
                link = rec.setdefault("links", {}).setdefault(target, {"via": [], "n": 0})
                _append_unique(link["via"], eid)
                if not replayed:
                    link["n"] += 1
                    stats["links"] += 1
            elif kind in ("modal", "panel") and target:
                if not replayed:
                    _bump(el.setdefault("opens", {}), target)
                    stats["opens"] += 1
                ps = page_state(rec, target)
                _append_unique(ps["entered_via"], eid)
                ps["last_seen"] = rec["last_seen"]
                ps.setdefault("kind", kind)
            elif kind == "state" and target:
                ps = page_state(rec, target)
                _append_unique(ps["entered_via"], eid)
                ps["last_seen"] = rec["last_seen"]
            # ------------------------------------------------- which STATE the page was in
            state = step.get("state")
            if state and state != DEFAULT_STATE:
                ps = page_state(rec, state)
                if not replayed:
                    ps["n_seen"] += 1
                    stats["states"] += 1
                ps["last_seen"] = rec["last_seen"]
                _append_unique(ps["elements"], eid)
                enabled = step_enabled(step, attrs)
                seen_as: dict[str, Any] = {"label": label}
                if enabled is not None:
                    seen_as["enabled"] = enabled
                # SCOPE, the driven half (2026-09-19). A driven step carries no DOM: `--op kw`
                # knows the keyword and nothing else, so nothing here can say whether the control
                # was inside the modal or on the page behind it. When a CAPTURE of this state has
                # already scoped this element, that fact is kept; otherwise the key is simply
                # absent -- COULD-NOT-CHECK, never `own` by default.
                prior = ((el.get("states") or {}).get(state) or {}).get("scope")
                if prior:
                    seen_as["scope"] = prior
                el.setdefault("states", {})[state] = seen_as
            chosen = step.get("chosen")
            verdict = step.get("verdict") or "COULD-NOT-CHECK"
            cands = ([chosen] if chosen else []) + list(step.get("alternatives") or [])
            seen = set()
            for i, c in enumerate(cands):
                if not c or not (c.get("kw") or c.get("name")):
                    continue
                rk = rung_key(c)
                if rk in seen:
                    continue
                seen.add(rk)
                rung = next((r for r in el["ladder"] if r.get("_key") == rk), None)
                if rung is None:
                    rung = {"_key": rk, "kw": c.get("kw") or "custom", "args": c.get("args") or [],
                            "kwargs": c.get("kwargs") or {}, "name": c.get("name"), "body": c.get("body"),
                            "why": c.get("why"), "score": c.get("score"), "n_verified": 0, "n_failed": 0,
                            "n_unverified": 0, "last_verdict": None, "last_seen": None,
                            "failure_signal": None, "origin": "session"}
                    el["ladder"].append(rung)
                    stats["rungs"] += 1
                rung["last_seen"] = rec["last_seen"]
                if i == 0 and chosen:
                    rung["last_verdict"] = verdict
                    if verdict in VERIFIED:
                        rung["n_verified"] += 1
                    elif verdict == "CAUGHT-BUG":
                        rung["n_failed"] += 1
                        rung["failure_signal"] = step.get("reason")
                    else:
                        rung["n_unverified"] += 1
                else:
                    rung["n_unverified"] += 0   # alternatives are known, not counted as tried
            # user override = a lesson about the primary
            if step.get("user_override"):
                el.setdefault("overrides", []).append(step["user_override"])
            el["ladder"] = order_ladder(el["ladder"])
        for rec in open_recs.values():
            self.put(rec)
        stats["pages"] = len(stats["pages"])
        return stats

    def merge_lessons(self, lessons: Iterable[dict]) -> int:
        """lessons.jsonl carries host/family/rung (no page) -> partition-level rung_stats."""
        n = 0
        by_part: dict[str, dict] = {}
        for L in lessons:
            host = L.get("host")
            if not host or host in ("login.salesforce.com", "test.salesforce.com"):
                continue
            alias = K.alias_for_host(host) if K.is_salesforce_host(host) else None
            part = alias or host
            st = by_part.setdefault(part, {})
            fam = L.get("control_family") or "generic"
            won = L.get("rung_won")
            for rung in L.get("rungs_tried") or []:
                d = st.setdefault(fam, {}).setdefault(rung, {"won": 0, "tried": 0, "failed": 0})
                d["tried"] += 1
                if rung == won and L.get("verdict") in VERIFIED:
                    d["won"] += 1
                if rung == won and L.get("verdict") == "CAUGHT-BUG":
                    d["failed"] += 1
            n += 1
        for part, st in by_part.items():
            p = os.path.join(self.org_map_dir if "." not in part else self.apps_dir, part, "pom", "_rung_stats.json")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            old = {}
            if os.path.exists(p):
                with open(p) as f:
                    old = json.load(f)
            for fam, d in st.items():
                for rung, c in d.items():
                    o = old.setdefault(fam, {}).setdefault(rung, {"won": 0, "tried": 0, "failed": 0})
                    for k in c:
                        o[k] = c[k]          # lessons.jsonl is the ledger; stats are a rebuild, not a sum
            tmp = p + ".tmp"
            with open(tmp, "w") as f:
                json.dump(old, f, indent=1, sort_keys=True)
            os.replace(tmp, p)
        return n

    def merge_l0(self, url: str, org: str | None, l0: dict, source: str, captured_at: str | None = None) -> dict:
        """Attach an L0 index (v3, or the v1 census fallback) to the page: elements not yet known
        from any session get an id and an empty ladder (origin l0) so the recorder can propose."""
        pk = self.key_for(url, org)
        rec = self._open(pk)
        rec["l0"] = {"source": source, "captured_at": captured_at or _iso(now()), "bytes": len(json.dumps(l0, default=str)),
                     "regions": l0.get("regions"), "fields": l0.get("fields"), "signals": l0.get("signals"),
                     "counts": l0.get("counts")}
        rec["last_seen"] = rec["last_seen"] or _iso(now())
        added = 0
        for e in l0.get("elements") or []:
            eid = element_id(e.get("family"), e.get("label"), e.get("region") or e.get("container"), e.get("attrs"))
            if eid not in rec["elements"]:
                rec["elements"][eid] = {"family": e.get("family"), "label": e.get("label"),
                                        "container": e.get("region") or e.get("container") or "",
                                        "attrs": stable_attrs(e.get("attrs")), "tag": e.get("tag"),
                                        "shadow_depth": e.get("shadow"), "ladder": [], "effects": {},
                                        "n_seen": 0, "last_seen": None, "origin": "l0"}
                added += 1
        self.put(rec)
        return {"key": pk["key"], "path": pk["path"], "elements_added": added, "bytes": rec["l0"]["bytes"]}

    def merge_prediction(self, url: str, org: str | None, expectation: dict,
                         comparison: dict | None = None) -> dict:
        """Persist a quick-action rendering prediction and its live outcome for this page key.

        Counts are kept apart on purpose -- `confirmations` (predicted == observed on real DOM) and
        `mismatches` (a CAUGHT-BUG on the map) -- so a page that has confirmed once and drifted
        since never reads as clean. `observed` records only what the DOM actually said: an
        expectation nobody has seen rendered keeps `observed: null` and status
        `resolved-from-metadata`, which is a prediction, not a pass.
        """
        ref = expectation.get("ref") or expectation.get("action")
        if not ref:
            return {"stored": False, "reason": "the expectation names no action"}
        pk = self.key_for(url, org)
        rec = self._open(pk)
        cur = rec["predictions"].get(ref) or {"confirmations": 0, "mismatches": 0}
        cur.update({"action": expectation.get("action"), "scope": expectation.get("scope"),
                    "predicted": expectation.get("rendering_family"),
                    "status": expectation.get("status"),
                    "source": expectation.get("source"), "via": expectation.get("via"),
                    "dom_signature": expectation.get("dom_signature"),
                    "field_families": [{"api": f.get("api"), "label": f.get("label"),
                                        "family": f.get("family"), "required": f.get("required")}
                                       for f in (((expectation.get("field_families") or {})
                                                  .get("fields")) or [])],
                    "last_seen": _iso(now())})
        if comparison:
            cur["observed"] = comparison.get("observed")
            cur["last_comparison"] = comparison.get("status")
            if comparison.get("status") == "metadata-confirmed":
                cur["confirmations"] += 1
                cur["status"] = "metadata-confirmed"
            elif comparison.get("status") == "CAUGHT-BUG":
                cur["mismatches"] += 1
                cur["status"] = "CAUGHT-BUG"
                cur["caught_bug"] = comparison
        rec["predictions"][ref] = cur
        rec["last_seen"] = _iso(now())
        self.put(rec)
        return {"stored": True, "key": pk["key"], "path": pk["path"], "action": ref,
                "status": cur["status"], "confirmations": cur["confirmations"],
                "mismatches": cur["mismatches"]}

    def prediction(self, url: str, org: str | None, action_ref: str) -> dict | None:
        """Read a stored prediction back -- the "known page" path: no re-derivation needed."""
        rec = self.get(url, org)
        return ((rec or {}).get("predictions") or {}).get(action_ref)

    # ----------------------------------------------------------------- render
    def render(self, partition: str) -> str | None:
        recs = self.records(partition)
        if not recs:
            return None
        kinds = {p["name"]: p["kind"] for p in self.partitions()}
        sf = kinds.get(partition, "host" if "." in partition else "org") == "org"
        out_path = (os.path.join(self.docs_root, "docs", "org-map", f"{partition}-pom.md") if sf
                    else os.path.join(self.docs_root, "docs", "recorder", "pom", f"{partition}.md"))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        lines = [f"# Page object model -- {partition} ({'org' if sf else 'host'})", "",
                 f"Rendered {_iso(now())} from `{os.path.dirname(recs[0].get('_path', '')) or ('~/.claude/state/' + ('org-map/' if sf else 'apps/') + partition + '/pom')}`. "
                 "Lookup before scan: a known page is read from here; a scan runs only on a miss, on drift, or after a failed replay.", ""]
        lines.append("| page | object | action | elements | verified primaries | failed twice | flows | last seen |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in recs:
            els = r.get("elements") or {}
            prim_ok = sum(1 for e in els.values() if e.get("ladder") and e["ladder"][0].get("n_verified", 0) > 0)
            fail2 = sum(1 for e in els.values() if e.get("ladder") and e["ladder"][0].get("n_failed", 0) >= 2)
            pg = r["page"]
            lines.append(f"| `{pg['pattern']}` | {pg.get('object') or ''} | {pg.get('action') or ''} | {len(els)} | {prim_ok} | {fail2} | {len(r.get('flows') or {})} | {r.get('last_seen') or ''} |")
        lines.append("")
        for r in recs:
            pg = r["page"]
            lines.append(f"## `{pg['pattern']}`" + (f" ({pg['object']})" if pg.get("object") else ""))
            lines.append("")
            lines.append(f"key `{pg['key']}` · visits {r.get('visits', 0)} · first seen {r.get('first_seen')} · L0 {((r.get('l0') or {}).get('source') or 'none')}")
            lines.append("")
            els = r.get("elements") or {}
            if els:
                lines.append("| element | family | primary | verified/failed | backups | leads to / opens | effects |")
                lines.append("|---|---|---|---|---|---|---|")
                for eid, e in sorted(els.items()):
                    lad = e.get("ladder") or []
                    prim = rung_line(lad[0]) if lad else "(none -- from L0, never acted on)"
                    vf = f"{lad[0].get('n_verified', 0)}/{lad[0].get('n_failed', 0)}" if lad else ""
                    eff = ", ".join(f"{k}×{v}" for k, v in (e.get("effects") or {}).items())
                    lines.append(f"| {_md(e.get('label') or eid)} | {e.get('family')} | `{_md(prim)}` | {vf} | {max(len(lad) - 1, 0)} | {_md(leads_to_cell(e))} | {eff} |")
                lines.append("")
            if r.get("links"):
                lines.append("links (this page's controls lead here -- the target may be in another partition):")
                lines.append("")
                for tgt, info in sorted((r["links"]).items()):
                    via = ", ".join(f"`{_md((els.get(v) or {}).get('label') or v)}`" for v in (info.get("via") or [])) or "(unknown control)"
                    lines.append(f"- {via} -> `{_md(tgt)}` ×{info.get('n', 0)}")
                lines.append("")
            if r.get("states"):
                lines.append("### states")
                lines.append("")
                lines.append("A page is not one control set. `default` is never written; every state below was observed. "
                             "`steps in it` counts steps recorded WHILE the page was in that state, so a state that was "
                             "only entered and never stepped in reads 0 -- entered is not the same fact as acted in.")
                lines.append("")
                lines.append("| state | steps in it | entered via | controls | last seen |")
                lines.append("|---|---|---|---|---|")
                for name, s in sorted(r["states"].items()):
                    ev_ = ", ".join(f"`{_md((els.get(v) or {}).get('label') or v)}`" for v in (s.get("entered_via") or [])) or ""
                    ctrls = []
                    for v in (s.get("elements") or []):
                        e = els.get(v) or {}
                        seen_as = ((e.get("states") or {}).get(name) or {})
                        lab = seen_as.get("label") or e.get("label") or v
                        if seen_as.get("enabled") is False:
                            lab += " (disabled)"
                        elif seen_as.get("enabled") is True:
                            lab += " (enabled)"
                        ctrls.append(f"`{_md(lab)}`")
                    lines.append(f"| {_md(name)} | {s.get('n_seen', 0)} | {ev_} | {', '.join(ctrls)} | {s.get('last_seen') or ''} |")
                lines.append("")
            if r.get("flows"):
                lines.append("flows: " + ", ".join(f"{k} (steps {v})" for k, v in r["flows"].items()))
                lines.append("")
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
        return out_path

    # ------------------------------------------------------------- apps (cross-partition view)
    def apps_registry(self) -> dict:
        """`docs/recorder/pom/apps.json` -- {slug: {label, entry_keys: [page key...]}}. The
        registry is the ONLY thing that says "these pages are one product"; the store itself stays
        partitioned by org/host and that rule does not bend (AI-POM-HANDOFF.md fact 2)."""
        p = os.path.join(self.docs_root, "docs", "recorder", "pom", "apps.json")
        try:
            with open(p) as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def app_graph(self, spec: dict) -> list[dict]:
        """Breadth-first over page `links` from the registry's entry keys. Each row is
        {key, partition, salesforce, elements, verified_primaries, reached_from, via, depth,
        record}; a key with no record yet is reported, never skipped -- the link is knowledge even
        when the destination page has never been recorded."""
        by_key = {}
        for r in self.records():
            k = ((r.get("page") or {}).get("key"))
            if k and k not in by_key:
                by_key[k] = r
        seen: dict[str, dict] = {}
        queue: list[str] = []
        for k in spec.get("entry_keys") or []:
            if k not in seen:
                seen[k] = {"key": k, "reached_from": None, "via": None, "depth": 0}
                queue.append(k)
        out = []
        while queue:
            k = queue.pop(0)
            row = seen[k]
            rec = by_key.get(k)
            els = (rec or {}).get("elements") or {}
            row.update({"record": rec,
                        "partition": ((rec or {}).get("page") or {}).get("partition") or k.split("|", 1)[0],
                        "salesforce": bool(((rec or {}).get("page") or {}).get("salesforce")),
                        "elements": len(els),
                        "verified_primaries": sum(1 for e in els.values()
                                                  if e.get("ladder") and (e["ladder"][0].get("n_verified") or 0) > 0)})
            out.append(row)
            for tgt, info in sorted(((rec or {}).get("links") or {}).items()):
                if tgt in seen:
                    continue
                via_id = next(iter(info.get("via") or []), None)
                seen[tgt] = {"key": tgt, "reached_from": k, "depth": row["depth"] + 1,
                             "via": (els.get(via_id) or {}).get("label") or via_id}
                queue.append(tgt)
        return out

    def render_app(self, slug: str, spec: dict) -> str:
        """docs/recorder/pom/apps/<slug>.md -- one product, every partition it spans."""
        rows = self.app_graph(spec)
        label = spec.get("label") or slug
        out_path = os.path.join(self.docs_root, "docs", "recorder", "pom", "apps", f"{slug}.md")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        lines = [f"# {label} -- app view (`{slug}`)", "",
                 f"Rendered {_iso(now())} by `python3 tools/recorder/pom/pom_cli.py render`. "
                 "Breadth-first from the registry's entry keys over each page's `links`.", "",
                 "**The partition rule does not bend for an app that spans both.** A page key's "
                 "partition is the org alias for a Salesforce page and the HOST for everything "
                 "else, so this product's pages live in different stores on purpose. What crosses "
                 "the boundary is the LINK: the control on one page that leads to the other. This "
                 "file is the index that makes that reachable; each page's detail stays in its own "
                 "partition's render.", "",
                 "| page | partition | elements | verified primaries | reached from | via |",
                 "|---|---|---|---|---|---|"]
        for r in rows:
            known = r["record"] is not None
            src = f"`{_md(r['reached_from'])}`" if r["reached_from"] else "(entry)"
            via = f"`{_md(r['via'])}`" if r.get("via") else ""
            cells = (f"{r['elements']}", f"{r['verified_primaries']}") if known else ("—", "—")
            lines.append(f"| `{_md(r['key'])}` | {r['partition']} | {cells[0]} | {cells[1]} | {src} | {via} |")
        lines.append("")
        missing = [r["key"] for r in rows if r["record"] is None]
        if missing:
            lines.append("Not in the store yet (the link is known, the page has never been recorded): "
                         + ", ".join(f"`{_md(k)}`" for k in missing))
            lines.append("")
        for r in rows:
            rec = r["record"]
            if not rec:
                continue
            els = rec.get("elements") or {}
            lines.append(f"## `{_md(r['key'])}`")
            lines.append("")
            render = (os.path.join("docs", "org-map", f"{r['partition']}-pom.md") if r["salesforce"]
                      else os.path.join("docs", "recorder", "pom", f"{r['partition']}.md"))
            lines.append(f"partition `{r['partition']}` · {r['elements']} elements · "
                         f"{r['verified_primaries']} verified primaries · detail: `{render}`")
            lines.append("")
            for tgt, info in sorted((rec.get("links") or {}).items()):
                via = ", ".join(f"`{_md((els.get(v) or {}).get('label') or v)}`" for v in (info.get("via") or []))
                lines.append(f"- leads to `{_md(tgt)}` via {via or '(unknown control)'} ×{info.get('n', 0)}")
            opens = [(e.get("label") or eid, t, n) for eid, e in sorted(els.items())
                     for t, n in sorted((e.get("opens") or {}).items())]
            for lab, t, n in opens:
                lines.append(f"- `{_md(lab)}` opens **{_md(t)}** ×{n}")
            if rec.get("links") or opens:
                lines.append("")
            if rec.get("states"):
                lines.append("| state | steps in it | entered via | controls |")
                lines.append("|---|---|---|---|")
                for name, s in sorted(rec["states"].items()):
                    ev_ = ", ".join(f"`{_md((els.get(v) or {}).get('label') or v)}`" for v in (s.get("entered_via") or []))
                    ctrls = ", ".join(f"`{_md(((els.get(v) or {}).get('states') or {}).get(name, {}).get('label') or (els.get(v) or {}).get('label') or v)}`"
                                      for v in (s.get("elements") or []))
                    lines.append(f"| {_md(name)} | {s.get('n_seen', 0)} | {ev_} | {ctrls} |")
                lines.append("")
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
        return out_path

    def render_apps(self) -> list[str]:
        return [self.render_app(slug, spec) for slug, spec in sorted(self.apps_registry().items())]


def _heal_promotion_enabled() -> bool:
    """Whether play-time heal counts (`n_verified`) may re-rank a ladder -- read off the heal
    ledger's own gate (tools/recorder/heal_ledger.py: >=200 rows, >=95% correct, <=1%
    wrong-and-green). FAILS CLOSED: an unreadable/absent ledger is OFF, never ON."""
    try:
        import heal_ledger  # flat sys.path, the same convention pom/keys.py is imported by
    except ImportError:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            import heal_ledger  # type: ignore
        except Exception:
            return False
    try:
        return bool(heal_ledger.promotion_enabled())
    except Exception:
        return False


def order_ladder(ladder: list[dict], promotion: bool | None = None) -> list[dict]:
    """Primary first: most verified, then fewest failures, then original score.

    `promotion` (Phase 1A step 3, docs/crt-train/FALLBACK-LADDER.md "Healing policy
    2026-09-09"): the `n_verified` term is a PROMOTION -- it is incremented when a rung ran at
    play time, including a rung that only ran because the step HEALED onto it. Until the heal
    ledger has been scored (>=200 rows, >=95% correct, <=1% wrong-and-green) that count is not
    evidence, so it does not re-rank anything; a capture-derived rung is born COULD-NOT-CHECK
    (pom-asset-v0-2026-09-07.md) and promoting it puts an untested rung ahead of a tested one.
    Demotion is NOT gated: a rung that failed at play time still sinks, because a failure is a
    real observation regardless of what the healer did afterwards.

    None (the default) consults the ledger; True/False is the explicit override tests use.
    """
    if promotion is None:
        promotion = _heal_promotion_enabled()
    if promotion:
        return sorted(ladder, key=lambda r: (-(r.get("n_verified") or 0), (r.get("n_failed") or 0),
                                             -(r.get("score") or 0), (r.get("origin") == "seed")))
    return sorted(ladder, key=lambda r: ((r.get("n_failed") or 0), -(r.get("score") or 0),
                                         (r.get("origin") == "seed")))


def rung_line(r: dict) -> str:
    parts = [r.get("kw") or r.get("name") or "custom"] + [str(a) for a in (r.get("args") or [])]
    parts += [f"{k}={v}" for k, v in (r.get("kwargs") or {}).items()]
    return "    ".join(parts)


def sessions_on_disk(state_root: str | None = None) -> list[str]:
    base = os.path.join(state_root or K.STATE, "recorder")
    return sorted(f for f in glob.glob(os.path.join(base, "*.json")) if not f.endswith("lessons.jsonl"))
