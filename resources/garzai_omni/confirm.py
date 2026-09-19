"""confirm -- one read-back check, used by every keyword that returns a value.

THE FAILURE THIS EXISTS TO MAKE IMPOSSIBLE
------------------------------------------
Six times in one codebase, a helper resolved the WRONG element and returned a
plausible-looking value. Nothing errored. Every test built on it passed. Measured,
all live:

  get_field_value("Stage")        -> "Stage"                    (the LABEL, not the value)
  get_highlight_field("Stage")    -> ":Proposal"                (label carries a colon)
  get_table_cell_by_header(...)   -> "...Contact 1-1Preview"    (hidden hover action leaked in)
  get_record_field("Account Owner")-> "Joseph GarzaPreviewChange Owner"
  ClickText("Save")               -> clicked "Save & New"       (superstring overshoot)
  TypeText("Phone","R20probe")    -> "(415) 901-7000R20probe"   (appended, guard skipped itself)

Each was fixed individually. That is the problem: six individual fixes and nothing
stopping a seventh. This module is the general form, and `test_confirm.py` fails the
build if a value-returning keyword does not route through it.

SAME FAMILY, A SECOND TOOL DIRECTORY: `tools/crt-runtime/SfDom.py` (a different Robot
Framework keyword library, not this one) was never wired into this enforcement and had
the identical failure, live-confirmed:

  get_table_cell_by_header(...)   -> "...GZD0060 Contact 1-1Preview"  (hover action
                                      glued onto the cell's real text, no separator)
  get_record_field("Account Owner") w/o tag= -> "Joseph GarzaPreviewChange Owner"
                                      (same: a hidden hover/menu action leaked in)

Neither is the "own label" bug the six above are -- the label/header text isn't what
leaked in, a Lightning row's hover-action text is. `no_hover_chrome` below is the
general form of THIS shape, added when SfDom.py was brought under this same
enforcement (see test_confirm.py's `test_sfdom_getters_route_through_confirm`).

THE RULE, in one line:
    If a wrong resolution could produce a plausible-looking value, read the value back
    and compare it to what you asked for.

Every check below uses data the caller ALREADY HAS. None of them loosen anything, and
none require an extra round trip to the page.
"""
from __future__ import annotations

import re
from datetime import datetime as _datetime, timezone as _timezone
from decimal import Decimal, InvalidOperation


class SilentWrongValue(AssertionError):
    """Raised when a read-back contradicts what was asked for.

    Deliberately its own class, and deliberately loud. The whole failure family is
    defined by being quiet, so the fix must be the opposite: a distinct, greppable
    exception naming what was asked, what came back, and why they disagree.
    """


class CouldNotCheck(SilentWrongValue):
    """The THIRD state, as its own class (user, 2026-09-08).

    `unreadable()` used to raise plain SilentWrongValue, so a blank read-back (could not
    check) was indistinguishable from a real mismatch (false). A retry path that catches the
    mismatch then REPEATS the action -- measured live on slockard 2026-09-08: combo_box read
    the committed pill as blank, raised, and the retry re-typed the search string into the
    pill, clearing a correct selection. Catching SilentWrongValue still catches this (it is
    a subclass) -- but a repair/retry path must `except CouldNotCheck: raise` first.
    """


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


#: Lightning renders a REQUIRED field's label with an asterisk marker, and the marker is
#: part of the text a label-matching locator scrapes: 'Stage' reads back as '*Stage' (and
#: as 'Stage *' in the v3 parser's index for the same control). Measured live on slockard's
#: New Opportunity modal, 2026-09-07 -- the marker made '*Stage' unequal to 'Stage', so the
#: label-echo guard below missed on every REQUIRED field while still firing on optional
#: ones. Required fields are exactly the fields tests assert on, so the guard was inverted
#: where it mattered most. Stripped for COMPARISON ONLY -- `got` is always returned
#: byte-identical, so a genuine value containing an asterisk is never rewritten.
_REQUIRED_MARKER = re.compile(r"^[\s*]+|[\s*]+$")


