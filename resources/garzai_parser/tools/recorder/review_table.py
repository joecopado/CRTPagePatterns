"""review_table -- the joint-validation review loop (docs/proposals/JOINT-VALIDATION-PLAN-2026-09-10.md).
Usage:
  python3 tools/recorder/review_table.py build     --capture <html> --org <alias> [--screenshot <png>] [--out-dir DIR]
  python3 tools/recorder/review_table.py live      --review <review.json> --org <alias> [--slot NAME]
  python3 tools/recorder/review_table.py correct   --review <review.json> --row N --column <label|family|keyword|index|xpath|not_interactive|needs_xpath|could_not_map> --to VALUE [--raw-had ATTR] [--note TEXT]
  python3 tools/recorder/review_table.py accept    --review <review.json> --rows <N,N,..|all|live-pass> [--note TEXT]
  python3 tools/recorder/review_table.py writeback --review <review.json> [--state-root DIR]
  python3 tools/recorder/review_table.py score     --review <review.json> [--scores PATH] [--no-append]
  python3 tools/recorder/review_table.py render    --review <review.json>
  python3 tools/recorder/review_table.py drive     --review <review.json> --org <alias> [--values '{"Industry":"Technology"}']
  python3 tools/recorder/review_table.py robot     --review <review.json> [--out FILE]   # inline steps, no variables, no custom keywords
  python3 tools/recorder/review_table.py demo      --review <review.json> [--out FILE]   # ACTIONS only: keyword form + xpath form (Dreamforce)
  python3 tools/recorder/review_table.py add       --review <review.json> --label L --family F --keyword K --call 'step ;; step' [--xpath XP]  # a row the parser missed

One row per parsed control: label, family, fill/verify keyword, group size, index, anchor
candidates, the parser's reason when it has no keyword, the RAW neighbourhood of the control from
the capture, and an xpath formed by a ladder (stable attribute > label association > text + real
tag > structural path from a stable ancestor) with its four numbers: (a) unique in the capture,
(b) resolves LIVE to the same element via QWeb `GetWebelement` (QWeb executes the xpath; this code
never resolves), (c) contains no generated value (the template's `dynamicValuePatterns`), (d)
survives cross-org on a shared page key (COULD-NOT-CHECK until a second org holds the key).

`live` also measures the KEYWORD column: whether the hinted keyword's own resolution
(`qforce_lite.resolve_input` for inputs, QWeb text resolution for buttons/links) lands on the node
the row describes. Identity is checked with an `identity_xpath` built from EVERY attribute of the
captured node -- generated values included, which is fine because the capture was taken in place
from the page the holder still shows; it is instrumentation, never a locator.

Corrections are DATA: `correct` records the column, the old and new value and `raw_had` (the
attribute or element the raw neighbourhood carried that the parse dropped -- the parser's
improvement backlog, cut by count). `writeback` stores every reviewed row against (org, page_key,
control) in the POM store as `verified` (n_verified=1 on the chosen rung, source `reviewed`), which
`pom_asset.consult` / `verified_labels` read. The parser is never edited here.
"""
from __future__ import annotations

