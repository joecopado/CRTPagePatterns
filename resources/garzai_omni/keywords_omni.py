"""keywords_omni -- OmniStudio (standard runtime) keywords, read-back enforced.

Usage: import from a Robot library or drive through the interop holder:
    python3 tools/interop/up.py dev1 --op kw --name omni_type --args '["ZooText","hello"]'

Stream S19, 2026-09-05. Every signature below was MEASURED on `dev1` against the
OmniScript we own (`Zoo_Omni_Intake`, Type/SubType `Zoo/Intake`), authored by S19
precisely so these could be proven rather than predicted -- fsc7f (S17) had no
launcher for any script, so every one of these was COULD-NOT-CHECK before today.

THE SCOPING ANCHOR
------------------
`[data-omni-key="<OmniProcessElement.Name>"]` sits on every OmniScript element HOST,
and equals the element's metadata Name exactly. Measured 2026-09-05 on dev1: 23/23
elements. That makes it the strongest locator on the page -- an author-controlled,
metadata-joined id -- and every keyword here scopes to it FIRST and then descends the
composed tree. No page-wide text search, ever.

WHY NOT PLAIN QWEb (four measured reasons, each one a naive green)
------------------------------------------------------------------
1. `ClickText`/`TypeText` search the whole page. S17 measured a page-wide option
   search picking `Agentforce` out of the Lightning nav bar and reporting a pass,
   because the step asserted nothing. Everything here is host-scoped and read back.
2. `option.click()` does NOT commit an OmniStudio combobox value. Measured by S17
   (0/1 committed) and reproduced here. **S19 solved it:** dispatch the full pointer
   sequence `mouseover -> mousedown -> mouseup -> click` on the DEEPEST node whose
   text is the option label. Measured 2026-09-05: `Bravo` asked, `Bravo` read back.
3. An open listbox overlays the next control -> `ElementClickInterceptedException` on
   the field BELOW it. Every select/typeahead/lookup keyword here sends Escape after
   committing, before returning.
4. Format-shifting reads. Currency `250000` reads back `$ 250,000.00`; Telephone
   `4159017000` reads back `(415) 901-7000`. A string-equal check gives a FALSE FAIL;
   a "did it change?" check gives a FALSE PASS. Both route through `confirm.py` with
   a family-aware normaliser (`_normalise_for`), so the read-back is format-aware and
   still a real comparison.

LABEL SOURCES DIFFER BY FAMILY (measured, corrects S17's fsc7f-only table)
--------------------------------------------------------------------------
In an OmniScript with the designer-default empty `placeholder`, S17's "the label comes
from the placeholder" is WRONG: `placeholder=""` and there is a real `<label for>` in
the element's own shadow root. Measured on dev1, 10 of 14 controls carry `label[for]`
(Text, Number, Currency, Date, Select, Telephone, Email, Lookup, Typeahead, BlockText).
The three that carry NO label element at all are **Radio, Checkbox and Multi-select** --
for those, `data-omni-key` is the only handle there is, which is exactly why these
keywords are key-first rather than label-first.

FLEXCARD HOST RESOLVER (added 2026-09-06, Phase 3 addendum (b))
-----------------------------------------------------------------
An OmniUiCard (FlexCard) renders NONE of its elements with `data-omni-key` -- that
attribute is `OmniProcessElement.Name`, an OmniScript-only metadata concept (measured
2026-09-06 on fsc7f's DigitalLending loan-calculator FlexCard: `grep -c data-omni-key`
on the captured page is 0; see docs/recorder/evidence/omni-fsc7f-2026-09-06.json). Every
keyword here calls `_require_host`, which now tries three anchors in order, so no
keyword body had to change -- only `__host(key)` in `_HELPERS`:

  1. `[data-omni-key="<key>"]`                    -- OmniScript (unchanged, tried first)
  2. `[data-element-label="<norm(key)>"]`         -- FlexCard, see below
  3. `[aria-label="<key>"]` or `[placeholder="<key>"]` on the leaf control -- FlexCard,
     last resort, for a control whose wrapper carries no `data-element-label` at all

`data-element-label` is the FlexCard's own metadata-joined id -- it sits on the
`runtime_omnistudio_flexcards-*` wrapper ONE LEVEL ABOVE the `runtime_omnistudio_common-*`
control that actually renders the input, and its value is the FlexCard Designer's
"Element Label" for that element, LOWERCASED WITH SPACES STRIPPED by the runtime.
Measured 2026-09-06 on fsc7f (`grep -o 'data-element-label="[^"]*"'` on the captured
loan-calculator page): `data-element-label="repaymenttype"` for the "Repayment Type"
select, `"loanamount"` for the Currency input, `"loantermselection"` for the Loan-Term
radio group (which the group's own `<fieldset>` carries no aria-label or legend text
for at all -- this is the ONLY anchor that reaches it), `"startdate"` for the Date
picker. `__norm()` lowercases and strips everything but `[a-z0-9]` from BOTH sides, so
a caller may pass the metadata label (`"repaymenttype"`), the FlexCard Designer's
spaced form (`"Repayment Type"`), or the rendered aria-label/placeholder text -- all
three normalise to the same string and all three resolve.

Measured DOM signatures per control family on THIS FlexCard (differs from the
aria-label-only table `docs/recorder/OMNISTUDIO.md` recorded from S17's 2026-09-05
hand-rolled pass -- this runtime build renders `label[for]` too):
  - Select     (`runtime_omnistudio_common-combobox`):      leaf `input[role=combobox]`
    carries `aria-label` AND `placeholder` AND a `<label for>` -- any of the three
    anchors resolves it.
  - Currency/Number/Text (`runtime_omnistudio_common-input`,
    `runtime_omnistudio_common-masked-input`): leaf `input` carries ONLY `placeholder`
    (no `aria-label`) -- anchor #3 needs the placeholder path specifically.
  - Radio group (`runtime_omnistudio_common-radio-group`): the `<fieldset>` has no
    aria-label and no legend text; `data-element-label` on the
    `runtime_omnistudio_flexcards-flex-radio-input` wrapper is the ONLY handle.
  - Date (`runtime_omnistudio_common-date-picker`): leaf `input[data-id=date-picker-
    slds-input]` carries `aria-label` with the accepted format baked in
    (`"Start Date (yyyy-MM-dd)"`).

Where `__host` resolves to the FlexCard's OUTER wrapper (anchors #1/#2), the existing
`__inside(h, sel)` composed-tree walk already recurses through nested shadow roots
(`runtime_omnistudio_flexcards-*` -> `runtime_omnistudio_common-*` -> its own shadow
DOM) with no change -- it was already generic. Where `__host` resolves directly to the
leaf `input` (anchor #3, no wrapper found), `__inside` still works because `n.matches(sel)`
checks the host node itself before descending, the same behaviour the OmniScript path
already relied on.
"""
from __future__ import annotations

