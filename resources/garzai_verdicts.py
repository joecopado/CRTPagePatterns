"""garzai_verdicts -- ONE session-wide verdict ledger for a CRT recording / Live Testing run, and
the ONE tally that prints it (F192, 2026-09-20).

WHY THIS EXISTS (docs/recorder/evidence/editor-session-n9-2026-09-20.md, F188 CAUGHT-BUG 6):
the n9 editor session ended on `Gz Mismatch Tally` printing `GarzAI TypeText mismatches this
session: 0` -- over a run with two `QWebElementNotFoundError`s, three steps the user had to Stop
by hand, and one vacuous green (a typeable combobox that read back the typed stamp and then
cleared it).  That tally counted exactly one thing, the TypeText override's own read-back
mismatches, and every other red in the session was invisible to it.  A summary that looks
complete stops you looking (CLAUDE.md, the no-silent-truncation rule).

WHAT IT DOES:
  * A LEDGER, module-global on purpose.  `garzai_recorder_override.py` keeps its STATE the same way
    and a Live Testing session has been measured to keep that process alive across selections
    (`served: 86` over one recording); a `Set Suite Variable` list is scoped to one execution and
    whether it survives a selection boundary is COULD-NOT-CHECK (the n9 tally read 0 and nothing
    says which of "no mismatch fired" or "the list was reset" produced it).
  * A LISTENER (Robot listener API v3, registered through `ROBOT_LIBRARY_LISTENER`), so a step the
    RESOURCES never see -- a stock `ClickElement` that raised, a `TypeText` the user Stopped --
    still lands in the ledger, from Robot's own result.  Only the OUTERMOST keyword of a step is a
    row (depth 1: a keyword whose parent is the test, a setup or a teardown), carrying the
    innermost message Robot already propagated to it; a keyword three frames down never becomes a
    second row.
  * Four classes and nothing else (CLAUDE.md): VERIFIED-PASS (a read-back matched), CAUGHT-BUG (a
    read-back mismatched, a sentinel landed, or the step RAISED -- an action that could not act
    is still a failure), COULD-NOT-CHECK (the step was STOPPED before it finished, or nothing could
    be read back), PASS-GUARDED (an ACTION keyword -- owner QForce / QWeb -- ended PASS with no
    verdict recorded inside it: the click landed, nothing says the page took it; F188's
    `ClickText Next` on a form that refused the click).  BuiltIn / Collections / String / the Gz
    resources are bookkeeping and never a row on their own.
  * ONE tally: `Gz Verdict Tally` prints a table (step, verdict class, value read back) and one
    summary line `VERIFIED-PASS n / CAUGHT-BUG n / COULD-NOT-CHECK n / PASS-GUARDED n`, then
    `red steps this session: N` where N counts CAUGHT-BUG + COULD-NOT-CHECK; `0` is therefore
    printed only when every step was green.  `Gz Mismatch Tally` (typetext override) and
    `Gz Omni Verdict Tally` (omni) both delegate here, so the suite's existing last step keeps
    working and prints the whole picture.

WRITERS: `Gz Report Mismatch` and the VERIFIED-PASS branch of the TypeText override, `Gz Omni
Verdict`, `Gz Sentinel Verdict` -- each calls `Gz Record Verdict <class> <step> <value>`.

Shipped beside the resources (`resources/garzai_verdicts.py` in CRTPagePatterns; each resource
imports it as `Library ${CURDIR}/garzai_verdicts.py`).  Source of truth:
tools/recorder/crt_override/garzai_verdicts.py; the vendored copy under
tools/recorder/tests/fixtures/omni_robot_clone_2026_09_19/resources/ is pinned byte-identical by
tools/recorder/tests/test_crt_override_verdict_tally_2026_09_20.py.  Pure stdlib + robot.api.
"""
from __future__ import annotations

import re
import threading

try:
    from robot.api import logger as _logger
except Exception:  # pragma: no cover - outside Robot (a plain import for the tests)
    _logger = None

CLASSES = ("VERIFIED-PASS", "CAUGHT-BUG", "COULD-NOT-CHECK", "PASS-GUARDED")
RED = ("CAUGHT-BUG", "COULD-NOT-CHECK")
# The libraries whose keywords ACT on the page.  A PASS from one of these with no verdict
# recorded inside it is PASS-GUARDED; a PASS from anything else is bookkeeping.
ACTION_OWNERS = ("QForce", "QWeb", "QMobile", "QVision")
# CRT's own wording for a step the user stopped ("Stopped keyword execution"), Robot's for a
# signal ("Execution terminated by signal"), and the generic shapes between them.
STOP_RX = re.compile(r"(?i)\bstopp?(ed|ing)?\b|terminat|interrupt|abort")
MSG_CHARS = 160  # a table cell; the full message is in the run's own log, which is named