import argparse
import collections
import html as _html
import json
import os
import re
import subprocess
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for _p in ('tools/interop/resources/pythonDom', 'tools/benchmark', 'tools/qforce-lite',
           'tools/recorder'):
    _abs = os.path.join(_ROOT, _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

from bs4 import BeautifulSoup, Comment, NavigableString  # noqa: E402  (the vendored 3.10+ bs4)
import lxml.html                                        # noqa: E402
from capture_orchestration import parse_elements_from_html  # noqa: E402
import metadata_dom_parity as PARITY                    # noqa: E402
import pom_asset as PA                                  # noqa: E402
import disambiguation_args as DA                         # noqa: E402
import pattern_library as PL                             # noqa: E402  (buckets + the recipe library, 2026-09-10)
import shutil                                            # noqa: E402
from pom.store import Store, element_id, stable_attrs, STABLE_ATTRS, UNSTABLE_VALUE  # noqa: E402
from pom import store as STORE_MOD                      # noqa: E402  -- apply_capture_stamp

TEMPLATE = os.path.join(_ROOT, 'docs', 'recorder', 'templates', 'salesforce-lightning.json')
SCORES_DEFAULT = os.path.join(_ROOT, 'docs', 'recorder', 'evidence', 'review-scores.jsonl')
COLUMNS = ('label', 'family', 'keyword', 'index', 'anchor', 'tag', 'attribute', 'call', 'xpath', 'xpath_call',
           'not_interactive', 'needs_xpath', 'could_not_map', 'status')
FILL_FAMILIES = ('input_field', 'dropdown', 'textarea', 'checkbox', 'radio', 'lookup', 'date',
                 'datetime', 'combobox', 'picklist')
_ASSISTIVE = ('slds-assistive-text', 'sr-only', 'visually-hidden')


# ----------------------------------------------------------------------------- generated values
def _generated_rules() -> tuple[list, list]:
    """The template's own `dynamicValuePatterns` (prefixes, patterns) -- the SAME rule the parser
    applies, read from the same file, so the xpath column cannot disagree with the hint ladder."""
    try:
        t = json.load(open(TEMPLATE))
        d = t.get('dynamicValuePatterns') or {}
        return list(d.get('prefixes') or []), [re.compile(p) for p in (d.get('patterns') or [])]
    except Exception:
        return [], []


_PREFIXES, _PATTERNS = _generated_rules()


def use_template(path) -> bool:
    """Point the generated-value rules at the template the PAGE selected, not a hardcoded one.

    TEMPLATE was pinned to salesforce-lightning.json, so a non-Salesforce capture was judged by
    Salesforce's dynamicValuePatterns and never by its own -- the same "it never looked at the page"
    class TEMPLATES.md SS10 records for parser v1 and fixed there. Measured 2026-09-12 on
    robotic.copado.com: web-generic's rules existed but were never consulted.
    """
    global TEMPLATE, _PREFIXES, _PATTERNS
    if not path or not os.path.exists(path):
        return False
    TEMPLATE = path
    _PREFIXES, _PATTERNS = _generated_rules()
    return True


def _adopt_page_template(capture_path: str) -> str:
    """Resolve the capture's own template through the SAME resolver the parser uses, and adopt it."""
    try:
        sys.path.insert(0, os.path.join(_ROOT, 'tools', 'interop', 'resources', 'pythonDom'))
        import dom_config as _dc
        html = open(capture_path, encoding='utf-8', errors='replace').read()
        prov = _dc.provenance_for_html(html) or {}
        p = prov.get('path')
        full = p if (p and os.path.isabs(p)) else (os.path.join(_ROOT, p) if p else None)
        if use_template(full):
            return "generated-value rules: %s (selected_by=%s)" % (prov.get('name'), prov.get('selected_by'))
        return "generated-value rules: COULD-NOT-CHECK (template %r not on disk); staying on %s" % (
            p, os.path.basename(TEMPLATE))
    except Exception as exc:                                  # never fatal -- say so and carry on
        return "generated-value rules: COULD-NOT-CHECK (%s: %s); staying on %s" % (
            type(exc).__name__, str(exc)[:80], os.path.basename(TEMPLATE))


def is_generated(value: str) -> bool:
    if not value:
        return False
    if UNSTABLE_VALUE.match(value):
        return True
    if any(value.startswith(p) for p in _PREFIXES):
        return True
    return any(p.search(value) for p in _PATTERNS)


# An attribute NAME can be the generated part, with an empty value: Angular writes
# `<button _ngcontent-ng-c540179591="">`, so an xpath predicate reads `@_ngcontent-ng-c540179591=""`.
# Scanning only quoted values tested `""`, found nothing, and stamped the row clean
# (measured 2026-09-12 on robotic.copado.com; the resulting identity xpath matched 0 elements live).
_ATTR_NAME_IN_XPATH = re.compile(r'@([A-Za-z_][\w:.-]*)')


def generated_values_in(xpath: str) -> list[str]:
    hits = [v for v in re.findall(r'"([^"]*)"', xpath) if is_generated(v)]
    hits += [n for n in _ATTR_NAME_IN_XPATH.findall(xpath) if is_generated(n)]
    return hits


# ----------------------------------------------------------------------------- xpath helpers
def _lit(s: str) -> str:
    if '"' not in s:
        return '"%s"' % s
    parts = s.split('"')
    return 'concat(' + ', \'"\', '.join('"%s"' % p for p in parts) + ')'


def _norm_text(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').replace(' ', ' ')).strip()


def _clean_label(label: str) -> str:
    return _norm_text(re.sub(r'^\*\s*|\s*\*$', '', label or ''))


class Capture:
    """One capture, parsed twice: bs4 for node matching and raw markup, lxml for xpath counts."""

    def __init__(self, path: str):
        self.path = path
        self.raw = open(path, errors='replace').read()
        self.soup = BeautifulSoup(self.raw, 'html.parser')
        self.doc = lxml.html.fromstring(self.raw)
        self._tag_counts: dict[str, int] = {}

    def count(self, xpath: str) -> int | None:
        try:
            return len(self.doc.xpath(xpath))
        except Exception:
            return None

    def tag_count(self, tag: str) -> int:
        if tag not in self._tag_counts:
            self._tag_counts[tag] = len(self.soup.find_all(tag))
        return self._tag_counts[tag]


def _attrs_of(node) -> dict:
    out = {}
    for k, v in (node.attrs or {}).items():
        out[k] = ' '.join(v) if isinstance(v, list) else (v if v is not None else '')
    return out


def _node_text(node) -> str:
    # bs4 types strings under <template> as TemplateString and get_text() skips them; the
    # capture serialises every shadow root as <template>, so walk the strings ourselves.
    if node is None:
        return ''
    parts = [str(s) for s in node.descendants
             if isinstance(s, NavigableString) and not isinstance(s, Comment)]
    return _norm_text(' '.join(p for p in parts if p.strip()))


def _assistive_text(node) -> str:
    for sp in node.find_all(True):
        cls = ' '.join(sp.get('class') or []) if isinstance(sp.get('class'), list) else (sp.get('class') or '')
        if any(a in cls for a in _ASSISTIVE):
            t = _node_text(sp)
            if t:
                return t
    return ''


def find_node(cap: Capture, e: dict, nth: int, claimed: set | None = None):
    """The captured node this parser element describes: same tag, every element_details attribute
    present with the same value, the label visible on/in it when the label came from text; the
    `nth` such node in DOM order (parser elements sharing one signature are emitted in DOM order).
    None when nothing matches -- the row then says COULD-NOT-CHECK for raw and xpath.

    2026-09-11: a node claimed by an earlier row is never a candidate again. The build counted `nth` per
    (tag, attrs, LABEL) while this matcher filters candidates by label only for text-derived sources, so
    seven differently-labelled `<input readonly type="text">` rows on Zoo_Nightmare_Inputs (labels from
    the form_element_label rung) all took candidate 0 -- one identity xpath on 7 rows, 22 of 39 page rows
    measured live against the wrong node; 36 of 1,470 industry page rows the same way."""
    det = e.get('element_details') or {}
    tag = det.get('tag')
    if not tag:
        return None
    want = det.get('attributes') or {}
    ident = e.get('identification') or {}
    label = _clean_label(ident.get('label_text') or '')
    src = ident.get('label_source')
    cands = []
    loose = []
    for n in cap.soup.find_all(tag):
        if claimed is not None and id(n) in claimed:
            continue
        a = _attrs_of(n)
        if any(a.get(k) != v for k, v in want.items() if k != 'class'):
            continue
        if src in ('inner_text',) and label:
            t = _node_text(n).lower()
            if t == label.lower():
                pass
            elif label.lower() in t:
                loose.append(n)     # "Save" is inside "Save & New": a fallback, never a first pick
                continue
            else:
                continue
        if src == 'assistive_text' and label and label.lower() not in _assistive_text(n).lower() \
                and label.lower() not in _node_text(n).lower():
            continue
        if src == 'label_span' and label and label.lower() not in _node_text(n).lower():
            continue
        cands.append(n)
    if not cands:
        cands = loose
    if not cands:
        return None
    return cands[nth] if nth < len(cands) else cands[-1]


def identity_xpath(cap: "Capture", node) -> str:
    """Instrumentation to find the SAME node live in the session the capture was taken from: a
    unique tag alone, else every attribute (generated ones included), else the node's first text
    string on top. Never a locator."""
    base = '//%s' % node.name
    if cap.tag_count(node.name) == 1:
        return base
    preds = []
    for k, v in sorted(_attrs_of(node).items()):
        if k.startswith('lwc-') or k in ('class', 'style', 'part'):
            continue
        if not re.match(r'^[A-Za-z_:][-A-Za-z0-9_:.]*$', k):
            continue
        if is_generated(v) or is_generated(k):
            # per-render ids (input-189, dropdown-element-172, 74:221;a) break on reload -- and so do
            # per-BUILD attribute NAMES with an empty value: Angular's `_ngcontent-ng-c540179591=""`.
            # Checking only the value kept that predicate, and the Artifacts tab's identity xpath
            # then matched 0 elements live (measured 2026-09-12, robotic.copado.com).
            continue
        preds.append('@%s=%s' % (k, _lit(v)))
    xp = base + ('[' + ' and '.join(preds) + ']' if preds else '')
    if cap.count(xp) == 1:
        return xp
    first = next((_norm_text(str(t)) for t in node.descendants
                  if isinstance(t, NavigableString) and not isinstance(t, Comment) and str(t).strip()), '')
    if first:
        xp2 = xp + '[.//text()[normalize-space(.)=%s]]' % _lit(first[:120])
        if cap.count(xp2) == 1:
            return xp2
        if cap.count(xp2):
            xp = xp2
    # still repeated: the node's position among the capture's matches (same structure on reload)
    matches = cap.doc.xpath(xp) if cap.count(xp) else []
    for i, m in enumerate(matches, 1):
        if _same_node(cap, m, node):
            return '(%s)[%d]' % (xp, i)
    return xp


def _same_node(cap: "Capture", lx, bs) -> bool:
    """lxml element == bs4 node, by tag, attributes and DOM position among same-tag nodes."""
    if lx.tag != bs.name:
        return False
    la = {k: v for k, v in lx.attrib.items()}
    ba = _attrs_of(bs)
    if {k: la.get(k) for k in ba} != ba:
        return False
    same_tag_lx = [e for e in cap.doc.iter(bs.name)]
    same_tag_bs = cap.soup.find_all(bs.name)
    # bs4 Tag.__eq__ is STRUCTURAL: two bare <input type="text"> compare equal and .index() returns
    # the first -- every attribute-less input on Zoo_Nightmare_Inputs collapsed onto one node.
    i_bs = next((i for i, x in enumerate(same_tag_bs) if x is bs), None)
    i_lx = next((i for i, x in enumerate(same_tag_lx) if x is lx), None)
    return i_bs is not None and i_bs == i_lx


def _preceding_texts(node, max_len: int = 40, limit: int = 40) -> list[str]:
    """Short, non-assistive texts before the node in DOM order, nearest first."""
    out = []
    for t in node.find_all_previous(string=True):
        if isinstance(t, Comment):
            continue
        txt = _norm_text(str(t))
        if not txt or len(txt) > max_len or not txt[0].isalnum():
            continue
        par = t.parent
        cls = ' '.join(par.get('class') or []) if par is not None and isinstance(par.get('class'), list) else (par.get('class') or '' if par is not None else '')
        if any(a in cls for a in _ASSISTIVE) or (par is not None and par.name in ('option', 'script', 'style')):
            continue
        if txt not in out:
            out.append(txt)
        if len(out) >= limit:
            break
    return out


def nearest_preceding_text(node, max_len: int = 60) -> str | None:
    """The closest short text BEFORE the node in DOM order that is not screen-reader-only: on a
    page whose labels are cousins of their inputs (Zoo_Nightmare_Inputs) this is the label a
    person reads. A GUESS the reviewer confirms, never a label the parser asserted."""
    for t in node.find_all_previous(string=True):
        if isinstance(t, Comment):
            continue
        txt = _norm_text(str(t))
        if not txt or len(txt) > max_len:
            continue
        par = t.parent
        cls = ' '.join(par.get('class') or []) if par is not None and isinstance(par.get('class'), list) else (par.get('class') or '' if par is not None else '')
        if any(a in cls for a in _ASSISTIVE) or (par is not None and par.name in ('option', 'script', 'style')):
            continue
        return txt
    return None


def raw_neighbourhood(node, limit: int = 420) -> tuple[str, list[str]]:
    """A few hundred bytes of the node's own markup plus the enclosing tags, so a reviewer can
    say what the raw had that the parse dropped."""
    own = str(node)
    own = own if len(own) <= limit else own[:limit] + '…'
    chain = [p.name for p in node.parents if p.name and p.name not in ('template', '[document]')][:6]
    return own, chain


_CHROME_HOSTS = ('one-appnav', 'one-app-nav-bar', 'one-app-launcher', 'oneheader', 'one-global',
                 'forcesearch', 'one-utility', 'devops_center-panel', 'one-app-nav-bar-menu')


def _chrome_containers() -> dict:
    try:
        return json.load(open(TEMPLATE)).get('chromeContainers') or {}
    except Exception:
        return {}


_CHROME_CONTAINERS = _chrome_containers()


def region_of(node) -> str:
    """`page` when the control sits inside the page's own content (a flexipage host, a generated
    page module, a custom element), `chrome` when it sits in Salesforce's header/nav/utility
    chrome. Chrome is reviewed ONCE per org (user, 2026-09-10) and left out of every later table,
    score and export unless asked for.

    2026-09-11: the template's `chromeContainers` decides first, by the NEAREST ancestor that carries a
    listed class fragment or tag prefix (page and chrome both listed, nearest wins) -- the console
    workspace tab strip lives INSIDE the flexipage host, so the old outermost-ancestor test called it
    page and the record's own action bar (under <header>) chrome: 'the region is inverted', 20-32 rows
    per console page in the 2026-09-11 audits."""
    cc = _CHROME_CONTAINERS
    if cc:
        c_frag = cc.get('chromeClassFragments') or []
        c_pre = tuple(cc.get('chromeTagPrefixes') or ())
        p_frag = cc.get('pageClassFragments') or []
        p_pre = tuple(cc.get('pageTagPrefixes') or ())
        for p in node.parents:
            if not p.name:
                continue
            cls = ' '.join(p.get('class') or []) if isinstance(p.get('class'), list) else (p.get('class') or '')
            t = p.name.lower()
            if any(f in cls for f in c_frag) or (c_pre and t.startswith(c_pre)):
                return 'chrome'
            if any(f in cls for f in p_frag) or (p_pre and t.startswith(p_pre)):
                return 'page'
    tags = [p.name for p in node.parents if p.name]
    if any('flexipage' in t or t.startswith('forcegenerated-') or t.startswith('c-') or t.startswith('runtime_')
           or t.startswith('records-') or t.startswith('force-record') for t in tags):
        return 'page'
    if any(t.startswith(_CHROME_HOSTS) for t in tags) or 'header' in tags or 'nav' in tags:
        return 'chrome'
    return 'page'


def xpath_ladder(cap: Capture, node, e: dict) -> dict:
    """stable attribute > label association > text + real tag > structural path from a stable
    ancestor. The first rung that is unique in the capture AND carries no generated value wins;
    otherwise the best rung is reported with its flags set, never silently."""
    det = e.get('element_details') or {}
    tag = node.name
    attrs = _attrs_of(node)
    ident = e.get('identification') or {}
    label = _clean_label(ident.get('label_text') or '')
    src = ident.get('label_source')
    rungs: list[tuple[str, str]] = []

    for k in STABLE_ATTRS:
        v = attrs.get(k)
        if v and not is_generated(v):
            rungs.append(('stable_attr', '//%s[@%s=%s]' % (tag, k, _lit(v))))
    if src == 'standard_label' and label:
        rungs.append(('label_association',
                      '//label[normalize-space(.)=%s]/following::%s[1]' % (_lit(label), tag)))
        rungs.append(('label_association',
                      '//label[contains(normalize-space(.),%s)]/following::%s[1]' % (_lit(label), tag)))
    sig = '[@type=%s]' % _lit(attrs['type']) if attrs.get('type') else ''
    own = label or nearest_preceding_text(node) or ''
    # 1. nearest UNIQUE preceding text (a section/card heading or the field's own unique label):
    #    the first <tag> after it must be this node -- no counting over a repeated set
    for t in _preceding_texts(node):
        if cap.count('//*[normalize-space(text())=%s]' % _lit(t)) != 1:
            continue
        # 0. the unique text's own container holds the control (a heading and its field in one box):
        #    following-sibling scoping needs no count at all -- exactly one control lives there
        xp0 = '//*[normalize-space(text())=%s]/following-sibling::*//%s%s' % (_lit(t), tag, sig)
        m0 = cap.doc.xpath(xp0)
        if len(m0) == 1 and _same_node(cap, m0[0], node):
            rungs.append(('sibling_scope', xp0))
            break
        xp = '(//*[normalize-space(text())=%s]/following::%s%s)[1]' % (_lit(t), tag, sig)
        m = cap.doc.xpath(xp)
        if m and _same_node(cap, m[0], node):
            rungs.append(('unique_preceding_text', xp))
            break
        # 2a. a text-bearing control (button/link): the unique heading, then the first such control
        #     carrying its own text -- the text lives INSIDE the control, so never following:: from it
        if own and own != t and src in ('inner_text', 'assistive_text'):
            xp1 = '(//*[normalize-space(text())=%s]/following::%s[normalize-space(.)=%s])[1]' % (_lit(t), tag, _lit(own))
            m1 = cap.doc.xpath(xp1)
            if m1 and _same_node(cap, m1[0], node):
                rungs.append(('scoped_text', xp1))
                break
            continue
        # 2b. that unique heading scoped over the control's own (repeated) label
        if own and own != t:
            xp2 = '(//*[normalize-space(text())=%s]/following::*[normalize-space(text())=%s])[1]/following::%s%s[1]' % (
                _lit(t), _lit(own), tag, sig)
            m2 = cap.doc.xpath(xp2)
            if m2 and _same_node(cap, m2[0], node):
                rungs.append(('scoped_label', xp2))
                break
    if not label:
        guess = nearest_preceding_text(node)
        if guess:
            sig = '[@type=%s]' % _lit(attrs['type']) if attrs.get('type') else ''
            base = '//*[normalize-space(text())=%s]/following::%s%s' % (_lit(guess), tag, sig)
            following = cap.doc.xpath(base)
            pos = next((i for i, m in enumerate(following, 1) if _same_node(cap, m, node)), None)
            if pos:
                rungs.append(('positional_last_resort', '(%s)[%d]' % (base, pos)))
    if label:
        if src == 'inner_text':
            # the exact text NODE: survives hidden siblings the capture dropped (display:none
            # subtrees are not serialised, so normalize-space(.) of the live element can differ)
            rungs.append(('text_node', '//%s[.//text()[normalize-space(.)=%s]]' % (tag, _lit(label))))
            rungs.append(('text_tag', '//%s[normalize-space(.)=%s]' % (tag, _lit(label))))
        elif src == 'assistive_text':
            # the exact text node first; then the assistive span as the raw actually shows it
            # (its real tag, its real class) -- never a generic OR over the template's list
            rungs.append(('text_node', '//%s[.//text()[normalize-space(.)=%s]]' % (tag, _lit(label))))
            for sp in node.find_all(True):
                cls = ' '.join(sp.get('class') or []) if isinstance(sp.get('class'), list) else (sp.get('class') or '')
                frag = next((a for a in _ASSISTIVE if a in cls), None)
                if frag and _norm_text(_node_text(sp)).lower() == label.lower():
                    rungs.append(('assistive_span', '//%s[.//%s[contains(@class,"%s")][normalize-space(.)=%s]]' % (
                        tag, sp.name, frag, _lit(label))))
                    break
        elif src == 'label_span':
            rungs.append(('text_tag', '//%s[.//*[normalize-space(.)=%s]]' % (tag, _lit(label))))
    # a stable attribute that is not unique page-wide (three 'Preview' buttons) but IS unique under
    # the nearest unique ancestor: //records-highlights2//button[@title="Change Owner"] -- never a
    # bare count over every button (user, 2026-09-10). Falls back to a count WITHIN that attribute set.
    for p in node.parents:
        if not p.name or p.name in ('template', '[document]', 'body', 'html'):
            continue
        if '-' in p.name and cap.tag_count(p.name) == 1:
            for k in STABLE_ATTRS:
                v = attrs.get(k)
                if not v or is_generated(v):
                    continue
                xp = '//%s//%s[@%s=%s]' % (p.name, tag, k, _lit(v))
                m = cap.doc.xpath(xp)
                if len(m) == 1 and _same_node(cap, m[0], node):
                    rungs.append(('scoped_attr', xp))
                    break
                pos = next((i for i, mm in enumerate(m, 1) if _same_node(cap, mm, node)), None)
                if pos and len(m) > 1:
                    rungs.append(('scoped_attr_positional', '(%s)[%d]' % (xp, pos)))
                    break
            break
    # structural: nearest ancestor that is unique in the capture (a custom element or one with a
    # stable attribute), then the node's position among that ancestor's descendants of its tag.
    anc_xp = None
    for p in node.parents:
        if not p.name or p.name in ('template', '[document]', 'body', 'html'):
            continue
        pa = _attrs_of(p)
        if '-' in p.name and cap.tag_count(p.name) == 1:
            anc_xp = '//%s' % p.name
            break
        for k in STABLE_ATTRS:
            v = pa.get(k)
            if v and not is_generated(v) and cap.count('//%s[@%s=%s]' % (p.name, k, _lit(v))) == 1:
                anc_xp = '//%s[@%s=%s]' % (p.name, k, _lit(v))
                break
        if anc_xp:
            break
    if anc_xp:
        sig = ''
        if attrs.get('type'):
            sig = '[@type=%s]' % _lit(attrs['type'])
        members = cap.doc.xpath('%s//%s%s' % (anc_xp, tag, sig))
        # position of THIS node among them, matched through the identity xpath
        me = cap.doc.xpath(identity_xpath(cap, node))
        pos = None
        if len(me) == 1:
            for i, m in enumerate(members, 1):
                if m is me[0]:
                    pos = i
                    break
        if pos:
            rungs.append(('structural', '(%s//%s%s)[%d]' % (anc_xp, tag, sig, pos)))

    evaluated = []
    for rung, xp in rungs:
        try:
            matches = cap.doc.xpath(xp)
        except Exception:
            matches = None
        n = None if matches is None else len(matches)
        gen = generated_values_in(xp)
        # unique AND this node: a rung that is unique but lands elsewhere in the capture is a miss
        this = bool(matches) and n == 1 and _same_node(cap, matches[0], node)
        evaluated.append({'rung': rung, 'xpath': xp, 'count_in_capture': n,
                          'unique_in_capture': this, 'generated_values': gen,
                          'unique_but_other_node': (n == 1 and not this) if n is not None else None})
    pick = next((r for r in evaluated if r['unique_in_capture'] and not r['generated_values']), None)
    if pick is None:
        pick = next((r for r in evaluated if r['unique_in_capture']), None) or (evaluated[0] if evaluated else None)
    out = {'value': pick['xpath'] if pick else None, 'rung': pick['rung'] if pick else None,
           'unique_in_capture': pick['unique_in_capture'] if pick else None,
           'count_in_capture': pick['count_in_capture'] if pick else None,
           'generated_values': pick['generated_values'] if pick else [],
           'ladder': evaluated,
           'live': None,
           'cross_org': None}
    if not pick:
        out['reason'] = 'no rung applies: no stable attribute, no label association, no text, no unique ancestor'
    return out


# ----------------------------------------------------------------------------- build
def _hint(e: dict) -> tuple[str | None, str | None, str | None]:
    """(fill keyword, verify keyword, parser reason)."""
    hf = e.get('hint_fill')
    hv = e.get('hint_verify')
    if isinstance(hf, dict):
        hf = hf.get('keyword')
    if isinstance(hv, dict):
        hv = hv.get('keyword')
    return hf, hv, e.get('hint_reason')


def _calls(e: dict) -> list[dict]:
    """The parser's EXACT proposed calls, one per locator option, in its order -- what a reviewer
    judges (anchor, tag, attribute, partial_match), never just the keyword name."""
    out = []
    for o in ((e.get('qforce_hints') or {}).get('locator_options') or []):
        out.append({'keyword': o.get('keyword'), 'locator': o.get('locator'), 'tag': o.get('tag'),
                    'call_example': o.get('call_example'), 'confidence': o.get('confidence'),
                    'anchor_candidates': [c.get('text') for c in (o.get('anchor_candidates') or [])],
                    'caveats': o.get('caveats') or []})
    return out


def _click_keyword(e: dict) -> str | None:
    if e.get('hint_act'):
        return e['hint_act']       # the family's ACT keyword (Open Console Subtab) beats the generic click rung
    opts = ((e.get('qforce_hints') or {}).get('locator_options') or [])
    return opts[0].get('keyword') if opts else None


def build_rows(cap: Capture, org: str | None) -> tuple[list[dict], dict]:
    verified = set()
    try:
        verified = PA.verified_labels(cap.path, org)
    except Exception:
        pass
    parsed = parse_elements_from_html(cap.raw, verified_labels=verified or None)
    els = list(parsed)
    tmpl = getattr(parsed, 'template', None) or {}
    seen_sig: dict = collections.Counter()
    claimed: set = set()      # 2026-09-11: one node, one row (see find_node)
    rows = []
    for i, e in enumerate(els):
        det = e.get('element_details') or {}
        ident = e.get('identification') or {}
        dis = e.get('disambiguation') or {}
        sig = (det.get('tag'), json.dumps(det.get('attributes') or {}, sort_keys=True),
               _clean_label(ident.get('label_text') or ''))
        nth = seen_sig[sig]
        seen_sig[sig] += 1
        # with claimed nodes excluded, the k-th element of a signature is the FIRST unclaimed candidate:
        # nth stays 0 so that a label-filtered count and an unfiltered candidate list cannot disagree
        node = find_node(cap, e, 0, claimed)
        if node is not None:
            claimed.add(id(node))
        hf, hv, reason = _hint(e)
        row = {
            'n': i,
            'element_type': e.get('element_type'),
            'label': ident.get('label_text'),
            'label_source': ident.get('label_source'),
            'tag': det.get('tag'),
            'attrs': det.get('attributes') or {},
            'value': det.get('value'),          # 2026-09-11: a grid cell's rendered value (its label is the column)
            'container': (e.get('context') or {}).get('section') or '',
            'hint_fill': hf,
            'hint_verify': hv,
            'hint_click': _click_keyword(e) if not hf else None,
            'hint_reason': reason,
            'calls': _calls(e),
            'group_size': dis.get('group_size'),
            'index': dis.get('index'),
            'anchor_candidates': [c.get('text') for c in (dis.get('anchor_candidates') or [])],
            'disambiguation_status': dis.get('disambiguation_status'),
            'confidence': dis.get('resolution') or (
                ((e.get('qforce_hints') or {}).get('locator_options') or [{}])[0].get('confidence')),
            'node_found': node is not None,
            'label_guess': nearest_preceding_text(node) if (node is not None and not (ident.get('label_text') or '').strip()) else None,
            'region': region_of(node) if node is not None else 'unknown',
            'raw': None, 'raw_context': [], 'identity_xpath': None,
            'xpath': {'value': None, 'rung': None, 'unique_in_capture': None,
                      'generated_values': [], 'live': None, 'cross_org': None,
                      'reason': 'COULD-NOT-CHECK: node not found in the capture'},
            'live': {'keyword': None, 'xpath': None},
            'review': {'status': 'unreviewed', 'changes': []},
        }
        if node is not None:
            row['raw'], row['raw_context'] = raw_neighbourhood(node)
            row['identity_xpath'] = identity_xpath(cap, node)
            row['xpath'] = xpath_ladder(cap, node, e)
        entry = PL.match(row, _library)
        if entry:
            row['pattern'] = entry['id']
            row['pattern_args'] = PL.find_pattern_args(entry, node)
        rows.append(row)
    PL.stamp(rows)          # bucket + representative on every row: the review works by shape, not by row
    return rows, tmpl


_library = PL.load_library()


def _carry_over(rows: list[dict], prev: dict | None) -> int:
    """A rebuild never loses a review: statuses, changes, corrections, live verdicts and drives
    carry over by row number when the label still matches."""
    if not prev:
        return 0
    # match by identity, not row number: a parser change that adds one row must not shift every
    # review after it (2026-09-10: the dueling-list row appeared at 77 and six container reviews
    # below it were lost). Key = (family, label, tag, k-th occurrence of that key).
    def _key(r):
        return (r.get('element_type'), r.get('label') or '', r.get('tag') or '')
    old, seen_old = {}, collections.Counter()
    # 2026-09-10: a parser fix that starts LABELLING a row the reviewer had labelled by correction
    # changes the row's key ('' -> 'Contract Term') and lost 31 of 84 reviews on the Nightmare page;
    # the second index keys the old row by its CORRECTED label so the review follows the fix
    old2, seen_old2 = {}, collections.Counter()
    for o in prev.get('rows') or []:
        k = _key(o); old[(k, seen_old[k])] = o; seen_old[k] += 1
        if o.get('label_corrected') and o.get('label_corrected') != (o.get('label') or ''):
            k2 = (o.get('element_type'), o['label_corrected'], o.get('tag') or '')
            old2[(k2, seen_old2[k2])] = o; seen_old2[k2] += 1
    seen_new, seen_new2 = collections.Counter(), collections.Counter()
    n = 0
    used = set()
    for r in rows:
        k = _key(r); o = old.get((k, seen_new[k])); seen_new[k] += 1
        if o is None or id(o) in used:
            o = old2.get((k, seen_new2[k])); seen_new2[k] += 1
        if not o or id(o) in used:
            continue
        used.add(id(o))
        r['review'] = o.get('review') or r['review']
        r['live'] = o.get('live') or r['live']
        if r['live'] and r['live'].get('xpath'):
            r['xpath']['live'] = r['live']['xpath']
        for k in list(o):
            if k.endswith('_corrected'):
                r[k] = o[k]
        # a fix stream landed: the parser now emits the label the reviewer corrected it to, so the
        # row is RIGHT as parsed (Phase 3 re-score, 2026-09-10) -- the history stays in `changes`
        if o.get('label_corrected') and o['label_corrected'] == (r.get('label') or ''):
            r['review']['changes'].append({'column': 'label', 'from': o.get('label'), 'to': r['label'],
                                           'note': 'parser fix landed: the parser now emits the corrected label',
                                           'at': time.strftime('%Y-%m-%dT%H:%M:%S')})
            r.pop('label_corrected', None)
            if (r['review'].get('status') == 'corrected'
                    and not any(k.endswith('_corrected') and k != 'label_corrected' for k in o)):
                r['review']['status'] = 'accepted'      # the label was the only correction: right as parsed now
        n += 1
    return n


def cmd_build(a) -> int:
    print(_adopt_page_template(a.capture))
    cap = Capture(a.capture)
    org = a.org or PA.org_for(a.capture)
    pk = PA.page_key_for(a.capture, org)
    rows, tmpl = build_rows(cap, org)
    out_dir = a.out_dir or os.path.dirname(os.path.abspath(a.capture))
    os.makedirs(out_dir, exist_ok=True)
    prev = None
    if os.path.exists(os.path.join(out_dir, 'review.json')):
        prev = json.load(open(os.path.join(out_dir, 'review.json')))
    carried = _carry_over(rows, prev)
    # THE STATE STAMP travels capture -> review -> store (user, 2026-09-18). Every row carries the
    # state its control was seen in, so `writeback` can attach it to that state instead of flat on
    # the page. Before this the review TABLE had no column for "which state was the page in when
    # this row was probed", so a reviewer had nowhere to put the answer even when they knew it --
    # which is why cicd-demo's Revenue Cloud Settings modal has 133 VERIFIED-PASS controls and
    # zero states (docs/audit/pom-states-and-modals-2026-09-18.md section 3, W3).
    stamp = capture_header(a.capture)
    for r in rows:
        r['state'] = stamp.get('state') or 'default'
    rel = lambda p: os.path.relpath(os.path.abspath(p), _ROOT) if p else None
    review = {
        'org': org,
        'capture': rel(a.capture),
        'state_stamp': {k: stamp.get(k) for k in
                        ('state', 'entered_via', 'host_url', 'state_stamp_present')},
        'screenshot': rel(a.screenshot) if a.screenshot else None,
        'page_key': pk['key'] if pk else None,
        'page': {k: pk.get(k) for k in ('pattern', 'object', 'action', 'host')} if pk else None,
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'template': tmpl if isinstance(tmpl, dict) else str(tmpl),
        'rows': rows,
        'buckets': PL.bucket(rows),
        'drives': (prev or {}).get('drives') or [],
        'live_session': (prev or {}).get('live_session'),
    }
    if prev and ((prev.get('page') or {}).get('url')) and review.get('page') is not None:
        review['page']['url'] = prev['page']['url']          # --url survives a rebuild
    if carried:
        print('carried over %d reviewed row(s) from the previous review.json' % carried)
    print('%d rows -> %d buckets (one representative each is what live / robot / demo work on; --all for every row); library patterns: %s' % (
        len(rows), len(review['buckets']), dict(collections.Counter(r['pattern'] for r in rows if r.get('pattern'))) or 'none'))
    _cross_org(review)
    path = os.path.join(out_dir, 'review.json')
    json.dump(review, open(path, 'w'), indent=1)
    print(f"review: {rel(path)}  rows {len(rows)}  page_key {review['page_key']}")
    _st = review['state_stamp']
    print("state stamp: state=%s  entered_via=%s  host_url=%s%s" % (
        _st['state'], _st['entered_via'], _st['host_url'] or '(none)',
        '' if _st['state_stamp_present'] else
        '  -- NO stamp in this capture header (taken before 2026-09-18, or by a writer that does '
        'not stamp): every row is filed under the default state with no opening control'))
    print_table(review)
    _render(review, os.path.join(out_dir, 'review.html'))
    return 0


def _cross_org(review: dict) -> None:
    """(d): does another org hold this page key? The store is partitioned per alias; a shared
    pattern in a second partition makes the check possible, otherwise COULD-NOT-CHECK."""
    pat = (review.get('page') or {}).get('pattern')
    if not pat:
        return
    store = Store()
    others = []
    for p in store.partitions():
        if p['name'] == review.get('org'):
            continue
        for r in store.records(p['name']):
            if (r.get('page') or {}).get('pattern') == pat:
                others.append(p['name'])
    for row in review['rows']:
        xp = row.get('xpath') or {}
        if others:
            xp['cross_org'] = {'status': 'UNMEASURED', 'orgs': sorted(set(others)),
                               'note': 'run `live` against each listed org'}
        else:
            xp['cross_org'] = {'status': 'COULD-NOT-CHECK',
                               'reason': 'no second org holds page pattern %s' % pat}


# ----------------------------------------------------------------------------- table / render
def _short(s, n):
    s = '' if s is None else str(s)
    return s if len(s) <= n else s[:n - 1] + '…'


def _kw(row) -> str:
    return row.get('hint_fill') or row.get('hint_click') or ''


def print_table(review: dict) -> None:
    print('%-3s %-16s %-28s %-14s %-10s %-11s %2s %2s %-6s %-6s %-9s %s' % (
        '#', 'family', 'label', 'source', 'fill/click', 'verify', 'gs', 'ix', 'xp(a)', 'xp(c)',
        'review', 'xpath rung / reason'))
    for r in review['rows']:
        xp = r.get('xpath') or {}
        a = {True: 'unique', False: 'x%s' % xp.get('count_in_capture'), None: 'CNC'}[xp.get('unique_in_capture')]
        c = 'clean' if xp.get('value') and not xp.get('generated_values') else ('GEN' if xp.get('value') else '-')
        why = xp.get('rung') or _short(xp.get('reason') or r.get('hint_reason') or '', 60)
        print('%-3d %-16s %-28s %-14s %-10s %-11s %2s %2s %-6s %-6s %-9s %s' % (
            r['n'], _short(r['element_type'], 16), _short(r['label'] or (('?' + r['label_guess']) if r.get('label_guess') else ''), 28), _short(r['label_source'] or ('guess' if r.get('label_guess') else ''), 14),
            _short(_kw(r), 10), _short(r.get('hint_verify') or '', 11), r.get('group_size') or '',
            r.get('index') or '', a, c, _short(r['review']['status'], 9), why))


def _calls_cell(r: dict) -> str:
    rc = robot_call(r)
    parts = ['<code>%s</code>' % _html.escape(c.get('call_example') or '') for c in (r.get('calls') or [])]
    if rc['primary']:
        parts.append('<small>robot:</small><br><code>%s</code>' % '<br>'.join(_html.escape(x) for x in rc['primary']))
    cands = r.get('anchor_candidates') or []
    if cands:
        parts.append('<small>anchor candidates: %s</small>' % _html.escape(', '.join(cands)))
    return '<br>'.join(parts) or '<span class="cnc">%s</span>' % _html.escape(_short(r.get('hint_reason') or 'no keyword', 120))


def _live_cell(v) -> str:
    if not v:
        return '<span class="cnc">not run</span>'
    cls = {'VERIFIED-PASS': 'ok', 'CAUGHT-BUG': 'bug'}.get(v.get('verdict'), 'cnc')
    ex = ('<br><code>%s</code>' % _html.escape(v['executed'])) if v.get('executed') else ''
    return '<span class="%s">%s</span><br><small>%s</small>%s' % (
        cls, _html.escape(v.get('verdict') or ''), _html.escape(_short(v.get('detail') or '', 140)), ex)


def _render(review: dict, path: str) -> None:
    rows = review['rows']
    shot = review.get('screenshot')
    shot_rel = os.path.relpath(os.path.join(_ROOT, shot), os.path.dirname(path)) if shot else None
    h = ['<!doctype html><meta charset="utf-8"><title>Review -- %s</title>' % _html.escape(review.get('page_key') or ''),
         '<style>body{font:13px/1.35 -apple-system,Helvetica,sans-serif;margin:16px;color:#111}'
         'table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left}'
         'th{background:#eee;position:sticky;top:0}pre{margin:0;white-space:pre-wrap;word-break:break-all;font-size:11px;max-width:420px}'
         '.ok{color:#0a7d2c;font-weight:600}.bug{color:#b00020;font-weight:600}.cnc{color:#8a6d00;font-weight:600}'
         '.corr{background:#fff7d6}.ni{color:#777}img{max-width:100%;border:1px solid #ccc}code{font-size:11px}</style>',
         '<h1>Review table -- %s</h1>' % _html.escape(review.get('page_key') or ''),
         '<p>%d chrome rows (greyed) are reviewed once per org and excluded from the score and the export.</p>' % sum(1 for r in rows if r.get('region') == 'chrome'),
         '<p>capture <code>%s</code> · built %s · org %s · rows %d</p>' % (
             _html.escape(review.get('capture') or ''), review.get('built_at'), review.get('org'), len(rows))]
    if shot_rel:
        h.append('<details open><summary>screenshot</summary><img src="%s"></details>' % _html.escape(shot_rel))
    h.append('<table><tr><th>#</th><th>family</th><th>label</th><th>parser call(s) -- what would run</th><th>verify</th>'
             '<th>gs / ix / anchor candidates</th><th>parser reason</th><th>xpath (rung · a · c · d)</th>'
             '<th>keyword live</th><th>xpath live (b)</th><th>review</th><th>raw neighbourhood</th></tr>')
    for r in rows:
        xp = r.get('xpath') or {}
        st = r['review']['status']
        cls = 'corr' if st == 'corrected' else ('ni' if st in ('not_interactive',) or r.get('region') == 'chrome' else '')
        a = {True: 'a:unique', False: 'a:x%s' % xp.get('count_in_capture'), None: 'a:CNC'}[xp.get('unique_in_capture')]
        c = 'c:clean' if xp.get('value') and not xp.get('generated_values') else ('c:GENERATED %s' % xp.get('generated_values') if xp.get('value') else 'c:-')
        d = (xp.get('cross_org') or {}).get('status') or ''
        changes = '<br>'.join('<b>%s</b>: %s → %s%s' % (
            _html.escape(ch['column']), _html.escape(str(ch.get('from'))), _html.escape(str(ch.get('to'))),
            (' <i>(raw had %s)</i>' % _html.escape(ch['raw_had'])) if ch.get('raw_had') else '')
            for ch in r['review'].get('changes') or [])
        h.append('<tr class="%s"><td>%d</td><td>%s</td><td>%s<br><small>%s</small></td><td>%s</td><td>%s</td>'
                 '<td>%s / %s<br><small>%s</small></td><td><small>%s</small></td>'
                 '<td><code>%s</code><br><small>%s · %s · %s · d:%s</small></td><td>%s</td><td>%s</td>'
                 '<td><b>%s</b><br>%s</td><td><pre>%s</pre><small>%s</small></td></tr>' % (
                     cls, r['n'], _html.escape(r['element_type'] or ''), _html.escape(str(r['label'])),
                     _html.escape(r['label_source'] or ''), _calls_cell(r), _html.escape(r.get('hint_verify') or ''),
                     r.get('group_size') or '', r.get('index') or '', _html.escape(', '.join(r.get('anchor_candidates') or [])),
                     _html.escape(r.get('hint_reason') or ''),
                     _html.escape(xp.get('value') or (xp.get('reason') or '')), _html.escape(xp.get('rung') or ''), a, c, _html.escape(d),
                     _live_cell((r.get('live') or {}).get('keyword')), _live_cell((r.get('live') or {}).get('xpath')),
                     _html.escape(st), changes,
                     _html.escape(r.get('raw') or ''), _html.escape(' > '.join(reversed(r.get('raw_context') or [])))))
    h.append('</table>')
    sc = score(review)
    h.append('<h2>Score</h2><pre>%s</pre>' % _html.escape(json.dumps(sc, indent=1)))
    open(path, 'w').write('\n'.join(h))


def cmd_render(a) -> int:
    review = json.load(open(a.review))
    out = os.path.join(os.path.dirname(os.path.abspath(a.review)), 'review.html')
    _render(review, out)
    print('rendered', os.path.relpath(out, _ROOT))
    return 0


# ----------------------------------------------------------------------------- robot steps (inline)
def _xp_arg(xp: str) -> str:
    """Robot form of an xpath argument: `xpath\=` (QWeb keywords take **kwargs, so a bare
    `xpath=` is parsed as a NAMED argument and the locator never arrives -- user, 2026-09-10),
    with every `=` inside the xpath escaped ONCE (CLAUDE.md)."""
    return 'xpath\\=' + re.sub(r'(?<!\\)=', r'\\=', xp)


def _rf(kw: str, *args, **kwargs) -> str:
    parts = [kw] + [str(a) for a in args if a is not None and a != '']
    parts += ['%s=%s' % (k, v) for k, v in kwargs.items() if v not in (None, '', False)]
    return '    '.join(parts)


def probe_value(row: dict) -> str:
    label = row.get('label_corrected') or _clean_label(row.get('label') or '')
    idx = row.get('index_corrected') if 'index_corrected' in row else row.get('index')
    return _DEFAULT_VALUES.get(label) or ('GZREV %s%s' % (label, (' %s' % idx) if idx else ''))


def _bucket_score(review: dict, rows: list) -> dict:
    """Per-bucket: right when the representative was accepted, changed when it was corrected;
    unreviewed otherwise. A member's own review, when it has one, does not move the bucket."""
    ns = {r['n'] for r in rows}
    by_n = {r['n']: r for r in review['rows']}
    out = {'count': 0, 'right': 0, 'changed': 0, 'unreviewed': 0, 'not_interactive': 0, 'could_not_map': 0, 'needs_xpath': 0}
    for b in review.get('buckets') or []:
        rep = by_n.get(b['representative'])
        if rep is None or rep['n'] not in ns:
            continue
        out['count'] += 1
        st = rep['review']['status']
        out[{'accepted': 'right', 'corrected': 'changed'}.get(st, st)] = out.get({'accepted': 'right', 'corrected': 'changed'}.get(st, st), 0) + 1
    return out


def _pattern_entry(row: dict) -> dict | None:
    """The library entry stamped on the row, when its recipe is one to RUN (a 'policy' or a
    measured-failure entry documents; it never replaces the parser's call)."""
    if not row.get('pattern'):
        return None
    e = next((x for x in _library if x['id'] == row['pattern']), None)
    return e if e and e.get('status') in ('verified', 'verified-on-one-page') else None


def robot_call(row: dict) -> dict:
    """The EXACT inline Robot steps for one control, built from the parser's first call and any
    corrections: primary (the action with its read-back), verify (a non-mutating existence
    check with the same locator strategy), xpath (the backup, verify + drive for inputs)."""
    calls = row.get('calls') or []
    c0 = calls[0] if calls else {}
    # 2026-09-11: a family's ACT keyword (Open Console Subtab, Click Tree Item -- routed by the template, read
    # back by the keyword itself) beats the parser's generic click rung; ClickText is its discouraged fallback
    act = row.get('hint_click') if row.get('hint_click') not in (None, '', 'ClickText', 'ClickItem', 'ClickElement') else None
    kw = row.get('keyword_corrected') or act or c0.get('keyword') or _kw(row)
    label = row.get('label_corrected') or _clean_label(row.get('label') or '')
    idx = row.get('index_corrected') if 'index_corrected' in row else row.get('index')
    ck = DA.to_call_kwargs({k: v for k, v in {'index': idx, 'anchor': row.get('anchor_corrected')}.items() if v})
    anchor = ck.get('anchor')
    tag = row.get('tag_corrected') or c0.get('tag') or row.get('tag')
    attr = row.get('attribute_corrected')
    locator = (row.get('attrs') or {}).get(attr) if attr else (c0.get('locator') if kw == 'ClickItem' else label)
    value = probe_value(row)
    out = {'primary': [], 'verify': [], 'xpath': []}
    entry = _pattern_entry(row) if not row.get('call_corrected') else None
    if row.get('call_corrected'):
        out['primary'] = [x.strip() for x in row['call_corrected'].split(' ;; ') if x.strip()]   # ' ;; ' separates steps
    elif entry:
        # a library recipe: the pattern that held on an earlier page, rendered with this row's one parameter
        out['primary'], recipe_xp = PL.recipe(entry, row, value)
        out['verify'] = [_rf('VerifyText', label, partial_match='False', timeout='5')] if label and kw in ('ClickText', None) else []
        out['_recipe_xpath'] = recipe_xp
    elif kw == 'Open Console Subtab':
        # keywords_console.open_console_subtab: clicks the workspace tab and reads back aria-selected AND the
        # landed URL against the tab's own href (a tab can highlight while the pane stays put)
        out['primary'] = [_rf('Open Console Subtab', label)]
        out['verify'] = [_rf('VerifyText', label, partial_match='False', timeout='5')]
    elif kw == 'ClickText':
        out['primary'] = [_rf('ClickText', label, anchor=anchor, partial_match='False')]
        out['verify'] = [_rf('VerifyText', label, anchor=anchor, partial_match='False', timeout='5')]
    elif kw == 'ClickItem':
        out['primary'] = [_rf('ClickItem', locator, tag=tag, anchor=anchor, partial_match='False')]
        out['verify'] = [_rf('VerifyItem', locator, tag=tag, anchor=anchor, partial_match='False', timeout='5')]
    elif kw == 'TypeText':
        out['primary'] = [_rf('TypeText', label, value, anchor=anchor),
                          _rf('VerifyInputValue', label, value, anchor=anchor)]
        out['verify'] = [_rf('VerifyInputElement', label, anchor=anchor, timeout='5')]
    elif kw == 'PickList':
        out['primary'] = [_rf(kw, label, value), _rf('VerifyText', value, timeout='5')]
        out['verify'] = [_rf('VerifyText', label, partial_match='False', timeout='5')]
    elif kw in ('GetFieldValue', 'VerifyField') or (row.get('family_corrected') or row.get('element_type')) == 'output_field':
        tv = row.get('truth')
        shown = '${EMPTY}' if tv == '' else (tv if tv is not None else '<value>')
        # a relationship value (Owner.Name, CreatedBy.Name) renders with more than the name
        # (audit fields add the timestamp): partial_match=True (user, 2026-09-10)
        pm = 'True' if ('.' in str(row.get('truth_path') or '') and tv) else None
        # a first member needs no anchor (D4); an index above 1 does
        out['primary'] = [_rf('VerifyField', label, shown, anchor=(anchor if anchor not in (None, '1') else None), partial_match=pm)]
        out['verify'] = []
    elif kw == 'DropDown':
        out['primary'] = [_rf('DropDown', label, value, anchor=anchor), _rf('VerifySelectedOption', label, value, anchor=anchor)]
        out['verify'] = [_rf('VerifyText', label, partial_match='False', timeout='5')]
    elif kw == 'ComboBox':
        out['primary'] = ['# UNVERIFIED: no drive rule and the option list could not be read; pick a real option:',
                          _rf(kw, label, value), _rf('VerifyText', value, timeout='5')]
        out['verify'] = [_rf('VerifyText', label, partial_match='False', timeout='5')]
    elif kw == 'ClickCheckbox':
        out['primary'] = [_rf('ClickCheckbox', label, 'on', anchor=anchor),
                          _rf('VerifyCheckboxStatus', label, 'on', anchor=anchor)]
        out['verify'] = []      # the xpath line in section 1 is the existence check; state is unknown until driven
    elif kw:
        out['primary'] = [_rf(kw, label, anchor=anchor)]
    xp = row.get('xpath_corrected') or (row.get('xpath') or {}).get('value')
    recipe_xp = out.pop('_recipe_xpath', None)
    if row.get('xpath_call_corrected'):
        out['xpath'] = [x.strip() for x in row['xpath_call_corrected'].split(' ;; ') if x.strip()]
    elif recipe_xp and xp:
        # the recipe's xpath form after the existence check (xpath[0] stays the VerifyElement contract)
        out['xpath'] = [_rf('VerifyElement', _xp_arg(xp), timeout='5')] + PL.recipe(entry, row, value)[1]
    elif xp:
        out['xpath'] = [_rf('VerifyElement', _xp_arg(xp), timeout='5')]
        fam = row.get('family_corrected') or row.get('element_type')
        if fam == 'input_field':
            out['xpath'] += [_rf('TypeText', _xp_arg(xp), value), _rf('VerifyInputValue', _xp_arg(xp), value)]
        elif fam == 'dropdown' and row.get('tag') == 'select':
            out['xpath'] += [_rf('DropDown', _xp_arg(xp), value), _rf('VerifySelectedOption', _xp_arg(xp), value)]
        elif fam == 'checkbox':
            out['xpath'] += [_rf('ClickElement', _xp_arg(xp))]
    return out


def _demo_lines(r: dict) -> tuple[list, list]:
    """(keyword-form lines, xpath-form lines) -- ACTIONS only, no verification."""
    rc = robot_call(r)
    kw = r.get('keyword_corrected') or _kw(r)
    xp = r.get('xpath_corrected') or (r.get('xpath') or {}).get('value')
    value = probe_value(r)
    fam = r.get('family_corrected') or r.get('element_type')
    label = r.get('label_corrected') or _clean_label(r.get('label') or '')
    if fam == 'output_field':
        # on a read page the read-back IS the action: VerifyField <label> <the value SOQL holds> -- but only
        # for a Details-tab field. A HIGHLIGHTS-panel value (records-highlights-details-item, the compact
        # layout under the record name) is not a form field: VerifyText <value> anchored on its label
        # (user, 2026-09-11). A blank value is a comment in both forms -- there is nothing to verify.
        truth = r.get('truth')
        highlights = (r.get('tag') == 'records-highlights-details-item') or ('records-highlights-details-item' in (r.get('raw') or '')[:200])
        if truth is None:
            note = ['# %s -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)' % label]
            return note, note
        if truth == '':
            note = ['# %s -- blank%s (nothing to verify)' % (label, ' in the highlights panel' if highlights else '')]
            return note, note
        if highlights:
            line = [_rf('VerifyText', str(truth), anchor=label)]
            return line, line
        vf = [x for x in rc['primary'] if x.split('    ')[0] == 'VerifyField']
        return vf, [_rf('VerifyText', str(truth), anchor=label)]
    if r.get('call_corrected'):
        acts = [x for x in rc['primary'] if not x.startswith('#') and not x.split('    ')[0].startswith('Verify')]
        if r.get('xpath_call_corrected'):
            return acts, [x for x in rc['xpath'] if not x.startswith('#') and not x.split('    ')[0].startswith('Verify')]
        if not xp or not acts:
            return acts, acts        # a corrected call with no xpath is the same in both forms
        # the xpath form drives the FIRST step by the xpath (the control), the rest as corrected
        # (a lookup: type into the searchbox by xpath, then ClickText the option)
        parts = acts[0].split('    ')
        if parts[0] in ('TypeText', 'DropDown', 'ClickCheckbox') and len(parts) > 1:
            first = _rf(parts[0], _xp_arg(xp), *parts[2:])
        elif parts[0] in ('ClickText', 'ClickItem', 'ClickElement'):
            first = _rf('ClickElement', _xp_arg(xp))
        else:
            return acts, acts
        return acts, [first] + acts[1:]
    lv = r.get('live') or {}
    kw_v = (lv.get('keyword') or {}).get('verdict')
    xp_v = (lv.get('xpath') or {}).get('verdict')
    if r['review']['status'] == 'needs_xpath':
        kw_form = ['# no keyword reaches this control (measured live) -- see the XPath form']
    elif kw_v == 'CAUGHT-BUG' and xp_v == 'VERIFIED-PASS':
        # 2026-09-11: a keyword form that MEASURED a failure (own or inherited from its bucket) is never
        # exported as a step -- the xpath form is the one that resolved; the line stays visible for the review
        kw_form = ['# keyword form measured CAUGHT-BUG live (%s) -- see the XPath form' % _short((lv.get('keyword') or {}).get('detail') or '', 90)]
        kw_form += ['# ' + x for x in rc['primary'] if not x.split('    ')[0].startswith('Verify')]
    else:
        kw_form = [x for x in rc['primary'] if not x.split('    ')[0].startswith('Verify')]
    if not xp:
        return kw_form, ['# (no xpath)']
    if fam == 'input_field' or kw == 'TypeText':
        xp_form = [_rf('TypeText', _xp_arg(xp), value)]
    elif fam == 'dropdown' and r.get('tag') == 'select':
        xp_form = [_rf('DropDown', _xp_arg(xp), value)]
    elif kw == 'ClickCheckbox' or fam == 'checkbox':
        xp_form = [_rf('ClickElement', _xp_arg(xp))]
    elif kw in ('PickList', 'ComboBox'):
        xp_form = [_rf('ClickElement', _xp_arg(xp)), _rf('ClickText', value)]
    else:
        xp_form = [_rf('ClickElement', _xp_arg(xp))]
    return kw_form, xp_form


def bucket_index(review: dict) -> dict:
    """row n -> its bucket record (count, representative, members)."""
    out = {}
    for b in review.get('buckets') or []:
        for n in b.get('members') or []:
            out[n] = b
        out[b['representative']] = b
    return out


def sample_per_bucket(rows: list, review: dict, per: int = 3) -> list:
    """The representative of every bucket plus up to `per - 1` more members, in row order -- enough of
    each family to see how its other members read, never a whole table (user, 2026-09-11). A corrected
    row is always kept."""
    idx = bucket_index(review)
    taken: dict = collections.Counter()
    out = []
    reps = {b['representative'] for b in review.get('buckets') or []}
    for r in rows:                              # representatives first so a bucket's first line is its rep
        b = idx.get(r['n'])
        if r.get('call_corrected') or (b is None) or r['n'] in reps:
            out.append(r)
            if b is not None:
                taken[b['representative']] += 1
    for r in rows:
        b = idx.get(r['n'])
        if r in out or b is None or r['n'] in reps:
            continue
        if taken[b['representative']] < per:
            out.append(r)
            taken[b['representative']] += 1
    order = {r['n']: i for i, r in enumerate(rows)}
    return sorted(out, key=lambda r: order[r['n']])


def _page_url(review: dict, a) -> str:
    """The GoTo target. The live probe records the holder's URL; when the org is read-only for the
    agent (cicd-demo) there is no probe, so `--url` names it and is kept on the review (page.url)."""
    page = review.setdefault('page', {})
    if getattr(a, 'url', None):
        page['url'] = a.url
        json.dump(review, open(a.review, 'w'), indent=1)
    if getattr(a, 'app', None):
        page['app'] = a.app                     # the Lightning app (label or 06m id) the page was captured in
        json.dump(review, open(a.review, 'w'), indent=1)
    return ((review.get('live_session') or {}).get('url') or page.get('url')
            or 'https://%s%s' % (page.get('host') or 'unknown-host', page.get('pattern') or ''))


def crt_header(review: dict, url: str):
    """2026-09-11: the user's CRT project (crt/resources/common.robot, crt/tests/salesforceTests.robot,
    github.com/joecopado/CRTPagePatterns) authenticates per org with
    `${token}=  JwtAuthenticate  ${client_id<S>}  ${username<S>}  ${private_key<S>}  [sandbox=true]` then
    `JwtLogin`; crt/orgs.json maps an org alias to its suffix S. Returns (settings lines, preamble lines,
    goto line) so an exported story drops straight into that suite: the Resource + Suite Setup/Teardown the
    suite already uses, the JWT preamble with the VARIABLE NAMES (never values), and a GoTo on
    ${login_url} + the page path. Without crt/orgs.json the export keeps its plain QWeb/QForce header."""
    try:
        orgs = json.load(open(os.path.join(_ROOT, 'crt', 'orgs.json')))
    except Exception:
        return None
    org = review.get('org') or ''
    o = orgs.get(org)
    if not isinstance(o, dict):
        return None
    s = o.get('suffix') or org
    from urllib.parse import urlparse
    u = urlparse(url)
    path = (u.path + ('?' + u.query if u.query else '')) if u.scheme else url
    settings = ['*** Settings ***', 'Resource                      ../resources/common.robot',
                'Resource                      ../resources/garzai_console.robot',
                'Resource                      ../resources/garzai_navigation.robot',
                'Suite Setup                   Setup Browser', 'Suite Teardown                End suite', '']
    pre = ['    # %s -- the suite\'s own variables; values live in CRT, never in this file' % (o.get('label') or org),
           '    ${token}=    JwtAuthenticate    ${client_id%s}    ${username%s}    ${private_key%s}%s' % (s, s, s, '    sandbox=true' if o.get('sandbox') else ''),
           '    JwtLogin']
    return settings, pre, nav_line(review, path)


def app_label(org: str, app: str | None) -> str | None:
    """An app named by LABEL is stable across orgs; an 06m DurableId is not. crt/apps.json (built from
    AppDefinition by `review_table.py apps --org`) maps an id to its label; a label passes through."""
    if not app:
        return None
    if not app.startswith('06m'):
        return app
    try:
        apps = json.load(open(os.path.join(_ROOT, 'crt', 'apps.json'))).get(org) or {}
    except Exception:
        apps = {}
    ent = apps.get(app)
    return (ent or {}).get('label') if isinstance(ent, dict) else None


_NAME_FIELD_FALLBACK = {'Case': 'CaseNumber', 'Contract': 'ContractNumber', 'ServiceAppointment': 'AppointmentNumber',
                        'Order': 'OrderNumber', 'WorkOrder': 'WorkOrderNumber', 'Solution': 'SolutionNumber'}


def name_field_of(org: str, sobject: str) -> str:
    """The object's name field from the org layer slice (docs/recorder/pom/layers/org/<alias>.json); a lazy
    object falls back to the platform's known auto-number names, else Name."""
    try:
        layer = json.load(open(os.path.join(_ROOT, 'docs', 'recorder', 'pom', 'layers', 'org', '%s.json' % org)))
        nf = ((layer.get('objects') or {}).get(sobject) or {}).get('name_field')
        if nf:
            return nf
    except Exception:
        pass
    return _NAME_FIELD_FALLBACK.get(sobject, 'Name')


def nav_line(review: dict, path: str) -> str:
    """2026-09-11 (user: 'resolving records and objects and apps ... a keyword directly that handles this
    navigation'): the exported step names WHAT to open, never a host, an app id or a record id --
    garzai_navigation.robot resolves them at run time (GetInstanceUrl, AppDefinition by label, SOQL by the
    object's name field) and reads the landing back. The record's name-field VALUE comes from the capture's
    own title ('00001031 | Case | Salesforce'); the app from `--app` / page.app (label, or an id mapped through
    crt/apps.json); anything the four keywords cannot name falls back to Open Lightning Path."""
    page = review.get('page') or {}
    org = review.get('org') or ''
    app = app_label(org, page.get('app'))
    app_arg = ('    app=%s' % app) if app else ''
    try:
        title = capture_header(os.path.join(_ROOT, review['capture'])).get('title') or ''
    except Exception:
        title = ''
    m = re.search(r'/lightning(?:/app/[A-Za-z0-9]+)?/r/([A-Za-z0-9_]+)/([A-Za-z0-9]{15,18}|\{id\})/(view|edit)', path or '') \
        or re.search(r'/r/([A-Za-z0-9_]+)/(\{id\})/(view)', page.get('pattern') or '')
    if m:
        sobject, action = m.group(1), m.group(3)
        value = title.split(' | ')[0].strip() if ' | ' in title else ''
        if value:
            return '    Open Record Page    %s    %s    %s%s' % (sobject, name_field_of(org, sobject), value, app_arg)
    m = re.search(r'/lightning(?:/app/[A-Za-z0-9]+)?/o/([A-Za-z0-9_]+)/(new|list|home)', path or '')
    if m:
        return '    Open Object Page    %s    %s%s' % (m.group(1), m.group(2), app_arg)
    m = re.search(r'/lightning(?:/app/[A-Za-z0-9]+)?/n/([A-Za-z0-9_]+)', path or '')
    if m:
        return '    Open Nav Tab    %s%s' % (m.group(1), app_arg)
    return '    Open Lightning Path    %s' % path


def live_ok(r: dict) -> bool:
    """Did either exported form of this row MEASURE a pass live? The live verdict is the review for
    an unreviewed row (2026-09-11, user: "none of these test files have any of the steps in them")."""
    lv = r.get('live') or {}
    return any(((lv.get(f) or {}).get('verdict') == 'VERIFIED-PASS') for f in ('keyword', 'xpath'))


def exported_row(r: dict) -> bool:
    """A row becomes STEPS: it was reviewed, or a form measured a live pass."""
    return r['review']['status'] != 'unreviewed' or live_ok(r)


def omitted_line(r: dict, note: str | None = None) -> str:
    """user, 2026-09-11 (hc-provider-contract: the record page's tab bar and the Contract History
    related list were PARSED into rows and the exported suite showed none of them -- the user
    concluded the parser had excluded them): an exported suite must SHOW every control the parser
    found. A row with no live pass is not a step; it is ONE comment line naming the verdict that
    kept it out, in the stored vocabulary, never a silent drop."""
    lv = r.get('live') or {}
    label = _short(r.get('label_corrected') or _clean_label(r.get('label') or '')
                   or ('row %d (%s)' % (r['n'], r.get('family_corrected') or r.get('element_type') or 'no family')), 90)
    if note:
        return '# %s -- not exported: %s' % (label, note)
    def verdict(form):
        return ((lv.get(form) or {}).get('verdict')) or 'not probed'
    return '# %s -- not exported: keyword %s / xpath %s' % (label, verdict('keyword'), verdict('xpath'))


def coverage_line(lines: list, omitted: int, buckets: int) -> str:
    """The suite's own coverage statement, one line in the header: how many steps it exports and how
    many controls it lists as comments instead. A step is an INDENTED non-comment line (the section
    headers and `*** ... ***` markers are not steps); `demo` counts its keyword form, whose xpath
    form mirrors it line for line."""
    steps = sum(1 for l in lines if l.startswith('    ') and l.strip() and not l.strip().startswith('#'))
    return '# coverage: %d steps, %d controls listed as comments (%d buckets)' % (steps, omitted, buckets)


def cmd_demo(a) -> int:
    review = json.load(open(a.review))
    page = review.get('page') or {}
    url = _page_url(review, a)
    # 2026-09-11 (user: "none of these test files have any of the steps in them"): an UNREVIEWED row whose
    # keyword or xpath form measured VERIFIED-PASS live is exported too -- the live verdict is its review
    candidates = [r for r in review['rows'] if r.get('region') != 'chrome'
                  and r['review']['status'] not in ('not_interactive', 'could_not_map')]
    rows = [r for r in candidates if exported_row(r)]
    # every candidate the live probe could not pass -- shown as a comment beside the steps, never dropped
    omitted = [] if getattr(a, 'hide_omitted', False) else [r for r in candidates if not exported_row(r)]
    buckets = {b['representative']: b for b in (review.get('buckets') or [])}
    per = int(getattr(a, 'per_bucket', None) or 3)
    if getattr(a, 'rows', None):
        # a demo is a story: the user names the rows in the order a person does them
        by_n = {r['n']: r for r in review['rows']}
        rows = [by_n[int(x)] for x in a.rows.split(',') if x.strip()]
        omitted = []                      # a named story carries exactly the rows the user named
    elif not getattr(a, 'all', False) and buckets:
        rows = sample_per_bucket(rows, review, per)
    member_of = bucket_index(review)
    omitted_n = {r['n'] for r in omitted}
    order = {r['n']: i for i, r in enumerate(review['rows'])}
    kw_lines, xp_lines = [], []
    for r in sorted(rows + omitted, key=lambda x: order.get(x['n'], x['n'])):
        label = r.get('label_corrected') or r.get('label') or ''
        b = member_of.get(r['n'])
        if r['n'] in omitted_n:
            line = '    ' + omitted_line(r)
            kw_lines.append(line)
            xp_lines.append(line)
            continue
        shown = label + ('  (%d of %d same-shape controls shown; the others take the same lines with their own label)' % (min(per, b['count']), b['count'])
                         if b and b['count'] > 1 and r['n'] == b['representative'] else '')
        if label.lower().startswith(('save', 'submit', 'delete')):
            k, x = _demo_lines(r)          # nothing is committed in a demo run: the call stays visible, commented
            kw_lines += ['    # %s -- commits; run it yourself after checking the form:' % label] + ['    # ' + l for l in k]
            xp_lines += ['    # %s -- commits; run it yourself after checking the form:' % label] + ['    # ' + l for l in x]
            continue
        if not getattr(a, 'rows', None) and label.lower() in ('cancel', 'close'):
            continue                      # dismisses the form mid-story; name it in --rows to include it
        k, x = _demo_lines(r)
        kw_lines += ['    # %s' % shown] + ['    ' + l for l in k]
        xp_lines += ['    # %s' % shown] + ['    ' + l for l in x]
    hdr = crt_header(review, url)
    settings = hdr[0] if hdr else ['*** Settings ***', 'Library    QWeb', 'Library    QForce', '']
    pre = hdr[1] if hdr else []
    goto = hdr[2] if hdr else '    GoTo    %s' % url
    n_buckets = len({(member_of.get(r['n']) or {}).get('id') for r in rows + omitted} - {None})
    L = settings + [
         coverage_line(kw_lines, len(omitted), n_buckets), '',
         '*** Test Cases ***',
         'Keyword form -- %s' % (page.get('pattern') or review.get('page_key')),
         '    # every action a person takes on this page, resolved by what a person sees (label, heading, index)'] + pre + [
         goto] + kw_lines + ['',
         'XPath form -- %s' % (page.get('pattern') or review.get('page_key')),
         '    # the same actions through the xpath backup: anchored on unique text, never an absolute path'] + pre + [
         goto] + xp_lines + ['']
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.review)), 'demo-steps.robot')
    open(out, 'w').write('\n'.join(L))
    print('wrote %s  (%d controls, two forms; %d listed as comments)'
          % (os.path.relpath(out, _ROOT), len(rows), len(omitted)))
    return 0