import time

import confirm

try:
    from QWeb.internal import browser as browser_internal
except ImportError:  # offline unit tests must still import this module
    browser_internal = None  # type: ignore[assignment]


class OmniElementNotFound(AssertionError):
    """No host carries this `data-omni-key`. Deliberately loud and deliberately NOT a
    'return None' -- a missing element must never read as an empty value."""


def _driver():
    return browser_internal.get_current_browser()


# --- one composed-tree helper, injected once per call ------------------------
# Chrome 152 THROWS on ShadowRoot.getElementById (docs/ERRORS.md 6.5) -- this uses
# querySelector('#'+CSS.escape(id)) everywhere instead.
_HELPERS = r"""
function __roots(){ const out=[document]; const seen=new Set();
  (function w(r){ if(!r||seen.has(r))return; seen.add(r);
    for(const e of r.querySelectorAll('*')){ if(e.shadowRoot){ out.push(e.shadowRoot); w(e.shadowRoot);} } })(document);
  return out; }
function __norm(s){ return (s||'').toLowerCase().replace(/[^a-z0-9]/g,''); }
function __host(key){
  for(const r of __roots()){
    const e = r.querySelector('[data-omni-key="'+CSS.escape(key)+'"]'); if(e) return e; }
  const nk = __norm(key);
  if(nk){
    for(const r of __roots()){
      for(const e of r.querySelectorAll('[data-element-label]')){
        if(__norm(e.getAttribute('data-element-label')) === nk) return e;
      }
    }
  }
  for(const r of __roots()){
    const e = r.querySelector('[aria-label="'+CSS.escape(key)+'"]'); if(e) return e; }
  for(const r of __roots()){
    const e = r.querySelector('[placeholder="'+CSS.escape(key)+'"]'); if(e) return e; }
  return null; }
function __inside(h, sel){ const out=[]; const seen=new Set();
  (function w(n){ if(!n||seen.has(n))return; seen.add(n);
    if(n.matches && n.matches(sel)) out.push(n);
    const kids = n.shadowRoot ? [...n.children, ...n.shadowRoot.children] : [...(n.children||[])];
    for(const c of kids) w(c); })(h);
  return out; }
function __setNative(el, v){
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const d = Object.getOwnPropertyDescriptor(proto, 'value');
  el.focus();                      // .click() does NOT focus a Lightning input
  d.set.call(el, v);
  for (const t of ['input','change','blur']) el.dispatchEvent(new Event(t,{bubbles:true,composed:true}));
}
function __listbox(h){
  const trig = __inside(h,'input[aria-controls]')[0];
  if(!trig) return {trig:null, opts:[]};
  const id = trig.getAttribute('aria-controls');
  let box = null;
  for(const r of __roots()){ let e=null; try{ e = r.querySelector('#'+CSS.escape(id)); }catch(x){}
    if(e){ box = e; break; } }
  const opts = box ? [...box.querySelectorAll('[role=option], li, [data-value]')] : [];
  return {trig, box, opts};
}
function __escape(h){ const t = __inside(h,'input[aria-controls]')[0];
  if(t) t.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,composed:true})); }
function __visible(e){ const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
// An OmniStudio FlexCard action host renders its own EMPTY
// `runtime_omnistudio_common-modal` up front (measured: the `editaction` host on
// fsc7f capture 05 contains one with an empty shadow root and an empty content
// slot). A raw querySelectorAll count is therefore NOT an oracle for "a modal
// opened" -- it is already >= 1 before any click. Count only modals that are
// actually on screen AND carry content.
function __openModals(){ let n = 0;
  for(const r of __roots()){
    for(const m of r.querySelectorAll('runtime_omnistudio_common-modal, [role=dialog]')){
      if(__visible(m) && (m.textContent||'').trim()) n++;
    }
  }
  return n; }
// --- SLDS calendar-widget helpers for __pickDate (omni_date) -----------------
// Measured live on fsc7f 2026-09-07 (docs/recorder/sessions/fsc7f/
// omni-date-calendar-fix-2026-09-07.json): a plain native-value write into
// `input[data-id=date-picker-slds-input]` never commits on this control (the
// CAUGHT-BUG `omni_date` used to ship with) -- only driving the SLDS calendar
// widget itself (year <select>, prevMonth/nextMonth buttons, a <td> day cell)
// commits a value. Each JS call below does ONE step and returns immediately;
// the Python side sleeps between calls because the LWC re-render that follows
// a click is NOT synchronous -- reading the month header in the same call that
// clicked prevMonth/nextMonth returns the PRE-click text (measured: 0/1 without
// a real wait, 15/15 with a ~0.3-0.5s wait per step).
function __dateOpen(host){
  const already = __inside(host, '[data-id="date-picker-div"]')[0];
  if(already) return {already:true};
  const btn = __inside(host, 'button[data-id=datePickerBtn]')[0];
  if(!btn) return {error:'no datePickerBtn'};
  btn.click();
  return {clicked:true};
}
function __dateState(host){
  const div = __inside(host, '[data-id="date-picker-div"]')[0];
  if(!div) return null;
  const h2 = div.querySelector('[data-id="selected_month"]');
  const sel = div.querySelector('select[data-id="select-01"]');
  return {open:true, month: h2 ? h2.textContent.trim() : null, year: sel ? sel.value : null};
}
function __dateSetYear(host, yearStr){
  const div = __inside(host, '[data-id="date-picker-div"]')[0];
  if(!div) return {error:'picker not open'};
  const sel = div.querySelector('select[data-id="select-01"]');
  if(!sel) return {error:'no year select'};
  const opt = [...sel.options].find(o => (o.textContent||'').trim() === yearStr);
  if(!opt) return {error:'year not offered', tried: yearStr};
  sel.value = opt.value;
  sel.dispatchEvent(new Event('change', {bubbles:true, composed:true}));
  return {ok:true};
}
function __dateNav(host, direction){
  const div = __inside(host, '[data-id="date-picker-div"]')[0];
  if(!div) return {error:'picker not open'};
  const btn = div.querySelector('button[data-id=' + direction + ']');
  if(!btn) return {error:'no ' + direction};
  btn.click();
  return {ok:true};
}
function __dateClickDay(host, wantLabel){
  const div = __inside(host, '[data-id="date-picker-div"]')[0];
  if(!div) return {error:'picker not open'};
  const cells = [...div.querySelectorAll('td.curr-month span[aria-label]')];
  const hit = cells.find(c => c.getAttribute('aria-label') === wantLabel);
  if(!hit) return {error:'day cell not found', wantLabel,
                   sample: cells.slice(0,3).map(c=>c.getAttribute('aria-label'))};
  hit.closest('td').click();
  return {ok:true};
}
"""