def _norm_marker(s: str | None) -> str:
    """`_norm`, with any required-marker asterisks stripped from both ends."""
    return _REQUIRED_MARKER.sub("", _norm(s))


def field_value(label: str, got: str | None, *, where: str = "") -> str | None:
    """A field's VALUE must not be its own LABEL.

    The original bug: the xpath searched //span inside the field's ancestor, and the
    label renders as an earlier sibling <span>, so it silently won every time.

    The 2026-09-07 bug: the same thing, wearing the required marker ('*Stage'), which
    slipped past both arms below until they compared marker-stripped forms.
    """
    g, l = _norm_marker(got), _norm_marker(label)
    if g and g.casefold() == l.casefold():
        raise SilentWrongValue(
            f"read the LABEL instead of the value for {label!r}"
            + (f" ({where})" if where else "")
            + f" -- got {got!r}. The locator matched the field's label element."
        )
    # a label that merely prefixes the value ("Stage:Proposal", "Stage Proposal")
    if g and l and g.casefold().startswith(l.casefold()):
        tail = g[len(l):].lstrip(": \t")
        if tail:
            raise SilentWrongValue(
                f"value for {label!r} still carries its label prefix -- got {got!r}, "
                f"meant {tail!r}. Strip the rendered label (it may carry a colon the "
                f"passed-in string does not)."
            )
    return got


def resolved_text(requested: str, actual: str | None, *, exact: bool = True) -> str | None:
    """What we clicked must be what we asked for.

    The original bug: ClickText("Save") resolved "Save & New" in an edit modal --
    deterministic, silent, and it clicks a genuinely different control.
    """
    r, a = _norm(requested), _norm(actual)
    if not a:
        return actual
    if exact and r.casefold() != a.casefold():
        raise SilentWrongValue(
            f"asked for {requested!r} but resolved {actual!r} -- a superstring or "
            f"neighbouring element won. Anchor the locator or pass an exact match; do "
            f"NOT loosen matching to make this pass."
        )
    if not exact and r.casefold() not in a.casefold():
        raise SilentWrongValue(f"asked for {requested!r}, resolved {actual!r} -- no overlap.")
    return actual


def typed_value(typed: str, actual: str | None, *, field: str = "",
                describe_type: str | None = None) -> str | None:
    """After typing, the field must contain what we typed -- compared by MEANING.

    The original bug: the repair pass re-resolved using the LABEL, got no .value back,
    and skipped -- so the guard its own docstring promised never ran. Result was an
    append: "(415) 901-7000R20probe".

    2026-09-08 (user-watched): a raw casefold string compare killed a live run on a date
    that had landed -- typed '10/08/2026', the control re-rendered '10/8/2026'. Values are
    now routed through `normalise()`: with a `describe_type` that type's rule applies; with
    none, both sides are tried as a date and as a number and compared on that reading when
    BOTH parse, else normalize-space + casefold. The corruption shapes stay caught:
    '(415) 901-7000R20probe' is neither a date nor a number, '202,525%' != '25'.
    """
    t, a = _norm(typed), _norm(actual)
    if a is None or a == "":
        raise CouldNotCheck(
            f"could not read back {field or 'the field'} after typing {typed!r}. "
            f"Unverified is not verified -- re-resolve with a locator that yields .value."
        )
    if lenient_equal(t, a, describe_type):
        return actual
    if a.casefold().startswith(t.casefold()):
        extra = a[len(t):]
        why = f" -- {extra!r} was appended after the typed value"
    elif a.casefold().endswith(t.casefold()):
        extra = a[:len(a) - len(t)]
        why = f" -- the old value {extra!r} was not cleared, the typed value was appended to it"
    else:
        why = f" -- field holds {actual!r}"
    raise SilentWrongValue(f"typed {typed!r} into {field or 'field'}{why}.")