def cmd_robot(a) -> int:
    review = json.load(open(a.review))
    page = review.get('page') or {}
    url = _page_url(review, a)
    rows = review['rows']
    wait = next((r.get('label_corrected') or _clean_label(r['label']) for r in rows
                 if (r.get('keyword_corrected') or _kw(r)) == 'TypeText' and r['review']['status'] != 'not_interactive'), 'Home')
    hdr = crt_header(review, url)
    L = (hdr[0] if hdr else ['*** Settings ***', 'Library    QWeb', 'Library    QForce', '']) + [
         '*** Test Cases ***',
         'Review %s' % (page.get('pattern') or review.get('page_key')),
         '    # Inline steps: no custom keywords. %s Generated from %s' % (
             'Authenticates with the suite\'s own JWT variables, then' if hdr else 'Log in first (OpenBrowser + your login), then',
             review.get('capture'))] + (hdr[1] if hdr else []) + [
         hdr[2] if hdr else '    GoTo    %s' % url,
         '    VerifyText    %s    timeout=30' % wait, '']

    def head(r):
        st = r['review']['status']
        note = '; '.join(_short(ch.get('note') or '', 100) for ch in (r['review'].get('changes') or []) if ch.get('note'))
        return '    # row %d  %s  "%s"  [%s]%s' % (r['n'], r.get('family_corrected') or r['element_type'],
                                                 r.get('label_corrected') or r.get('label'), st, ('  ' + note) if note else '')

    chrome = [r for r in rows if r.get('region') == 'chrome']
    if not a.include_chrome:
        rows = [r for r in rows if r.get('region') != 'chrome']
    candidates = list(rows)
    buckets = {b['representative']: b for b in (review.get('buckets') or [])}
    if not getattr(a, 'all', False) and buckets:
        # a few members per bucket, the count beside the first (user 2026-09-10: patterns, not rows;
        # 2026-09-11: "I need to see multiples of the families ... not an entire table worth"); --all for every row
        rows = sample_per_bucket(rows, review, int(getattr(a, 'per_bucket', None) or 3))
    # user, 2026-09-11: a suite must SHOW every control the parser found. Whatever the sample left
    # behind is listed by name with the reason it is not a step, never dropped silently.
    kept = {r['n'] for r in rows}
    omitted = [] if getattr(a, 'hide_omitted', False) else [r for r in candidates if r['n'] not in kept]

    _head0 = head

    member_of = bucket_index(review)
    per = int(getattr(a, 'per_bucket', None) or 3)

    def head(r):                                                       # noqa: F811
        b = member_of.get(r['n'])
        if not b or b['count'] <= 1:
            return _head0(r)
        if r['n'] == b['representative']:
            return _head0(r) + '  -- %d of %d same-shape controls (bucket %s)' % (min(per, b['count']), b['count'], b['id'])
        return _head0(r) + '  -- member of bucket %s' % b['id']
    fills = [r for r in rows if ((r.get('keyword_corrected') or _kw(r)) in ('TypeText', 'PickList', 'DropDown', 'ComboBox', 'ClickCheckbox', 'GetFieldValue', 'VerifyField')
                                 or (r.get('family_corrected') or r.get('element_type')) == 'output_field'
                                 or r.get('call_corrected'))          # a measured call always exports
             and r['review']['status'] not in ('not_interactive', 'could_not_map')]
    clicks = [r for r in rows if (r.get('keyword_corrected') or _kw(r)) in ('ClickText', 'ClickItem')
              and r['review']['status'] not in ('not_interactive', 'could_not_map')]
    rest = [r for r in rows if r not in fills and r not in clicks]
    L.append('    # ===== 1. every control resolves (non-mutating) =====')
    for r in fills + clicks:
        rc = robot_call(r)
        L.append(head(r))
        if r['review']['status'] != 'needs_xpath':      # a label the keyword cannot reach is not verified by label
            L += ['    ' + x for x in rc['verify']]
        L += ['    ' + x for x in rc['xpath'][:1]]
    L.append('')
    L.append('    # ===== 2. fill controls, each read back (nothing is saved) =====')
    for r in fills:
        rc = robot_call(r)
        L.append(head(r))
        if r['review']['status'] == 'needs_xpath' and not r.get('call_corrected'):
            L.append('    # keyword call the parser proposed -- CAUGHT-BUG live (lands on another member); the xpath drives it:')
            L += ['    # ' + x for x in rc['primary']]
            L += ['    ' + x for x in rc['xpath'][1:]]
        else:
            L += ['    ' + x for x in rc['primary']]
    L.append('')
    L.append('    # ===== 3. clicks, each preceded by a fresh GoTo (many of these navigate away) =====')
    for r in clicks:
        rc = robot_call(r)
        L.append(head(r))
        L.append('    GoTo    %s' % url)
        L.append('    VerifyText    %s    timeout=30' % wait)
        label = (r.get('label_corrected') or _clean_label(r.get('label') or '')).lower()
        if label.startswith('save') or label.startswith('submit') or label.startswith('delete'):
            # D13 (user, 2026-09-08): a Save is never clicked by an exported review step -- validation
            # is a screenshot before Save and SOQL after, outside the keyword; the call stays visible.
            L.append('    # commits a record -- run it yourself after checking the form:')
            L += ['    # ' + x for x in rc['primary']]
        else:
            L += ['    ' + x for x in rc['primary']]
    L.append('')
    if chrome and not a.include_chrome:
        L.append('    # ===== %d chrome controls (nav bar, search, global actions) reviewed once for this org; --include-chrome to export them =====' % len(chrome))
        L.append('')
    L.append('    # ===== not exported: containers / hidden / no keyword =====')
    for r in rest:
        L.append(head(r) + '  -- ' + _short(r.get('hint_reason') or (r['review'].get('changes') or [{}])[-1].get('note') or 'no keyword', 110))
    if omitted:
        L.append('')
        L.append('    # ===== %d more controls the parser found, left out of this sample =====' % len(omitted))
        for r in omitted:
            b = member_of.get(r['n'])
            note = None if not live_ok(r) else ('bucket %s sample capped at %d members (--all exports every row)'
                                                % ((b or {}).get('id', '?'), per))
            L.append('    ' + omitted_line(r, note))
    n_buckets = len({(member_of.get(r['n']) or {}).get('id') for r in candidates} - {None})
    L.insert(L.index('*** Test Cases ***'), coverage_line(L, len(omitted), n_buckets))
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.review)), 'review-steps.robot')
    open(out, 'w').write('\n'.join(L) + '\n')
    print('wrote %s  (%d fill, %d click, %d not exported, %d listed as comments, %d chrome %s)'
          % (os.path.relpath(out, _ROOT), len(fills), len(clicks), len(rest), len(omitted), len(chrome),
             'included' if a.include_chrome else 'left out'))
    return 0


