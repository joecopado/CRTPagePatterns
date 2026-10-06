"""garzai_page_reader -- three Robot keywords that let the CRT Test Agent READ a page instead of
guessing it: `Gz Read Page`, `Gz Show`, `Gz Verify` (W2.14, docs/PLAN-SWARM-POST-RESET-2026-10.md).

WHY (measured, never assumed):
  * The agent's own `read_page` hands the model the FIRST 40,000 characters of a 99 KB element list:
    on Zoo Nightmare inputs 46 of its 78 elements were GHOSTS of a hidden sibling tab, 0 of the 6 real
    inputs carried a label, and 34 controls never reached the model
    (docs/recorder/evidence/crt-test-agent-dom-2026-10-01.md).
  * `try_keyword` reports `passed: true` with no read-back, and returns PASS/FAIL only -- never the
    keyword's return value. The agent reads CONSOLE output only (`logger.console`), and it reads the
    LAST ~30 lines of the whole session buffer first; a big print does not truncate, it BURIES the
    answer (the 2026-10-05 probe, VERIFIED-PASS by END-line hashes:
    docs/audit/cicd-crt-gate-demo-2026-10-05/test-agent-probe-tails.json).
  * It fabricates when asked to recite its own context (41 of 44 'listed' keywords did not exist),
    so the keyword NAME and ARGUMENT NAMES are the only documentation it sees unprompted.

SO EVERY KEYWORD HERE: prints its answer to the console AND returns it; keeps one answer inside a
~30-line tail; puts the verdict or the 'page 1 of N -- NEXT' pointer on the LAST line; and never
prints a block that pushes an earlier answer out of reach.

  Gz Read Page    page=1    include_chrome=False    org=
      capture the page in the browser (the SAME shadow-piercing serializer `up.py --op capture`
      ships), parse it with the job's parser bundle (one schema-driven template per platform), and
      print a compact page plan: each control as a person sees it, its family, and the EXACT call to
      use -- stock QForce/QWeb first (label keyword > ClickItem attribute+tag > relative xpath; an
      index only on a repeated label; never an absolute or positional xpath). The shipped
      verified-locator store (resources/garzai_pom) is consulted FIRST: a rung that passed live
      LEADS and is marked `# verified`. Chrome, controls behind an open modal, layout wrappers of
      an editable field and table cells are not listed; the cut line counts each, and the whole map
      (every control, every cut with its reason) is written as a JSON run artifact.
  Gz Show    label    index=
      one control in full: every rung (stock keyword, ClickItem, relative xpath) with where it came
      from, the store's own rungs with their verdicts, the member index on a repeated label, and the
      anchor candidates the parser saw.
  Gz Verify    label    expected_value    index=    on_mismatch=fail
      read the control's value back WITHOUT touching it (D13: GetInputValue / VerifyCheckboxValue /
      GetSelected / GetFieldValue or the fresh capture -- never a type, never a click) and print a
      VERDICT compared by meaning (confirm.lenient_equal: 10/08/2026 == 10/8/2026, 25000 ==
      25,000.00): VERIFIED-PASS / CAUGHT-BUG / COULD-NOT-CHECK. Only VERIFIED-PASS passes; the other
      two FAIL by default, because `try_keyword` shows the agent PASS/FAIL and nothing else -- a
      verdict that passes on a mismatch is `passed: true` again. `on_mismatch=warn` prints and
      returns instead.

WHERE THE PIECES COME FROM (nothing re-implemented):
  capture   compose_live.live_capture   -> tools/dom-miner/cdp_capture.build_serializer
  classify  compose_live.parse_capture  -> review_table.build_rows (parser + identity xpath + ladder)
  store     pom/store.Store(state_root=<garzai_pom>).get + pom/consult.consult + consult.merged_call
  modal     pom/scope.find_dialog_subtree + scopes_for_capture
  index     disambiguation_args.to_call_kwargs (the ONE place index= becomes QWeb's numeric anchor=)
  compare   confirm.lenient_equal / typed_value (tools/qforce-lite/confirm.py, in the bundle)

IMPORT IS LAZY. Robot imports a Library while it reads the Settings table, long before a browser
exists, and an import that raises fails the whole suite -- so nothing about the bundle is touched
until a keyword runs (the same rule garzai_recorder_override.py follows).

Shipped as `resources/garzai_page_reader.py` in the CRT job, beside `resources/garzai_parser/` and
`resources/garzai_pom/`; imported by `resources/common.robot` so the three keywords sit in the
agent's auto-loaded test-keywords list. Source of truth: this file; the job's copy is verbatim.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sys
import time

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
VERSION = "2026-10-06 w214 v1"

PAGE_SIZE = 20            # controls per printed page: header 2 + 20 + cut 1 + pointer 1 = 24 lines,
                          # inside the ~30-line tail `read_executor_output` returns first
SHOW_MEMBERS_INLINE = 3   # Gz Show prints this many members of a repeated label in full

VERIFIED_PASS, CAUGHT_BUG, COULD_NOT_CHECK = "VERIFIED-PASS", "CAUGHT-BUG", "COULD-NOT-CHECK"

# families, as a person names them
FAMILY_WORD = {
    "input_field": "field", "textarea": "text area", "checkbox": "checkbox", "radio": "radio",
    "dropdown": "picklist", "combobox": "combobox", "lookup": "lookup", "date": "date",
    "datetime": "date/time", "dual_listbox": "dual list", "output_field": "value",
    "button": "button", "link": "link", "tab": "tab", "menuitem": "menu item",
    "table_cell": "cell", "column_header": "column", "iframe": "frame",
    "custom_component": "component", "unknown": "unknown",
}
TYPE_FAMILIES = {"input_field", "textarea", "search", "email", "phone", "url", "number",
                 "password", "combobox"}
DATE_FAMILIES = {"date", "datetime", "time"}
CLICK_FAMILIES = {"button", "link", "tab", "menuitem", "radio", "generic", "icon"}
TABLE_FAMILIES = {"table_cell", "column_header", "datatable", "native_table"}
CONTAINER_FAMILIES = {"custom_component", "iframe", "unknown"}
EDITABLE_FAMILIES = TYPE_FAMILIES | DATE_FAMILIES | {"checkbox", "dropdown", "lookup",
                                                     "dual_listbox", "radio"}
# the ladder rungs that pick a node by its POSITION -- never offered (user, 2026-10-03: "Absolute
# XPath should never be in there"; feedback_a_fallback_ladder_never_contains_absolute_xpath_and)
POSITIONAL_RUNGS = {"positional_last_resort", "scoped_attr_positional", "structural"}
# the dialog-ladder rungs that make the page behind them unreachable (pom/scope._DIALOG_LADDER's
# first two; a [role=dialog] composer or a [role=menu] leaves the page interactive)
MODAL_SELECTORS = ("[aria-modal=true]", "div.slds-modal, section.slds-modal")

CUT_WORDS = {
    "chrome": "chrome",
    "behind_modal": "behind the open modal",
    "wrapper": "layout wrapper of an editable field",
    "table_cell": "table cells (their links and checkboxes are listed)",
    "no_call": "with no call",
}


# ------------------------------------------------------------------------------------ console
def _console(text):
    if _logger is not None:
        _logger.console(text)
    else:  # pragma: no cover
        print(text)


def _cut(s, n=300):
    """At most n characters, and SAYS so when it cut (an instrument may elide, never silently)."""
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else "%s... (%d chars; the whole text is in the run log)" % (s[:n], len(s))


def _say(lines):
    """Print the block to the console and return it as one string -- the agent reads the console,
    a caller reads the return value; the two are always the same text."""
    text = "\n".join(lines)
    _console(text)
    return text


# ------------------------------------------------------------------------------------ the bundle
class _Mods:
    """The job's parser bundle, imported on first use. `where` names what was loaded."""

    def __init__(self, where, CL, RT, DA, PK, ST, CONSULT, MATCH, SCOPE, CONFIRM, confirm_why):
        self.where, self.CL, self.RT, self.DA, self.PK = where, CL, RT, DA, PK
        self.ST, self.CONSULT, self.MATCH, self.SCOPE = ST, CONSULT, MATCH, SCOPE
        self.CONFIRM, self.confirm_why = CONFIRM, confirm_why


