"""garzai_parser_walkthrough -- the parser's pipeline, one stage at a time, in plain words.

WHY THIS FILE EXISTS (user, 2026-10-07): "a test that I can run: what happens from the parsers, step
by step ... how things happen and what actually goes over to the AI: that breakdown of things, the
sequencing." tests/parser-walkthrough.robot is that test. Every stage that already has a keyword
uses it (Open Nav Tab, Gz Read Page); the three stages that had NONE -- the capture, the parse and
the proposed calls -- have a keyword here, because the page reader (garzai_page_reader.py) runs all of
them inside ONE keyword and prints only the last stage.

NOTHING IS RE-IMPLEMENTED. Each keyword calls the same functions Gz Read Page calls, on the same
parser bundle (resources/garzai_parser):

  Gz Walk Capture      compose_live.live_capture   the page serialized as the parser receives it
  Gz Walk Parse        compose_live.parse_capture  the parser's elements (label / family / tag)
  Gz Walk Calls        garzai_page_reader.build_plan   the proposed call and its backup per control
  Gz Walk Pages Total  reads the `page 1 of N` pointer the page reader prints
  Gz Walk Plan Size    counts the lines and bytes of the page-reader text the AI is given
  Gz Walk Summary      one closing line: page KB -> parser elements -> plan lines / bytes

The stage that goes to the AI (`Gz Read Page`) is the page reader's own keyword, called from the
suite; this file only measures what it returned. This file reads the page and never acts on it: no
click, no type, no save. Every keyword prints to the console AND the Robot log.

ONE ENVIRONMENT FACT THIS SUITE SURFACED (first CRT build of it, 2026-10-07, build 6195617): the parser
bundle imports `lxml`, a compiled extension that cannot be vendored, and the CRT BUILD container did not
have it (`ModuleNotFoundError: No module named 'lxml'`) -- the same import Gz Read Page makes. Gz Walk
Capture therefore installs lxml for the run only (pip --target a temp folder) when it is missing, says so
on the console, and reports COULD-NOT-CHECK with pip's reason if that fails too.

Shipped beside garzai_page_reader.py; imported by tests/parser-walkthrough.robot only (not by
common.robot, so the Test Agent's keyword list is unchanged). The parser bundle is untouched.
"""
from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback

try:
    from robot.api import logger as _logger
    from robot.api.deco import keyword
except Exception:  # pragma: no cover - outside Robot
    _logger = None

    def keyword(name=None, **_kw):
        def deco(fn):
            fn.robot_name = name
            return fn
        return deco

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "2026-10-07 walkthrough v1"
SHOW = 10     # controls shown per stage; the totals above them are the whole page