# ----------------------------------------------------------------------------- SOQL truth for record pages
def record_truth(org: str, sobject: str, record_id: str, labels: list) -> dict:
    """label -> the value SOQL holds for that field on this record, for the read-mode class
    (VerifyField vs VerifyText). Rendered labels drop the object prefix ('Phone' for 'Account
    Phone') and lookups render the related Name; addresses are compound and left COULD-NOT-CHECK."""
    env = dict(os.environ, FORCE_COLOR='0', NO_COLOR='1')
    def sf(args):
        p = subprocess.run(['sf'] + args + ['--json'], capture_output=True, text=True, env=env, timeout=120)
        t = p.stdout
        return json.loads(t[t.index('{'):]) if '{' in t else {}
    desc = (sf(['sobject', 'describe', '-o', org, '-s', sobject]).get('result') or {}).get('fields') or []
    by_label = {f['label']: f for f in desc}
    def field_for(label):
        bare = re.sub(r'^%s\s+' % re.escape(sobject), '', label)      # 'Account Owner' -> 'Owner'
        for cand in (label, '%s %s' % (sobject, label), '%s ID' % label, '%s %s ID' % (sobject, label),
                     bare, '%s ID' % bare):
            if cand in by_label:
                return by_label[cand]
        return None
    picks, out, pick_labels = {}, {}, {}
    for lab in labels:
        f = field_for(lab)
        if not f:
            out[lab] = None
            continue
        if f['type'] == 'reference' and f.get('relationshipName'):
            picks[lab] = '%s.Name' % f['relationshipName']
        elif f['type'] == 'address':
            out[lab] = None          # compound: rendered as several lines
        else:
            picks[lab] = f['name']
            if f['type'] in ('picklist', 'multipicklist') and f.get('picklistValues'):
                # 2026-09-11 (hc-assessment-task audit): the page renders the picklist LABEL ('Inspection
                # Checklist'), SOQL returns the API VALUE ('InspectionChecklist'); the truth is the label
                pick_labels[lab] = {v.get('value'): v.get('label') for v in f['picklistValues'] if isinstance(v, dict)}
    if picks:
        q = 'SELECT %s FROM %s WHERE Id = \'%s\'' % (', '.join(sorted(set(picks.values()))), sobject, record_id)
        recs = (sf(['data', 'query', '-o', org, '-q', q]).get('result') or {}).get('records') or []
        rec = recs[0] if recs else {}
        for lab, path in picks.items():
            if not recs:
                out[lab] = None      # the record is not in this org: no truth, COULD-NOT-CHECK -- never a blank to compare against
                continue
            v = rec
            for part in path.split('.'):
                v = (v or {}).get(part) if isinstance(v, dict) else None
            if lab in pick_labels and isinstance(v, str) and v:
                v = ';'.join(pick_labels[lab].get(x, x) for x in v.split(';'))
            out[lab] = '' if v is None else v          # mapped and empty is a real value: blank
        if not recs:
            out['__record__'] = 'not found: %s %s in %s' % (sobject, record_id, org)
    out['__paths__'] = picks
    return out