_MODS = None


def bundle_dirs():
    """(compose_live dir, vendor dir, label) -- the bundle named by GZ_PARSER_BUNDLE, else the one
    beside this file (`resources/garzai_parser`, a MANIFEST.json says it IS a bundle), else this
    repo's own tree when the file runs from tools/recorder/crt_override. None when there is none."""
    cands = []
    if os.environ.get("GZ_PARSER_BUNDLE"):
        cands.append(os.environ["GZ_PARSER_BUNDLE"])
    cands.append(os.path.join(HERE, "garzai_parser"))
    for b in cands:
        if os.path.isfile(os.path.join(b, "MANIFEST.json")):
            return (os.path.join(b, "tools", "recorder", "crt_override"),
                    os.path.join(b, "tools", "interop", "resources", "pythonDom", "vendor"),
                    "bundle %s" % b)
    if os.path.isfile(os.path.join(HERE, "compose_live.py")):
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        return (HERE, os.path.join(root, "tools", "interop", "resources", "pythonDom", "vendor"),
                "repo %s" % root)
    return None


def mods():
    """Import the bundle once. Raises RuntimeError naming what is missing -- a keyword turns that
    into COULD-NOT-CHECK, never a pass."""
    global _MODS
    if _MODS is not None:
        return _MODS
    dirs = bundle_dirs()
    if dirs is None:
        raise RuntimeError("no parser bundle: resources/garzai_parser/ is not beside %s and "
                           "GZ_PARSER_BUNDLE is unset" % HERE)
    entry, vendor, where = dirs
    for p in (vendor, entry):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    import compose_live as CL                        # noqa: E402  (puts tools/recorder on the path)
    import review_table as RT                        # noqa: E402  (puts tools/qforce-lite there too)
    import disambiguation_args as DA                 # noqa: E402
    from pom import keys as PK                       # noqa: E402
    from pom import store as ST                      # noqa: E402
    from pom import consult as CONSULT               # noqa: E402
    from pom import match as MATCH                   # noqa: E402
    from pom import scope as SCOPE                   # noqa: E402
    try:
        import confirm as CONFIRM                    # tools/qforce-lite/confirm.py
        why = ""
    except Exception as exc:                         # an older bundle without it
        CONFIRM, why = None, "%s: %s" % (type(exc).__name__, exc)
    try:
        from pom import export_flow as EXPORT_FLOW   # the store-rung -> CRT keyword map (KW_NAME)
    except Exception:                                # an older bundle without it
        EXPORT_FLOW = None
    _MODS = _Mods(where, CL, RT, DA, PK, ST, CONSULT, MATCH, SCOPE, CONFIRM, why)
    _MODS.EXPORT_FLOW = EXPORT_FLOW
    return _MODS


# ------------------------------------------------------------------------------------ helpers
def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().casefold()


def header_of(html):
    """The `<!-- key: value -->` header a capture carries (host, path, stats, org...)."""
    out = dict(re.findall(r"<!-- ([a-z_]+): (.*?) -->", (html or "")[:4000]))
    if "stats" in out:
        m = re.match(r"(\{.*\})", out["stats"])
        try:
            out["stats"] = json.loads(m.group(1)) if m else {}
        except Exception:
            out["stats"] = {}
    return out


def url_of(hdr):
    host, path = hdr.get("host") or "", hdr.get("path") or ""
    return ("https://%s%s" % (host, path)) if host else None


def pack_dir():
    """The verified-locator store this job ships: GZ_POM_DIR, else `garzai_pom` beside this file.
    None when there is none -- never the developer's ~/.claude/state (compose_live's container rule)."""
    env = os.environ.get("GZ_POM_DIR")
    if env is not None:
        return env.strip() or None
    p = os.path.join(HERE, "garzai_pom")
    return p if os.path.isdir(p) else None


_HOST_ALIAS: dict = {}


def org_for_host(host, pack):
    """The org alias the shipped pack files this host under (every record carries page.host and
    page.alias), or None. A third-party host is partitioned by itself and needs no alias."""
    if not host or not pack:
        return None
    if pack not in _HOST_ALIAS:
        table = {}
        root = os.path.join(pack, "org-map")
        for alias in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            d = os.path.join(root, alias, "pom")
            for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                try:
                    with open(os.path.join(d, name)) as f:
                        page = (json.load(f) or {}).get("page") or {}
                except Exception:
                    continue
                if page.get("host"):
                    table.setdefault(page["host"].lower(), page.get("alias") or alias)
        _HOST_ALIAS[pack] = table
    return _HOST_ALIAS[pack].get(host.lower())


def _rf(m, kw, *args, **kwargs):
    return m.RT._rf(kw, *args, **kwargs)


def _anchor_kwargs(m, member):
    """`anchor=<n>` for member n>1 of a repeated label, nothing otherwise: QWeb's default anchor is
    "1", so member 1 needs no argument (D4) -- the line stays the shortest correct one."""
    if not member or member[1] <= 1 or member[0] <= 1:
        return {}
    return m.DA.to_call_kwargs({"index": member[0]})


def is_absolute_xpath(xp):
    s = str(xp or "").lstrip("( ")
    return s.startswith("/html") or bool(re.match(r"^/[^/]", s))


def is_positional_xpath(xp):
    """Absolute, or a COUNT past the first match: `(<...>/following::input)[3]` picks the third
    of a set by position. `(...)[1]` -- the first control after a unique text -- is the ladder's own
    relative rung and is allowed."""
    m = re.search(r"\)\[(\d+)\]\s*$", str(xp or ""))
    return is_absolute_xpath(xp) or bool(m and int(m.group(1)) > 1)


def relative_xpaths(row):
    """The ladder rungs a person may be offered: unique in the capture, this node, no generated
    value, and neither absolute nor positional."""
    lad = ((row.get("xpath") or {}).get("ladder")) or []
    out = []
    for r in lad:
        if r.get("rung") in POSITIONAL_RUNGS or is_absolute_xpath(r.get("xpath")):
            continue
        if r.get("unique_in_capture") and not r.get("generated_values"):
            out.append(r)
    return out


def placeholder_for(kw):
    return {"TypeText": "<value>", "TypeSecret": "<value>", "DropDown": "<option>",
            "PickList": "<option>", "MultiPickList": "<option>", "ComboBox": "<record name>",
            "ClickCheckbox": "<on|off>"}.get(kw)