def _gpr():
    """The page reader MODULE (its functions, not the Robot library instance). Imported on first use:
    Robot imports a library while reading the Settings table, long before a browser exists."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import garzai_page_reader as GPR
    return GPR


def _say(lines):
    """Print to the console AND the Robot log; return the same text."""
    text = "\n".join(lines)
    if _logger is not None:
        _logger.info(text, also_console=True)
    else:  # pragma: no cover
        print(text)
    return text


def _kb(n):
    return "%.1f KB" % (n / 1024.0)


def _nbytes(text):
    return len(str(text).encode("utf-8"))


def _ensure_lxml():
    """The parser bundle (review_table.py) imports `lxml.html` at module level, and lxml is a compiled
    extension that cannot be vendored into the bundle. Whether a CRT BUILD container has it was
    COULD-NOT-CHECK until the first run of this suite (2026-10-07, build 6195617: `No module named
    'lxml'`). If it is missing, install it for THIS RUN ONLY into a temp folder and say so on the
    console, so the walkthrough can show the stages; if that fails too, the reason is the answer
    (COULD-NOT-CHECK), never a pass. Returns a sentence for the log."""
    try:
        import lxml.etree as _etree
        return "lxml %s was already installed in this container" % ".".join(str(x) for x in _etree.LXML_VERSION)
    except ImportError:
        pass
    target = os.path.join(tempfile.gettempdir(), "gz_walk_lxml")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
           "--target", target, "lxml"]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    except Exception as exc:
        raise AssertionError("GZ WALK: COULD-NOT-CHECK -- lxml is not installed in this container and "
                             "pip could not be run: %s: %s" % (type(exc).__name__, exc))
    if done.returncode != 0:
        tail = " | ".join((done.stderr or done.stdout or "").strip().splitlines()[-4:])
        raise AssertionError("GZ WALK: COULD-NOT-CHECK -- lxml is not installed in this container and "
                             "`pip install lxml` failed (exit %d): %s" % (done.returncode, tail))
    if target not in sys.path:
        sys.path.insert(0, target)
    import importlib
    importlib.invalidate_caches()
    try:
        import lxml.etree as _etree
    except ImportError as exc:
        raise AssertionError("GZ WALK: COULD-NOT-CHECK -- pip reported success but lxml still does not "
                             "import: %s" % exc)
    return ("lxml was NOT installed in this container; installed %s for this run only (pip --target %s)"
            % (".".join(str(x) for x in _etree.LXML_VERSION), target))


def _bundle():
    """The page reader module and its parser bundle, loaded once. A failure prints the traceback tail
    to the console (the build log shows only the exception's last line) and raises COULD-NOT-CHECK."""
    GPR = _gpr()
    try:
        return GPR, GPR.mods()
    except ImportError:
        pass
    note = _ensure_lxml()
    _say(["GZ WALK: %s" % note])
    try:
        return GPR, GPR.mods()
    except Exception as exc:
        tail = "".join(traceback.format_exc().splitlines(True)[-12:])
        _say(["GZ WALK: the parser bundle did not load (last 12 lines of the traceback):", tail])
        raise AssertionError("GZ WALK: COULD-NOT-CHECK -- the parser bundle did not load: %s: %s" % (
            type(exc).__name__, exc))


class garzai_parser_walkthrough:
    """Gz Walk Capture / Parse / Calls / Pages Total / Plan Size / Summary -- see the module docstring."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = VERSION

    def __init__(self):
        self.cap = None        # {'html','url','stats','capture_ms','bytes','org','pack','title'}
        self.parsed = None     # compose_live.Parsed
        self.plan = None       # garzai_page_reader.build_plan(...)
        self.shown = []        # the row numbers stage 3 showed; stage 4 shows the SAME rows
        self.size = None       # what Gz Walk Plan Size measured

    # -- the browser ---------------------------------------------------------------------------
    @staticmethod
    def _driver():
        GPR = _gpr()
        return GPR.garzai_page_reader._driver()

    def _need(self, what):
        if what == "cap" and self.cap is None:
            raise AssertionError("GZ WALK: COULD-NOT-CHECK -- run Gz Walk Capture first (stage 2)")
        if what == "parsed" and self.parsed is None:
            raise AssertionError("GZ WALK: COULD-NOT-CHECK -- run Gz Walk Parse first (stage 3)")

    # -- stage 2 -------------------------------------------------------------------------------
    @keyword("Gz Walk Capture")
    def gz_walk_capture(self, org=None):
        """STAGE 2. Serialize the page open in the browser exactly as the parser receives it, and print
        its size, how many shadow roots were opened, and how much was left out. Never acts on the page."""
        GPR, m = _bundle()
        runtime = "Python %s.%s.%s" % tuple(sys.version_info[:3])
        drv = self._driver()
        if drv is None:
            msg = "GZ WALK CAPTURE: COULD-NOT-CHECK -- no browser is open in this session"
            _say([msg])
            raise AssertionError(msg)
        url = drv.current_url or ""
        host = ((re.match(r"^[a-z]+://([^/]+)", url) or [None, ""])[1] or "").lower()
        pack = GPR.pack_dir()
        alias = org or GPR.org_for_host(host, pack)
        cap = m.CL.live_capture(drv, alias)
        html = cap["html"]
        hdr = GPR.header_of(html)
        stats = cap.get("stats") or (hdr.get("stats") if isinstance(hdr.get("stats"), dict) else {}) or {}
        self.cap = {"html": html, "url": cap["url"], "stats": stats, "capture_ms": cap.get("capture_ms"),
                    "bytes": _nbytes(html), "org": alias, "pack": pack, "title": cap.get("title")}
        self.parsed = self.plan = self.size = None
        self.shown = []
        s = stats
        lines = [
            "GZ WALK 2 CAPTURE -- the page as the parser receives it",
            "  url          %s" % cap["url"],
            "  title        %s" % (cap.get("title") or "(none)"),
            "  size         %s bytes (%s) of serialized HTML" % (format(self.cap["bytes"], ","), _kb(self.cap["bytes"])),
            "  shadow roots %s opened and written out (the serializer walks element.shadowRoot; "
            "outerHTML would have left them out)" % s.get("shadowRoots", "?"),
            "  elements     %s visible DOM nodes kept; %s hidden subtrees dropped; %s labels; %s input/select/textarea; "
            "%s custom elements" % (s.get("nodes", "?"), s.get("hiddenSkipped", "?"), s.get("labels", "?"),
                                    s.get("inputs", "?"), s.get("customElements", "?")),
            "  frames       %s iframes, %s cross-origin; %s closed-root suspects; depth-capped nodes: %s" % (
                s.get("iframes", "?"), s.get("crossOriginFrames", "?"), s.get("closedRootSuspects", "?"),
                len(s.get("depthCapped") or [])),
            "  took         %s ms in the page (one round trip); org for the store lookup: %s" % (
                cap.get("capture_ms"), alias or "(none: the host is not in the shipped store)"),
            "  parser from  %s; %s" % (m.where, runtime),
        ]
        return _say(lines)

    # -- stage 3 -------------------------------------------------------------------------------
    @keyword("Gz Walk Parse")
    def gz_walk_parse(self, show=SHOW):
        """STAGE 3. Parse the captured page and print how many elements the parser found, split into
        the app's chrome and the page's own, by family, and the first few as label / family / tag."""
        self._need("cap")
        GPR, m = _bundle()
        c = self.cap
        parsed = m.CL.parse_capture(c["html"], c["url"], c["org"])
        self.parsed = parsed
        rows = parsed.rows
        page_rows = [r for r in rows if r.get("region") != "chrome"]
        chrome = len(rows) - len(page_rows)
        fam = collections.Counter((r.get("element_type") or "unknown") for r in page_rows)
        n = max(1, int(show))
        self.shown = [r["n"] for r in page_rows[:n]]
        lines = [
            "GZ WALK 3 PARSE -- what the parser found in those %s bytes" % format(c["bytes"], ","),
            "  parser       %d elements in %s ms: %d on the page itself, %d chrome (the Salesforce header and "
            "nav bar, left out of the AI's list by default)" % (len(rows), parsed.parse_ms, len(page_rows), chrome),
            "  page key     %s" % (parsed.page_key or "(none)"),
            "  by family    %s" % ", ".join("%s %d" % (k, v) for k, v in fam.most_common()),
            "  the first %d of the page's own %d elements, in page order (row = its place in the parser's list, "
            "which counts the chrome too; then label / family / tag):" % (len(self.shown), len(page_rows)),
        ]
        for r in page_rows[:n]:
            label = " ".join(str(r.get("label") or "").split()) or "(no label)"
            lines.append("    row %-3s %-34s %-16s <%s>" % (r["n"], '"%s"' % label[:32], r.get("element_type") or "unknown",
                                                          r.get("tag") or "?"))
        return _say(lines)

    # -- stage 4 -------------------------------------------------------------------------------
    @keyword("Gz Walk Calls")
    def gz_walk_calls(self):
        """STAGE 4. For the same rows stage 3 showed: the CRT line the parser proposes (keyword form) and
        its backup, and whether the page reader keeps it, takes a verified one from the job's store, or
        leaves the control out of the AI's list."""
        self._need("parsed")
        GPR, _m = _bundle()
        c = self.cap
        plan = GPR.build_plan(c["html"], c["url"], None, c["pack"], include_chrome=False)
        self.plan = plan
        by_n = {x["n"]: x for x in GPR.all_controls(plan)}
        listed = len(plan["controls"])
        cut = {k: len(v) for k, v in plan["cut"].items() if v}
        lines = [
            "GZ WALK 4 CLASSIFY + CALLS -- the call the parser proposes for each control, and its backup",
            "  plan         %d of the parser's %d elements become controls the AI is told to act on; cut: %s" % (
                listed, plan["rows"], "; ".join("%d %s" % (v, GPR.CUT_WORDS[k]) for k, v in cut.items()) or "nothing"),
            "  store        %s" % (("the job's page-object store has this page: %s" % plan.get("page_key"))
                                    if plan.get("store_record") else (plan.get("store_note") or "no store")),
            "  the same %d rows as stage 3:" % len(self.shown),
        ]
        for n in self.shown:
            x = by_n.get(n)
            if x is None:
                lines.append("    row %-3s (not in the plan)" % n)
                continue
            lad = x.get("ladder") or []
            lines.append("    row %-3s %s  [%s]" % (n, x["display"], x["family_word"]))
            if lad:
                lines.append("      proposes  %s    # %s" % (lad[0]["line"], lad[0]["why"]))
                lines.append("      backup    %s" % (("%s    # %s" % (lad[1]["line"], lad[1]["why"])) if len(lad) > 1
                                                      else "(none: this is the only rung)"))
            else:
                lines.append("      proposes  (no call: %s)" % (x.get("cut_detail") or "nothing a keyword reaches"))
            if x.get("cut"):
                lines.append("      the AI is told  nothing about it: cut as %s" % GPR.CUT_WORDS.get(x["cut"], x["cut"]))
            elif x.get("call_from") == "store":
                lines.append("      the AI is told  %s    # verified x%s, from the store" % (x["call"], x.get("verified_passes")))
            else:
                lines.append("      the AI is told  %s" % x["call"])
        return _say(lines)

    # -- stage 5 helpers (Gz Read Page itself is the page reader's keyword) -------------------------
    @keyword("Gz Walk Pages Total")
    def gz_walk_pages_total(self, first_page_text):
        """The N in `page 1 of N` on the last line of the first Gz Read Page text, as an integer."""
        m = re.search(r"GZ READ PAGE page 1 of (\d+) ref", str(first_page_text))
        if not m:
            msg = "GZ WALK: COULD-NOT-CHECK -- the first Gz Read Page text has no `page 1 of N` pointer line"
            _say([msg])
            raise AssertionError(msg)
        return int(m.group(1))

    @keyword("Gz Walk Plan Size")
    def gz_walk_plan_size(self, pages):
        """STAGE 5, measured. `pages` is the list of texts Gz Read Page returned (page 1, 2, ...). Print their
        lines and bytes -- exactly what the Test Agent is given -- beside the raw capture, and put the whole
        text in the Robot log."""
        self._need("cap")
        texts = [str(p) for p in pages]
        per = []
        for i, t in enumerate(texts, 1):
            per.append((i, len(t.split("\n")), _nbytes(t), re.search(r" ref ([0-9a-f]{8}) ", t)))
        total_lines = sum(p[1] for p in per)
        total_bytes = sum(_nbytes(t) for t in texts) + max(0, len(texts) - 1)   # one newline between pages
        raw = self.cap["bytes"]
        m = re.search(r"-- (\d+) controls? to act on", texts[0]) if texts else None
        told = int(m.group(1)) if m else None
        self.size = {"pages": len(texts), "lines": total_lines, "bytes": total_bytes, "controls": told}
        lines = [
            "GZ WALK 5 PLAN FOR THE AI -- the text Gz Read Page hands the Test Agent, measured",
        ]
        for i, nl, nb, ref in per:
            lines.append("  page %d of %d  %2d lines  %6s bytes   ref %s" % (
                i, len(per), nl, format(nb, ","), ref.group(1) if ref else "(none)"))
        lines.append("  together     %d lines, %s bytes (%s); about %s tokens (bytes / 4, an estimate, not a count)" % (
            total_lines, format(total_bytes, ","), _kb(total_bytes), format(total_bytes // 4, ",")))
        lines.append("  against      the raw capture %s bytes (%s): the plan is %.1f%% of it" % (
            format(raw, ","), _kb(raw), 100.0 * total_bytes / raw if raw else 0.0))
        if told is not None and self.plan is not None:
            same = told == len(self.plan["controls"])
            lines.append("  consistency  Gz Read Page lists %d controls; stage 4 built %d from its own capture: %s" % (
                told, len(self.plan["controls"]),
                "same page, same count" if same else "DIFFERENT (the page changed between the two captures)"))
        _say(lines)
        # the whole text the AI receives goes to the log (not the console: Gz Read Page already printed it)
        if _logger is not None:
            _logger.info("THE EXACT TEXT THE TEST AGENT RECEIVES, page by page:\n\n" + "\n\n".join(
                "----- Gz Read Page    page=%d -----\n%s" % (i, t) for i, t in enumerate(texts, 1)))
        return json.dumps(self.size)

    # -- stage 6 -------------------------------------------------------------------------------
    @keyword("Gz Walk Summary")
    def gz_walk_summary(self):
        """STAGE 6. One closing line: page KB -> parser elements -> plan lines / bytes for the AI."""
        self._need("cap")
        self._need("parsed")
        if not self.size:
            msg = "GZ WALK SUMMARY: COULD-NOT-CHECK -- run Gz Walk Plan Size first (stage 5)"
            _say([msg])
            raise AssertionError(msg)
        rows = self.parsed.rows
        page_rows = [r for r in rows if r.get("region") != "chrome"]
        s = self.size
        line = ("GZ WALK 6 SUMMARY -- page %s -> parser %d elements (%d on the page) -> %d controls listed -> "
                "plan %d lines / %s bytes for the AI (%d page%s of at most %d controls)" % (
                    _kb(self.cap["bytes"]), len(rows), len(page_rows), s["controls"] if s["controls"] is not None else -1,
                    s["lines"], format(s["bytes"], ","), s["pages"], "" if s["pages"] == 1 else "s",
                    _gpr().PAGE_SIZE))
        return _say([line])
