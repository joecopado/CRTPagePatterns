"""Pure text-comparison helpers used by qforce_lite's click_text and
type_text_clearing guards -- no Selenium/QWeb/browser dependency, so these
can be (and are, see test_text_match.py) unit-tested offline with the exact
strings measured live against cicd-demo in
docs/specs/locator-stack-head-to-head.md (M2/M4) and cross-referenced in
docs/specs/silent-wrong-value-helpers.md.

Extracted as pure functions on purpose (the pattern Streams R5 and R17 used):
the actual bugs these guard against were never in string comparison -- they
were in which DOM node/attribute got compared -- but the comparison logic
itself is exactly the kind of thing that's easy to get subtly wrong (does
"Save" match "Save "? does normalization eat a real difference like
"20be" vs "R20probe"?), so it gets its own tested module rather than being
inlined and trusted.
"""
from __future__ import annotations

import re


def normalize_visible_text(text: str | None) -> str:
    """Collapse all whitespace (including newlines) to single spaces and
    strip the ends. Used to compare a resolved element's rendered text
    against an author-level handle without being tripped up by incidental
    whitespace differences Lightning's markup introduces -- but NEVER used
    for substring/containment checks, only for exact-equality checks, since
    containment is the exact failure mode being guarded against."""
    return " ".join((text or "").split())


def resolved_text_matches(requested: str, resolved_text: str) -> bool:
    """True iff a ClickText/VerifyText-style resolution's target text is an
    EXACT match (after whitespace normalization) for the handle that was
    asked for. Deliberately not `requested in resolved_text` -- that is
    precisely the silent-overshoot bug this guards against: QWeb's own
    resolver falls back to a `contains()` xpath whenever a call site doesn't
    explicitly request partial matching (QWeb's ContainingTextMatch/
    PartialMatch default is True at the config level), so "Save" legitimately
    "contains-matches" "Save & New" -- exact identity is the only check that
    tells the two apart.
    """
    return normalize_visible_text(requested) == normalize_visible_text(resolved_text)


def needs_retype_repair(typed: str, actual_value: str | None) -> bool:
    """True iff a just-typed field's actual value does not match what was
    typed and therefore needs type_text_clearing's clear()+send_keys()
    repair pass. `actual_value=None` means the repair pass could not resolve
    a real input value at all -- historically (before this fix) that was
    read as "nothing to repair" and silently skipped, which is exactly the
    M4 bug: the caller re-resolved by LABEL text, got a node with no
    `.value`, and treated that null as success. This function does not fix
    that by itself (the real fix is resolving the correct WebElement in the
    first place, in qforce_lite.type_text_clearing) -- it only makes the
    comparison decision testable in isolation.
    """
    if actual_value is None:
        return False
    a, t = _normalize_field_text(actual_value), _normalize_field_text(typed)
    if a == t:
        return False
    # Numeric fields REFORMAT on blur, and that is correct behaviour, not a failure.
    # Measured live on a real New Opportunity form 2026-08-30: typing "25000" into Amount left the
    # field holding "25,000.00". The value had landed perfectly, but a string compare called it
    # "value did not land" -- a FALSE failure introduced by the new mandatory verification, which
    # is the standing risk of adding an assertion. Compare numerically when BOTH sides are numbers.
    # Deliberately narrow: this must not rescue the corruption cases it exists to catch --
    # "202,525%" vs "25" still differ numerically, and "(415) 901-7000R20probe" is not a number
    # at all, so both stay caught. Pinned by tests in test_text_match.py.
    ta, tt = _as_number(a), _as_number(t)
    if ta is not None and tt is not None:
        return ta != tt
    # Date fields re-render too (user-watched 2026-09-08: typed '10/08/2026', control shows
    # '10/8/2026'); a zero-padding difference is the same value, not a failed type.
    da, dt = _as_date(a), _as_date(t)
    if da is not None and dt is not None:
        return da != dt
    return True


