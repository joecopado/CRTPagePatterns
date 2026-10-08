"""consult -- the ONE rule for "does the store already know how to resolve this control?".

Parity plan phase 1 (docs/recorder/PLAN-RECORDER-LOCATOR-PARITY-2026-09-13.md), and its own
instruction: *"Import `pom/match.find_control` + `best_verified_rung` -- interop already does;
write it once."* This is that once.

THE GAP. The plan's diagnosis: *"Three things resolve a control today and they do not agree. ...
the recorder is the only resolver that starts from zero on a known page."* interop consults the
store before it drives (phase 0, landed 2026-09-15). Neither recorder does -- the Dock
(`tools/recorder/server.py`) holds zero store references, and the CRT override's composer imports
`pom.match` only for `norm_label` and the family tables, never `find_control` or
`best_verified_rung`. So a page with 67 live-verified rungs is re-derived from scratch every time
it is recorded.

THE RULE, and it is a TRI-STATE, never a boolean:

    verified          the store holds this control AND a rung that passed live and did not fail
                      last. Use it as the PRIMARY; the derived locator becomes a dormant backup.
                      Since D27 (2026-10-07) a PROVEN rung answers first -- a recorded validation
                      (read-back, SOQL, judged screenshot, observed effect) passed -- and `why`
                      names it; a rung whose last validation failed is demoted; a bare live verdict
                      says it carries no validation (`basis: legacy-verdict`).
    known-unverified  the store holds the control with nothing verified. DERIVE, and say the
                      store knew the control but could not vouch for a call -- "known" is not
                      "verified" (CLAUDE.md's tri-state rule, and interop's own wording).
    unknown-control   the store knows this page key and not this control. Derive.
    unknown-page      no record for this page key. Derive.

Every answer carries `why` in words a person can act on, because a silent miss is
indistinguishable from a store that was never run.

WHAT THIS MODULE DOES NOT DO. It does not drive, does not write, does not decide what line to
compose, and does not turn a rung into a call. `disambiguation_args.to_call_kwargs` is the one
place `index=` becomes QWeb's numeric `anchor=` (D14) and it stays the caller's step: the Dock, the
override and interop each build their own call shape.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import match as MATCH   # noqa: E402

#: the four answers, as constants so a caller never spells one wrong in a comparison.
VERIFIED = "verified"
KNOWN_UNVERIFIED = "known-unverified"
UNKNOWN_CONTROL = "unknown-control"
UNKNOWN_PAGE = "unknown-page"

#: answers a caller may treat as "the store has spoken". Only one of them.
USABLE = (VERIFIED,)


#: what a `verified` answer stands on (D27, 2026-10-07). `proven`: a recorded validation -- a
#: read-back, a SOQL read, a judged full-page screenshot or an observed effect -- passed and none
#: has failed since. `legacy-verdict`: a live verdict with NO validation recorded, which is what 793
#: of slockard's 819 "verified" calls were ("found and acted without an error").
BASIS_PROVEN = "proven"
BASIS_LEGACY = "legacy-verdict"


def _proof_words(rung: dict) -> tuple[str, dict]:
    """(why, proof) for a proven rung: which validation(s), how many, the last one's run context and time."""
    p = rung.get("proven") or {}
    last = p.get("last") or {}
    run = last.get("run") or {}
    kinds = sorted(k for k, c in (p.get("by_kind") or {}).items() if int((c or {}).get("pass") or 0) > 0)
    who = run.get("user") or "the org's API user"
    prof = run.get("profile") or "profile unknown"
    why = ("proven by %s: %d validation(s) passed, %d failed; last %s %s at %s as %s (%s) on %s -- %s %s"
           % ("/".join(kinds) or "?", int(p.get("n_pass") or 0), int(p.get("n_fail") or 0),
              last.get("kind"), last.get("result"), last.get("at"), who, prof, run.get("org"),
              rung.get("kw"), list(rung.get("args") or [])))
    proof = {"kinds": kinds, "n_pass": int(p.get("n_pass") or 0), "n_fail": int(p.get("n_fail") or 0),
             "last": {k: last.get(k) for k in ("kind", "result", "at", "run", "source")}}
    return why, proof