def _js(script, *args):
    return _driver().execute_script(_HELPERS + "\n" + script, *args)


def _require_host(key: str) -> None:
    """Resolve `key` to a host via `__host()` in `_HELPERS` -- tries, in order:
    `[data-omni-key=key]` (OmniScript), `[data-element-label=norm(key)]` (FlexCard,
    metadata-joined, case/space-insensitive), then `[aria-label=key]` or
    `[placeholder=key]` on the leaf control (FlexCard last resort). See the module
    docstring's "FLEXCARD HOST RESOLVER" section for the measured DOM signatures."""
    if not _js("return !!__host(arguments[0]);", key):
        raise OmniElementNotFound(
            f"no element host resolves for key/label {key!r} by any of: "
            "data-omni-key (OmniScript, equals OmniProcessElement.Name), "
            "data-element-label (FlexCard, equals the Designer Element Label, "
            "lowercased/despaced), or aria-label/placeholder on the leaf control "
            "(FlexCard last resort). Check the metadata name/label, not an "
            "unrelated rendered string."
        )


# --- family-aware normalisation ---------------------------------------------
# Measured on dev1 2026-09-05: currency 250000 -> '$ 250,000.00';
# telephone 4159017000 -> '(415) 901-7000'. Both are the runtime being CORRECT.
_DIGITS = str.maketrans("", "", "()-. ")


def _normalise_for(family: str, value):
    s = "" if value is None else str(value)
    if family in ("omni-currency", "omni-number"):
        s = s.replace("$", "").replace(",", "").strip()
        if s.endswith(".00"):
            s = s[:-3]
        return s
    if family == "omni-telephone":
        return s.translate(_DIGITS)
    if family == "omni-date":
        # Measured live on fsc7f 2026-09-07: the calendar widget commits in
        # MM-DD-YYYY (`04-17-1990`) regardless of the ISO `YYYY-MM-DD` asked
        # for -- a format shift, not a value mismatch. Normalise both sides to
        # a bare YYYY-MM-DD so a real mismatch still raises.
        s = s.strip()
        for sep in ("-", "/"):
            parts = s.split(sep)
            if len(parts) == 3:
                a, b, c = parts
                if len(a) == 4:  # already YYYY-first
                    y, mo, d = a, b, c
                else:  # MM-DD-YYYY
                    mo, d, y = a, b, c
                try:
                    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
                except ValueError:
                    return s
        return s
    return s.strip()


def _confirm_readback(family: str, key: str, asked, got):
    """The read-back gate. Never let a format shift read as either FAIL or PASS by
    accident: normalise BOTH sides the same way, then hand the pair to confirm.py so
    an actual mismatch still raises SilentWrongValue."""
    if got is None:
        confirm.unreadable(f"{family} {key}", tried="data-omni-key host scope")
    confirm.typed_value(_normalise_for(family, asked), _normalise_for(family, got),
                        field=f"{key} ({family})")
    return got


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------
def omni_type(key: str, value, family: str = "omni-text"):
    """Set any OmniStudio free-text-ish control (Text, Number, Currency, Email,
    Telephone, Date) by its `data-omni-key`, then READ IT BACK."""
    _require_host(key)
    got = _js(
        """const h = __host(arguments[0]);
           const inp = __inside(h,'input:not([type=hidden]), textarea')[0];
           if(!inp) return null;
           __setNative(inp, arguments[1]);
           return inp.value;""", key, str(value))
    return _confirm_readback(family, key, value, got)


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]