_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$|^(\d{4})-(\d{2})-(\d{2})$")


def _as_date(text: str) -> str | None:
    """'M/D/YYYY', 'MM/DD/YYYY' or ISO -> 'YYYY-MM-DD', else None."""
    m = _DATE_RE.match(text.strip())
    if not m:
        return None
    if m.group(1):
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return f"{m.group(4)}-{m.group(5)}-{m.group(6)}"


def _as_number(text: str) -> float | None:
    """Parse a normalised field value as a number, or None if it is not purely numeric."""
    cleaned = text.replace("$", "").replace("\u00a0", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_field_text(text: str) -> str:
    """Strips display-only formatting (thousands commas, %, surrounding
    whitespace) so a typed value and the field's actual resulting value can
    be compared for real equality, not just substring containment --
    containment is NOT safe here: a corrupted, concatenated value like
    "202,525%" still contains "25" as a substring even though it's wrong."""
    return text.replace(",", "").replace("%", "").strip()


# ---------------------------------------------------------------------------
# AmbiguousTextError message formatting (pure, no Selenium/QWeb dependency).
#
# qforce_lite.py's click_text needs real QWeb resolution to find CANDIDATE elements (that part
# lives in qforce_lite.py itself, next to the resolver calls it needs), but the FORMATTING of
# what to tell the caller about those candidates has no browser dependency at all -- it only
# needs each candidate to expose `.tag_name` and `.get_attribute(name)`, which a real Selenium
# WebElement does and so does a plain duck-typed fake, so this half is pulled out here (same
# reuse pattern this module's own docstring already documents for Streams R5/R17) and unit-tested
# offline in test_click_guard.py without a browser or a QConnect interpreter.
# ---------------------------------------------------------------------------


def describe_ambiguous_candidates(text: str, candidates: list) -> list[str]:
    """One short, human-usable line per ambiguous candidate: its real HTML tag (never the ARIA/
    behavioural role -- this project's own standing rule for ClickItem's `tag=`) plus a short
    xpath that targets it specifically. Prefers a stable identifying attribute
    (`data-testid`/`id`/`name`/`aria-label`) over a positional index, since a positional index is
    exactly the kind of locator that silently breaks the next time the DOM order changes -- the
    same class of fragility this whole guard exists to catch.

    `candidates` items only need `.tag_name` and `.get_attribute(name)` -- a real Selenium
    WebElement satisfies this, and so does a simple fake, which is what makes this testable with
    no browser at all."""
    lines = []
    for i, el in enumerate(candidates, start=1):
        try:
            tag = el.tag_name
        except Exception:
            tag = "?"
        xp = None
        for attr in ("data-testid", "id", "name", "aria-label"):
            try:
                val = el.get_attribute(attr)
            except Exception:
                val = None
            if val:
                xp = f'//{tag}[@{attr}="{val}"]'
                break
        if xp is None:
            xp = f'(//{tag}[normalize-space(.)="{text}"])[{i}]'
        lines.append(f"#{i} <{tag}> {xp}")
    return lines


def ambiguous_text_message(text: str, candidates: list) -> str:
    """The AmbiguousTextError message body: the count, each candidate's description, and the fix
    (`pass anchor=N`, or `ClickItem` with an explicit `tag=`) -- see qforce_lite.py's
    AmbiguousTextError docstring for the live-measured bug this exists to name loudly instead of
    silently clicking DOM-order match #1."""
    desc = "\n  ".join(describe_ambiguous_candidates(text, candidates))
    return (
        f"ClickText({text!r}) found {len(candidates)} VISIBLE elements with exactly this text -- "
        f"refusing to silently pick one. The default anchor (\"1\") would take DOM-order match #1, "
        f"which may not be the control you mean. Candidates:\n  {desc}\n"
        f"Fix: pass anchor=\"N\" (1-based, matching the order above), or use ClickItem with an "
        f"explicit tag= and a distinguishing attribute (e.g. data-testid) instead of text alone."
    )
