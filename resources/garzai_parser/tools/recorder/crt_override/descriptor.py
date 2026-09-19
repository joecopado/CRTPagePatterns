"""descriptor -- identity by what the page can SAY about the element it just recorded.

Usage (library):
    from descriptor import describe_js, RESOLVE_JS, NONCE_ATTR, find_row
    js   = describe_js(spec)          # the page-side `window.__gzDescribe`, spec = the template's
                                      # formElementLabel block (no fork: the data comes from there)
    el   = drv.execute_script(RESOLVE_JS, nonce)     # the stamped element, open shadow roots too
    row, why = find_row(rows, descriptor)            # which reviewed/parsed row it is

Why this module exists (2026-09-18, ledger F40/F42/F44):

  * F44 -- the composer matched a recorded element to a review row by an identity XPATH that is
    POSITIONAL over the whole page: `(//input[@type="text"])[3]`. One extra text input in the DOM
    (an App Launcher search box left after use, an Add Line row) shifts every index, so none of the
    seven Nightmare inputs matched its row and both Save clicks missed row 67.
  * F42 -- the same positional xpaths resolve to exactly ONE element on ANY page, so on a Lead form
    `Last Name` matched the Zoo page's `Renewal Notice (days)` with a confident backup line.
  * F40 -- Lightning Setup controls sit in native shadow roots; xpath from the driver reaches none
    of them, so no identity of any kind could be established and no proposal was possible.

So identity stops being an xpath the composer re-evaluates. The page stamps the element it recorded
with a one-shot attribute (`data-gz-ev="<nonce>"`, removed after 10 s) and sends a DESCRIPTOR of it.
The composer finds the element by the nonce with ONE shadow-piercing walk -- never by xpath -- and
names the row by LABEL + FAMILY, which is what a person reads and what neither an extra input nor a
different page can quietly change.

The match rule is `tools/recorder/pom/match.py` -- the ONE rule for "does the store already know
this control?" -- applied to a list of rows instead of a POM record: the same label normalisation
(whitespace collapsed, case folded, a trailing live count dropped, a prefix NEVER a match) and the
same family compatibility (button/link/menuitem/tab are one click family; input/textarea/combobox
one type family). It is imported when the POM package is importable and reproduced here when it is
not (the generated CRT library ships alone, without the parser bundle); `test_descriptor_match.py`
fails if the two ever disagree.

Nothing here decides a LINE. It answers which row, and says how it knows -- `label`, `attribute` or
`positional` -- so a decision can be read and argued with.
"""
from __future__ import annotations

import json
import re

NONCE_ATTR = 'data-gz-ev'
NONCE_TTL_MS = 10000

# ----------------------------------------------------------------------------- the match rule
try:                                                     # the ONE rule, when it can be imported
    from pom.match import norm_label, families_compatible, CLICK_FAMILIES, TYPE_FAMILIES
except Exception:                                        # ... and its stated twin when it cannot
    CLICK_FAMILIES = {'button', 'link', 'menuitem', 'tab', 'click', 'a'}
    TYPE_FAMILIES = {'input', 'input_field', 'textarea', 'combobox', 'text', 'type', 'search'}
    _COUNT_SUFFIX = re.compile(r'\s*\(\d+\)\s*$')

    def norm_label(s):
        s = re.sub(r'\s+', ' ', (s or '')).strip().strip('*').strip()
        s = _COUNT_SUFFIX.sub('', s)
        return s.casefold()

    def families_compatible(want, have):
        if not want or not have:
            return True
        w, h = want.casefold(), have.casefold()
        if w == h:
            return True
        if w in CLICK_FAMILIES and h in CLICK_FAMILIES:
            return True
        if w in TYPE_FAMILIES and h in TYPE_FAMILIES:
            return True
        return False


# The rungs a descriptor offers as "the label a person reads", in order. The first four are the
# locator doctrine's own order (visible text, aria-label, title only for icon-only controls); the
# association comes first because a form control's own text is empty.
LABEL_RUNGS = ('label', 'text', 'aria_label', 'title', 'placeholder')


def label_candidates(desc: dict) -> list:
    """[(text, rung)] for this descriptor, best first. `title` and `placeholder` are last: the
    locator doctrine allows a tooltip only for an icon-only control with no visible text."""
    out = []
    for rung in LABEL_RUNGS:
        v = (desc or {}).get(rung)
        if v and str(v).strip():
            out.append((str(v).strip(), rung))
    return out