def lenient_equal(expected, actual, describe_type: str | None = None) -> bool:
    """Meaning-equality for a RENDERED value against what was asked (user, 2026-09-08).

    With a describe_type: `normalise()` for that type. Without one: equal if both sides parse
    as the same date, or as the same number, or match after normalize-space + casefold.
    Never rescues a blank actual (that is could-not-check, handled by the caller) and never
    a genuinely different value: '10/08/2026' == '10/8/2026' and '25000' == '25,000.00',
    but 'Save' != 'Save & New' and '25' != '202,525%'.
    """
    if describe_type:
        return normalise(expected, describe_type) == normalise(actual, describe_type)
    e, a = _norm(str(expected)), _norm(str(actual))
    if e.casefold() == a.casefold():
        return True
    ne, na = normalise(e, "double"), normalise(a, "double")
    if isinstance(ne, Decimal) and isinstance(na, Decimal):
        return ne == na
    de, da = normalise(e, "date"), normalise(a, "date")
    if _ISO_DATE_RE.match(str(de)) and _ISO_DATE_RE.match(str(da)):   # both parsed as dates
        return de == da
    return False


def selection(asked: str, shown: str | None, *, control: str = "") -> str | None:
    """A picklist/combobox must display the option we chose.

    Also the locale trap: an org rendering Spanish shows "Analista" where the API value
    is "Analyst". A mismatch here is real information, not noise.

    BLANK RULE (2026-09-07, vacuous-pass fix): a `None`/empty `shown` used to fall through
    the `if s and ...` guard untouched and return `shown` (i.e. `None`) as if it were a
    passing read-back -- exactly the shape measured live on slockard's Zoo_Screen_Components
    flow, where `pick_list()` reported success against a native `<select>` it never actually
    touched (its `Select(...).first_selected_option.text` came back blank). `typed_value` and
    `field_state` in this same file already refuse a blank read-back via `unreadable()`; this
    function was the one holdout. Never let a blank actual collapse into a pass -- see
    `equal()`'s BLANK RULE.
    """
    a, s = _norm(asked), _norm(shown)
    if not s:
        unreadable(f"the selection on {control or 'the control'}", tried=f"selected {asked!r}")
    if not lenient_equal(a, s) and a.casefold() not in s.casefold():
        raise SilentWrongValue(
            f"selected {asked!r} on {control or 'the control'} but it displays {shown!r}. "
            f"Either the pick did not take, or the org renders a different locale for that "
            f"option (the API value and the rendered label are not the same string)."
        )
    return shown


def field_state(expected: bool, actual: bool | None, *, control: str = "", state: str = "") -> bool:
    """A control's boolean state (required/disabled/readonly) must match what was asked.

    Same shape as `selection` (a picklist's displayed option) and `typed_value` (a field's
    text after typing): the caller already has both the ask and the read-back, this just
    refuses to let a mismatch -- or an unreadable state -- pass quietly. `actual is None` is
    routed through `unreadable()` by the caller BEFORE this is reached in the normal case
    (verify_field_state's own could-not-check path), but this still guards it directly so a
    future caller that skips that step fails loudly rather than comparing None == expected.
    """
    if actual is None:
        unreadable(f"{state or 'state'} of {control or 'the control'}", tried=f"expected {expected!r}")
    if bool(actual) != bool(expected):
        raise SilentWrongValue(
            f"{state or 'state'} of {control or 'the control'} expected {expected!r}, got {actual!r}."
        )
    return actual


_HOVER_ACTION_TOKENS = (
    "Preview", "Change Owner", "Edit", "Delete", "View All", "Follow",
    "Following", "Clone", "Remove", "Show More", "Load More",
    "More Actions", "Log a Call", "New Task", "New Event",
)