def consult(record: dict | None, label: str | None, family: str | None = None,
            page_key: str | None = None, require_proof: bool = False) -> dict:
    """The tri-state answer for one control. Never raises, never returns None.

    `record` is a store record (`Store.get(page_key)`); passing it in rather than a Store keeps
    this pure and lets a caller consult many controls against one already-loaded record, which is
    what a composer does -- one page, many controls.

    `verified` answers from a PROVEN rung first (D27: a recorded validation passed and none failed
    since), and its `why` names the validation. A rung whose last validation FAILED is demoted and
    never answers. A rung with only a live verdict and no validation still answers `verified` with
    `basis: legacy-verdict` and a `why` that says no validation is recorded -- unless
    `require_proof`, when it is `known-unverified`: acted is not proven.

    Returns {'verdict', 'why', 'rung', 'element_id', 'label', 'family', 'page_key', 'basis', 'proof'}.
    """
    out = {"verdict": UNKNOWN_PAGE, "why": "", "rung": None, "element_id": None,
           "label": label, "family": family, "page_key": page_key, "basis": None, "proof": None}
    if not label or not str(label).strip():
        out["verdict"] = UNKNOWN_CONTROL
        out["why"] = "no label to match on -- an unlabelled control cannot be looked up"
        return out
    if not record:
        out["why"] = ("the store holds no record for page key %r -- this page has never been "
                      "recorded or crawled" % (page_key,))
        return out
    try:
        element = MATCH.find_control(record, label, family)
    except Exception as exc:                       # a malformed record must not stop a recording
        out["verdict"] = UNKNOWN_CONTROL
        out["why"] = "COULD-NOT-CHECK: %s while matching %r (%s)" % (
            type(exc).__name__, label, exc)
        return out
    if element is None:
        out["verdict"] = UNKNOWN_CONTROL
        out["why"] = ("the store knows this page but no %s-family control labelled %r"
                      % (family or "any", label))
        return out
    out["element_id"] = element.get("_id")
    proven = MATCH.best_proven_rung(element)
    if proven is not None:
        out["verdict"], out["rung"], out["basis"] = VERIFIED, proven, BASIS_PROVEN
        out["why"], out["proof"] = _proof_words(proven)
        return out
    demoted = [r for r in element.get("ladder") or [] if MATCH.proven_failed(r)]
    rung = MATCH.best_verified_rung(element)
    if rung is not None and require_proof:
        out["verdict"] = KNOWN_UNVERIFIED
        out["why"] = ("the store's rung %s %s carries a live verdict with no validation recorded -- "
                      "acted is not proven (D27): deriving, and saying so"
                      % (rung.get("kw"), list(rung.get("args") or [])))
        return out
    if rung is None:
        out["verdict"] = KNOWN_UNVERIFIED
        if demoted:
            last = (demoted[0].get("proven") or {}).get("last") or {}
            out["why"] = ("the store's rung %s %s was demoted: its last validation (%s at %s) FAILED -- "
                          "deriving, and saying so"
                          % (demoted[0].get("kw"), list(demoted[0].get("args") or []),
                             last.get("kind"), last.get("at")))
        else:
            out["why"] = ("the store holds this control with no VERIFIED-PASS rung -- deriving, and "
                          "saying so: known is not verified")
        return out
    out["verdict"], out["rung"], out["basis"] = VERIFIED, rung, BASIS_LEGACY
    out["why"] = ("the store holds a rung that passed live and did not fail last: %s %s "
                  "(a live verdict; no validation recorded -- D27)"
                  % (rung.get("kw"), list(rung.get("args") or [])))
    return out


def primary_and_backup(answer: dict, derived: dict | None) -> tuple:
    """(primary rung, backup rungs, why) for a composer, given a `consult` answer.

    The plan's phase-1 rule in one function: *"its best VERIFIED-PASS rung is the primary, the
    derived locator becomes a backup, only an unknown control is derived."*

    The derived rung is NEVER dropped when the store answers. It becomes a dormant backup, because
    the store's rung was verified on some past run and this page may have changed since -- and
    because a person reading the pane is owed the alternative the recorder would have proposed.
    That is the same rule F224 applies to the gesture's own stock lines.
    """
    if (answer or {}).get("verdict") == VERIFIED and answer.get("rung"):
        backups = [derived] if derived else []
        return answer["rung"], backups, "store rung (%s)" % answer.get("why", "verified")
    return derived, [], (answer or {}).get("why") or "no store answer -- derived"


# --------------------------------------------------------------- the store-led CALL (F246, C1)
# WHAT WENT WRONG. Phase 1 wired both recorders to consult, and then each rebuilt the store-led
# line from the rung's POSITIONAL ARGS ALONE. Measured by the challenge swarm's C1 over
# `docs/recorder/review/slockard-zoo-nightmare-inputs/capture.html` (84 controls, 73 store-led):
#
#   * `TypeText    Contract Term` -- the typed value GONE, on 5 rows. A Robot step that types
#     nothing, stamped `# verified: AI POM store rung, 1 live pass(es)`.
#   * `ClickItem    Toggle Panel` -- `tag=button` gone, which CLAUDE.md names by itself:
#     *"`ClickItem` silently finds nothing without an explicit `tag=`"*.
#   * `index` dropped on 37 of the 73, and `partial_match=False` on the 42 ClickText rows.
#   * all 73 store-led lines had FEWER cells than the derived line they replaced; 0 were equal.
#
# And the mirror image, which is why the value can never come from the rung: the Zoo_Aura_Inputs
# record stores `TypeText ["Close Date", "12/1/2026"]` -- a PAST RUN'S LITERAL. Replaying it would
# hard-code a 2026 date into every recording of that page, which is exactly what D19 / F141 /
# F146 exist to prevent.
#
# THE RULE, in one line: **the store's rung supplies the LOCATOR; the recorded event supplies the
# DATA.** Everything below is that sentence made checkable, and it lives here rather than in
# either recorder because the two produced DIFFERENT calls for the same control (C1: the Dock kept
# the rung's kwargs, the CRT composer dropped them) -- the divergence phase 1 existed to end.