def _default_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of the GENERATED library's embedded table."""
    return (row.get('label'), row.get('type'), row.get('index'), row.get('group_size'))


def parsed_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of `review_table.build_rows`."""
    return (row.get('label_corrected') or row.get('label'),
            row.get('family_corrected') or row.get('element_type'),
            row.get('index_corrected') if 'index_corrected' in row else row.get('index'),
            row.get('group_size'))


def find_row(rows, desc: dict, get=_default_get):
    """(row, why) -- the row this descriptor names, by label + family, or (None, why not).

    A label that occurs once names its row outright. A label that repeats is settled by the
    descriptor's `label_index`: the element's 1-based position among the same-label, family-
    compatible controls in DOM order, counted BY THE PAGE, against the row's own `index` (the
    parser's position among the same-label matches). When the two disagree, or the page could not
    count, nothing is returned -- an ambiguous label is a COULD-NOT-DISAMBIGUATE, never a guess.
    """
    if not rows or not desc:
        return None, 'no descriptor'
    fam = desc.get('family')
    tried = []
    for text, rung in label_candidates(desc):
        want = norm_label(text)
        if not want:
            continue
        cands = [r for r in rows
                 if norm_label(get(r)[0]) == want and families_compatible(fam, get(r)[1])]
        tried.append('%s=%r -> %d' % (rung, text[:40], len(cands)))
        if not cands:
            continue
        if len(cands) == 1:
            return cands[0], 'label (%s) %r' % (rung, text[:40])
        idx = desc.get('label_index')
        if idx:
            hits = [r for r in cands if (get(r)[2] or 1) == idx]
            if len(hits) == 1:
                return hits[0], 'label (%s) %r + page index %d of %s' % (
                    rung, text[:40], idx, desc.get('label_group_size'))
        return None, ('COULD-NOT-DISAMBIGUATE: %d rows carry label %r and the page counted index %r'
                      % (len(cands), text[:40], idx))
    return None, 'no row carries this descriptor label (%s)' % ('; '.join(tried) or 'none offered')


def attribute_identity(desc, row):
    """The stable attribute this descriptor and this row AGREE on, or None. Never a generated
    value: a row's own identity is built with generated values stripped (review_table.is_generated),
    so an agreement here is on a value the parser already judged stable."""
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    for key, dkey in (('name', 'name'), ('aria-label', 'aria_label'), ('data-testid', 'data_testid'),
                      ('title', 'title'), ('placeholder', 'placeholder'), ('id', 'id')):
        want, have = desc.get(dkey), attrs.get(key)
        if want and have and str(want) == str(have):
            return '@%s=%r' % (key, want)
    return None


# ----------------------------------------------------------------------------- the page side
RESOLVE_JS = """
var want = arguments[0];
function walk(root){
  var el = null;
  try { el = root.querySelector('[%s="' + want + '"]'); } catch (e) { el = null; }
  if (el) { return el; }
  var all = root.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var sr = all[i].shadowRoot;
    if (sr) { var r = walk(sr); if (r) { return r; } }
  }
  return null;
}
return walk(document);
""" % NONCE_ATTR

# The page-side describer. `__GZ_FE_SPEC__` is the template's own `formElementLabel` block
# (docs/recorder/templates/*.json): the SLDS shape whose label is a cousin of its control, which is
# every labelled control on Zoo_Nightmare_Inputs and most of a Lightning record page. It is injected
# by the generator, never restated here -- a fork of the parser's label rungs is exactly what this
# module must not become.
DESCRIBE_JS_TEMPLATE = r"""
;(function(){
var FE = __GZ_FE_SPEC__;
var SCAN_SELECTOR = 'input,select,textarea,button,a,[role],[contenteditable="true"]';
var SCAN_CAP = 1200;
function cls(el){ try { return (el.getAttribute && el.getAttribute('class')) || ''; } catch(e){ return ''; } }
function hasFrag(el, frags){ var c = cls(el); for (var i=0;i<(frags||[]).length;i++){ if (c.indexOf(frags[i])>=0) return true; } return false; }
function isFormElement(el){ var c = cls(el); if (c.indexOf(FE.containerClassFragment)<0) return false;
  var ex = FE.excludeContainerClassFragments||[]; for (var i=0;i<ex.length;i++){ if (c.indexOf(ex[i])>=0) return false; } return true; }
function txt(el){ var t=''; try { t = el.innerText || el.textContent || ''; } catch(e){} return t.replace(/\s+/g,' ').trim(); }
function up(el){ if (!el) return null; if (el.parentElement) return el.parentElement;
  var p = el.parentNode; return (p && p.host) ? p.host : null; }
function esc(s){ try { return (window.CSS && CSS.escape) ? CSS.escape(String(s)) : String(s).replace(/["\\]/g,'\\$&'); } catch(e){ return String(s); } }
function attr(el,k){ try { var v = el.getAttribute(k); return (v===null||v==='') ? null : v; } catch(e){ return null; } }
function formElementLabel(el){
  var tags = FE.targetTags || [], tag = el.tagName.toLowerCase();
  if (tags.length && tags.indexOf(tag) < 0){
    var wrapper = FE.wrapperMayBeTarget && tag.indexOf('-')>0 &&
                  el.querySelectorAll('input,select,textarea').length === 1;
    if (!wrapper) return '';
  }
  var p = up(el), hops = 0;
  while (p && hops < 4){ if (hasFrag(p, FE.targetInsideExcludedClassFragments)) return ''; p = up(p); hops++; }
  var cur = up(el), h = 0, max = FE.maxClimb || 8;
  while (cur && h < max){
    if (isFormElement(cur)){
      var all = cur.querySelectorAll('*');
      for (var i=0;i<all.length;i++){
        var c = all[i], toks = cls(c).split(/\s+/), hit = false, frs = FE.labelClassFragments || [];
        for (var j=0;j<frs.length;j++){ if (toks.indexOf(frs[j])>=0){ hit = true; break; } }
        if (hit && c !== el && !c.contains(el)){ var t = txt(c); if (t) return t; }
      }
    }
    cur = up(cur); h++;
  }
  return '';
}
function nearestLabel(el){
  var root = el.getRootNode ? el.getRootNode() : document;
  try { var id = attr(el,'id');
        if (id){ var l = root.querySelector('label[for="'+esc(id)+'"]'); if (l){ var t=txt(l); if (t) return [t,'label_for']; } } } catch(e){}
  try { var lb = attr(el,'aria-labelledby');
        if (lb){ var parts = lb.split(/\s+/), out = [];
          for (var i=0;i<parts.length;i++){ var n = null;
            try { n = root.getElementById ? root.getElementById(parts[i]) : root.querySelector('#'+esc(parts[i])); } catch(e){}
            if (n) out.push(txt(n)); }
          var t2 = out.join(' ').trim(); if (t2) return [t2,'aria_labelledby']; } } catch(e){}
  try { var a = el.closest ? el.closest('label') : null; if (a){ var t3 = txt(a); if (t3) return [t3,'wrapping_label']; } } catch(e){}
  var fe = formElementLabel(el); if (fe) return [fe,'form_element_label'];
  try { var s = el.previousElementSibling, g = 0;
        while (s && g < 3){ if (s.tagName === 'LABEL' || hasFrag(s, FE.labelClassFragments)){ var t4 = txt(s); if (t4) return [t4,'sibling_label']; } s = s.previousElementSibling; g++; } } catch(e){}
  return ['', null];
}
function familyOf(el){
  var tag = el.tagName.toLowerCase(), ty = (attr(el,'type')||'').toLowerCase(), role = (attr(el,'role')||'').toLowerCase();
  if (tag === 'select') return 'dropdown';
  if (tag === 'textarea') return 'input_field';
  if (tag === 'input'){ if (ty === 'checkbox') return 'checkbox'; if (ty === 'radio') return 'radio';
                        if (ty === 'button' || ty === 'submit' || ty === 'reset') return 'button'; return 'input_field'; }
  if (tag === 'button' || tag === 'a') return 'button';
  if (role === 'button' || role === 'tab' || role === 'menuitem' || role === 'option' || role === 'link') return 'button';
  if (role === 'combobox' || role === 'textbox' || role === 'searchbox') return 'input_field';
  if (role === 'checkbox' || role === 'switch') return 'checkbox';
  return tag;
}
var CLICKF = {button:1, link:1, menuitem:1, tab:1, click:1, a:1};
var TYPEF  = {input:1, input_field:1, textarea:1, combobox:1, text:1, type:1, search:1};
function compat(a,b){ if (!a || !b) return true; if (a === b) return true;
  if (CLICKF[a] && CLICKF[b]) return true; if (TYPEF[a] && TYPEF[b]) return true; return false; }
function norm(s){ return String(s||'').replace(/\s+/g,' ').trim().replace(/^\*|\*$/g,'').trim().replace(/\s*\(\d+\)\s*$/,'').toLowerCase(); }
function controls(){
  /* ONE depth-first walk, shadow content inlined right after its host, so the list is in the page's
     own reading order -- the order the parser sees in a capture (shadow roots serialise in place as
     <template>). Collecting a root's own matches first and descending afterwards counted a control
     at shadow depth 2 before one at depth 1 and the index disagreed with the review's. */
  var out = [], capped = false;
  function walk(root){
    if (capped) return;
    var all; try { all = root.querySelectorAll('*'); } catch(e){ all = []; }
    for (var i=0;i<all.length;i++){
      var e = all[i], hit = false;
      try { hit = e.matches && e.matches(SCAN_SELECTOR); } catch(err){ hit = false; }
      if (hit){ out.push(e); if (out.length >= SCAN_CAP){ capped = true; return; } }
      if (e.shadowRoot){ walk(e.shadowRoot); if (capped) return; }
    }
  }
  walk(document);
  return {list: out, capped: capped};
}
function labelIndex(el, label, fam){
  if (!label) return null;
  var want = norm(label), c = controls(), k = 0, found = null;
  for (var i=0;i<c.list.length;i++){
    var e = c.list[i];
    if (!compat(fam, familyOf(e))) continue;
    var L = nearestLabel(e)[0] || txt(e).slice(0,80);
    if (norm(L) !== want) continue;
    k++;
    if (e === el) found = k;
  }
  return {index: found, group_size: k, scanned: c.list.length, capped: c.capped};
}
function hostChain(el){
  var out = [], r = el.getRootNode ? el.getRootNode() : document, g = 0;
  while (r && r !== document && r.host && g < 12){ out.push(r.host.tagName.toLowerCase()); r = r.host.getRootNode ? r.host.getRootNode() : document; g++; }
  return out;
}
window.__gzDescribe = function(el){
  var d = {};
  try {
    d.tag = el.tagName.toLowerCase();
    d.type = attr(el,'type');
    d.name = attr(el,'name');
    d.id = attr(el,'id');              /* raw: the composer only uses it when the ROW carries the
                                          same value, and the parser strips generated ones (D5) */
    d.aria_label = attr(el,'aria-label');
    d.placeholder = attr(el,'placeholder');
    d.title = attr(el,'title');
    d.role = attr(el,'role');
    d.data_testid = attr(el,'data-testid') || attr(el,'data-test-id');
    d.text = txt(el).slice(0,80);
    var nl = nearestLabel(el);
    d.label = nl[0] || null;
    d.label_source = nl[1];
    d.family = familyOf(el);
    var root = el.getRootNode ? el.getRootNode() : document;
    d.in_shadow = !!(root && root !== document && root.host);
    d.host_chain = hostChain(el);
    var li = labelIndex(el, d.label || d.text, d.family);
    d.label_index = li ? li.index : null;
    d.label_group_size = li ? li.group_size : null;
    d.scan_capped = li ? li.capped : null;
  } catch (e) { d.error = String(e); }
  return d;
};
var NONCE_N = 0;
window.__gzStamp = function(el){
  try {
    var n = 'gz' + (++NONCE_N) + '-' + Date.now().toString(36);
    el.setAttribute('%(attr)s', n);
    setTimeout(function(){ try { if (el.getAttribute('%(attr)s') === n) el.removeAttribute('%(attr)s'); } catch(e){} }, %(ttl)d);
    return n;
  } catch (e) { return null; }
};
})();
""" % {'attr': NONCE_ATTR, 'ttl': NONCE_TTL_MS}


def describe_js(fe_spec: dict) -> str:
    """The page-side describer with the template's formElementLabel block injected."""
    return DESCRIBE_JS_TEMPLATE.replace('__GZ_FE_SPEC__', json.dumps(fe_spec or {}))