# ------------------------------------------------------------------------------------ the calls
def stock_kw(row):
    """(keyword, locator kind) for this row's stock QForce/QWeb call, or (None, why)."""
    fam = row.get("element_type") or ""
    c0 = (row.get("calls") or [{}])[0] or {}
    kw0 = c0.get("keyword") or ""
    tag = (row.get("tag") or "").lower()
    attrs = row.get("attrs") or {}
    if fam in DATE_FAMILIES or kw0 in ("Set Datetime", "Aura Date", "SetDate"):
        return "TypeText", "date"            # D19: a date is TYPED in the user's locale, never picked
    if fam == "checkbox" or kw0 == "ClickCheckbox":
        return "ClickCheckbox", "label"
    if fam == "dual_listbox" or kw0 in ("Multi Pick List", "MultiPickList"):
        return "MultiPickList", "label"
    if fam == "lookup" or kw0 in ("Aura Lookup", "ComboBox"):
        return "ComboBox", "label"
    if fam == "dropdown" or kw0 in ("PickList", "DropDown", "Aura PickList"):
        return ("DropDown" if (tag == "select" or kw0 == "DropDown") else "PickList"), "label"
    if fam in TYPE_FAMILIES or kw0 in ("TypeText", "TypeSecret"):
        return ("TypeSecret" if (attrs.get("type") == "password") else "TypeText"), "label"
    if fam == "output_field" or kw0 == "GetFieldValue":
        return "GetFieldValue", "label"
    if kw0 == "ClickItem" and c0.get("locator"):
        return "ClickItem", "attribute"
    if fam in CLICK_FAMILIES or kw0 in ("ClickText", "Open Console Subtab", "Click Tree Item"):
        return "ClickText", "label"
    return None, "no keyword routes family %r" % fam


def derived_call(m, row, label, member):
    """{'kw','args','kwargs','line','rung','why'} for the stock call this recorder would derive, or
    None when there is none. Rung order (user, 2026-10-03): keyword form -> ClickItem -> relative
    xpath; typing never goes through ClickItem."""
    kw, kind = stock_kw(row)
    c0 = (row.get("calls") or [{}])[0] or {}
    ak = _anchor_kwargs(m, member)
    if kw and kind == "attribute":
        tag = c0.get("tag") or row.get("tag")
        kwargs = dict(ak)
        kwargs["tag"] = tag
        args = [c0.get("locator")]
        return {"kw": "ClickItem", "args": args, "kwargs": dict(kwargs, partial_match="False"),
                "line": _rf(m, "ClickItem", *args, tag=tag, partial_match="False", **ak),
                "rung": "clickitem", "why": "parser: ClickItem by its %s" % (
                    row.get("label_source") or "attribute")}
    if kw and label:
        data = [] if kw in ("GetFieldValue", "ClickText") else [
            "<date>" if kind == "date" else placeholder_for(kw)]
        extra = {"partial_match": "False"} if kw == "ClickText" else {}
        return {"kw": kw, "args": [label] + data, "kwargs": dict(ak, **extra),
                "line": _rf(m, kw, label, *data, **dict(ak, **extra)),
                "rung": "keyword", "why": "parser: %s by its label (%s)" % (
                    kw, row.get("label_source") or "label")}
    # no label a person can see: the relative xpath is the answer (doctrine (3): a control no
    # keyword reaches goes straight to its xpath)
    rel = relative_xpaths(row)
    if rel:
        xp = m.RT._xp_arg(rel[0]["xpath"])
        fam = row.get("element_type") or ""
        if fam in TYPE_FAMILIES or fam in DATE_FAMILIES or kw in ("TypeText", "TypeSecret"):
            k, data = "TypeText", ["<value>"]
        elif fam == "dropdown" and (row.get("tag") or "") == "select":
            k, data = "DropDown", ["<option>"]
        elif kw or fam in CLICK_FAMILIES or fam == "checkbox":
            k, data = "ClickElement", []
        else:
            return None
        return {"kw": k, "args": [xp] + data, "kwargs": {}, "line": _rf(m, k, xp, *data),
                "rung": "xpath", "why": "no visible label: relative xpath (%s)" % rel[0]["rung"]}
    return None


def ladder(m, row, label, member):
    """Every rung a person may try for this control, strongest first, as [{'rung','line','why'}].
    Steps x rungs (user, 2026-10-03): typing is one step (label -> placeholder -> relative xpath);
    a click or a checkbox is one step (keyword -> ClickItem -> relative xpath)."""
    out = []
    d = derived_call(m, row, label, member)
    if d:
        out.append({"rung": d["rung"], "line": d["line"], "why": d["why"]})
    fam = row.get("element_type") or ""
    attrs = row.get("attrs") or {}
    tag = row.get("tag") or ""
    ak = _anchor_kwargs(m, member)
    typing = fam in TYPE_FAMILIES or fam in DATE_FAMILIES
    if typing and attrs.get("placeholder") and norm(attrs["placeholder"]) != norm(label):
        out.append({"rung": "placeholder",
                    "line": _rf(m, "TypeText", attrs["placeholder"], "<value>", **ak),
                    "why": "the field's placeholder text"})
    if not typing and fam not in TABLE_FAMILIES and fam != "output_field":
        # ClickItem before any xpath for a click or a checkbox
        for c in (row.get("calls") or [])[1:]:
            if c.get("keyword") == "ClickItem" and c.get("locator"):
                line = _rf(m, "ClickItem", c["locator"], tag=c.get("tag") or tag,
                           partial_match="False", **ak)
                if not any(o["line"] == line for o in out):
                    out.append({"rung": "clickitem", "line": line,
                                "why": "parser: ClickItem by a stable attribute"})
                break
        if fam == "checkbox" and label:
            out.append({"rung": "clickitem",
                        "line": _rf(m, "ClickItem", "checkbox", tag="input", anchor=label),
                        "why": "ClickItem on the box's type, anchored by its label (it TOGGLES: "
                               "read the state before and after)"})
    for r in relative_xpaths(row):
        xp = m.RT._xp_arg(r["xpath"])
        k, data = (("TypeText", ["<value>"]) if typing else
                   ("DropDown", ["<option>"]) if (fam == "dropdown" and tag == "select") else
                   ("ClickElement", []))
        line = _rf(m, k, xp, *data)
        if not any(o["line"] == line for o in out):
            out.append({"rung": "xpath", "line": line,
                        "why": "relative xpath, unique in the capture (%s)" % r["rung"]})
    return out


# ------------------------------------------------------------------------------------ the store
# The keywords a store rung may LEAD with: the stock QForce/QWeb set a CRT job has. A rung recorded
# under a holder's Python name (`click_item_first`, `click_text`, `verify_text`) is first put in its
# CRT form by `pom/export_flow` (KW_NAME + `_kw_line`, the export's own rule); anything still not in
# this set (`custom`, `Aura Date`, `SetDate`) never leads -- it is shown by Gz Show, not offered.
STOCK_KEYWORDS = {"ClickText", "ClickItem", "ClickElement", "TypeText", "TypeSecret",
                  "ClickCheckbox", "DropDown", "PickList", "MultiPickList", "ComboBox",
                  "GetFieldValue", "VerifyText", "VerifyItem", "VerifyElement"}
_STOCK_BY_NORM = {k.casefold(): k for k in STOCK_KEYWORDS}