# ----------------------------------------------------------------------------- live (b) + keyword
_LIVE_SCRIPT = r'''
import json
from QWeb.keywords.element import get_webelement
rows = json.loads(%(rows)r)
out = []
def same(a, b):
    try:
        return bool(drv.execute_script("return arguments[0]===arguments[1] || arguments[0].contains(arguments[1]) || arguments[1].contains(arguments[0]);", a, b))
    except Exception:
        return False
def els(xp):
    try:
        r = get_webelement(xp, timeout=2)
    except Exception as exc:
        return None, "%%s: %%s" %% (type(exc).__name__, str(exc)[:160])
    if r is None:
        return [], None
    return (r if isinstance(r, list) else [r]), None
for r in rows:
    rec = {"n": r["n"]}
    ident, err = els(r["identity_xpath"]) if r.get("identity_xpath") else (None, "no identity xpath")
    if not ident or len(ident) != 1:
        try:
            in_dom = len(drv.find_elements("xpath", r["identity_xpath"])) if r.get("identity_xpath") else None
        except Exception:
            in_dom = None
        rec["identity"] = "COULD-NOT-CHECK: identity xpath matched %%s QWeb-visible live, %%s in the DOM (%%s)" %% (
            None if ident is None else len(ident), in_dom, err)
        rec["xpath"] = {"verdict": "COULD-NOT-CHECK", "detail": rec["identity"]}
        rec["keyword"] = {"verdict": "COULD-NOT-CHECK", "detail": rec["identity"]}
        out.append(rec); continue
    target = ident[0]
    # (b) the ladder xpath, executed by QWeb
    if r.get("xpath"):
        found, err = els(r["xpath"])
        rec["xpath_executed"] = "QWeb.keywords.element.get_webelement(%%r, timeout=2)" %% r["xpath"]
        if found is None:
            rec["xpath"] = {"verdict": "COULD-NOT-CHECK", "detail": err}
        elif len(found) != 1:
            rec["xpath"] = {"verdict": "CAUGHT-BUG", "detail": "xpath matched %%d elements live" %% len(found)}
        elif same(found[0], target):
            rec["xpath"] = {"verdict": "VERIFIED-PASS", "detail": "1 match, same node as the row"}
        else:
            rec["xpath"] = {"verdict": "CAUGHT-BUG", "detail": "1 match but a DIFFERENT node than the row"}
    else:
        rec["xpath"] = {"verdict": "COULD-NOT-CHECK", "detail": "no xpath formed"}
    # the keyword column: does the hinted keyword's own resolution land on this node
    kw = r.get("keyword"); label = r.get("label_clean") or ""
    try:
        if not kw or not label:
            rec["keyword"] = {"verdict": "COULD-NOT-CHECK", "detail": "no keyword or no label"}
        elif kw in ("TypeText",):
            # the SAME resolver + arguments type_text_clearing hands to QWeb's type_text; a chosen
            # text anchor WINS over the index (disambiguation_args.to_call_kwargs)
            from QWeb.internal import input_ as QI
            _a = r.get("anchor") or (str(r["index"]) if r.get("index") else "1")
            rec["executed"] = "QWeb.internal.input_.get_input_elements_from_all_documents(%%r, anchor=%%r, timeout=2, index=1)  # what TypeText/type_text_clearing resolves" %% (label, _a)
            el = QI.get_input_elements_from_all_documents(label, _a, timeout=2, index=1)
            rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "QWeb's input resolver (TypeText%%s) landed on this node" %% (" anchor=%%s" %% r["index"] if r.get("index") else "")} if same(el, target)
                              else {"verdict": "CAUGHT-BUG", "detail": "QWeb's input resolver (TypeText%%s) landed on a DIFFERENT node -- index mode did not reach this member" %% (" anchor=%%s" %% r["index"] if r.get("index") else "")})
        elif kw == "ClickCheckbox":
            from QWeb.internal import checkbox as QC
            _a = r.get("anchor") or (str(r["index"]) if r.get("index") else "1")
            rec["executed"] = "QWeb.internal.checkbox.get_checkbox_elements_from_all_documents(%%r, anchor=%%r, index=1)  # what ClickCheckbox resolves" %% (label, _a)
            cb, _loc = QC.get_checkbox_elements_from_all_documents(label, _a, 1)
            rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "QWeb's checkbox resolver landed on this node"} if cb is not None and same(cb, target)
                              else {"verdict": "CAUGHT-BUG", "detail": "QWeb's checkbox resolver landed on %%s" %% ("nothing" if cb is None else "a DIFFERENT node")})
        elif kw in ("GetFieldValue", "VerifyField"):
            truth = r.get("truth")
            rec["executed"] = "qforce_lite.get_field_value(%%r)  == SOQL value %%r" %% (label, truth)
            got = ql.get_field_value(label)
            if truth is None:
                rec["keyword"] = {"verdict": "COULD-NOT-CHECK", "detail": "read back %%r; no SOQL truth for this label (compound or unmapped)" %% (str(got)[:60])}
            else:
                try:
                    import confirm as _cf
                    eq = _cf.lenient_equal(str(got or ""), str(truth))
                except Exception:
                    eq = (str(got or "").strip() == str(truth).strip())
                # a picklist/currency renders "CODE - Label" for an API value of CODE (USD - U.S. Dollar)
                if not eq and str(got or "").strip().startswith(str(truth).strip() + " - "):
                    eq = True
                rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "read back %%r == SOQL %%r" %% (str(got)[:40], str(truth)[:40])} if eq
                                  else {"verdict": "CAUGHT-BUG", "detail": "read back %%r != SOQL %%r" %% (str(got)[:40], str(truth)[:40])})
        elif kw == "DropDown":
            from QWeb.internal import dropdown as QD
            _a = r.get("anchor") or (str(r["index"]) if r.get("index") else "1")
            rec["executed"] = "QWeb.internal.dropdown.get_dd_elements_from_all_documents(%%r, anchor=%%r, index=1)  # what DropDown resolves" %% (label, _a)
            sel = QD.get_dd_elements_from_all_documents(label, _a, 1)
            el = getattr(sel, "_el", None) or getattr(sel, "wrapped_element", None) or sel
            rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "QWeb's dropdown resolver landed on this <select>"} if same(el, target)
                              else {"verdict": "CAUGHT-BUG", "detail": "QWeb's dropdown resolver landed on a DIFFERENT node"})
        elif kw == "PickList" and (r.get("tag") == "select"):
            rec["executed"] = "qforce_lite._resolve_native_select(%%r)  # pick_list's native <select> branch" %% label
            el = ql._resolve_native_select(label)
            rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "pick_list's native <select> resolver landed on this node"} if el is not None and same(el, target)
                              else {"verdict": "CAUGHT-BUG", "detail": "pick_list's native <select> resolver landed on %%s" %% ("nothing" if el is None else "a DIFFERENT node")})
        elif kw == "ComboBox":
            rec["keyword"] = {"verdict": "COULD-NOT-CHECK", "detail": "combo_box has no resolve-only entry point; the drive step is the proof"}
        elif kw in ("PickList",):
            txp = ql._picklist_trigger_xpath_for(label, r.get("index") or 1)
            rec["executed"] = "QWeb.keywords.element.get_webelement(%%r)  # pick_list's own trigger xpath for label %%r" %% (txp, label)
            found, err = els(txp)
            if found is None:
                rec["keyword"] = {"verdict": "CAUGHT-BUG", "detail": "pick_list trigger xpath found nothing: %%s" %% err}
            elif len(found) != 1:
                rec["keyword"] = {"verdict": "CAUGHT-BUG", "detail": "pick_list trigger xpath matched %%d" %% len(found)}
            else:
                rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "pick_list's own trigger xpath landed on this node"} if same(found[0], target)
                                  else {"verdict": "CAUGHT-BUG", "detail": "pick_list's trigger xpath landed on a DIFFERENT node"})
        else:
            etype = "item" if kw == "ClickItem" else "text"
            kwargs = {"tag": r["tag"]} if etype == "item" and r.get("tag") else {}
            loc = r.get("locator") or label
            _a = r.get("anchor") or str(r.get("index") or 1)
            rec["executed"] = "QWeb.keywords.element.get_webelement(%%r, anchor=%%r, element_type=%%r, timeout=2%%s)  # %%s resolution" %% (
                loc, _a, etype, "".join(", %%s=%%r" %% kv for kv in kwargs.items()), kw)
            kwargs["partial_match"] = False
            el = get_webelement(loc, anchor=_a, element_type=etype, timeout=2, **kwargs)
            rec["keyword"] = ({"verdict": "VERIFIED-PASS", "detail": "%%s resolution landed on this node" %% kw} if el is not None and same(el, target)
                              else {"verdict": "CAUGHT-BUG", "detail": "%%s resolution landed on %%s" %% (kw, "nothing" if el is None else "a DIFFERENT node")})
    except Exception as exc:
        rec["keyword"] = {"verdict": "CAUGHT-BUG", "detail": "%%s: %%s" %% (type(exc).__name__, str(exc)[:200])}
    out.append(rec)
result = out
'''