#: keywords whose SECOND positional cell is DATA a person supplied, not part of the locator. The ONE
#: list lives in match.py (with the QWeb source lines it was read from), so the store's proven-call
#: identity (store.proven_call) and this merge read the same cells as data.
VALUE_KEYWORDS = MATCH.VALUE_KEYWORDS

#: keywords that locate by XPATH. `click_element(xpath, timeout, js, **kwargs)`
#: (QWeb/keywords/element.py:32) has NO `anchor`, no `tag` and no `partial_match` parameter, so
#: every one of them would be swallowed into `**kwargs` and silently ignored -- the green-signal
#: failure this codebase is named for. A merged call on one of these carries none of them.
XPATH_KEYWORDS = frozenset({"ClickElement", "VerifyElement"})

#: the only keywords that document a `tag=` argument (QWeb/keywords/text.py:929, `click_item`'s
#: own docstring: *"tag : html tag of preferred element"*). `click_text` has none.
TAG_KEYWORDS = frozenset({"ClickItem", "VerifyItem"})

#: kwargs that describe how to resolve a TEXT locator. Meaningless on an xpath keyword.
TEXT_RESOLUTION_KWARGS = ("index", "anchor", "tag", "partial_match", "css", "limit_traverse")


def merged_call(rung: dict | None, derived: dict | None = None,
                hints: dict | None = None) -> dict:
    """The call a STORE-LED step actually makes. ONE rule, both recorders, so they cannot diverge.

    `rung`    the store's best verified rung: {'kw', 'args', 'kwargs'}.
    `derived` the call this recorder would have made on its own: {'kw', 'args', 'kwargs'}.
    `hints`   what the CALLER's own row/event knows and neither call carries: `tag` (the real HTML
              tag) and `index` (this member's 1-based position among the same-label matches, the
              parser's DESCRIPTION -- D14).

    Returns {'kw', 'args', 'kwargs', 'from_store', 'why'}. `kwargs` are in the DESCRIBED form:
    `index`, never `anchor`. `disambiguation_args.to_call_kwargs` is still the ONE place that
    becomes QWeb's numeric `anchor=`, and it stays the caller's step (this module composes no
    line and imports no renderer).

    `from_store` False means the rung did NOT lead and the derived call stands -- `why` says which
    of the two reasons it was. That is the tri-state, held open: "the store knows this control" is
    not the same fact as "the store knows this step", and collapsing them hands a recorder a call
    nothing has ever run.
    """
    derived = dict(derived or {})
    d_args = [str(a) for a in (derived.get("args") or [])]
    stands = {"kw": derived.get("kw"), "args": list(d_args),
              "kwargs": dict(derived.get("kwargs") or {}), "from_store": False, "why": ""}
    r_kw = (rung or {}).get("kw")
    r_args = list((rung or {}).get("args") or [])
    if not r_kw or not r_args or not str(r_args[0]).strip():
        stands["why"] = "the store rung carries no locator -- the derived call stands"
        return stands

    # D19, and the Zoo_Aura_Inputs date: the rung's OWN args[1:] are a past run's data and are
    # dropped here, unconditionally. A stored literal never becomes a recorded value.
    data = list(d_args[1:])
    takes = 1 if r_kw in VALUE_KEYWORDS else 0
    if len(data) != takes:
        stands["why"] = (
            "the store's verified rung is %s (%d data cell%s) and the step recorded here is %s "
            "(%d) -- the rung resolves the control but cannot express THIS action, so it stands "
            "as a dormant backup and the derived call leads"
            % (r_kw, takes, "" if takes == 1 else "s", derived.get("kw"), len(data)))
        return stands

    # The rung's kwargs WIN over the derived ones: the rung passed live WITH them, and a call
    # assembled from a verified rung minus its own arguments is a call nothing has ever run.
    kwargs = dict(derived.get("kwargs") or {})
    kwargs.update(dict((rung or {}).get("kwargs") or {}))
    for key in ("tag", "index"):
        if key not in kwargs and (hints or {}).get(key) not in (None, "", 0):
            kwargs[key] = (hints or {})[key]
    if r_kw not in TAG_KEYWORDS:
        kwargs.pop("tag", None)
    if r_kw in XPATH_KEYWORDS:
        for key in TEXT_RESOLUTION_KWARGS:
            kwargs.pop(key, None)
    return {"kw": r_kw, "args": [str(r_args[0])] + data, "kwargs": kwargs, "from_store": True,
            "why": "the store's rung supplies the locator; the recorded step supplies the data"}