def crt_rung(m, rung):
    """(rung in CRT form {'kw','args','kwargs'}, None) or (None, why). Robot matches keyword names
    ignoring case and spaces, so `Multi Pick List` IS `MultiPickList`."""
    kw, args, kwargs = rung.get("kw"), list(rung.get("args") or []), dict(rung.get("kwargs") or {})
    ef = getattr(m, "EXPORT_FLOW", None)
    if ef is not None and kw in getattr(ef, "KW_NAME", {}):
        line = ef._kw_line({"chosen": {"kw": kw, "args": args, "kwargs": kwargs}})
        kw, args, kwargs = m.CL.split_step_body(line)
        args = [a.replace("\\=", "=") for a in args]           # re-escaped below, ONCE
        kwargs = {k: v.replace("\\=", "=") for k, v in kwargs.items()}
    stock = _STOCK_BY_NORM.get(re.sub(r"[\s_]", "", str(kw or "")).casefold())
    if not stock:
        return None, ("the store's verified rung is %r, not a stock QForce/QWeb keyword this job "
                      "has -- derived" % kw)
    return {"kw": stock, "args": args, "kwargs": kwargs, "n_verified": rung.get("n_verified"),
            "last_verdict": rung.get("last_verdict")}, None


def render_call(m, kw, args, kwargs):
    """One Robot line. An xpath keyword's locator goes through `review_table._xp_arg` (`xpath\\=`
    and every `=` escaped once): Robot otherwise reads `(//a[@b="c"])[1]` as a NAMED argument and
    the locator never arrives -- measured with robot's own ArgumentSpec.resolve: 'expected 1 to 3
    non-named arguments, got 0'."""
    args = list(args)
    if kw in ("ClickElement", "VerifyElement") and args:
        a0 = str(args[0])
        if a0.startswith("xpath\\="):
            a0 = a0[len("xpath\\="):].replace("\\=", "=")
        elif a0.startswith("xpath="):
            a0 = a0[len("xpath="):]
        args[0] = m.RT._xp_arg(a0)
    return _rf(m, kw, *args, **kwargs)


def store_rung_line(m, r):
    """One store rung as Gz Show prints it: its CRT form with the LOCATOR only (a past run's typed
    value is never shown as data -- D19), its verdict and pass count, and why it would never lead."""
    c, why = crt_rung(m, r)
    kw = (c or {}).get("kw") or r.get("kw")
    args = list((c or r).get("args") or [])[:1]
    kwargs = m.DA.to_call_kwargs(dict((c or r).get("kwargs") or {}))
    try:
        line = render_call(m, kw, args, kwargs) if c else "%s %s" % (kw, args)
    except Exception:
        line = "%s %s" % (kw, args)
    tail = "%s x%s" % (r.get("last_verdict"), r.get("n_verified") or 0)
    if c is None:
        tail += " (not a stock keyword here)"
    elif kw in ("ClickElement", "VerifyElement") and is_positional_xpath(args[0] if args else ""):
        tail += " (positional, never offered)"
    return "%s  %s" % (line, tail)


def rung_index(rung):
    kw = (rung or {}).get("kwargs") or {}
    for k in ("index", "anchor"):
        v = kw.get(k)
        if v is not None and re.fullmatch(r"\s*\d+\s*", str(v)):
            return int(v)
    return None


def store_answer(m, record, page_key, row, label, member, derived):
    """(call dict or None, store summary dict). The store's verified rung LEADS when consult says
    `verified`, merged_call can express THIS action with it, the rung is not an absolute xpath, and
    -- on a repeated label -- the rung was verified for THIS member. Every other case derives and
    says why, in words."""
    ans = m.CONSULT.consult(record, label, row.get("element_type"), page_key=page_key)
    summary = {"verdict": ans.get("verdict"), "why": ans.get("why"),
               "element_id": ans.get("element_id")}
    element = None
    if ans.get("element_id") and record:
        element = (record.get("elements") or {}).get(ans["element_id"])
    summary["rungs"] = [
        {"kw": r.get("kw"), "args": r.get("args"), "kwargs": r.get("kwargs"),
         "last_verdict": r.get("last_verdict"), "n_verified": r.get("n_verified"),
         "n_failed": r.get("n_failed")} for r in ((element or {}).get("ladder") or [])]
    summary["rung_lines"] = [store_rung_line(m, r) for r in summary["rungs"]]
    rung = ans.get("rung")
    if ans.get("verdict") != m.CONSULT.VERIFIED or not rung or not derived:
        return None, summary
    rung, why = crt_rung(m, rung)
    if rung is None:
        summary["why"] = why
        return None, summary
    if (rung.get("kw") in m.CONSULT.XPATH_KEYWORDS
            and is_positional_xpath((rung.get("args") or [""])[0])):
        summary["why"] = ("the store's verified rung is an absolute or positional xpath -- never "
                          "offered; derived")
        return None, summary
    if member and member[1] > 1:
        ri = rung_index(rung) or 1
        if ri != member[0]:
            summary["why"] = ("the store's verified rung is for member %d of this repeated "
                              "label, this is member %d -- derived" % (ri, member[0]))
            return None, summary
    call = m.CONSULT.merged_call(rung, {"kw": derived["kw"], "args": derived["args"],
                                        "kwargs": {k: v for k, v in derived["kwargs"].items()
                                                   if k != "anchor"}},
                                 {"tag": row.get("tag"),
                                  "index": member[0] if (member and member[1] > 1) else None})
    if not call.get("from_store"):
        summary["why"] = call.get("why")
        return None, summary
    kwargs = m.DA.to_call_kwargs(dict(call["kwargs"]))
    if kwargs.get("anchor") == "1":
        kwargs.pop("anchor")
    line = render_call(m, call["kw"], call["args"], kwargs)
    return {"kw": call["kw"], "args": call["args"], "kwargs": kwargs, "line": line,
            "rung": "store", "n_verified": int(rung.get("n_verified") or 0),
            "why": "store: passed live %d time(s)" % int(rung.get("n_verified") or 0)}, summary


# ------------------------------------------------------------------------------------ the plan
def _resolve1(parsed, xp):
    if not xp:
        return None
    els = parsed.resolve(xp)
    return els[0] if len(els) == 1 else None


def wrapper_twins(parsed, rows):
    """{n of an output_field row: n of the editable row it wraps}. On an edit form Lightning wraps
    each field in a records-record-layout-item the parser reads as an output_field with the SAME
    label; a person sees ONE field. Measured on slockard's New Account modal: the store's
    live-verified call is `TypeText Account Name <value>` with NO anchor, while the parser counted
    the wrapper as member 1 and the input as member 2. Containment is checked in the capture tree;
    an identity that names no single node is never folded (no guessed merge)."""
    editable = [(r, _resolve1(parsed, r.get("identity_xpath"))) for r in rows
                if r.get("element_type") in EDITABLE_FAMILIES]
    editable = [(r, el) for r, el in editable if el is not None]
    out = {}
    for r in rows:
        if r.get("element_type") != "output_field":
            continue
        w = _resolve1(parsed, r.get("identity_xpath"))
        if w is None:
            continue
        inside = [c for c, el in editable if any(a is w for a in el.iterancestors())]
        if not inside:
            continue
        # the same-label editable control first (it is the field this wrapper names); a compound
        # field's wrapper (Billing Address around Street/City/...) wraps several, none same-label
        same = [c for c in inside if norm(c.get("label")) == norm(r.get("label"))]
        out[r["n"]] = (same or inside)[0]["n"]
    return out