def capture_header(path: str) -> dict:
    """title / path / host the capture serializer stamped in its header comments."""
    head = open(path, errors='replace').read(4000)
    out = {}
    for key in ('title', 'path', 'host'):
        m = re.search(r'<!--\s*%s:\s*(.*?)\s*-->' % key, head)
        if m:
            out[key] = m.group(1).strip()
    # THE STATE STAMP (user, 2026-09-18) -- one reader, in pom_asset, for the one line
    # cdp_capture writes. A review row that does not know which state its control was seen in
    # cannot write that state back, which is why `cicd-demo`'s Revenue Cloud Settings modal had
    # 133 VERIFIED-PASS controls and zero states.
    out.update(PA.state_stamp(head))
    return out


def page_state_check(org: str, review: dict, slot: str | None = None) -> tuple[bool, str]:
    """2026-09-11 (user: 'the second time I've seen a mistake with the navigation'): live/drive bind to
    whatever page the holder shows. Compare the capture's own header (title, path) with the holder's
    live document.title / location.pathname; a mismatch is CAUGHT-BUG on the run, never a silent
    COULD-NOT-CHECK. Six console captures had been the console Home tab; a table story was driven on
    the record tab while the captured grid lived on the console Home."""
    hdr = capture_header(os.path.join(_ROOT, review['capture']))
    # up.py --op eval takes an EXPRESSION (a leading `return` is a JS_ERROR) and answers {"result": {"value": ...}};
    # the first cut of this guard sent `return ...` and read "result" as a string, so it refused every page as
    # COULD-NOT-CHECK -- a guard firing for the wrong reason (17/17 refused, 2026-09-11 07:20)
    cmd = ['python3', os.path.join(_ROOT, 'tools', 'interop', 'up.py'), org, '--op', 'eval',
           '--js-file', 'document.title + "|" + location.pathname', '--json']
    if slot:
        cmd += ['--slot', slot]
    want_title, want_path = hdr.get('title', ''), hdr.get('path', '')
    # a console app prefixes /lightning/app/<id>; the record part after /r/ must agree; a query string is not
    # page state (the New Contact capture carried ?count=1, the goto did not -- refused 2026-09-11)
    tail = lambda s: (s.split('/r/', 1)[-1] if '/r/' in s else s).split('?', 1)[0].rstrip('/')
    # Lightning sets document.title LATE: right after a goto it still reads 'Lightning Experience' (fsc-action-plan,
    # 2026-09-11, refused on a page that was the right one 2 s later). Poll like the drive script does, 30 s cap.
    t0 = time.time()
    live_title = live_path = ''
    value = None
    while True:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        try:
            res = json.loads(p.stdout).get('result')
            value = res.get('value') if isinstance(res, dict) else res
        except Exception:
            value = None
        if isinstance(value, str) and '|' in value:
            live_title, _, live_path = value.rpartition('|')   # a Lightning title is "Name | Object | Salesforce"; the path holds no '|'
            same_title = (not want_title) or want_title.strip() == live_title.strip()
            same_path = (not want_path) or tail(want_path) == tail(live_path)
            if same_title and same_path:
                return True, 'capture title %r path %r | live title %r path %r (after %.1f s)' % (want_title, want_path, live_title, live_path, time.time() - t0), live_path
        if time.time() - t0 > 30:
            break
        time.sleep(2)
    if not isinstance(value, str) or '|' not in value:
        return False, 'COULD-NOT-CHECK: the holder returned no title (%s)' % _short(p.stdout[-200:] + p.stderr[-200:], 160), ''
    detail = 'capture title %r path %r | live title %r path %r (after 30 s)' % (want_title, want_path, live_title, live_path)
    return False, 'CAUGHT-BUG: the holder is not on the captured page state -- ' + detail, live_path


def cmd_live(a) -> int:
    review = json.load(open(a.review))
    ok, detail, live_path = page_state_check(a.org, review, a.slot)
    print('page state:', 'VERIFIED-PASS' if ok else detail)
    if not ok and not getattr(a, 'force_state', False):
        print('refusing to probe a different page state (--force-state to override); goto the captured path and retry')
        return 2
    payload = []
    page = review.get('page') or {}
    truth = {}
    # the SOQL truth is for the record the HOLDER shows (the guard proved it is the captured one, or --force-state
    # said another org's record is intended); a previous session's url or the capture path are the fallbacks.
    # 2026-09-11: the first cross-org probe queried slockard's record Id on dev1 and scored 8 rendered values
    # as CAUGHT-BUG against an empty truth
    m = (re.search(r'/r/([A-Za-z0-9_]+)/([a-zA-Z0-9]{15,18})/view', live_path or '')
         or re.search(r'/lightning/r/([A-Za-z0-9_]+)/([a-zA-Z0-9]{15,18})/view', (review.get('live_session') or {}).get('url') or ''))
    cap_url = re.search(r'<!--\s*path:\s*(/lightning/r/([A-Za-z0-9_]+)/([a-zA-Z0-9]{15,18})/view)', open(os.path.join(_ROOT, review['capture']), errors='replace').read(4000))
    sobject, rid = (m.group(1), m.group(2)) if m else ((cap_url.group(2), cap_url.group(3)) if cap_url else (None, None))
    if sobject and rid:
        labels = [(r.get('label_corrected') or _clean_label(r.get('label') or '')) for r in review['rows'] if r.get('element_type') == 'output_field']
        try:
            truth = record_truth(a.org, sobject, rid, labels)
            print('SOQL truth for %s %s: %d of %d field labels mapped' % (sobject, rid, sum(1 for v in truth.values() if v is not None), len(labels)))
        except Exception as exc:
            print('COULD-NOT-CHECK: SOQL truth unavailable:', exc)
    for r in review['rows']:
        if not r.get('node_found'):
            continue
        c0 = (r.get('calls') or [{}])[0]
        item = {'n': r['n'], 'identity_xpath': r.get('identity_xpath'),
                'xpath': r.get('xpath_corrected') or (r.get('xpath') or {}).get('value'),
                'keyword': r.get('keyword_corrected') or _kw(r) or None,
                'label_clean': r.get('label_corrected') or _clean_label(r.get('label') or ''),
                'locator': ((r.get('attrs') or {}).get(r['attribute_corrected']) if r.get('attribute_corrected')
                            else (c0.get('locator') if c0.get('keyword') == 'ClickItem' else None)),
                'index': r.get('index_corrected') if 'index_corrected' in r else r.get('index'),
                'anchor': r.get('anchor_corrected'),
                'truth': truth.get(r.get('label_corrected') or _clean_label(r.get('label') or '')) if r.get('element_type') == 'output_field' else None,
                'tag': r.get('tag_corrected') or c0.get('tag') or r.get('tag')}
        # 2026-09-11 (eleven audits): a row stamped with a VERIFIED library pattern is probed with the pattern's
        # first line (ClickItem NewEvent tag=button), never with the parser's own ClickText that the pattern
        # exists to replace -- `robot` and `drive` already export the recipe; `live` measured the wrong form
        entry = _pattern_entry(r) if not (r.get('call_corrected') or r.get('keyword_corrected')) else None
        if entry:
            try:
                first = (PL.recipe(entry, r, probe_value(r))[0] or [''])[0]
                pk = parse_robot_line(first) if first else None      # (keyword, positional args, kwargs)
            except Exception:
                pk = None
            if pk and pk[0] in ('ClickItem', 'ClickText', 'ClickElement', 'TypeText', 'DropDown', 'ClickCheckbox'):
                args = list(pk[1] or [])
                kw = dict(pk[2] or {})
                item['keyword'] = pk[0]
                if args:
                    item['locator' if pk[0] in ('ClickItem', 'ClickElement') else 'label_clean'] = args[0]
                if kw.get('tag'):
                    item['tag'] = kw['tag']
                if kw.get('anchor'):
                    item['anchor'] = kw['anchor']
                item['pattern_probe'] = first
        payload.append(item)
    if getattr(a, 'rows', None):
        want = {int(x) for x in a.rows.split(',') if x.strip()}
        payload = [x for x in payload if x['n'] in want]
    elif not getattr(a, 'all', False):
        # one representative per bucket (user, 2026-09-10: patterns, not every row); --all for every row
        reps = {r['n'] for r in PL.representatives(review['rows'])} | {r['n'] for r in review['rows'] if r.get('call_corrected')}
        payload = [x for x in payload if x['n'] in reps]
        print('probing %d representative row(s) of %d buckets (--all for every row)' % (len(payload), len(review.get('buckets') or PL.bucket(review['rows']))))
    # the holder finishes one --op within 120 s or drops the result (938 rows on the Data Template
    # detail page, 2026-09-10): probe in batches, each its own op, and never lose a finished batch
    batch = max(1, int(getattr(a, 'batch', None) or 40))
    sp = os.path.join(os.path.dirname(os.path.abspath(a.review)), '.live_probe.py')
    cmd0 = [sys.executable if 'venv' not in sys.executable else 'python3',
            os.path.join(_ROOT, 'tools', 'interop', 'up.py'), a.org, '--op', 'py', '--py-file', sp, '--json']
    if a.slot:
        cmd0 += ['--slot', a.slot]
    rows_out, inner, res = [], {}, {}
    for i in range(0, len(payload), batch):
        chunk = payload[i:i + batch]
        open(sp, 'w').write(_LIVE_SCRIPT % {'rows': json.dumps(chunk)})
        got = None
        for attempt in range(6):                     # a busy holder (an earlier op still running) is waited for, never re-driven
            p = subprocess.run(cmd0, capture_output=True, text=True, timeout=600)
            m = re.search(r'\{.*\}\s*$', p.stdout, re.S)
            res = json.loads(m.group(0)) if m else {'ok': False, 'error': (p.stdout[-800:] + p.stderr[-400:])}
            inner = (res.get('result') or {})
            got = inner.get('result') if isinstance(inner, dict) else None
            if got or 'busy' not in json.dumps(res):
                break
            time.sleep(20)
        if got:
            rows_out += got
            print('live batch %d-%d: %d rows' % (i + 1, i + len(chunk), len(got)))
        else:
            err = _short(json.dumps(res.get('error') or res)[:400], 300)
            print('COULD-NOT-CHECK: holder error on batch %d-%d: %s' % (i + 1, i + len(chunk), err))
            rows_out += [{'n': x['n'], 'keyword': {'verdict': 'COULD-NOT-CHECK', 'detail': 'holder error: ' + err},
                          'xpath': {'verdict': 'COULD-NOT-CHECK', 'detail': 'holder error: ' + err}} for x in chunk]
    try:
        os.remove(sp)
    except OSError:
        pass
    if not rows_out:
        print('COULD-NOT-CHECK: no rows probed (nothing in --rows, or no node found)')
        return 2
    by_n = {x['n']: x for x in rows_out}
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    for r in review['rows']:
        x = by_n.get(r['n'])
        if not x:
            continue
        r['live'] = {'keyword': dict(x.get('keyword') or {}, at=stamp, executed=x.get('executed')),
                     'xpath': dict(x.get('xpath') or {}, at=stamp, executed=x.get('xpath_executed'))}
        if r.get('element_type') == 'output_field':
            _lab = r.get('label_corrected') or _clean_label(r.get('label') or '')
            r['truth'] = truth.get(_lab)
            r['truth_path'] = (truth.get('__paths__') or {}).get(_lab)
        (r.get('xpath') or {})['live'] = r['live']['xpath']
    review['live_at'] = stamp
    review['live_session'] = {'url': inner.get('url'), 'session': res.get('session'),
                              'elapsed_ms': inner.get('elapsed_ms')}
    # a representative's verdict applies to its bucket: members carry it marked as inherited, and a
    # member probed on its own keeps its own verdict
    rows_by_n = {r['n']: r for r in review['rows']}
    for b in review.get('buckets') or []:
        rep = rows_by_n.get(b['representative'])
        if not rep or rep['n'] not in by_n or not rep.get('live'):
            continue
        for n in b['members']:
            m = rows_by_n.get(n)
            if m is None or n == rep['n'] or n in by_n:
                continue
            m['live'] = {k: dict(v or {}, inherited_from=rep['n'], detail='inherited from representative row %d: %s' % (rep['n'], (v or {}).get('detail') or ''))
                         for k, v in rep['live'].items() if k in ('keyword', 'xpath')}
            # 2026-09-11 (hc-um-case audit): a VALUE read-back is per label -- "read back 'Medium' == SOQL" on the
            # Priority row was being copied onto Account, Owner, every detail field in the bucket, a manufactured
            # proof on 40 of 41 output fields. A member inherits the representative's RESOLUTION shape only; its
            # own value is COULD-NOT-CHECK until its own row is probed.
            kw = m['live'].get('keyword') or {}
            if 'read back' in (kw.get('detail') or ''):
                m['live']['keyword'] = dict(kw, verdict='COULD-NOT-CHECK',
                                            detail='inherited from representative row %d: resolution shape only -- a value read-back is per label and is never inherited (probe this row with --rows %d)' % (rep['n'], n))
            (m.get('xpath') or {})['live'] = m['live'].get('xpath')
    json.dump(review, open(a.review, 'w'), indent=1)
    c_kw = collections.Counter(((r.get('live') or {}).get('keyword') or {}).get('verdict') for r in review['rows'] if r.get('live'))
    c_xp = collections.Counter(((r.get('live') or {}).get('xpath') or {}).get('verdict') for r in review['rows'] if r.get('live'))
    print('live keyword:', dict(c_kw))
    print('live xpath (b):', dict(c_xp))
    if res.get('session') == 'healed':
        print('session: healed during the probe -- treat rows driven before the heal as COULD-NOT-CHECK')
    _render(review, os.path.join(os.path.dirname(os.path.abspath(a.review)), 'review.html'))
    return 0