_LOCK = threading.Lock()
LEDGER = {"rows": [], "frames": []}   # frames: one dict per open keyword (depth = len)


def _console(text):
    if _logger is not None:
        _logger.console(text)
    else:  # pragma: no cover
        print(text)


def _cut(s, n=MSG_CHARS):
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1] + "…" + " (%d chars; full text in the run log)" % len(s)


class garzai_verdicts:
    """The library.  GLOBAL scope so one instance (and one listener) serves the whole run; the
    ledger itself is module-global so even a re-import shares it."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self

    # ------------------------------------------------------------------ the listener half
    def start_keyword(self, data, result):
        with _LOCK:
            LEDGER["frames"].append({"verdicts": 0})

    def end_keyword(self, data, result):
        with _LOCK:
            frame = LEDGER["frames"].pop() if LEDGER["frames"] else {"verdicts": 0}
            depth = len(LEDGER["frames"])
        if depth != 0:
            return                      # not the outermost keyword of a step: never a row
        if str(getattr(result, "type", "KEYWORD") or "KEYWORD").upper() != "KEYWORD":
            return                      # FOR / IF / TRY bodies are not steps
        status = str(getattr(result, "status", "") or "").upper()
        step = self._step_name(result)
        if status == "FAIL":
            msg = str(getattr(result, "message", "") or "")
            if STOP_RX.search(msg):
                self._record("COULD-NOT-CHECK", step, "stopped: " + _cut(msg),
                             source="listener")
            else:
                self._record("CAUGHT-BUG", step, "raised: " + _cut(msg), source="listener")
            return
        if status == "PASS" and not frame.get("verdicts"):
            owner = str(getattr(result, "owner", "") or "")
            if owner in ACTION_OWNERS:
                self._record("PASS-GUARDED", step,
                             "the action ran; nothing read the page back", source="listener")

    @staticmethod
    def _step_name(result):
        name = str(getattr(result, "name", "") or "")
        args = getattr(result, "args", None) or ()
        cells = [name] + [str(a) for a in list(args)[:2]]
        return _cut("    ".join(c for c in cells if c), 96)

    # ------------------------------------------------------------------ the keyword half
    def _record(self, verdict, step, value, source="keyword"):
        verdict = str(verdict or "").strip().upper()
        if verdict not in CLASSES:
            raise ValueError("verdict %r is not one of %s -- no bare FAIL, no 'guard' (CLAUDE.md)"
                             % (verdict, "/".join(CLASSES)))
        with _LOCK:
            LEDGER["rows"].append({"n": len(LEDGER["rows"]) + 1, "step": str(step or ""),
                                   "verdict": verdict, "value": "" if value is None else str(value),
                                   "source": source})
            for fr in LEDGER["frames"]:
                fr["verdicts"] = fr.get("verdicts", 0) + 1
        return len(LEDGER["rows"])

    def gz_record_verdict(self, verdict, step, value=""):
        """Land one verdict in the session ledger: ``Gz Record Verdict    <class>    <step>
        <value read back>``.  Called by every verdict line the resources print (TypeText,
        Omni, sentinel); a caller of its own may call it too.  Returns the row count."""
        return self._record(verdict, step, value)

    def gz_verdict_rows(self):
        """The ledger rows as a list of dicts (n, step, verdict, value, source)."""
        with _LOCK:
            return [dict(r) for r in LEDGER["rows"]]

    def gz_verdict_reset(self):
        """Empty the ledger (a suite that wants per-test tallies)."""
        with _LOCK:
            n = len(LEDGER["rows"])
            LEDGER["rows"] = []
        return n

    def gz_verdict_tally(self):
        """Print EVERY verdict of the session as one table plus the four-class summary, and
        return the number of red steps (CAUGHT-BUG + COULD-NOT-CHECK).  0 only when every step
        was green."""
        rows = self.gz_verdict_rows()
        counts = {c: 0 for c in CLASSES}
        for r in rows:
            counts[r["verdict"]] += 1
        red = sum(counts[c] for c in RED)
        _console("GarzAI verdict tally -- %d step%s recorded this session"
                 % (len(rows), "" if len(rows) == 1 else "s"))
        _console("| # | step | verdict | value read back |")
        _console("|---|---|---|---|")
        for r in rows:
            _console("| %d | %s | %s | %s |" % (r["n"], r["step"], r["verdict"], _cut(r["value"])))
        _console("VERIFIED-PASS %d / CAUGHT-BUG %d / COULD-NOT-CHECK %d / PASS-GUARDED %d"
                 % tuple(counts[c] for c in CLASSES))
        _console("red steps this session: %d" % red)
        return red