def member_of(row, rows_by_label, excluded):
    """(index, group_size) on a repeated label, or None. The parser's own index is the description
    (D14); a member that is not a separate control a person can reach -- a layout wrapper of the
    field, or (with a modal open, where the plan says UseModal On and QWeb searches only the modal)
    a control behind the modal -- leaves the group, and one before this member shifts it down."""
    g, i = row.get("group_size"), row.get("index")
    if not g or g <= 1 or not i or row["n"] in excluded:
        return None
    same = rows_by_label.get(norm(row.get("label"))) or []
    t_before = sum(1 for r in same if r["n"] in excluded and (r.get("index") or 0) < i)
    t_all = sum(1 for r in same if r["n"] in excluded)
    g2, i2 = g - t_all, i - t_before
    return (i2, g2) if g2 > 1 else None


def modal_scope(m, parsed, html, rows):
    """(scope by row n, note). When a MODAL is open, a row is `own` (inside it) or `shell` (the page
    behind it, which a person cannot reach until the modal closes). Empty dict when no modal is open
    or the subtree cannot be resolved -- then nothing is cut for this reason, and the note says so."""
    soup = getattr(parsed.cap, "soup", None)
    if soup is None:
        return {}, "COULD-NOT-CHECK: the capture has no tree to look for a modal in"
    node, sel, note = m.SCOPE.find_dialog_subtree(soup)
    if node is None:
        return {}, note
    if sel not in MODAL_SELECTORS:
        return {}, "a %s is open; it is not modal, so the page behind it stays listed" % sel
    try:
        scopes = m.SCOPE.scopes_for_capture(html, state="modal", kind="modal",
                                            element_id=m.ST.element_id,
                                            stable_attrs=m.ST.stable_attrs)
    except Exception as exc:
        return {}, "COULD-NOT-CHECK: %s while splitting the modal from the page (%s)" % (
            type(exc).__name__, exc)
    if not scopes:
        return {}, "COULD-NOT-CHECK: a modal is open (%s) but its subtree could not be split" % sel
    out = {}
    for r in rows:
        if not norm(r.get("label")):
            continue          # scope's denominator is label-bearing controls only; unlabelled stay
        rid = m.ST.element_id(r.get("element_type"), r.get("label"), r.get("container") or "",
                              m.ST.stable_attrs(r.get("attrs") or {}), tag=r.get("tag"))
        if rid in scopes:
            out[r["n"]] = scopes[rid]
    return out, "a modal is open (%s): its own controls are listed, the page behind it is not" % sel


def display_label(row, member):
    lab = row.get("_clean_label") or ""
    if not lab:
        return "(no label)"
    if member:
        lab = "%s (%d of %d)" % (lab, member[0], member[1])
    if row.get("label_source") == "assistive_text":
        lab += " (screen-reader text)"
    return lab


def build_plan(html, url=None, org=None, pack=None, include_chrome=False):
    """The page plan for ONE capture: no driver, no network, no org contact. `pack` is the
    verified-locator store root (None = no store shipped). Returns a JSON-able dict."""
    m = mods()
    t0 = time.time()
    hdr = header_of(html)
    url = url or url_of(hdr)
    host = ((re.match(r"^[a-z]+://([^/]+)", url or "") or [None, ""])[1] or "").lower()
    org_src = "argument" if org else None
    if not org and host:
        org = org_for_host(host, pack)
        org_src = "the shipped pack (host %s)" % host if org else None
    parsed = m.CL.parse_capture(html, url, org)
    page_key = None
    try:
        page_key = (m.PK.page_key(url, org=org) or {}).get("key") if url else None
    except Exception:
        page_key = None
    record, store_note = None, None
    if not pack:
        store_note = "no verified-locator store is shipped with this job (resources/garzai_pom)"
    elif not page_key:
        store_note = "COULD-NOT-CHECK: no page key (the capture carries no URL)"
    else:
        try:
            record = m.ST.Store(state_root=pack).get(page_key)
        except Exception as exc:
            store_note = "COULD-NOT-CHECK: %s reading the store (%s)" % (type(exc).__name__, exc)
        if record is None and store_note is None:
            store_note = "the store has no record for %s -- every call is derived" % page_key
    rows = parsed.rows
    for r in rows:
        r["_clean_label"] = m.RT._clean_label(r.get("label") or "") if r.get("label") else ""
    rows_by_label = {}
    for r in rows:
        if norm(r.get("label")):
            rows_by_label.setdefault(norm(r.get("label")), []).append(r)
    twins = wrapper_twins(parsed, rows)
    modal, modal_note = modal_scope(m, parsed, html, rows)
    controls, cut = [], {k: [] for k in CUT_WORDS}
    excluded = set(twins) | {n for n, s in modal.items() if s == "shell"}
    for r in rows:
        member = member_of(r, rows_by_label, excluded)
        label = r["_clean_label"]
        fam = r.get("element_type") or "unknown"
        derived = derived_call(m, r, label, member)
        led, store = (None, {"verdict": "skipped", "why": "nothing to look up"})
        if derived and label:
            led, store = store_answer(m, record, page_key, r, label, member, derived)
        call = led or derived
        c = {"n": r["n"], "label": label, "display": display_label(r, member), "family": fam,
             "family_word": FAMILY_WORD.get(fam, fam), "tag": r.get("tag"),
             "label_source": r.get("label_source"), "region": r.get("region"),
             "container": r.get("container") or "", "member": list(member) if member else None,
             "parser_index": r.get("index"), "parser_group": r.get("group_size"),
             "call": call["line"] if call else None, "call_from": call["rung"] if call else None,
             "verified_passes": (call or {}).get("n_verified", 0) if led else 0,
             "why": (call or {}).get("why"), "store": store,
             "ladder": ladder(m, r, label, member),
             "anchors": r.get("anchor_candidates") or [],
             "parser_hint": ((r.get("calls") or [{}])[0] or {}).get("keyword") or r.get("hint_click"),
             "caveats": sorted({cv for c0 in (r.get("calls") or []) for cv in (c0.get("caveats") or [])}),
             "identity_xpath": r.get("identity_xpath"), "scope": modal.get(r["n"]),
             "attrs": r.get("attrs") or {}, "value": r.get("value")}
        reason = None
        if r["n"] in twins:
            reason = "wrapper"
            c["cut_detail"] = "wraps row %d" % twins[r["n"]]
        elif modal.get(r["n"]) == "shell":
            reason = "behind_modal"
        elif r.get("region") == "chrome" and not include_chrome:
            reason = "chrome"
        elif fam in TABLE_FAMILIES:
            reason = "table_cell"
        elif not call:
            reason = "no_call"
            c["cut_detail"] = stock_kw(r)[1] if not stock_kw(r)[0] else (
                "no visible label and no relative xpath unique in the capture")
        c["cut"] = reason
        if reason:
            cut[reason].append(c)
        else:
            controls.append(c)
    stats = hdr.get("stats") if isinstance(hdr.get("stats"), dict) else {}
    return {"version": VERSION, "bundle": m.where, "url": url, "host": host, "org": org,
            "org_from": org_src, "page_key": page_key, "pack": pack,
            "store_note": store_note, "store_record": bool(record),
            "modal_note": modal_note, "hidden_at_capture": stats.get("hiddenSkipped"),
            "rows": len(rows), "controls": controls, "cut": cut,
            "parse_ms": parsed.parse_ms, "plan_ms": round((time.time() - t0) * 1000, 1)}