# ----------------------------------------------------------------------------- correct / accept
def cmd_correct(a) -> int:
    review = json.load(open(a.review))
    row = next((r for r in review['rows'] if r['n'] == a.row), None)
    if row is None:
        print('no row', a.row)
        return 2
    col = a.column
    c0 = (row.get('calls') or [{}])[0]
    frm = {'label': row.get('label'), 'family': row.get('element_type'), 'keyword': _kw(row),
           'index': row.get('index'), 'anchor': None, 'tag': c0.get('tag') or row.get('tag'),
           'attribute': next((k for k, v in (row.get('attrs') or {}).items() if v == c0.get('locator')), None),
           'call': robot_call(row)['primary'][0] if robot_call(row)['primary'] else None,
           'xpath': (row.get('xpath') or {}).get('value')}.get(col)
    change = {'column': col, 'from': frm, 'to': a.to, 'raw_had': a.raw_had, 'note': a.note,
              'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    row['review']['changes'].append(change)
    if col == 'status':
        if a.to not in ('accepted', 'corrected', 'unreviewed', 'not_interactive', 'needs_xpath', 'could_not_map'):
            print('status must be one of accepted|corrected|unreviewed|not_interactive|needs_xpath|could_not_map')
            return 2
        row['review']['status'] = a.to          # the deliberate way to lift a flag
    elif col in ('not_interactive', 'needs_xpath', 'could_not_map'):
        row['review']['status'] = col
    else:
        if row['review']['status'] not in ('not_interactive', 'needs_xpath', 'could_not_map'):
            row['review']['status'] = 'corrected'  # a later column edit never lifts a status flag
        # the value is stored whatever the status is (a flagged row can still carry a measured call)
        if col == 'label':
            row['label_corrected'] = a.to
        elif col == 'family':
            row['family_corrected'] = a.to
        elif col == 'keyword':
            row['keyword_corrected'] = a.to
        elif col == 'index':
            row['index_corrected'] = int(a.to) if str(a.to).isdigit() else None
        elif col == 'anchor':
            row['anchor_corrected'] = a.to
        elif col == 'tag':
            row['tag_corrected'] = a.to
        elif col == 'attribute':
            if a.to not in (row.get('attrs') or {}):
                print('row %d has no attribute %r (has %s)' % (a.row, a.to, sorted((row.get('attrs') or {}).keys())))
                return 2
            row['attribute_corrected'] = a.to
        elif col == 'call':
            row['call_corrected'] = a.to
        elif col == 'xpath_call':
            # the whole xpath-form call when it differs from the keyword form by more than the first
            # locator (a lookup: type by xpath, pick the option by a host-scoped xpath, verify the pill)
            row['xpath_call_corrected'] = a.to
        elif col == 'xpath':
            row['xpath_corrected'] = a.to
            cap = Capture(os.path.join(_ROOT, review['capture']))
            n = cap.count(a.to)
            row['xpath']['corrected'] = {'value': a.to, 'unique_in_capture': n == 1,
                                         'count_in_capture': n, 'generated_values': generated_values_in(a.to)}
    json.dump(review, open(a.review, 'w'), indent=1)
    print('row %d %s: %s -> %s%s' % (a.row, col, frm, a.to, (' (raw had %s)' % a.raw_had) if a.raw_had else ''))
    if getattr(a, 'bucket', False) and col != 'label':
        # the correction applies to every same-shape control (user, 2026-09-10); a label is the one
        # parameter that differs per member, so it is never bucket-applied
        b = next((b for b in (review.get('buckets') or []) if a.row in b['members']), None)
        others = [n for n in (b['members'] if b else []) if n != a.row]
        for n in others:
            sub = argparse.Namespace(**{**vars(a), 'row': n, 'bucket': False,
                                        'note': ((a.note or '') + ' [bucket %s, via row %d]' % (b['id'], a.row)).strip()})
            cmd_correct(sub)
        print('applied to %d other member(s) of bucket %s' % (len(others), b['id'] if b else '?'))
    return 0


def cmd_add(a) -> int:
    """A row for a control the parser produced NOTHING for (Entitled Services, an SLDS dueling
    list, 2026-09-10). It carries the label, family, the measured call and the xpath the reviewer
    proved live; it exports, scores as `corrected` and writes back like any other row."""
    review = json.load(open(a.review))
    n = max((r['n'] for r in review['rows']), default=-1) + 1
    xp = a.xpath or ''
    row = {'n': n, 'element_type': a.family, 'label': a.label, 'label_source': 'reviewer', 'tag': a.tag,
           'attrs': {}, 'container': '', 'hint_fill': None, 'hint_verify': None, 'hint_click': None,
           'hint_reason': 'ADDED BY THE REVIEWER: the parser produced no row for this control', 'calls': [],
           'group_size': None, 'index': None, 'anchor_candidates': [], 'disambiguation_status': None,
           'confidence': 'verified', 'node_found': False, 'raw': a.raw or '', 'raw_context': [],
           'identity_xpath': None, 'region': 'page', 'label_guess': None,
           'xpath': {'value': xp or None, 'rung': 'reviewer', 'unique_in_capture': None, 'count_in_capture': None,
                     'generated_values': generated_values_in(xp) if xp else [], 'live': None, 'cross_org': None},
           'live': {'keyword': None, 'xpath': None},
           'review': {'status': 'corrected', 'changes': [{'column': 'added', 'from': None, 'to': a.label,
                      'raw_had': a.raw_had, 'note': a.note, 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}]},
           'keyword_corrected': a.keyword, 'call_corrected': a.call, 'xpath_corrected': xp or None}
    review['rows'].append(row)
    json.dump(review, open(a.review, 'w'), indent=1)
    print('added row %d %s "%s" (%s)' % (n, a.family, a.label, a.keyword))
    return 0


def cmd_accept(a) -> int:
    review = json.load(open(a.review))
    if a.rows == 'all':
        pick = [r for r in review['rows'] if r['review']['status'] == 'unreviewed']
    elif a.rows == 'live-pass':
        pick = [r for r in review['rows'] if r['review']['status'] == 'unreviewed'
                and ((r.get('live') or {}).get('keyword') or {}).get('verdict') == 'VERIFIED-PASS']
    else:
        want = {int(x) for x in a.rows.split(',') if x.strip()}
        pick = [r for r in review['rows'] if r['n'] in want]
    for r in pick:
        r['review']['status'] = 'accepted'
        r['review']['accepted_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        if a.note:
            r['review']['note'] = a.note
    json.dump(review, open(a.review, 'w'), indent=1)
    print('accepted', len(pick), 'rows')
    return 0


# ----------------------------------------------------------------------------- write-back
def cmd_writeback(a) -> int:
    review = json.load(open(a.review))
    cap_path = os.path.join(_ROOT, review['capture'])
    pk = PA.page_key_for(cap_path, review.get('org'))
    if not pk:
        print('COULD-NOT-CHECK: no page key for', review['capture'])
        return 2
    # BUG (ea1701e23a, 2026-09-18): the STORE is isolated by --state-root, the RENDERED DOC was
    # not -- `Store(state_root=...)` alone leaves `docs_root` at its default (os.getcwd()), so
    # `store.render()` below re-rendered docs/org-map/<alias>-pom.md from whatever (possibly empty)
    # tmp state root a test gave it, clobbering the committed doc down to a few lines. A state root
    # now carries its render beside it; the default path (no --state-root) is unchanged.
    store = Store(state_root=a.state_root, docs_root=a.state_root)
    if a.state_root:
        pk = PA._repartition(store, pk)
    rec = store._open(pk)
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    rec.setdefault('reviews', []).append({'review': review.get('capture'), 'at': stamp,
                                          'rows': len(review['rows'])})
    # THE STATE STAMP, read off the review (which read it off the capture header). A review built
    # before 2026-09-18 carries no `state_stamp`; it is then re-read from the capture on disk, and
    # failing that it is the default state with an unknown opener -- the truth about it.
    hdr_stamp = review.get('state_stamp') or PA.state_stamp(
        open(cap_path, errors='replace').read(4000) if os.path.exists(cap_path) else '')
    written = 0
    by_state: dict = {}
    for r in review['rows']:
        st = r['review']['status']
        if st == 'unreviewed':
            continue
        family = r.get('family_corrected') or r.get('element_type')
        label = r.get('label_corrected') or r.get('label') or ''
        eid = element_id(family, label, r.get('container'), r.get('attrs'))
        el = rec['elements'].setdefault(eid, {})
        # same fold as pom_asset: a reviewed control absorbs any `capture-stamp` placeholder
        # another page's state stamp left for it, so one control is never two records
        STORE_MOD.absorb_stamp_placeholder(rec, eid, label)
        el.update({
            'family': family, 'label': label, 'container': r.get('container'),
            'attrs': stable_attrs(r.get('attrs')), 'tag': r.get('tag'),
            'source': 'reviewed',
            'evidence': sorted(set((el.get('evidence') or []) + [review['capture']])),
            'verdict': ('VERIFIED-PASS' if st in ('accepted', 'corrected') or (st == 'needs_xpath' and (
                r.get('xpath_corrected') or ((r.get('xpath') or {}).get('live') or {}).get('verdict') == 'VERIFIED-PASS'))
                        else 'COULD-NOT-CHECK'),
            'verdict_by': 'review',
            'verdict_date': stamp,
            'review': {'status': st, 'changes': r['review'].get('changes') or [],
                       'row': r['n'], 'live': r.get('live')},
            'interactive': st not in ('not_interactive',),
            'last_seen': stamp,
            'n_seen': (el.get('n_seen') or 0) + 1,
        })
        el.setdefault('effects', {})
        ladder = list(el.get('ladder') or [])
        if st in ('accepted', 'corrected'):
            kw = r.get('keyword_corrected') or _kw(r)
            idx = r.get('index_corrected') if 'index_corrected' in r else r.get('index')
            if kw:
                rung = next((x for x in ladder if x.get('kw') == kw and (x.get('args') or [None])[0] == label), None)
                if rung is None:
                    rung = {'kw': kw, 'args': [label], 'kwargs': {'index': idx} if idx else {},
                            'why': 'reviewed %s' % stamp, 'read_back': PA.read_back_for(kw, {'label': label}),
                            'anchor': None, 'anchor_candidates': r.get('anchor_candidates') or [],
                            'score': None, 'n_failed': 0, 'n_unverified': 0, 'failure_signal': None,
                            'origin': 'review', 'rank': -2}
                    ladder.insert(0, rung)
                rung.update({'n_verified': max(1, rung.get('n_verified') or 0), 'confidence': 'verified',
                             'last_verdict': 'VERIFIED-PASS', 'last_seen': stamp, 'verdict_pending': False,
                             'kwargs': {'index': idx} if idx else {}})
        xp = r.get('xpath_corrected') or ((r.get('xpath') or {}).get('value')
                                          if ((r.get('xpath') or {}).get('live') or {}).get('verdict') == 'VERIFIED-PASS' else None)
        if st == 'needs_xpath':
            kw = _kw(r)
            for x in ladder:
                if x.get('kw') == kw and not x.get('xpath_backup'):
                    x.update({'n_verified': 0, 'n_failed': (x.get('n_failed') or 0) + 1, 'last_verdict': 'CAUGHT-BUG',
                              'last_seen': stamp, 'confidence': 'unverified',
                              'failure_signal': 'review: keyword did not reach this member live'})
        if xp and st in ('accepted', 'corrected', 'needs_xpath'):
            rung = next((x for x in ladder if x.get('xpath_backup') and (x.get('args') or [None])[0] == xp), None)
            if rung is None:
                rung = {'kw': 'ClickElement', 'args': [xp], 'kwargs': {}, 'why': 'xpath backup (reviewed)',
                        'read_back': None, 'anchor': None, 'score': None, 'n_verified': 1, 'n_failed': 0,
                        'n_unverified': 0, 'last_verdict': 'VERIFIED-PASS', 'last_seen': stamp,
                        'confidence': 'verified', 'origin': 'review', 'rank': 9, 'xpath_backup': True}
                ladder.append(rung)
            if st == 'needs_xpath':
                rung['rank'] = -3
                ladder.remove(rung)
                ladder.insert(0, rung)
        el['ladder'] = ladder
        by_state.setdefault(r.get('state') or hdr_stamp.get('state') or 'default', []).append(eid)
        written += 1
    rec['last_seen'] = stamp
    # One call per state seen in this review, through the SAME writer pom_asset.build_record uses,
    # so a review and a capture can never disagree about how a state is recorded. A routed modal's
    # controls stay flat on the modal's own key and the LINK is written on the host -- never a
    # state named after the modal's title on the modal's own page key with `entered_via` empty,
    # which is the defect the 20:08 audit caught the live streams producing.
    stamp_results = []
    for state_name, eids in sorted(by_state.items()):
        stamp_results.append(STORE_MOD.apply_capture_stamp(
            store, rec, eids, state=state_name, entered_via=hdr_stamp.get('entered_via'),
            host_url=hdr_stamp.get('host_url'), org=pk.get('alias'), stamp=stamp,
            evidence=review.get('capture')))
    path = store.put(rec)
    try:
        store.render(pk['partition'])
    except Exception:
        pass
    print('wrote %d reviewed control(s) -> %s' % (written, path))
    for sr in stamp_results:
        print('  state stamp: %s' % json.dumps(sr, default=str))
    return 0


# ----------------------------------------------------------------------------- score
def score(review: dict, include_chrome: bool = False) -> dict:
    all_rows = review['rows']
    chrome = [r for r in all_rows if r.get('region') == 'chrome']
    rows = all_rows if include_chrome else [r for r in all_rows if r.get('region') != 'chrome']
    by_status = collections.Counter(r['review']['status'] for r in rows)
    by_col = collections.Counter(ch['column'] for r in rows for ch in (r['review'].get('changes') or []))
    raw_had = collections.Counter(ch['raw_had'] for r in rows for ch in (r['review'].get('changes') or []) if ch.get('raw_had'))
    reviewed = [r for r in rows if r['review']['status'] != 'unreviewed']
    interactive = [r for r in reviewed if r['review']['status'] not in ('not_interactive',)]
    right = [r for r in reviewed if r['review']['status'] == 'accepted']
    changed = [r for r in reviewed if r['review']['status'] != 'accepted']
    xp_a = sum(1 for r in rows if (r.get('xpath') or {}).get('unique_in_capture'))
    xp_c = sum(1 for r in rows if (r.get('xpath') or {}).get('value') and not (r.get('xpath') or {}).get('generated_values'))
    xp_b = collections.Counter(((r.get('xpath') or {}).get('live') or {}).get('verdict') for r in rows)
    kw_live = collections.Counter(((r.get('live') or {}).get('keyword') or {}).get('verdict') for r in rows)
    # 2026-09-10 (seventeen page audits, every one): a bucket member's inherited verdict is a copy of
    # its representative's -- counted alongside the executed ones it inflates the page to 94 passes
    # when 17 were run. The measured counts are the rows whose own locator was executed.
    own = [r for r in rows if r.get('live') and not ((r.get('live') or {}).get('keyword') or {}).get('inherited_from')]
    kw_measured = collections.Counter(((r.get('live') or {}).get('keyword') or {}).get('verdict') for r in own)
    xp_measured = collections.Counter(((r.get('xpath') or {}).get('live') or {}).get('verdict') for r in own)
    # (b) on the pages/rows the keyword ladder fails -- the bar in the plan
    kw_failed = [r for r in rows if ((r.get('live') or {}).get('keyword') or {}).get('verdict') == 'CAUGHT-BUG']
    xp_on_kw_failed = collections.Counter(((r.get('xpath') or {}).get('live') or {}).get('verdict') for r in kw_failed)
    return {
        'page_key': review.get('page_key'), 'org': review.get('org'), 'capture': review.get('capture'),
        'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'rows': len(rows), 'chrome_rows': len(chrome),
        'chrome_included': include_chrome,
        'reviewed': len(reviewed), 'rows_right': len(right), 'rows_changed': len(changed),
        'right_rate': round(len(right) / len(reviewed), 3) if reviewed else None,
        'by_status': dict(by_status), 'changed_by_column': dict(by_col), 'raw_had': dict(raw_had),
        'interactive_rows': len(interactive),
        # the number the user asked for (2026-09-10): patterns right / patterns changed, not rows
        'buckets': _bucket_score(review, rows),
        'patterns': dict(collections.Counter(r.get('pattern') for r in rows if r.get('pattern'))),
        'xpath': {'a_unique_in_capture': xp_a, 'c_no_generated_value': xp_c,
                  'b_live': {k or 'not-run': v for k, v in xp_b.items()},
                  'b_live_on_keyword_failed_rows': {k or 'not-run': v for k, v in xp_on_kw_failed.items()},
                  'd_cross_org': ((rows[0].get('xpath') or {}).get('cross_org') or {}).get('status') if rows else None},
        'keyword_live': {k or 'not-run': v for k, v in kw_live.items()},
        'keyword_live_measured': {k or 'not-run': v for k, v in kw_measured.items()},
        'xpath_live_measured': {k or 'not-run': v for k, v in xp_measured.items()},
        'live_rows_measured': len(own),
    }


def cmd_score(a) -> int:
    review = json.load(open(a.review))
    sc = score(review, include_chrome=a.include_chrome)
    print(json.dumps(sc, indent=1))
    if not a.no_append:
        path = a.scores or SCORES_DEFAULT
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a') as f:
            f.write(json.dumps(sc, sort_keys=True) + '\n')
        print('appended ->', os.path.relpath(path, _ROOT))
    return 0


# ----------------------------------------------------------------------------- drive (generate-and-run)
def parse_robot_line(line: str) -> tuple:
    """One inline Robot step -> (keyword, positional args, kwargs), the way Robot reads it: cells
    split on 2+ spaces, `name=value` is a kwarg only when the `=` is UNESCAPED, `\=` is a literal
    `=` (so `xpath\=//a[@b\="c"]` is one positional locator), `${EMPTY}` is ''."""
    parts = [p for p in re.split(r' {2,}|\t', line.strip()) if p != '']
    kw, args, kwargs = parts[0], [], {}
    for p in parts[1:]:
        p = p.replace('${EMPTY}', '')
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', p)
        if m:
            kwargs[m.group(1)] = m.group(2).replace('\\=', '=')
        else:
            args.append(p.replace('\\=', '='))
    return kw, args, kwargs


# the exported Robot keyword -> the callable the holder runs (QWeb by module, qforce-lite by snake name)
_ROBOT_KW = {
    'TypeText': ('QWeb.keywords.input_', 'type_text'), 'VerifyInputValue': ('QWeb.keywords.input_', 'verify_input_value'),
    'VerifyInputElement': ('QWeb.keywords.input_', 'verify_input_element'),
    'ClickText': ('QWeb.keywords.text', 'click_text'), 'ClickItem': ('QWeb.keywords.text', 'click_item'),
    'VerifyText': ('QWeb.keywords.text', 'verify_text'), 'VerifyItem': ('QWeb.keywords.text', 'verify_item'),
    'VerifyNoText': ('QWeb.keywords.text', 'verify_no_text'),
    'ClickElement': ('QWeb.keywords.element', 'click_element'), 'VerifyElement': ('QWeb.keywords.element', 'verify_element'),
    'DropDown': ('QWeb.keywords.dropdown', 'drop_down'), 'VerifySelectedOption': ('QWeb.keywords.dropdown', 'verify_selected_option'),
    'Open Console Subtab': ('keywords_console', 'open_console_subtab'),   # qforce-lite (tools/qforce-lite/keywords_console.py), on the holder's path
    'ClickCheckbox': ('QWeb.keywords.checkbox', 'click_checkbox'), 'VerifyCheckboxStatus': ('QWeb.keywords.checkbox', 'verify_checkbox_status'),
    # 2026-09-11: the table keywords, so a repeat whose instance is a ROW can be driven as exported
    # (UseTable <header> ;; GetCellText r?<row key>/c?<header> ;; ClickCell ...)
    'UseTable': ('QWeb.keywords.table', 'use_table'), 'VerifyTable': ('QWeb.keywords.table', 'verify_table'),
    'GetCellText': ('QWeb.keywords.table', 'get_cell_text'), 'ClickCell': ('QWeb.keywords.table', 'click_cell'),
    'GetTableRow': ('QWeb.keywords.table', 'get_table_row'),
}

_DRIVE_SCRIPT = r'''
import json, time, re, importlib
from QWeb.keywords.input_ import type_text as _qweb_type_text
from QWeb.keywords.element import get_webelement as _gw
steps = json.loads(%(steps)r)
_ROBOT_KW = json.loads(%(robot_kw)r)
%(parse_src)s
def _snake(k): return re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
def run_robot_line(line):
    """the exported step, executed as written: the same keyword and arguments CRT would run"""
    kwn, args, kwargs = parse_robot_line(line)
    if kwn in _ROBOT_KW:
        mod, fn = _ROBOT_KW[kwn]
        getattr(importlib.import_module(mod), fn)(*args, **kwargs)     # QWeb converts Robot's strings itself
    elif hasattr(ql, _snake(kwn)):
        cast = {"index": int, "timeout": float, "partial_match": lambda v: str(v).lower() == "true"}
        getattr(ql, _snake(kwn))(*args, **{k: cast.get(k, str)(v) for k, v in kwargs.items()})
    else:
        raise ValueError("no callable for keyword %%s" %% kwn)
drv.get(%(url)r)          # generate-and-run opens the page fresh; the first keyword's timeout is the wait
out = []
# 2026-09-11: the page-state check -- the captured title must be the live title before any keyword runs
_want_title = %(want_title)r
_t0 = time.time(); _state_ok = not _want_title
while _want_title and time.time() - _t0 < 30:
    if (drv.title or '').strip() == _want_title.strip():
        _state_ok = True; break
    time.sleep(0.25)
if not _state_ok:
    result = {"page_state": "CAUGHT-BUG: live title %%r != captured title %%r after 30 s -- nothing driven" %% (drv.title, _want_title), "result": []}
    raise SystemExit(0)
for s in steps:
    t0 = time.time(); rec = {"label": s["label"], "kw": s["kw"], "value": s["value"], "index": s.get("index"), "via": s.get("via"), "locator": s.get("locator")}
    try:
        if s["kw"] == "ROBOT":
            rec["call"] = " ;; ".join(s["lines"]); rec["lines"] = []
            for line in s["lines"]:
                t1 = time.time()
                try:
                    run_robot_line(line)
                    rec["lines"].append({"line": line, "ms": round((time.time() - t1) * 1000), "verdict": "VERIFIED-PASS"})
                except Exception as exc:
                    rec["lines"].append({"line": line, "ms": round((time.time() - t1) * 1000), "verdict": "CAUGHT-BUG", "detail": "%%s: %%s" %% (type(exc).__name__, str(exc)[:300])})
                    raise
            rec["detail"] = "; ".join("%%s %%d ms" %% (l["line"].split("  ")[0], l["ms"]) for l in rec["lines"])
        elif s["kw"] == "DropDown" and s.get("via") == "xpath":
            from QWeb.keywords.dropdown import drop_down as _qweb_drop_down
            rec["call"] = "QWeb.keywords.dropdown.drop_down('xpath=%%s', %%r); read back selected option text" %% (s["locator"], s["value"])
            _qweb_drop_down("xpath=" + s["locator"], s["value"], timeout=10)
            got = _gw(s["locator"], timeout=5); got = got[0] if isinstance(got, list) else got
            sel = drv.execute_script("const o=arguments[0].selectedOptions; return o.length? o[0].text.trim() : ''", got)
            if sel != s["value"]:
                raise ValueError("option did not land via xpath: asked %%r, select holds %%r" %% (s["value"], sel))
        elif s["kw"] == "TypeText" and s.get("via") == "xpath":
            # the same shape as type_text_clearing: resolve, clear when non-empty, type, read back
            rec["call"] = "el = get_webelement(%%r); el.clear() if el.value; QWeb.keywords.input_.type_text(el, %%r); read back el.value" %% (s["locator"], s["value"])
            el = _gw(s["locator"], timeout=10); el = el[0] if isinstance(el, list) else el
            if (el.get_attribute("value") or "") != "":
                el.clear()
            _qweb_type_text(el, s["value"], timeout=10)
            got = _gw(s["locator"], timeout=5)
            got = (got[0] if isinstance(got, list) else got).get_attribute("value")
            if (got or "") != s["value"]:
                raise ValueError("value did not land via xpath: asked %%r, field holds %%r" %% (s["value"], got))
        elif s["kw"] == "TypeText":
            rec["call"] = "qforce_lite.type_text_clearing(%%r, %%r, anchor=%%r)" %% (s["locator"], s["value"], str(s["index"]) if s.get("index") else "1")
            ql.type_text_clearing(s["locator"], s["value"], anchor=str(s["index"]) if s.get("index") else "1")
        elif s["kw"] == "DropDown":
            from QWeb.keywords.dropdown import drop_down as _dd
            from QWeb.internal import dropdown as _QD
            _a = str(s.get("index") or 1)
            rec["call"] = "QWeb.keywords.dropdown.drop_down(%%r, %%r, anchor=%%r); read back the selected option" %% (s["label"], s["value"], _a)
            _dd(s["label"], s["value"], anchor=_a, timeout=10)
            _sel = _QD.get_dd_elements_from_all_documents(s["label"], _a, 1)
            _el = getattr(_sel, "_el", None) or getattr(_sel, "wrapped_element", None) or _sel
            got = drv.execute_script("const o=arguments[0].selectedOptions; return o.length? o[0].text.trim() : ''", _el)
            if got != s["value"]:
                raise ValueError("option did not land: asked %%r, select holds %%r" %% (s["value"], got))
        elif s["kw"] == "PickList":
            rec["call"] = "qforce_lite.pick_list(%%r, %%r, index=%%d)" %% (s["label"], s["value"], int(s.get("index") or 1))
            ql.pick_list(s["label"], s["value"], index=int(s.get("index") or 1))
        elif s["kw"] == "ClickCheckbox":
            rec["call"] = "qforce_lite.click_checkbox(%%r, 'on', anchor=%%r)" %% (s["label"], str(s.get("index") or 1))
            ql.click_checkbox(s["label"], "on", anchor=str(s.get("index") or 1))
        elif s["kw"] == "COULD-NOT-CHECK":
            rec["verdict"] = "COULD-NOT-CHECK"; rec["detail"] = s.get("why") or "no drive rule for this keyword"
            rec["elapsed_ms"] = 0; out.append(rec); continue
        else:
            raise ValueError("no drive rule for keyword %%s" %% s["kw"])
        rec["verdict"] = "VERIFIED-PASS"; rec["detail"] = "landed first time (keyword read-back passed)"
    except Exception as exc:
        rec["verdict"] = "CAUGHT-BUG"; rec["detail"] = "%%s: %%s" %% (type(exc).__name__, str(exc)[:300])
    rec["elapsed_ms"] = round((time.time() - t0) * 1000)
    out.append(rec)
result = out
'''

_DEFAULT_VALUES = {'Industry': 'Technology', 'Country': 'USA', 'State': 'Texas', 'City': 'Austin',
                   'Amount': '12345', 'Close Date': '10/8/2026', 'Territory': 'Southwest',
                   'Escalation Regions': 'EMEA', 'Start Date': '2026-09-20', 'End Date': '2026-09-21',
                   'Contract Term': '24', 'Renewal Notice (days)': '60', 'Approved Budget': '130000'}


def cmd_drive(a) -> int:
    """generate-and-run from the STORE: every reviewed, interactive fill control on the page key,
    in DOM order, driven through its verified rung with no capture first. The number is steps
    landed first time. Nothing is saved: the page's Save button is never clicked."""
    review = json.load(open(a.review))
    cap_path = os.path.join(_ROOT, review['capture'])
    pk = PA.page_key_for(cap_path, review.get('org'))
    store = Store(state_root=a.state_root)
    if a.state_root:
        pk = PA._repartition(store, pk)
    rec = store.get(pk['key'], org=pk.get('alias'))
    if not rec and not getattr(a, 'rows', None):
        print('COULD-NOT-CHECK: no store record for', pk['key'])
        return 2
    rec = rec or {'elements': {}}          # a --rows story drives the review's own rows; no store needed
    values = dict(_DEFAULT_VALUES)
    if a.values:
        values.update(json.loads(a.values))
    order = {}
    for r in review['rows']:
        if r['review']['status'] in ('not_interactive', 'could_not_map'):
            continue
        order.setdefault(r.get('label_corrected') or r.get('label') or '', r['n'])
    steps = []
    for el in rec['elements'].values():
        if el.get('source') != 'reviewed' or not el.get('interactive') or el.get('verdict') != 'VERIFIED-PASS':
            continue
        rung = next((x for x in (el.get('ladder') or []) if (x.get('n_verified') or 0) > 0
                     and (x.get('kw') in ('TypeText', 'PickList', 'DropDown', 'ClickCheckbox', 'ComboBox') or x.get('xpath_backup'))), None)
        if not rung:
            continue
        if rung.get('kw') == 'ComboBox':
            # never typed through an xpath: a combobox input takes a selection, not keys
            steps.append({'label': el.get('label') or '', 'kw': 'COULD-NOT-CHECK', 'value': None, 'index': None,
                          'why': 'ComboBox: no drive rule yet (combo_box needs a label it can resolve; this one is a cousin)',
                          'n': order.get(el.get('label') or '', 10 ** 6)})
            continue
        label = el.get('label') or ''
        idx = (rung.get('kwargs') or {}).get('index')
        val = values.get(label) or ('GZREV %s%s' % (label, (' %s' % idx) if idx else ''))
        if rung.get('xpath_backup'):
            if el.get('family') == 'input_field':
                kw = 'TypeText'
            elif el.get('family') == 'dropdown' and el.get('tag') == 'select':
                kw = 'DropDown'
            else:
                continue        # no xpath-driven rule for this family -- COULD-NOT-CHECK, not a silent skip
            steps.append({'label': label, 'kw': kw, 'locator': rung['args'][0], 'value': val,
                          'index': None, 'via': 'xpath', 'n': order.get(label, 10 ** 6)})
            continue
        steps.append({'label': label, 'kw': rung['kw'], 'locator': label, 'value': val, 'index': idx,
                      'via': 'label', 'n': order.get(label, 10 ** 6)})
    # the STORY: rows the reviewer named (--rows, in order) or every row with a corrected multi-step
    # call, driven as the exported Robot lines -- the same keyword + arguments CRT runs, so a miss
    # here is a miss of the export, not of a private script (user, 2026-09-10)
    form = getattr(a, 'form', None) or 'keyword'
    by_n = {r['n']: r for r in review['rows']}
    if getattr(a, 'rows', None):
        story_rows = [by_n[int(x)] for x in a.rows.split(',') if x.strip()]
        steps = []
    else:
        story_rows = [r for r in review['rows'] if r.get('call_corrected') and r.get('region') != 'chrome'
                      and r['review']['status'] not in ('not_interactive', 'could_not_map')]
        done = {(r.get('label_corrected') or r.get('label') or '') for r in story_rows}
        steps = [s for s in steps if s['label'] not in done]
    for r in story_rows:
        label = r.get('label_corrected') or r.get('label') or ''
        if label.lower().startswith(('save', 'submit', 'delete')):
            continue                                   # nothing is committed by a drive
        rc = robot_call(r)
        lines = rc['xpath'] if form == 'xpath' else rc['primary']
        lines = [x for x in lines if x and not x.startswith('#')]
        if not lines:
            steps.append({'label': label, 'kw': 'COULD-NOT-CHECK', 'value': None, 'index': None, 'why': 'no %s-form line for this row' % form, 'n': r['n']})
            continue
        steps.append({'label': label, 'kw': 'ROBOT', 'lines': lines, 'value': None, 'index': None, 'via': form, 'n': r['n']})
    steps.sort(key=lambda s: s['n']) if not getattr(a, 'rows', None) else None
    if not steps:
        print('COULD-NOT-CHECK: no reviewed fill controls with a verified rung on this page')
        return 2
    url = _page_url(review, a)
    import inspect
    want_title = '' if getattr(a, 'force_state', False) else (capture_header(cap_path).get('title') or '')
    script = _DRIVE_SCRIPT % {'steps': json.dumps(steps), 'url': url, 'robot_kw': json.dumps(_ROBOT_KW),
                              'parse_src': inspect.getsource(parse_robot_line), 'want_title': want_title}
    sp = os.path.join(os.path.dirname(os.path.abspath(a.review)), '.drive.py')
    open(sp, 'w').write(script)
    cmd = ['python3', os.path.join(_ROOT, 'tools', 'interop', 'up.py'), a.org, '--op', 'py', '--py-file', sp, '--json']
    if a.slot:
        cmd += ['--slot', a.slot]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    try:
        os.remove(sp)
    except OSError:
        pass
    m = re.search(r'\{.*\}\s*$', p.stdout, re.S)
    if not m:
        print('COULD-NOT-CHECK: holder returned no JSON\n', p.stdout[-2000:], p.stderr[-1000:])
        return 2
    res = json.loads(m.group(0))
    inner = res.get('result') or {}
    rows_out = inner.get('result') if isinstance(inner, dict) else None
    if not rows_out:
        print('COULD-NOT-CHECK: holder error:', json.dumps(res)[:1500])
        return 2
    landed = sum(1 for x in rows_out if x.get('verdict') == 'VERIFIED-PASS')
    cnc = sum(1 for x in rows_out if x.get('verdict') == 'COULD-NOT-CHECK')
    drive = {'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'mode': 'generate-and-run', 'org': a.org,
             'page_key': pk['key'], 'steps': len(rows_out), 'landed_first_time': landed,
             'could_not_check': cnc, 'rescans': 0, 'session': res.get('session'), 'url': inner.get('url'),
             'elapsed_ms': inner.get('elapsed_ms'), 'results': rows_out}
    review.setdefault('drives', []).append(drive)
    json.dump(review, open(a.review, 'w'), indent=1)
    for x in rows_out:
        print('%-22s %6s ms  %s\n      %s' % (x['verdict'], x['elapsed_ms'], x.get('call') or '', _short(x.get('detail') or '', 110)))
    print('steps landed first time: %d / %d  (%d could-not-check listed above; rescans 0; mode generate-and-run; session %s)' % (
        landed, len(rows_out) - cnc, cnc, res.get('session')))
    if not a.no_append:
        path = a.scores or SCORES_DEFAULT
        with open(path, 'a') as f:
            f.write(json.dumps({k: v for k, v in drive.items() if k != 'results'}, sort_keys=True) + '\n')
    return 0


# ----------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('--capture', required=True); b.add_argument('--org')
    b.add_argument('--screenshot'); b.add_argument('--out-dir'); b.set_defaults(fn=cmd_build)
    l = sub.add_parser('live'); l.add_argument('--review', required=True); l.add_argument('--org', required=True)
    l.add_argument('--slot'); l.add_argument('--rows', help='probe only these row numbers (comma-separated)')
    l.add_argument('--all', action='store_true', help='every row, not one representative per bucket')
    l.add_argument('--force-state', action='store_true', help='probe even when the holder is not on the captured page state (the verdicts are then about a different page)')
    l.add_argument('--batch', type=int, default=40, help='rows per holder op (each op must finish within the holder\'s 120 s)')
    l.set_defaults(fn=cmd_live)
    c = sub.add_parser('correct'); c.add_argument('--review', required=True); c.add_argument('--row', type=int, required=True)
    c.add_argument('--column', choices=COLUMNS, required=True); c.add_argument('--to', required=True)
    c.add_argument('--bucket', action='store_true', help='apply the same correction to every same-shape control (never for label)')
    c.add_argument('--raw-had'); c.add_argument('--note'); c.set_defaults(fn=cmd_correct)
    ac = sub.add_parser('accept'); ac.add_argument('--review', required=True); ac.add_argument('--rows', required=True)
    ac.add_argument('--note'); ac.set_defaults(fn=cmd_accept)
    w = sub.add_parser('writeback'); w.add_argument('--review', required=True); w.add_argument('--state-root')
    w.set_defaults(fn=cmd_writeback)
    s = sub.add_parser('score'); s.add_argument('--review', required=True); s.add_argument('--scores')
    s.add_argument('--no-append', action='store_true'); s.add_argument('--include-chrome', action='store_true'); s.set_defaults(fn=cmd_score)
    r = sub.add_parser('render'); r.add_argument('--review', required=True); r.set_defaults(fn=cmd_render)
    rb = sub.add_parser('robot'); rb.add_argument('--review', required=True); rb.add_argument('--out')
    rb.add_argument('--include-chrome', action='store_true'); rb.add_argument('--all', action='store_true', help='every row, not a sample per bucket')
    rb.add_argument('--per-bucket', type=int, default=3, help='members exported per same-shape bucket (default 3: enough to see how a family reads, never a whole table)')
    rb.add_argument('--url', help='GoTo target when no live probe recorded one (read-only orgs); kept on the review')
    rb.add_argument('--app', help='the Lightning app the page was captured in (label, or 06m id mapped through crt/apps.json); kept on the review as page.app')
    rb.add_argument('--hide-omitted', action='store_true', help='drop the controls this sample left out instead of listing them as comments (default: show them -- user, 2026-09-11)')
    rb.set_defaults(fn=cmd_robot)
    ad = sub.add_parser('add'); ad.add_argument('--review', required=True); ad.add_argument('--label', required=True)
    ad.add_argument('--family', required=True); ad.add_argument('--keyword', required=True); ad.add_argument('--call', required=True)
    ad.add_argument('--xpath'); ad.add_argument('--tag'); ad.add_argument('--raw'); ad.add_argument('--raw-had'); ad.add_argument('--note')
    ad.set_defaults(fn=cmd_add)
    de = sub.add_parser('demo'); de.add_argument('--review', required=True); de.add_argument('--out')
    de.add_argument('--url', help='GoTo target when no live probe recorded one; kept on the review')
    de.add_argument('--app', help='the Lightning app the page was captured in (label, or 06m id mapped through crt/apps.json); kept on the review as page.app')
    de.add_argument('--rows', help='comma-separated row numbers in story order (default: one representative per bucket in DOM order, Cancel/Close skipped)')
    de.add_argument('--all', action='store_true', help='every row, not a sample per bucket')
    de.add_argument('--per-bucket', type=int, default=3, help='members exported per same-shape bucket (default 3)')
    de.add_argument('--hide-omitted', action='store_true', help='drop the controls with no live pass instead of listing them as comments (default: show them -- user, 2026-09-11)')
    de.set_defaults(fn=cmd_demo)
    d = sub.add_parser('drive'); d.add_argument('--review', required=True); d.add_argument('--org', required=True)
    d.add_argument('--slot'); d.add_argument('--values', help='JSON {label: value} overriding the probe values')
    d.add_argument('--state-root'); d.add_argument('--scores'); d.add_argument('--no-append', action='store_true')
    d.add_argument('--rows', help='story order: comma-separated row numbers driven as their exported Robot lines (default: store rungs + every corrected call)')
    d.add_argument('--form', choices=('keyword', 'xpath'), default='keyword', help='which exported form the story rows run')
    d.add_argument('--url', help='GoTo target when no live probe recorded one; kept on the review')
    d.add_argument('--app', help='the Lightning app the page was captured in (label or 06m id); kept on the review as page.app')
    d.add_argument('--force-state', action='store_true', help='drive even when the live title differs from the captured title')
    d.set_defaults(fn=cmd_drive)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