def omni_date(key: str, value: str):
    """Set an OmniStudio Date element by DRIVING ITS OWN SLDS CALENDAR WIDGET.

    `value` is `YYYY-MM-DD`.

    CAUGHT-BUG (fsc7f 2026-09-06/07, docs/recorder/sessions/fsc7f/
    omni-activation-and-elements-2026-09-07.json and loopN1-pillar1-2-2026-09-06.json):
    the Date element renders a TEXT input (`[data-id=date-picker-slds-input]`) that
    LOOKS like any other free-text control, so the original `omni_date` reused
    `omni_type`'s native-value-setter body. Measured live, twice, on two different
    fsc7f surfaces (the OmniScript AND the FlexCard): the typed value never commits
    -- `inp.value` reads back the just-written string in the SAME call (a
    self-referential, vacuous check), but a genuine second read through
    `get_omni_value`'s canonical selector comes back empty. dev1's authored
    OmniScript passed because ITS date control happens to accept a plain native
    write; that made the bug org-specific and the matrix that recorded only dev1
    shipped it as VERIFIED-PASS.

    THE FIX: this control only commits through its own calendar widget (SLDS
    `slds-datepicker`): a "Select Date" icon-button opens a `role=dialog` with a
    year `<select>` and prevMonth/nextMonth buttons; clicking a `<td class=
    curr-month>` day cell is the actual commit gesture. Reproduced and proven
    live on fsc7f 2026-09-07 (docs/recorder/sessions/fsc7f/
    omni-date-calendar-fix-2026-09-07.json): a plain write left `''`; driving the
    widget below committed `04-17-1990` for `1990-04-17`, read back through the
    SAME independent `get_omni_value` path used for the CAUGHT-BUG.

    Each step below is its own `_js` round trip because the LWC re-render that
    follows a click is NOT synchronous -- reading the month header back inside
    the SAME script that clicked prevMonth/nextMonth returns the PRE-click text
    (measured 0/1 without a real wait between steps, 15/15 with one).
    """
    _require_host(key)
    parts = str(value).split("-")
    if len(parts) != 3:
        confirm.unreadable(f"omni-date {key}",
                           tried=f"expected 'YYYY-MM-DD', got {value!r}")
    y, m, dnum = (int(p) for p in parts)
    want_month = _MONTH_NAMES[m - 1]
    # JS's own Date().toDateString() is the day-cell oracle -- it is what the
    # widget's aria-label is generated from, so no separate formatting logic
    # can drift out of sync with it.
    want_label = _js(
        "return new Date(arguments[0], arguments[1]-1, arguments[2]).toDateString();",
        y, m, dnum)

    opened = _js("return __dateOpen(__host(arguments[0]));", key)
    if opened.get("error"):
        confirm.unreadable(f"omni-date {key}", tried=f"could not open the calendar: {opened}")
    time.sleep(0.4)

    year_res = _js("return __dateSetYear(__host(arguments[0]), arguments[1]);", key, str(y))
    if year_res.get("error"):
        confirm.unreadable(f"omni-date {key}", tried=f"could not select year {y}: {year_res}")
    # The year <select>'s 'change' handler re-renders the DAY GRID on its own React
    # tick -- measured live (fsc7f 2026-09-07, Start Date field): when the
    # currently-shown MONTH TEXT already equals the target month, the month-nav
    # loop below never clicks anything and so never waits, and the day grid still
    # shows the OLD year's cells (`sel.value` itself updates synchronously, so
    # polling the <select> proves nothing). Poll the actual rendered day cells for
    # the target year instead of a fixed sleep or the select's own value.
    for _ in range(10):
        year_seen = _js(
            """const h = __host(arguments[0]);
               const div = __inside(h, '[data-id="date-picker-div"]')[0];
               if(!div) return null;
               const c = div.querySelector('td.curr-month span[aria-label]');
               return c ? c.getAttribute('aria-label').slice(-4) : null;""", key)
        if year_seen == str(y):
            break
        time.sleep(0.2)
    else:
        confirm.unreadable(f"omni-date {key}",
                           tried=f"day grid still shows year {year_seen!r} after selecting {y!r}")

    for _ in range(15):
        st = _js("return __dateState(__host(arguments[0]));", key)
        if not st or not st.get("open"):
            confirm.unreadable(f"omni-date {key}", tried="calendar closed unexpectedly mid-navigation")
        if st["month"] == want_month:
            break
        cur_idx = _MONTH_NAMES.index(st["month"])
        want_idx = m - 1
        diff = (want_idx - cur_idx) % 12
        direction = "nextMonthBtnId" if diff <= 6 else "prevMonthBtnId"
        nav = _js("return __dateNav(__host(arguments[0]), arguments[1]);", key, direction)
        if nav.get("error"):
            confirm.unreadable(f"omni-date {key}", tried=f"month navigation failed: {nav}")
        time.sleep(0.4)
    else:
        confirm.unreadable(f"omni-date {key}",
                           tried=f"month never reached {want_month!r} in 15 clicks "
                                 f"(stuck at {st.get('month')!r})")

    day_res = _js("return __dateClickDay(__host(arguments[0]), arguments[1]);", key, want_label)
    if day_res.get("error"):
        confirm.unreadable(f"omni-date {key}", tried=f"day cell {want_label!r} not clickable: {day_res}")
    time.sleep(0.4)

    got = get_omni_value(key, family="omni-date")
    return _confirm_readback("omni-date", key, value, got)


def omni_select(key: str, value: str, timeout: float = 4.0):
    """Commit an OmniStudio Select. This is the keyword S17 could not write.

    Three things it does that a hand-rolled ClickText does not:
      - scopes options to the combobox's OWN listbox via `aria-controls`
      - dispatches mouseover/mousedown/mouseup/click on the deepest text node
        (a bare `.click()` on the <li> leaves the field EMPTY -- measured twice)
      - sends Escape afterwards so the overlay cannot intercept the next control
    """
    _require_host(key)
    _js("""const h = __host(arguments[0]);
           const t = __inside(h,'input[aria-controls]')[0];
           if(t){ t.focus(); t.click(); }""", key)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _js("return __listbox(__host(arguments[0])).opts.length;", key):
            break
        time.sleep(0.15)
    shown = _js(
        """const h = __host(arguments[0]); const want = arguments[1];
           const {opts} = __listbox(h);
           let target = opts.find(o => (o.textContent||'').trim() === want)
                     || opts.find(o => (o.textContent||'').trim().includes(want));
           if(!target) return {ok:false, opts: opts.map(o=>o.textContent.trim())};
           let node = target;
           while(node.children.length === 1 &&
                 (node.children[0].textContent||'').trim() === want) node = node.children[0];
           for(const t of ['mouseover','mousedown','mouseup','click'])
             node.dispatchEvent(new MouseEvent(t,{bubbles:true,composed:true,cancelable:true}));
           return {ok:true};""", key, value)
    if not shown.get("ok"):
        confirm.unreadable(
            f"omni-select {key}",
            tried=f"option {value!r} is not in this combobox's own listbox; "
                  f"scoped options were {shown.get('opts')!r}")
    time.sleep(0.3)
    got = _js("""const h = __host(arguments[0]);
                 const inp = __inside(h,'input[aria-controls]')[0];
                 __escape(h);
                 return inp ? inp.value : null;""", key)
    return _confirm_readback("omni-select", key, value, got)


def omni_radio(key: str, value: str):
    """Radio groups have NO `label[for]` -- the `value` attribute is the only handle."""
    _require_host(key)
    got = _js(
        """const h = __host(arguments[0]);
           const r = __inside(h,'input[type=radio][value="'+CSS.escape(arguments[1])+'"]')[0]
                  || __inside(h,'input[type=radio]').find(x => x.value === arguments[1]);
           if(!r) return null;
           r.click();
           const on = __inside(h,'input[type=radio]').filter(x=>x.checked).map(x=>x.value);
           return on.join(',');""", key, value)
    return _confirm_readback("omni-radio", key, value, got)


def omni_checkbox(key: str, checked=True):
    """Checkbox has no label element at all; `data-omni-key` is the whole locator."""
    _require_host(key)
    want = str(checked).lower() not in ("false", "0", "no", "")
    got = _js(
        """const h = __host(arguments[0]);
           const c = __inside(h,'input[type=checkbox]')[0];
           if(!c) return null;
           if(c.checked !== arguments[1]) c.click();
           return c.checked;""", key, want)
    return _confirm_readback("omni-checkbox", key, want, got)


def omni_multiselect(key: str, values):
    """Multi-select renders as a checkbox GROUP whose every input carries
    `name="<OmniProcessElement.Name>"` -- another metadata join, measured on dev1."""
    _require_host(key)
    wanted = values if isinstance(values, list) else [v.strip() for v in str(values).split("|")]
    got = _js(
        """const h = __host(arguments[0]);
           for(const v of arguments[1]){
             const c = __inside(h,'input[type=checkbox]').find(x => x.value === v);
             if(c && !c.checked) c.click();
           }
           return __inside(h,'input[type=checkbox]').filter(x=>x.checked).map(x=>x.value).join('|');""",
        key, wanted)
    return _confirm_readback("omni-multiselect", key, "|".join(wanted), got)