# ------------------------------------------------------------------------------------ rendering
def pages_of(plan, per_page=PAGE_SIZE):
    n = len(plan["controls"])
    return max(1, (n + per_page - 1) // per_page)


def render_page(plan, page=1, per_page=PAGE_SIZE, fresh_note=None):
    """The printed block for one page: header (2 lines), at most `per_page` controls, the cut line,
    and the pointer LAST."""
    total = pages_of(plan, per_page)
    page = max(1, int(page))
    ctr = plan["controls"]
    n_ver = sum(1 for c in ctr if c.get("call_from") == "store")
    where = plan.get("page_key") or plan.get("url") or "(no URL)"
    lines = ["GZ READ PAGE %s -- %d control%s to act on%s" % (
        where, len(ctr), "" if len(ctr) == 1 else "s",
        (" (%s)" % fresh_note) if fresh_note else "")]
    if plan.get("store_record"):
        lines.append("  %d of %d calls passed live before (# verified, from the job's store); "
                     "the rest are derived from this page" % (n_ver, len(ctr)))
    else:
        lines.append("  every call is derived from this page: %s" % plan.get("store_note"))
    if str(plan.get("modal_note") or "").startswith("a modal is open"):
        # crt-qforce-qweb skill rule 2 and error ledger 'QWebElementNotFoundError inside any
        # Lightning modal': UseModal On before, UseModal Off after
        lines.append("  a modal is open: run UseModal    On before these calls and UseModal    Off "
                     "once it closes")
    if page > total:
        lines.append("GZ READ PAGE: COULD-NOT-CHECK -- page %d asked, the plan has %d page%s; "
                     "call Gz Read Page    page=1" % (page, total, "" if total == 1 else "s"))
        return lines
    start = (page - 1) * per_page
    body = []
    for i, c in enumerate(ctr[start:start + per_page], start + 1):
        mark = ("    # verified x%d" % c["verified_passes"]) if c.get("call_from") == "store" else ""
        body.append("%2d. %s [%s] %s%s" % (i, c["display"], c["family_word"], c["call"], mark))
    lines += body
    ref = page_ref(body)
    cut = plan["cut"]
    bits = []
    for k in ("chrome", "behind_modal", "wrapper", "table_cell", "no_call"):
        if cut.get(k):
            word = CUT_WORDS[k]
            if k == "chrome":
                word += " (Gz Read Page    include_chrome=True lists them)"
            if k == "no_call":
                word += " (Gz Show    <label> says why)"
            bits.append("%d %s" % (len(cut[k]), word))
    if plan.get("hidden_at_capture"):
        bits.append("%s hidden subtrees never captured" % plan["hidden_at_capture"])
    lines.append("  not listed: " + ("; ".join(bits) if bits else "nothing"))
    if page < total:
        lines.append("GZ READ PAGE page %d of %d ref %s -- NEXT: Gz Read Page    page=%d    "
                     "(one control in full: Gz Show    <label>; check a value: Gz Verify    "
                     "<label>    <value>)" % (page, total, ref, page + 1))
    else:
        lines.append("GZ READ PAGE page %d of %d ref %s -- END of the page plan (%d controls; one "
                     "in full: Gz Show    <label>; check a value: Gz Verify    <label>    <value>)"
                     % (page, total, ref, len(ctr)))
    return lines


def page_ref(body_lines):
    """8 hex over a page's control lines: a reader that quotes it read the LAST line (the probe
    method of 2026-10-05 -- a value it cannot infer from anything printed before it)."""
    return hashlib.sha1("\n".join(body_lines).encode("utf-8", "replace")).hexdigest()[:8]


def all_controls(plan):
    return list(plan["controls"]) + [c for k in plan["cut"] for c in plan["cut"][k]]


def find_members(plan, label):
    """(members in DOM order, suggestions). Exact match on the label as a person sees it."""
    want = norm(label)
    every = sorted(all_controls(plan), key=lambda c: c["n"])
    hits = [c for c in every if norm(c["label"]) == want]
    if hits:
        return hits, []
    labels = sorted({c["label"] for c in every if c["label"]})
    sugg = difflib.get_close_matches(label, labels, n=5, cutoff=0.5)
    if not sugg:
        sugg = [lab for lab in labels if want and want in norm(lab)][:5]
    return [], sugg


def render_show(plan, label, index=None):
    members, sugg = find_members(plan, label)
    where = plan.get("page_key") or plan.get("url")
    if not members:
        return ["GZ SHOW \"%s\": COULD-NOT-CHECK -- no control with this label on %s%s" % (
            label, where, ("; closest: " + ", ".join(sugg)) if sugg else "")]
    lines = ["GZ SHOW \"%s\" -- %d control%s with this label on %s" % (
        label, len(members), "" if len(members) == 1 else "s", where)]
    pick = members
    if index not in (None, "", "None"):
        try:
            k = int(index)
        except (TypeError, ValueError):
            return lines + ["GZ SHOW \"%s\": COULD-NOT-CHECK -- index=%r is not a number" % (label, index)]
        if not 1 <= k <= len(members):
            return lines + ["GZ SHOW \"%s\": COULD-NOT-CHECK -- index=%d asked, %d member%s" % (
                label, k, len(members), "" if len(members) == 1 else "s")]
        pick = [members[k - 1]]
    if len(pick) > SHOW_MEMBERS_INLINE:
        for k, c in enumerate(pick, 1):
            lines.append("  #%d [%s] %s -- %s" % (k, c["family_word"], c.get("container") or "-",
                                                 c["call"] or "no call"))
        lines.append("GZ SHOW \"%s\": %d members -- one in full: Gz Show    %s    index=<n>" % (
            label, len(pick), label))
        return lines
    for c in pick:
        k = members.index(c) + 1
        mem = (" member %d of %d;" % tuple(c["member"])) if c.get("member") else ""
        listed = ("not listed by Gz Read Page: %s%s" % (CUT_WORDS.get(c["cut"], c["cut"]),
                  (" -- " + c["cut_detail"]) if c.get("cut_detail") else "")) if c.get("cut") else "listed"
        lines.append("#%d [%s, <%s>]%s label from %s; %s" % (
            k, c["family_word"], c.get("tag") or "?", mem, c.get("label_source") or "-", listed))
        for j, r in enumerate(c.get("ladder") or [], 1):
            lines.append("  rung %d %-11s %s    (%s)" % (j, r["rung"], r["line"], r["why"]))
        if not c.get("ladder"):
            lines.append("  no rung: %s" % (c.get("cut_detail") or c.get("why") or "nothing routes it"))
        st = c.get("store") or {}
        sr = st.get("rung_lines") or []
        if sr:
            # consult's own `why` for a verified answer quotes the rung WITH a past run's typed
            # value; the rung lines already carry the locator, so only a rewritten why is shown
            why = st.get("why") or ""
            why = "" if why.startswith("the store holds a rung that passed live") else "; " + why
            lines.append("  store (%s%s): %s" % (st.get("verdict"), why, " | ".join(sr[:3])) + (
                " | +%d more rung(s) in the run artifact" % (len(sr) - 3) if len(sr) > 3 else ""))
        else:
            lines.append("  store: %s -- %s" % (st.get("verdict"), st.get("why")))
        if c.get("anchors"):
            lines.append("  anchor candidates: " + ", ".join(c["anchors"][:6]) + (
                " (+%d more in the run artifact)" % (len(c["anchors"]) - 6) if len(c["anchors"]) > 6 else ""))
        if c.get("caveats"):
            lines.append("  caveat: " + c["caveats"][0][:200] + (
                " (%d chars; whole text in the run artifact)" % len(c["caveats"][0])
                if len(c["caveats"][0]) > 200 else ""))
    listed = [c for c in pick if not c.get("cut")]
    if len(listed) > 1:
        lines.append("GZ SHOW \"%s\": %d members -- each one's rung 1 above is its call (anchor=<n> "
                     "picks member n); check one: Gz Verify    %s    <value>    index=<n>"
                     % (label, len(listed), label))
        return lines
    best = (listed or pick)[0]
    lines.append("GZ SHOW \"%s\": use %s%s" % (
        label, best["call"] or "no call -- see the rungs above",
        ("    # verified x%d" % best["verified_passes"]) if best.get("call_from") == "store" else ""))
    return lines


# ------------------------------------------------------------------------------------ the verdict
CHECK_ON = {"on", "true", "checked", "yes", "1", "selected", "ticked"}
CHECK_OFF = {"off", "false", "unchecked", "no", "0", "unselected", "cleared"}


def judge(label, expected, actual, family=None, confirm=None, sentinel=None):
    """(verdict, why) for one read-back, compared by MEANING. Pure. A blank read is never evidence
    either way (COULD-NOT-CHECK, D13); a read that returns the field's own LABEL is the codebase's
    signature false positive and is CAUGHT-BUG; a sentinel read back is CAUGHT-BUG."""
    exp = "" if expected is None else str(expected)
    if actual is None or str(actual).strip() == "":
        return COULD_NOT_CHECK, ("the read-back of %r was blank -- a blank read is not evidence "
                                 "either way" % label)
    act = str(actual)
    if family == "checkbox":
        e = "on" if norm(exp) in CHECK_ON else "off" if norm(exp) in CHECK_OFF else None
        if e is None:
            return COULD_NOT_CHECK, ("a checkbox is on or off; expected %r is neither" % exp)
        return ((VERIFIED_PASS, "the box is %s" % act) if norm(act) == e else
                (CAUGHT_BUG, "the box is %s, expected %s" % (act, e)))
    if sentinel is not None and sentinel(act):
        return CAUGHT_BUG, "a sentinel landed: %r reads %r (a placeholder never meant as data)" % (label, act)
    if norm(act) == norm(label) and norm(exp) != norm(label):
        return CAUGHT_BUG, ("the read returned the field's own LABEL %r, not its value -- the read "
                            "resolved the label" % act)
    if act.strip() == exp.strip():
        return VERIFIED_PASS, "reads %r, exactly as expected" % act
    if confirm is None:
        return COULD_NOT_CHECK, ("reads %r, expected %r: not equal as text, and the meaning "
                                 "comparison (confirm.py) is not in this bundle" % (act, exp))
    try:
        if confirm.lenient_equal(exp, act):
            return VERIFIED_PASS, "reads %r, equal to %r by meaning (date/number/format)" % (act, exp)
    except Exception as exc:
        return COULD_NOT_CHECK, "the meaning comparison raised %s: %s" % (type(exc).__name__, exc)
    a, e = norm(act), norm(exp)
    if e and a.endswith(e) and a != e:
        return CAUGHT_BUG, ("reads %r: the expected %r is at its END -- typed onto an old value "
                            "that was never cleared" % (act, exp))
    return CAUGHT_BUG, "reads %r, expected %r" % (act, exp)


class RobotReader:
    """Reads a control's value through the job's own QWeb/QForce keywords, never by acting on it."""

    def __init__(self, timeout="3s"):
        self.timeout = timeout

    def _run(self, name, *args):
        from robot.libraries.BuiltIn import BuiltIn
        return BuiltIn().run_keyword(name, *args)

    def read(self, family, label, anchor, tag=None):
        """(value, how). Raises when the control cannot be read; the caller makes that
        COULD-NOT-CHECK. `anchor=` only for member 2+ of a repeated label (QWeb's default is 1)."""
        a = ["anchor=%s" % anchor] if (anchor and int(anchor) > 1) else []
        t = ["timeout=%s" % self.timeout]
        shown = lambda kw, *x: "    ".join([kw, label] + list(x) + a)   # noqa: E731
        if family == "checkbox":
            last = None
            for state in ("on", "off"):
                try:
                    self._run("VerifyCheckboxValue", label, state, *(a + t))
                    return state, shown("VerifyCheckboxValue", state)
                except Exception as exc:          # noqa: PERF203
                    last = exc
            raise RuntimeError("VerifyCheckboxValue found neither on nor off: %s" % last)
        if family == "dropdown" and (tag or "") == "select":
            return self._run("GetSelected", label, *(a + t)), shown("GetSelected")
        if family == "output_field":
            # QForce's GetFieldValue (licensed; its signature is not checkable outside CRT, so only
            # the label and, on a repeated label, the anchor are passed)
            return self._run("GetFieldValue", label, *a), shown("GetFieldValue")
        return self._run("GetInputValue", label, *(a + t)), shown("GetInputValue")


# families whose value lives in a control's text, not in an input property: read from a FRESH
# capture (a Lightning picklist is a <button>; a native <select> goes through GetSelected)
CAPTURE_READ = {"dropdown"}


def capture_value(c, row):
    """The displayed value of a Lightning picklist button from the capture row (its `data-value`
    attribute, else its own text when that is not its label), or None."""
    attrs = (row or {}).get("attrs") or {}
    for k in ("data-value", "value"):
        if attrs.get(k) not in (None, ""):
            return str(attrs[k])
    v = (row or {}).get("value")
    if v and norm(v) != norm(c.get("label")):
        return str(v)
    return None


# ------------------------------------------------------------------------------------ the library
class garzai_page_reader:
    """Gz Read Page / Gz Show / Gz Verify -- see the module docstring."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = VERSION

    def __init__(self):
        self._last = None          # {'fp','url','plan','rows_by_n','at'}
        self.reader = RobotReader()
        self.include_chrome = False

    # -- live glue ----------------------------------------------------------------------------
    @staticmethod
    def _driver():
        from QWeb.internal import browser as _b
        return _b.get_current_browser()

    def _output_dir(self):
        try:
            from robot.libraries.BuiltIn import BuiltIn
            return BuiltIn().get_variable_value("${OUTPUT DIR}")
        except Exception:
            return None

    def _write_artifact(self, plan):
        d = self._output_dir()
        if not d:
            return None
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", plan.get("page_key") or plan.get("url") or "page")[:120]
        path = os.path.join(d, "gz-page-plan-%s.json" % slug.strip("_"))
        try:
            with open(path, "w") as f:
                json.dump(plan, f, indent=1, default=str)
            return path
        except Exception:
            return None

    _SAME = object()

    def _plan(self, org=_SAME, include_chrome=_SAME, force=False):
        """(plan, note). Reuses the last plan while the page's fingerprint is unchanged; a fresh
        capture otherwise. Gz Show / Gz Verify pass nothing and keep the last read's `org` and
        `include_chrome`. Raises RuntimeError when there is no browser or no bundle."""
        m = mods()
        last = self._last
        if org is self._SAME:
            org = last["org_arg"] if last else None
        if include_chrome is self._SAME:
            include_chrome = last["include_chrome"] if last else False
        drv = self._driver()
        if drv is None:
            raise RuntimeError("no browser is open in this session (QWeb has no current browser)")
        url = drv.current_url or ""
        fp = m.CL._fingerprint(drv)
        if (not force and last and last["fp"] == fp and fp != "-1" and last["url"] == url
                and last["include_chrome"] == bool(include_chrome) and last["org_arg"] == (org or None)):
            return last["plan"], "same page as the last read"
        pack = pack_dir()
        host = ((re.match(r"^[a-z]+://([^/]+)", url) or [None, ""])[1] or "").lower()
        alias = org or org_for_host(host, pack)
        cap = m.CL.live_capture(drv, alias)
        # the caller's own `org` (or None): build_plan resolves the alias from the pack itself and
        # records WHERE it came from
        plan = build_plan(cap["html"], cap["url"], org or None, pack, include_chrome=include_chrome)
        plan["capture_ms"] = cap.get("capture_ms")
        # the ref each printed page ends on, kept in the run artifact so a person can check a
        # quoted ref against what was printed
        plan["page_refs"] = [render_page(plan, p)[-1].split(" ref ", 1)[1].split(" ", 1)[0]
                             for p in range(1, pages_of(plan) + 1)]
        plan["artifact"] = self._write_artifact(plan)
        note = "fresh read" if last is None else (
            "the page changed since the last read -- fresh read" if last["url"] == url else "fresh read")
        self._last = {"fp": fp, "url": url, "plan": plan, "include_chrome": bool(include_chrome),
                      "org_arg": org or None, "at": time.time()}
        return plan, note

    # -- the keywords -------------------------------------------------------------------------
    @keyword("Gz Read Page")
    def gz_read_page(self, page=1, include_chrome=False, org=None):
        """Read the CURRENT page and print its control plan, 20 controls per page: each control as a
        person sees it, its family, and the exact keyword call to use (`# verified xN` = that call
        passed live before). The LAST line says `page 1 of N -- NEXT: Gz Read Page    page=2` or
        END. Prints to the console and returns the same text. Never acts on the page."""
        inc = str(include_chrome).strip().lower() in ("true", "1", "yes", "on")
        try:
            plan, note = self._plan(org=org or None, include_chrome=inc)
        except Exception as exc:
            msg = "GZ READ PAGE: COULD-NOT-CHECK -- %s: %s" % (type(exc).__name__, exc)
            _say([msg])
            raise AssertionError(msg)
        try:
            p = int(str(page).strip())
        except (TypeError, ValueError):
            p = 1
        lines = render_page(plan, p, fresh_note=note)
        return _say(lines)

    @keyword("Gz Show")
    def gz_show(self, label, index=None):
        """Show ONE control in full: every rung to call it (keyword, ClickItem, relative xpath),
        the store's own rungs with their verdicts, the member number on a repeated label and the
        anchor candidates. The LAST line is the call to use. Never acts on the page."""
        try:
            plan, _note = self._plan()
        except Exception as exc:
            msg = "GZ SHOW \"%s\": COULD-NOT-CHECK -- %s: %s" % (label, type(exc).__name__, exc)
            _say([msg])
            raise AssertionError(msg)
        lines = render_show(plan, label, index)
        text = _say(lines)
        if lines[-1].startswith("GZ SHOW \"%s\": COULD-NOT-CHECK" % label):
            raise AssertionError(lines[-1])
        return text

    @keyword("Gz Verify")
    def gz_verify(self, label, expected_value, index=None, on_mismatch="fail"):
        """Read a control's value back WITHOUT touching it and print a verdict compared by meaning:
        VERIFIED-PASS / CAUGHT-BUG / COULD-NOT-CHECK, on the LAST line. Only VERIFIED-PASS passes;
        CAUGHT-BUG and COULD-NOT-CHECK fail the step (on_mismatch=warn prints and returns instead).
        On a repeated label pass index=<member> (Gz Read Page shows `(2 of 3)`)."""
        lines, verdict, why = self._verify(label, expected_value, index)
        lines.append("%s: %s" % (verdict, why))
        text = _say(lines)
        if verdict != VERIFIED_PASS and str(on_mismatch).strip().lower() != "warn":
            raise AssertionError("%s: %s" % (verdict, why))
        return lines[-1]

    def _verify(self, label, expected, index):
        head = "GZ VERIFY \"%s\" expected %r" % (label, "" if expected is None else str(expected))
        try:
            m = mods()
        except Exception as exc:
            return [head], COULD_NOT_CHECK, "%s: %s" % (type(exc).__name__, exc)
        try:
            plan, _note = self._plan()
        except Exception as exc:
            return [head], COULD_NOT_CHECK, "could not read the page: %s: %s" % (type(exc).__name__, exc)
        members, sugg = find_members(plan, label)
        k = None
        if index not in (None, "", "None"):
            try:
                k = int(index)
            except (TypeError, ValueError):
                return [head], COULD_NOT_CHECK, "index=%r is not a number" % (index,)
        if not members:
            return [head], COULD_NOT_CHECK, "no control labelled %r on this page%s" % (
                label, ("; closest: " + ", ".join(sugg)) if sugg else "")
        if len(members) > 1 and k is None:
            return [head], COULD_NOT_CHECK, (
                "%r labels %d controls here -- say which: Gz Verify    %s    %s    index=<1..%d> "
                "(Gz Show    %s lists them)" % (label, len(members), label, expected, len(members), label))
        if k is not None and not 1 <= k <= len(members):
            return [head], COULD_NOT_CHECK, "index=%d asked, %d member(s)" % (k, len(members))
        c = members[(k or 1) - 1]
        fam = c["family"]
        anchor = c["member"][0] if c.get("member") else 1
        sentinel = getattr(m.CL, "sentinel_landed", None)
        if fam in CAPTURE_READ and (c.get("tag") or "") != "select":
            try:
                plan2, _n = self._plan(force=True)
            except Exception as exc:
                return [head], COULD_NOT_CHECK, "could not re-read the page: %s" % exc
            fresh = [x for x in all_controls(plan2) if x["n"] == c["n"] and norm(x["label"]) == norm(c["label"])]
            val = capture_value(c, fresh[0]) if fresh else None
            how = "the picklist's displayed value in a fresh capture"
            if val is None:
                return [head, "  read: %s" % how], COULD_NOT_CHECK, (
                    "the capture shows no selected value for %r" % label)
        elif fam in TYPE_FAMILIES | DATE_FAMILIES | {"checkbox", "lookup", "output_field", "dropdown"}:
            try:
                val, how = self.reader.read(fam, c["label"], anchor, c.get("tag"))
            except Exception as exc:
                return [head], COULD_NOT_CHECK, "the read-back raised %s: %s" % (
                    type(exc).__name__, _cut(exc))
            if fam == "output_field" and m.CONFIRM is not None:
                # confirm.field_value: a read-only value that IS its label, or still carries it as
                # a prefix ('Stage:Proposal'), is the label, not the value
                try:
                    m.CONFIRM.field_value(c["label"], val)
                except Exception as exc:
                    cnc = getattr(m.CONFIRM, "CouldNotCheck", None)
                    verdict = COULD_NOT_CHECK if (cnc and isinstance(exc, cnc)) else CAUGHT_BUG
                    return [head, "  read: %s -> %r" % (how, val)], verdict, _cut(exc)
        else:
            return [head], COULD_NOT_CHECK, ("no read-back for a %s yet (family %s)" % (
                c["family_word"], fam))
        verdict, why = judge(c["label"], expected, val, fam, m.CONFIRM, sentinel)
        return [head, "  read: %s -> %r" % (how, val)], verdict, why