def no_hover_chrome(value: str | None, *, where: str = "") -> str | None:
    """A read value must not carry a Lightning hover/menu action glued onto its tail.

    The original bugs (SfDom.py, tools/crt-runtime/, live-confirmed):
        get_record_field("Account Owner")   -> "Joseph GarzaPreviewChange Owner"
        get_table_cell_by_header(...)       -> "...Contact 1-1Preview"

    Lightning renders a row/field's hover actions (Preview, Edit, Change Owner, ...)
    into the DOM even though they are only visible on :hover -- the CSS that hides
    them adds no text-node boundary, so a GetText over the field/row's whole
    ancestor container (rather than just the value node) can pick the action text
    up with NO separating whitespace.

    Deliberately a known-token check, not a blanket "capital letter after a
    lowercase letter" heuristic: real display values legitimately contain internal
    capitals with no space ("iPhone", "McAfee", part numbers), so a blanket
    heuristic would false-positive on real data constantly. This only fires when a
    known Lightning action word is glued directly onto the immediately preceding
    character with no space -- exactly the shape both measured bugs share.

    A glued-on-the-tail check ALSO isn't enough by itself: real generated test data
    (e.g. "QFLProof-QBranchEditNoArg-4ee7b4") embeds an action word like "Edit"
    mid-token, glued on BOTH sides, as part of an unbroken identifier -- 6/20 real
    dev1 Account rows hit this false positive (docs/ERRORS.md 87b14132ec). Both
    live bugs share a second trait the false positive does not: the token sits at
    a TRAILING boundary -- either the end of the whole string, or immediately
    followed by whitespace, or immediately followed by another known hover-action
    token (Lightning chains them: "...PreviewChange Owner"). A legitimate glued
    token is instead followed by more of the same unbroken identifier ("NoArg...",
    "REAL..."). So this only fires when BOTH sides are glued: no separating
    whitespace before the token AND no separating boundary after it.
    """
    v = value if value is not None else ""
    for token in _HOVER_ACTION_TOKENS:
        idx = v.find(token)
        while idx != -1:
            glued_before = idx > 0 and not v[idx - 1].isspace()
            tail = v[idx + len(token):]
            glued_after = tail != "" and not tail[0].isspace() and not any(
                tail.startswith(t) for t in _HOVER_ACTION_TOKENS
            )
            if glued_before and not glued_after:
                raise SilentWrongValue(
                    f"value carries a glued-on hover action {token!r}"
                    + (f" ({where})" if where else "")
                    + f" -- got {value!r}. A hidden Lightning row/hover action leaked "
                      f"into the read text with no separating whitespace; re-scope the "
                      f"xpath to the value node itself, not its whole container."
                )
            idx = v.find(token, idx + 1)
    return value


_NUMERIC_TYPES = {"int", "double", "currency", "percent"}
_RICHTEXT_WRAP_RE = re.compile(r"^\s*<p>(.*)</p>\s*$", re.IGNORECASE | re.DOTALL)
_US_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _to_utc_minute(value):
    """Parse an ISO-ish datetime string and truncate it to the minute in UTC.

    ASSUMPTION (stated per this task's rule, never silently baked in): the caller has
    already converted any org/user-local wall-clock input into an ISO string using the
    org's own TimeZoneSidKey -- ui_case_runner.py's `_expected_datetime_iso` does exactly
    that for the 'want' side; SOQL's own datetime serialization is already UTC with a
    numeric offset for the 'got' side. This function does not itself know the org's
    timezone -- it only puts two already-timezone-aware ISO strings on the same UTC-minute
    footing so a real comparison is not defeated by fractional-second noise or an offset
    written as '+0000' on one side and '+00:00' on the other.
    """
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)  # +0000 -> +00:00
    try:
        dt = _datetime.fromisoformat(s)
    except ValueError:
        return _norm(str(value))
    if dt.tzinfo is not None:
        dt = dt.astimezone(_timezone.utc)
    return dt.replace(second=0, microsecond=0)