def omni_lookup(key: str, search: str, choose: str | None = None, timeout: float = 8.0):
    """Server-backed SObject lookup. Typing is local; the option list is a round trip,
    so the wait is real and a timeout is COULD-NOT-CHECK, never a pass."""
    _require_host(key)
    _js("""const h = __host(arguments[0]);
           const inp = __inside(h,'input[role=combobox]')[0];
           if(inp){ __setNative(inp, arguments[1]);
                    inp.dispatchEvent(new Event('keyup',{bubbles:true,composed:true})); }""",
        key, search)
    if choose is None:
        got = _js("""const h = __host(arguments[0]);
                     const inp = __inside(h,'input[role=combobox]')[0];
                     return inp ? inp.value : null;""", key)
        return _confirm_readback("omni-lookup", key, search, got)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _js("return __listbox(__host(arguments[0])).opts.length;", key):
            break
        time.sleep(0.25)
    return omni_select_commit(key, choose, "omni-lookup")


def omni_typeahead(key: str, search: str, choose: str | None = None, timeout: float = 6.0):
    """Typeahead opens its listbox on TYPING, never on a click -- clicking the trigger
    leaves `opts=[]`, which is what a naive select-style keyword reports as an empty
    field. Measured on dev1 2026-09-05 (the CAUGHT-BUG that produced this keyword)."""
    _require_host(key)
    _js("""const h = __host(arguments[0]);
           const inp = __inside(h,'input[aria-autocomplete=list], input[aria-controls]')[0];
           if(inp){ inp.focus(); __setNative(inp, arguments[1]);
                    inp.dispatchEvent(new Event('keyup',{bubbles:true,composed:true})); }""",
        key, search)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _js("return __listbox(__host(arguments[0])).opts.length;", key):
            break
        time.sleep(0.2)
    return omni_select_commit(key, choose or search, "omni-typeahead")


def omni_select_commit(key: str, value: str, family: str):
    """Shared commit half of select/lookup/typeahead: full pointer sequence on the
    deepest matching node, Escape afterwards, then read back."""
    shown = _js(
        """const h = __host(arguments[0]); const want = arguments[1];
           const {opts} = __listbox(h);
           let target = opts.find(o => (o.textContent||'').trim() === want)
                     || opts.find(o => (o.textContent||'').trim().includes(want));
           if(!target) return {ok:false, opts: opts.map(o=>o.textContent.trim())};
           let node = target;
           while(node.children.length === 1 &&
                 (node.children[0].textContent||'').trim() === want) node = node.children[0];
           for(const t of ['mouseover','mousedown','mouseup','click'])
             node.dispatchEvent(new MouseEvent(t,{bubbles:true,composed:true,cancelable:true}));
           return {ok:true};""", key, value)
    if not shown.get("ok"):
        confirm.unreadable(
            f"{family} {key}",
            tried=f"{value!r} not in this control's own listbox; scoped options were "
                  f"{shown.get('opts')!r} (a page-wide search would have matched the nav bar)")
    time.sleep(0.3)
    got = _js("""const h = __host(arguments[0]);
                 const inp = __inside(h,'input[aria-controls]')[0];
                 __escape(h);
                 return inp ? inp.value : null;""", key)
    return _confirm_readback(family, key, value, got)


def omni_edit_block_add_row(key: str, timeout: float = 4.0):
    """Add one repeatable row to an Edit Block and PROVE the row count went up.

    CAUGHT-BUG, fixed here (fsc7f 2026-09-07, `EmploymentBlock` on
    DigitalLendingDF/ApplicantIntakeSecured -- the first real Edit Block surface
    this keyword has ever been proven against; the Edit Block existed NOWHERE in
    fsc7f before this org's product-fetch fix unblocked Loan Details): the ORIGINAL
    oracle counted `[data-omni-key]` elements SCOPED TO THE ONE BLOCK INSTANCE
    `_require_host(key)` resolves. Clicking Add does not add rows inside that
    block -- it adds a whole NEW SIBLING block ("Employment 2", "Employment 3", ...)
    that is NOT a descendant of the first block's host at all, so a host-scoped
    count can never see it. Measured live: the keyword reported "count did not
    rise (11 -> 11)" on a click that, per a full-page text dump taken in the same
    pass, had visibly rendered four new "Employment N" blocks with their own
    Delete buttons. The fix counts something that lives OUTSIDE any one block's
    scope: the page-wide number of `aria-label="Delete the block named ..."`
    buttons, which the runtime renders exactly one of per block, anywhere on the
    page -- so it is unaffected by which block instance `key` happened to resolve.
    """
    _require_host(key)

    def _block_count():
        return _js(
            """let n = 0;
               for(const r of __roots())
                 for(const e of r.querySelectorAll('[aria-label^="Delete the block named"]')) n++;
               return n;""")

    before = _block_count()
    clicked = _js(
        """const h = __host(arguments[0]);
           const b = __inside(h,'button').filter(x => __visible(x) &&
                     /add|new/i.test((x.textContent||'') + ' ' + (x.title||'') + ' ' +
                                     (x.getAttribute('aria-label')||'')))[0];
           if(!b) return {ok:false, saw: __inside(h,'button').map(x=>(x.textContent||'').trim())};
           b.click(); return {ok:true};""", key)
    if not clicked.get("ok"):
        confirm.unreadable(f"omni-edit-block {key}",
                           tried=f"no visible Add control inside the block; buttons were "
                                 f"{clicked.get('saw')!r}")
    deadline = time.time() + timeout
    after = before
    while time.time() < deadline:
        after = _block_count()
        if after > before:
            break
        time.sleep(0.2)
    if after <= before:
        confirm.unreadable(f"omni-edit-block {key}",
                           tried=f"Add was clicked but the page-wide block count did not rise "
                                 f"({before} -> {after}); the click did not create a row")
    return after


def omni_next_step(label: str = "Next", timeout: float = 12.0):
    """Advance the script and CHECK THE LANDING CHANGED.

    Three things measured on dev1 that break the obvious implementation:
      - BOTH steps' Next buttons are in the DOM at once; only one has a box. Scope to
        the visible one, and require exactly one, or you click the wrong step's button.
      - The button's text lives inside `runtime_omnistudio_common-button`'s own shadow
        root, so a light-DOM `textContent` scan sees `''` and finds nothing.
      - **The vacuous green this keyword shipped with for one run:** the first version
        asserted only that the step chart reported *some* aria-current step. It does,
        always -- including when the click did nothing. Measured 2026-09-05: the keyword
        returned VERIFIED-PASS with `index: 0` after a click that never left step 1.
        The landing check now compares against the index taken BEFORE the click, and a
        step that did not move is COULD-NOT-CHECK with the on-screen validation errors
        named, never a pass.
      - **CAUGHT-BUG, fixed here (fsc7f 2026-09-06, docs/errors/entries -- 'step chart
        never left index -1'):** on `DigitalLendingDF/ApplicantIntakeSecured` the
        `omniscriptStepChart` host's buttons NEVER carry `aria-current="step"` --
        `_chart()` reports `index: -1` both before AND after a click that genuinely
        advanced the script (proven live: a capture taken right after the raise showed
        'Progress: 7.14%' with the next step's controls already rendered). The old
        oracle can therefore never pass on this script -- comparing -1 to -1 always
        reads as "did not move", a permanent false negative, not a caught bug.
        FIX: this script renders a `Progress: N%` text node next to the step chart
        that DOES move on a genuine advance. When the chart index is -1 both before
        and after the click (this script's shape), fall back to comparing that
        percentage; only when NEITHER oracle moves are the on-screen errors trusted
        as a real block. `index == -1` and `of == 0` (chart host itself missing) is
        the same fallback path, so a script with no step chart at all is not
        automatically COULD-NOT-CHECK either.
    """
    def _chart():
        return _js(
            """const c = __host('omniscriptStepChart');
               if(!c) return null;
               const bs = __inside(c,'button');
               const i = bs.findIndex(b => b.getAttribute('aria-current') === 'step');
               return {index: i, of: bs.length,
                       label: i >= 0 ? (bs[i].textContent||'').trim().split('\\n')[0] : null};""")

    def _progress():
        return _js(
            """for(const r of __roots()){
                 for(const e of r.querySelectorAll('*')){
                   if(e.children.length) continue;
                   const t = (e.textContent||'').trim();
                   const m = t.match(/^Progress:\\s*([\\d.]+)\\s*%$/);
                   if(m) return parseFloat(m[1]);
                 }
               }
               return null;""")

    before = _chart()
    start = before.get("index", -1) if before else -1
    progress_before = _progress()
    picked = _js(
        """const want = arguments[0]; const hits = [];
           for(const r of __roots()) for(const b of r.querySelectorAll('button'))
             if((b.textContent||'').trim() === want && __visible(b)) hits.push(b);
           if(hits.length !== 1) return {ok:false, n:hits.length};
           hits[0].click(); return {ok:true};""", label)
    if not picked.get("ok"):
        confirm.unreadable("omni-next-step",
                           tried=f"expected exactly one VISIBLE button reading {label!r}, "
                                 f"found {picked.get('n')}")
    deadline = time.time() + timeout
    landed = before
    while time.time() < deadline:
        landed = _chart()
        if landed and landed.get("index", -1) != start:
            return landed
        # Fallback oracle: only trusted when the chart index genuinely cannot move on
        # this script (start == -1, i.e. aria-current never resolves at all) -- so a
        # script whose chart index DOES work is never silently routed around it.
        if start == -1:
            progress_after = _progress()
            if progress_after is not None and progress_after != progress_before:
                return {"index": landed.get("index", -1) if landed else -1,
                        "of": landed.get("of") if landed else None,
                        "label": None,
                        "oracle": "progress-percent",
                        "progress_before": progress_before,
                        "progress_after": progress_after}
        time.sleep(0.3)
    errors = _js(
        """const out = [];
           for(const r of __roots())
             for(const e of r.querySelectorAll('[class*=has-error], [class*=error-message], [role=alert]'))
               { const t = (e.textContent||'').trim(); if(t && __visible(e)) out.push(t.slice(0,120)); }
           return [...new Set(out)].slice(0,6);""")
    confirm.unreadable(
        "omni-next-step",
        tried=f"clicked {label!r} but the step chart never left index {start} "
              f"(still {landed}) and Progress stayed at {progress_before}%; "
              f"on-screen errors: {errors!r}")


def get_omni_value(key: str, family: str = "omni-text"):
    """Read one OmniScript control's current value. Routes through confirm.py: a value
    identical to its own rendered label is the six-times bug this project exists to
    stop, and an unreadable control is COULD-NOT-CHECK, never ''."""
    _require_host(key)
    raw = _js(
        """const h = __host(arguments[0]); const fam = arguments[1];
           const ins = __inside(h,'input:not([type=hidden]), textarea');
           if(fam === 'omni-checkbox' || fam === 'omni-radio' || fam === 'omni-multiselect'){
             const on = ins.filter(x => (x.type==='checkbox'||x.type==='radio') && x.checked);
             return on.map(x => x.value === '' ? String(x.checked) : x.value).join('|');
           }
           if(fam === 'omni-date'){
             const d = __inside(h,'input[data-id=date-picker-slds-input]')[0];
             if(d) return d.value;
           }
           const inp = ins.find(x => x.type !== 'checkbox' && x.type !== 'radio') || ins[0];
           if(inp) return inp.value;
           const o = __inside(h,'span')[0];
           return o ? (o.textContent||'').trim() : null;""", key, family)
    if raw is None:
        confirm.unreadable(f"{family} {key}", tried="no input or output node inside the host")
    # The label-equality check is the six-times bug guard -- but for OPTION families
    # the value legitimately IS an option's rendered label ('Yes', 'Red'), so applying it
    # there is a false positive. Measured 2026-09-05: get_omni_value('ZooRadio') raised
    # SilentWrongValue on a perfectly correct read. Exempt them by family, by name.
    _OPTION_FAMILIES = ("omni-radio", "omni-checkbox", "omni-multiselect", "omni-select")
    if family not in _OPTION_FAMILIES:
        label = _js("""const h = __host(arguments[0]);
                       const l = __inside(h,'label')[0];
                       return l ? l.textContent.trim() : '';""", key)
        if label:
            confirm.field_value(label, raw, where=f"data-omni-key={key}")
    return raw


def verify_omni_value(key: str, expected, family: str = "omni-text"):
    """Assert one control's value, format-aware. Returns the raw read-back."""
    got = get_omni_value(key, family=family)
    confirm.typed_value(_normalise_for(family, expected), _normalise_for(family, got),
                        field=f"{key} ({family})")
    return got