def normalise(value, describe_type: str | None):
    """Reduce a value to a type-appropriate canonical form so two representations of the
    SAME underlying value compare equal -- e.g. a typed sample `'7.5'` against SOQL's
    `7.5` float, or a typed `'12/31/2026'` against SOQL's `'2026-12-31'` ISO date.

    THE FAILURE THIS EXISTS TO MAKE IMPOSSIBLE (BACKLOG row 85, UI-BATTERY.md Run 2 SS10.2):
    `ui_case_runner.py` compared `rows[0].get(k) != v` -- a raw Python `!=` between whatever
    SOQL returned (a real int/float/str) and whatever string the generator had typed. Twelve
    genuinely-correct saves were reported FAIL because the SAME field, correctly saved, comes
    back from SOQL and from the UI as two different Python representations of one value. Every
    one of those twelve had to be hand-reclassified by an independent `sf data query` re-check
    -- this function is the general form, so the next run does not repeat that hand review.

    Per-type rule (this task's spec, docs/crt-train/COMPARATOR.md SS1):
      - int / double / currency / percent -> Decimal, after stripping thousands separators
        and a leading currency symbol (and a trailing '%' for percent)
      - date -> ISO 'YYYY-MM-DD' (accepts a US 'MM/DD/YYYY' display form on either side --
        the only locale form measured live on slockard/dev1, control-signatures/*/date-*.json)
      - datetime -> UTC, truncated to the minute (see `_to_utc_minute`)
      - boolean -> True/False, accepting '1'/'0'/'true'/'false'/'yes'/'no'/'on'/'off'
      - textarea -> the platform's single `<p>...</p>` wrap stripped (a rich-text field
        renders as `textarea` in describe with no separate type; a PLAIN textarea's value
        never happens to match that wrap, so the strip is a no-op for it), then
        normalize-space
      - everything else -> normalize-space, exact

    `describe_type` is the Salesforce field describe `type` string (predict.py's own
    vocabulary: string/email/phone/url/textarea/picklist/multipicklist/reference/boolean/
    date/datetime/currency/double/int/percent). An unknown or missing type falls through to
    the default (normalize-space, exact) rather than raising -- a type this function does not
    know yet is not evidence the values differ.
    """
    if value is None:
        return None
    t = (describe_type or "").lower()

    if t in _NUMERIC_TYPES:
        s = str(value).strip().replace(",", "")
        s = re.sub(r"^[^\d+\-.]+", "", s)   # strip a leading currency symbol ($, USD, etc.)
        s = s.rstrip("%").strip()
        try:
            return Decimal(s)
        except InvalidOperation:
            return _norm(str(value))

    if t == "date":
        s = str(value).strip()
        m = _ISO_DATE_RE.match(s)
        if m:
            return m.group(1)
        m = _US_DATE_RE.match(s)
        if m:
            mm, dd, yyyy = m.groups()
            return f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
        return _norm(s)

    if t == "datetime":
        return _to_utc_minute(value)

    if t == "boolean":
        s = str(value).strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
        return s

    if t == "textarea":
        s = str(value)
        m = _RICHTEXT_WRAP_RE.match(s)
        if m:
            s = m.group(1)
        return _norm(s)

    return _norm(str(value))


def equal(expected, actual, describe_type: str | None) -> bool:
    """Type-aware equality between an EXPECTED value (what a case asked to be saved) and an
    ACTUAL value (a SOQL read-back) -- the comparator `ui_case_runner.py` should call instead
    of its own raw `!=` (BACKLOG row 85).

    BLANK RULE: an actual that is `None` or an empty/whitespace-only string never compares as
    a plain `False` -- it raises via `unreadable()` instead. A blank actual is not "the values
    differ", it is "we could not read a value back at all", and the tri-state rule (true /
    false / could-not-check) says that third state must never collapse into a plain failed
    comparison a caller could silently count and move past, any more than into a plain pass.
    """
    if actual is None or (isinstance(actual, str) and actual.strip() == ""):
        unreadable(
            f"a describe_type={describe_type!r} field's actual value",
            tried=f"expected {expected!r}",
        )
    return normalise(expected, describe_type) == normalise(actual, describe_type)


def unreadable(what: str, *, tried: str = "") -> None:
    """Explicit 'I could not check this'. Call it instead of returning quietly.

    Tri-state discipline: true / false / could-not-check. Letting the third collapse into
    the first is the shared root of every bug in this file's header.
    """
    raise CouldNotCheck(
        f"could not verify {what} -- reporting UNKNOWN rather than passing."
        + (f" Tried: {tried}" if tried else "")
    )