# ---------------------------------------------------------------------------
# omni-output / omni-action -- stream W9, 2026-09-07
#
# THE MEASUREMENT THAT FORCED TWO NEW RUNGS (docs/recorder/evidence/
# industry-omni-families-2026-09-07.md). Counted over the three committed
# fsc7f OmniStudio captures (02 / 03 / 05):
#
#   runtime_omnistudio_common-output-field   217 hosts, 217 carry ONLY
#       `data-style-id`. ZERO carry `data-omni-key` and ZERO carry
#       `data-element-label`. `__host(key)` therefore CANNOT resolve one, by
#       any of its three anchors -- so `get_omni_value` / `verify_omni_value`
#       (the callables `Omni Verify Output` is wired to, despite its
#       patternKind saying `omni-output`) have never been able to read this
#       family at all. They read OmniScript INPUT controls. The 119-element
#       `omni-output` family the fsc7f app-scan reports had no rung; this is it.
#
#   runtime_omnistudio_common-action         58 hosts, 0 attributes of any
#       kind, and their shadow root is a bare `<slot name="action">` with NO
#       light-DOM child assigned. They are empty placeholders -- there is
#       nothing to click. `omni_click_action` refuses them BY NAME rather than
#       silently finding nothing (the `ClickItem`-without-tag failure shape).
#
#   runtime_omnistudio_flexcards-flex-action 18 hosts, 18/18 carry
#       `data-element-label` AND a real clickable `a.slds-action_item` inside
#       their own shadow root with an `aria-label`. THIS is the clickable node.
# ---------------------------------------------------------------------------

_OUTPUT_HOST = "runtime_omnistudio_common-output-field"
_ACTION_HOST = "runtime_omnistudio_flexcards-flex-action"
_ACTION_DECOY = "runtime_omnistudio_common-action"


def omni_read_output(label: str, allow_empty: bool = False):
    """Read one OmniStudio OUTPUT FIELD's rendered VALUE by its rendered LABEL.

    `Omni Read Output    First Name`  ->  'Jane'

    LOCATOR (measured, docs/dom-captures/fsc7f-omnistudio/05-*.html):
      composed-tree scan for `runtime_omnistudio_common-output-field` hosts, then
      INSIDE each host's own shadow root:
          <label class="slds-form-element__label">First Name</label>
          <span  class="field-value">Jane</span>
      The label is matched case/space-insensitively (`__norm`), the same way the
      FlexCard `data-element-label` anchor is, so `First Name` and `firstname`
      both resolve. There is NO key attribute on this host -- the rendered label
      is the only handle that exists (217/217 hosts carry only `data-style-id`,
      which is a generated style hook and changes with the card layout).

    FOUR SHAPES, ONLY ONE OF WHICH IS A VALUE (measured 217 hosts; the unit test
    `test_output_field_has_four_shapes_and_only_one_is_readable` re-measures it):

      (label, .field-value, non-empty)  n     what it is
      ---------------------------------------------------------------------
      yes  yes  yes                     90    a real field -> THIS is a value
      yes  yes  no                      29    a labelled field rendering BLANK
      no   yes  no                      45    an unlabelled empty placeholder
      no   no   no                      53    a caption-only rich-text
                                              ('Application Form', 'Email')

    Only 90 of 217 output-field hosts carry a value a test can assert on. The
    other three shapes are each a way for a naive reader to return something
    that LOOKS like a value:

      - the CAPTION shape is this project's signature bug in its purest form. A
        reader that falls back to "first span inside the host" returns 'Email'
        for `Omni Read Output  Email` -- `get_field_value("Stage")` returning
        `"Stage"`, again. Caption hosts have no label element, so they are never
        matched as value hosts, AND the value is compared to the label through
        `confirm.field_value`, which raises when they are equal.
      - the BLANK shapes collapse the tri-state. `''` is not "the field is
        empty", it is "I could not read this" -- 29 labelled hosts render an
        empty `.field-value` span. So an empty read is `confirm.unreadable`
        (COULD-NOT-CHECK) unless the caller passes `allow_empty=True` to say it
        genuinely expects a blank.

    Returns the value string. Raises OmniElementNotFound when no output field
    carries this label (COULD-NOT-CHECK, never '')."""
    hit = _js(
        """const want = __norm(arguments[0]);
           const HOST = arguments[1];
           const captions = [];
           for(const r of __roots()){
             for(const h of r.querySelectorAll(HOST)){
               const labs = __inside(h, 'label');
               const vals = __inside(h, '.field-value');
               if(!labs.length || !vals.length){
                 const t = (h.textContent||'').trim();
                 if(t) captions.push(t.slice(0,60));
                 continue;
               }
               const lab = (labs[0].textContent||'').trim();
               if(__norm(lab) !== want) continue;
               return {ok:true, label: lab, value: (vals[0].textContent||'').trim()};
             }
           }
           return {ok:false, captions: [...new Set(captions)].slice(0,8)};""",
        label, _OUTPUT_HOST)
    if not hit.get("ok"):
        raise OmniElementNotFound(
            f"no {_OUTPUT_HOST} carries a label reading {label!r}. This family has NO "
            f"data-omni-key and NO data-element-label (measured 217/217 on fsc7f) -- the "
            f"rendered label is the only handle. Caption-only output fields on this page "
            f"(no label/value pair, NOT readable as values): {hit.get('captions')!r}")
    if not hit["value"] and not allow_empty:
        confirm.unreadable(
            f"omni-output {label}",
            tried=f"the {_OUTPUT_HOST} host labelled {hit['label']!r} resolved, but its "
                  f".field-value span is EMPTY. 29 of 217 hosts render this way; '' is "
                  f"COULD-NOT-CHECK, not 'the field is blank'. Pass allow_empty=True if a "
                  f"blank is genuinely what this step expects.")
    # The six-times-bug gate: a value identical to its own label is the label leaking
    # through, not a read. confirm.field_value raises on that.
    confirm.field_value(hit["label"], hit["value"],
                        where=f"{_OUTPUT_HOST} label={hit['label']!r}")
    return hit["value"]


def verify_omni_output(label: str, expected):
    """Assert one OmniStudio output field's rendered value. Returns the read-back.
    An expected value of '' is an explicit blank assertion and opts into allow_empty."""
    got = omni_read_output(label, allow_empty=(str(expected).strip() == ""))
    confirm.typed_value(_normalise_for("omni-output", expected),
                        _normalise_for("omni-output", got),
                        field=f"{label} (omni-output)")
    return got


def omni_click_action(key: str, timeout: float = 8.0):
    """Click one OmniStudio FlexCard ACTION and READ BACK WHERE IT LANDED.

    `Omni Click Action    editaction`

    LOCATOR (measured, docs/dom-captures/fsc7f-omnistudio/05-*.html):
      `runtime_omnistudio_flexcards-flex-action` host matched on
      `data-element-label` (`__norm`-compared, so 'Edit Action' finds
      'editaction'), then the clickable node INSIDE that host's own shadow root.

      THERE ARE TWO CLICKABLE SHAPES, measured over 18 flex-action hosts -- a
      locator that knew only the first would silently miss the most important
      action on the card:
        15/18  `<a class="slds-action_item" aria-label="AF-00000006">` -- a
               DATA-VALUED link (a record number, an email address).
         3/18  a nested `runtime_omnistudio_common-button` whose OWN shadow root
               holds `<button class="vlocity-btn" aria-label="Edit">` -- this is
               the `editaction` / `deactivatedcalculatebutton` shape, two shadow
               roots deep. `__inside` pierces both.
      Both are matched, and the inner node's `aria-label` is accepted as an
      alternative handle, so `Omni Click Action  Edit` addresses the button by
      what the user actually sees while `editaction` addresses it by metadata.

    WHY NOT ClickText: the action's visible text lives inside the host's shadow
    root, so a light-DOM text scan sees nothing; and the text is frequently a
    DATA value ('AF-00000006', 'janesmith93@gmail.com'), which a page-wide
    ClickText would happily match somewhere else entirely.

    THE DECOY THIS REFUSES BY NAME: `runtime_omnistudio_common-action` -- 58 of
    them across the captures, every one carrying NO attributes and wrapping a
    bare empty `<slot name="action">`. They are placeholders with nothing
    clickable inside. A locator that accepted them would report a successful
    click on a node that cannot be clicked.

    READ-BACK: the landing must CHANGE. The URL before the click is compared to
    the URL after; if the URL is unchanged, a newly-visible modal
    (`runtime_omnistudio_common-modal`) counts as the landing. If NEITHER moved
    within `timeout`, this is COULD-NOT-CHECK (confirm.unreadable), never a pass
    -- an OmniStudio action that silently does nothing is the exact shape of a
    vacuous green.

    Returns {'landed': 'url'|'modal', 'url_before':..., 'url_after':...}."""
    decoys = _js("""let n = 0;
                    for(const r of __roots()) n += r.querySelectorAll(arguments[0]).length;
                    return n;""", _ACTION_DECOY)
    before = _js("""const want = __norm(arguments[0]); const HOST = arguments[1];
        const seen = [];
        for(const r of __roots()){
          for(const h of r.querySelectorAll(HOST)){
            const el = h.getAttribute('data-element-label') || '';
            const a = __inside(h, 'a.slds-action_item, a[data-action-focus], button.vlocity-btn, button')[0];
            const aria = a ? (a.getAttribute('aria-label') || '') : '';
            seen.push(el || aria);
            if(__norm(el) !== want && __norm(aria) !== want) continue;
            if(!a) return {ok:false, reason:'host matched but no clickable a.slds-action_item / button inside it',
                           label: el};
            return {ok:true, label: el || aria,
                    url: location.href,
                    modals: __openModals()};
          }
        }
        return {ok:false, reason:'no flex-action host matches', offered:[...new Set(seen)].slice(0,12)};""",
        key, _ACTION_HOST)
    if not before.get("ok"):
        raise OmniElementNotFound(
            f"no {_ACTION_HOST} resolves for {key!r}: {before.get('reason')}. "
            f"Offered data-element-label / aria-label values on this page: "
            f"{before.get('offered')!r}. NOTE: {decoys} {_ACTION_DECOY} hosts are on this "
            f"page and are deliberately NOT candidates -- they carry no attributes and "
            f"wrap an empty slot, so there is nothing to click inside them.")
    url_before = before["url"]
    modals_before = before["modals"]
    clicked = _js("""const want = __norm(arguments[0]); const HOST = arguments[1];
        for(const r of __roots()){
          for(const h of r.querySelectorAll(HOST)){
            const el = h.getAttribute('data-element-label') || '';
            const a = __inside(h, 'a.slds-action_item, a[data-action-focus], button.vlocity-btn, button')[0];
            const aria = a ? (a.getAttribute('aria-label') || '') : '';
            if(__norm(el) !== want && __norm(aria) !== want) continue;
            if(!a) continue;
            // A bare .click() is NOT enough on an OmniStudio action -- measured live on
            // fsc7f 2026-09-07: a.click() on the `partyprofilevalue` action moved neither
            // the URL nor a modal in 8s. This is the SAME failure the module docstring
            // records for `option.click()` on an OmniStudio combobox (reason 2), and the
            // same remedy: dispatch the full pointer sequence the runtime's own handler
            // listens for, then click.
            for(const type of ['pointerover','mouseover','pointerdown','mousedown',
                               'pointerup','mouseup']){
              const Ctor = type.startsWith('pointer') && window.PointerEvent
                           ? PointerEvent : MouseEvent;
              a.dispatchEvent(new Ctor(type, {bubbles:true, composed:true, cancelable:true}));
            }
            a.click();
            return true;
          }
        }
        return false;""", key, _ACTION_HOST)
    if not clicked:
        confirm.unreadable(f"omni-action {key}",
                           tried="the host resolved on the read pass but not on the click pass")
    deadline = time.time() + timeout
    while time.time() < deadline:
        after = _js("""return {url: location.href,
                    modals: __openModals()};""")
        if after["url"] != url_before:
            return {"landed": "url", "label": before["label"],
                    "url_before": url_before, "url_after": after["url"]}
        if after["modals"] > modals_before:
            return {"landed": "modal", "label": before["label"],
                    "url_before": url_before, "url_after": after["url"],
                    "modals_before": modals_before, "modals_after": after["modals"]}
        time.sleep(0.25)
    confirm.unreadable(
        f"omni-action {key}",
        tried=f"clicked the a.slds-action_item / button inside the {_ACTION_HOST} host labelled "
              f"{before['label']!r}, but neither the URL ({url_before}) nor the modal count "
              f"({modals_before}) changed within {timeout}s. An OmniStudio action that reports "
              f"no error and moves nothing is COULD-NOT-CHECK, never a pass.")
