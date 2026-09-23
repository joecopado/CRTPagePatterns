#!/usr/bin/env python3
"""Can the org map's metadata actually SEE the rendered DOM?

Usage:
  python3 tools/recorder/metadata_dom_parity.py --capture <file.html> --org <alias> [--object Obj] [--json]
  python3 tools/recorder/metadata_dom_parity.py --all [--json] [--captures-dir docs/dom-captures]
  python3 tools/recorder/metadata_dom_parity.py --all --json --out docs/recorder/evidence/x.json

WHY (user, 2026-09-07). Every keyword-prediction claim in this repo assumes the metadata layers
(detail_layout_sections / page_layouts / quick_actions / record_page / list_views / flow_screens /
navigation) describe the page a test will actually drive. Nobody had measured the DIFFERENCE. This
tool joins the two sides label-by-label on a committed capture and answers in the project tri-state:

  PREDICTED   -- controls the org map names for this object+page-kind, each with its routed keyword.
  RENDERED    -- controls parse_elements_from_html returns from the committed capture.
  diff        -- predicted-and-rendered / predicted-not-rendered / rendered-not-predicted (by SHAPE).

Rates are per-page atoms rolled up with a 95% Wilson interval (tools/benchmark/metrics.wilson).
A page whose object cannot be tied to a map object is COULD-NOT-TIE and is EXCLUDED from every
numerator and denominator -- printed, never silently dropped.

Reader API: the org map is read through its own on-disk contract (the same JSON
tools/qforce-lite/discovery/discover.py query reads); the DOM through
tools/interop/resources/pythonDom/capture_orchestration.parse_elements_from_html.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, os.path.abspath(os.path.join(_ROOT, 'tools', 'interop', 'resources', 'pythonDom')))
sys.path.insert(0, os.path.abspath(os.path.join(_ROOT, 'tools', 'benchmark')))
sys.path.insert(0, os.path.abspath(os.path.join(_ROOT, 'tools', 'qforce-lite')))

from parser_gateway import parse_elements_from_html  # noqa: E402  (F250: LATE-BOUND -- a
# module-level `from capture_orchestration import ...` is stranded by the harness's two
# deliberate sys.modules purges; see tools/recorder/parser_gateway.py)
from metrics import wilson  # noqa: E402
# Stream B6 fix (2026-09-07): this file's own quick-action prediction used to route the LITERAL
# `render.keyword_family` TEXT ("aura-picklist / aura-date / aura-lookup (NOT QForce PickList...")
# as if it were a callable keyword name -- the exact CAUGHT-BUG PB0 named ("predict.py routing
# table" section). Route through predict.py's real family->keyword table instead, the ONE place
# that mapping now lives (BACKLOG 80).
from predict import QUICK_ACTION_FAMILY_KEYWORD  # noqa: E402
# stream 2A 2026-09-09: the ONE describe-type router. This file used to carry its own copy.
from predict import type_to_keyword as predict_type_to_keyword  # noqa: E402

MAP_DIR = os.path.expanduser('~/.claude/state/org-map')
COULD_NOT_TIE = 'COULD-NOT-TIE'

# The B5 page-inventory layers (app_chrome / related_list_actions / list_view_chrome /
# control_tabs). `--no-b5-layers` sets this back to None, which is what makes the before/after
# in docs/crt-train/evidence/org-map-page-inventory-layers-2026-09-07.md a comparison of the
# LAYERS and nothing else -- same tool, same captures, same run, one switch.
try:
    sys.path.insert(0, os.path.join(_ROOT, 'tools', 'qforce-lite', 'discovery'))
    import page_chrome as PAGE_CHROME          # noqa: E402
except Exception:                              # noqa: BLE001
    PAGE_CHROME = None

# ---------------------------------------------------------------- keyword routing
# stream 2A 2026-09-09. This used to be a SECOND hand-written describe-type table, and it
# disagreed with predict.py -- the router that owns this mapping -- on seven types. The two that
# mattered on the corpus: `time` routed here to 'Set Datetime' while predict.type_to_keyword calls
# it a stated could-not-check gap (there is no time-only keyword), and `multipicklist` routed here
# to 'PickList' while predict routes it to multi_pick_list. Both produced keyword DISAGREEMENTS
# that were really router disagreements. The table is now DERIVED from predict.py; a type predict
# states no keyword for becomes 'unrouted', which `assess` already excludes from the agreement
# denominator instead of scoring it as a miss. Pinned by
# tools/recorder/tests/test_keyword_router_contract_2026_09_09.py.
_CALLABLE_TO_RUNG = {
    'type_text_clearing': 'Type Text Clearing',
    'pick_list': 'PickList',
    'multi_pick_list': 'Multi Pick List',
    'combo_box': 'ComboBox',
    'click_checkbox': 'ClickCheckbox',
    'set_datetime': 'Set Datetime',
    'set_address': 'Set Address',
    'set_geolocation': 'Set Geolocation',
}
_ROUTED_TYPES = (
    'string', 'textarea', 'phone', 'email', 'url', 'int', 'long', 'double', 'currency', 'percent',
    'encryptedstring', 'picklist', 'multipicklist', 'combobox', 'reference', 'boolean',
    'date', 'datetime', 'time', 'address', 'complexvalue', 'location', 'id', 'base64',
)


def _rung_for_type(ftype: str) -> str:
    kw, _confidence = predict_type_to_keyword(ftype)
    if kw is None:
        return 'unrouted'
    return _CALLABLE_TO_RUNG.get(kw, kw)


TYPE_KEYWORD = {t: _rung_for_type(t) for t in _ROUTED_TYPES}
COMPOUND_ADDRESS = re.compile(r'address$', re.I)


def keyword_for(api_name: str, ftype: str) -> str:
    if COMPOUND_ADDRESS.search(api_name or '') and (ftype in ('address', 'textarea', 'string')):
        return 'Set Address'
    return TYPE_KEYWORD.get((ftype or '').lower(), 'unrouted')


# ---------------------------------------------------------------- keyword comparison
# The ACTION CLASS of a rung. A metadata prediction and a DOM hint agree when they name the same
# rung OR when both are the same KIND of action -- two ways to resolve one click are not two
# different answers. This was already half-implemented and ASYMMETRIC: the DEFAULT comparison
# accepted `predicted=<any click>` against `rendered=ClickText`, but not the mirror image, so 51 of
# the 58 disagreements measured on 2026-09-09 (docs/recorder/evidence/keyword-routing-2026-09-09.md
# Sec2) were a predicted ClickText against a rendered ClickItem -- the label-source rung order
# (hintOrderByLabelSource) deliberately puts ClickItem first when the label came from
# aria-label/title, because ClickText searches RENDERED text. Fixed 2026-09-09 (stream DEC): the
# CLICK/CLICK case is symmetric in the default rule too, not only under intent_aware. The
# intent_aware flag still exists for the wider ACTION_CLASS (tabs, tree items, path stages, …),
# which the click-only fix does not attempt to cover.
_ACTION_CLASS = {
    'clicktext': 'click', 'clickitem': 'click', 'clickelement': 'click',
    'opentab': 'click', 'clicktreeitem': 'click', 'clickpathstage': 'click',
    'openconsolesubtab': 'click', 'opentertiarytab': 'click', 'openutilityitem': 'click',
    'selectsplitviewrow': 'click', 'omniclickaction': 'click',
}

# The three rungs that are ALWAYS interchangeable locator strategies for one plain click --
# never a family/behaviour difference. `ClickTableCell`, `ClickCheckbox`, `ClickPathStage` etc.
# also contain the substring "click" but name a genuinely different resolution (a grid cell, a
# read-back checkbox, a path stage); folding them in here would have hidden the in_grid
# misclassification the corpus actually has (predicted ClickText / rendered Click Table Cell,
# a real parser miss -- see the decomposition doc). Membership, not substring, is the fix.
_CLICK_TEXT_FAMILY = {'clicktext', 'clickitem', 'clickelement'}


def _same_keyword(predicted: str, rendered: str, intent_aware: bool = False) -> bool:
    pk = (predicted or '').lower().replace(' ', '')
    rk = (rendered or '').lower().replace(' ', '')
    if not pk or not rk:
        return False
    if pk in rk or rk in pk:
        return True
    if intent_aware:
        return (_ACTION_CLASS.get(pk) is not None
                and _ACTION_CLASS.get(pk) == _ACTION_CLASS.get(rk))
    # symmetric fix for the asymmetry named above: ClickText/ClickItem/ClickElement agree with
    # each other in EITHER direction. Nothing wider -- see _CLICK_TEXT_FAMILY's comment.
    return pk in _CLICK_TEXT_FAMILY and rk in _CLICK_TEXT_FAMILY


# ---------------------------------------------------------------- label normalisation
_REQ = re.compile(r'[\*\u2022]|\(required\)|required', re.I)


def norm(label: str) -> str:
    if not label:
        return ''
    s = _REQ.sub(' ', label)
    s = s.replace('\u00a0', ' ')
    s = re.sub(r'[:\u2013\u2014]+\s*$', '', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


# ---------------------------------------------------------------- map access
_MAPS: dict = {}


def load_map(org):
    if org in _MAPS:
        return _MAPS[org]
    path = os.path.join(MAP_DIR, '%s.json' % org)
    if not os.path.exists(path):
        _MAPS[org] = None
        return None
    with open(path) as fh:
        _MAPS[org] = json.load(fh)
    return _MAPS[org]


def _val(node, key):
    """org-map layers are {'value': ..., 'verified': ...} wrappers."""
    if not isinstance(node, dict):
        return None
    layer = node.get(key)
    if isinstance(layer, dict) and 'value' in layer:
        return layer['value']
    return layer


# ---------------------------------------------------------------- page kind
def page_kind(path: str, filename: str) -> str:
    p = (path or '').lower()
    f = filename.lower()
    if '/new?' in p or 'new-modal' in f or '/action/quick/' in p:
        return 'new-edit-modal'
    if '/edit' in p:
        return 'new-edit-modal'
    if '/related/' in p:
        return 'related-list'
    if re.search(r'/lightning/o/[^/]+/list', p):
        return 'list-view'
    if re.search(r'/lightning/r/[^/]+/[^/]+/view', p):
        return 'record-page'
    if '/flow/runtime' in p or 'flow-screen' in f:
        return 'flow-screen'
    if '/lightning/setup/' in p:
        return 'setup'
    if '/lightning/n/' in p or '/lightning/page/' in p:
        return 'console-custom'
    if '/apex/' in p or 'one.app' in p:
        return 'vf-console'
    return 'other'


def object_from_path(path: str):
    m = re.search(r'/lightning/[ro]/([A-Za-z0-9_]+)/', path or '')
    if m:
        return m.group(1)
    m = re.search(r'objectApiName=([A-Za-z0-9_]+)', path or '')
    if m:
        return m.group(1)
    return None


def capture_header(html_head: str) -> dict:
    out = {}
    for key in ('capture', 'title', 'path'):
        m = re.search(r'<!--\s*%s:\s*(.*?)\s*-->' % key, html_head)
        if m:
            out[key] = m.group(1)
    return out


# ---------------------------------------------------------------- prediction
def predict(org: str, obj: str, kind: str):
    """Return (predicted controls, notes). Each control: label, meta_type, keyword, source."""
    notes = []
    omap = load_map(org)
    if omap is None:
        return [], ['no map for org %s' % org]
    node = (omap.get('objects') or {}).get(obj)
    if node is None:
        return [], ['object %s not in %s map' % (obj, org)]

    fields = _val(node, 'inventory') or {}
    if isinstance(fields, dict):
        fields = fields.get('fields') or {}
        if isinstance(fields, dict) and 'value' in fields:
            fields = fields['value']
    if not isinstance(fields, dict):
        fields = {}

    def field_control(api, source, section=None):
        meta = fields.get(api) or {}
        label = meta.get('label') or api
        ftype = meta.get('type') or 'unknown'
        return {
            'label': label, 'norm': norm(label), 'api_name': api,
            'meta_type': ftype, 'keyword': keyword_for(api, ftype),
            'source': source, 'section': section,
            'required': (meta.get('nillable') is False and meta.get('defaulted_on_create') is False),
            'readonly': meta.get('updateable') is False,
        }

    preds = []
    seen = set()

    def add(c):
        k = (c['norm'], c['source'])
        if c['norm'] and k not in seen:
            seen.add(k)
            preds.append(c)

    if kind in ('record-page', 'new-edit-modal', 'related-list'):
        dls = _val(node, 'detail_layout_sections') or []
        if not dls:
            notes.append('no detail_layout_sections layer (object is inventory-lite / lazy)')
        # Restrict to the layout the RUNNING user's profile is assigned, when the
        # profile_layout layer can resolve it. Unioning every layout over-predicts:
        # a page renders exactly one. If it cannot be resolved, the union is used and
        # the note says so -- never a silent union.
        pl = _val(node, 'profile_layout') or {}
        assigned = None
        for asg in (pl.get('assignments') or []) if isinstance(pl, dict) else []:
            if asg.get('profile_name') == 'System Administrator':
                assigned = asg.get('layout_name')
                break
        if assigned:
            picked = [ly for ly in dls if ly.get('layout_name') == assigned]
            if picked:
                dls = picked
                notes.append('layout restricted to profile assignment: %s' % assigned)
            else:
                notes.append('profile assignment %s not in detail_layout_sections; union used' % assigned)
        elif dls:
            notes.append('no System Administrator profile_layout assignment; union of %d layouts used' % len(dls))
        for layout in dls:
            for sec in (layout.get('sections') or []):
                for api in (sec.get('fields') or []):
                    add(field_control(api, 'detail_layout_sections', sec.get('label')))
        for qa in (_val(node, 'quick_actions') or []):
            lbl = qa.get('label') or qa.get('name')
            family = (qa.get('render') or {}).get('family')
            add({'label': lbl, 'norm': norm(lbl), 'api_name': qa.get('name'),
                 'meta_type': qa.get('type'), 'section': None, 'required': False, 'readonly': False,
                 'keyword': QUICK_ACTION_FAMILY_KEYWORD.get(family, 'ClickText'),
                 'source': 'quick_actions'})
        # record_page tabs' related_lists_named -- was never predicted at all (0/32 measured,
        # PB0's "true 0/32"). predict.py's own set is the source of truth (predict_record_page_
        # regions_from_map); mirrored here rather than imported so this file's flat add()/norm()
        # pipeline stays untouched -- keyword and source match predict.py's RELATED_LIST_KEYWORD.
        rp_val = _val(node, 'record_page') or {}
        default_page = None
        if isinstance(rp_val, dict):
            pages = rp_val.get('pages') or {}
            default_name = (rp_val.get('org_default') or {}).get('developer_name')
            default_page = pages.get(default_name) if default_name else None
            if default_page is None and pages:
                default_page = next(iter(pages.values()))
        for tab in ((default_page or {}).get('tabs') or []):
            tab_label = tab.get('label')
            for rl in (tab.get('related_lists_named') or []):
                add({'label': rl, 'norm': norm(rl), 'api_name': rl, 'meta_type': 'RelatedList',
                     'keyword': 'ClickTableCell', 'source': 'record_page', 'section': tab_label,
                     'required': False, 'readonly': False})

    if kind == 'list-view':
        lvs = _val(node, 'list_views') or []
        if not lvs:
            notes.append('no list_views layer')
        for lv in (lvs if isinstance(lvs, list) else []):
            lbl = (lv.get('label') or lv.get('name')) if isinstance(lv, dict) else str(lv)
            add({'label': lbl, 'norm': norm(lbl), 'api_name': lbl, 'meta_type': 'ListView',
                 'keyword': 'ClickText (list view picker)', 'source': 'list_views',
                 'section': None, 'required': False, 'readonly': False})

    if kind == 'flow-screen':
        fss = _val(node, 'flow_screens') or []
        if not fss:
            notes.append('no flow_screens layer for this object')
        for scr in (fss if isinstance(fss, list) else []):
            for fld in ((scr.get('fields') or []) if isinstance(scr, dict) else []):
                lbl = fld.get('label') or fld.get('name')
                add({'label': lbl, 'norm': norm(lbl), 'api_name': fld.get('name'),
                     'meta_type': fld.get('type'), 'keyword': 'Flow family',
                     'source': 'flow_screens', 'section': None,
                     'required': bool(fld.get('required')), 'readonly': False})

    nav = _val(node, 'navigation') or {}
    if isinstance(nav, dict):
        for t in (nav.get('tabs') or []):
            lbl = t.get('label') if isinstance(t, dict) else str(t)
            add({'label': lbl, 'norm': norm(lbl), 'api_name': lbl, 'meta_type': 'Tab',
                 'keyword': 'ClickText (tab)', 'source': 'navigation',
                 'section': None, 'required': False, 'readonly': False})

    # ---------------------------------------------------------------- B5 page-inventory layers
    # (stream B5, 2026-09-07). PB0's own "layers I'd add" table, now built and read here. Each
    # block is guarded on the layer being PRESENT: a map without it predicts exactly what it did
    # before, so a before/after comparison is a comparison of the layers and nothing else.
    if PAGE_CHROME is not None:
        # related-list actions -- the Layout XML's <relatedLists>, which the map used to discard.
        if kind in ('record-page', 'related-list'):
            rla = PAGE_CHROME.read_related_list_actions(node) or {}
            for c in (rla.get('controls') or []):
                lbl = c.get('label')
                add({'label': lbl, 'norm': norm(lbl), 'api_name': lbl,
                     'meta_type': 'RelatedListAction', 'keyword': 'ClickText',
                     'source': 'related_list_actions', 'section': c.get('related_list'),
                     'required': False, 'readonly': False})

        # app chrome -- org-level, identical on every page of an app, so it applies to EVERY kind.
        # Guarded on the layer actually being IN THIS MAP. `app_chrome_controls` falls back to the
        # platform global header for a map without the layer, which is right for a driver ("this
        # much is true of every org") and WRONG here: this tool measures what the MAP knows, and
        # predicting 17 header controls out of a map that carries none would credit the map for a
        # layer it does not have. Caught by test_metadata_dom_parity.py's fixture org (3 -> 20).
        if PAGE_CHROME.read_app_chrome(omap):
            for c in PAGE_CHROME.app_chrome_controls(omap):
                lbl = c.get('label')
                add({'label': lbl, 'norm': norm(lbl), 'api_name': lbl,
                     'meta_type': 'AppChrome', 'keyword': c.get('keyword') or 'ClickText',
                     'source': 'app_chrome', 'section': c.get('source'),
                     'required': False, 'readonly': False})

        # list-view chrome -- the platform vocabulary, on the list-shaped page kinds only. Same
        # rule: only when the map carries the layer.
        if kind in ('list-view', 'related-list') and PAGE_CHROME.read_list_view_chrome(omap):
            for c in PAGE_CHROME.list_view_chrome_controls(omap):
                lbl = c.get('label')
                add({'label': lbl, 'norm': norm(lbl), 'api_name': lbl,
                     'meta_type': 'ListViewChrome', 'keyword': c.get('keyword') or 'ClickText',
                     'source': 'list_view_chrome', 'section': None,
                     'required': False, 'readonly': False})

    rp = _val(node, 'record_page') or {}
    if isinstance(rp, dict) and kind == 'record-page':
        def walk(v):
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 in ('label', 'componentName') and isinstance(v2, str):
                        add({'label': v2, 'norm': norm(v2), 'api_name': v2,
                             'meta_type': 'FlexiPage component', 'keyword': 'component-specific',
                             'source': 'record_page', 'section': None,
                             'required': False, 'readonly': False})
                    else:
                        walk(v2)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
        walk(rp)

    # Tab annotation (stream B5). Every predicted control is stamped with the record-page tab it
    # lives behind, so a "predicted but not rendered" control can be classed "behind tab X" rather
    # than counted as a metadata miss. PB0 measured ~450 of 646 such misses as exactly this.
    if PAGE_CHROME is not None:
        ct = PAGE_CHROME.read_control_tabs(node)
        open_tab = (ct or {}).get('default_tab')
        for p in preds:
            p['tab'] = PAGE_CHROME.tab_for(p.get('source'), ct)
            # A control behind a tab that is NOT the one the page opens on genuinely is not in
            # the DOM. That is a fact about the capture, not an error in the metadata.
            p['behind_closed_tab'] = bool(p['tab'] and open_tab and p['tab'] != open_tab)
        if ct:
            notes.append('tab annotation from control_tabs (%s, opens on %s)'
                         % (ct.get('tab_source'), open_tab))
    return preds, notes


# ---------------------------------------------------------------- shapes
CHROME = {'search', 'setup', 'favorites', 'app launcher', 'help', 'notifications',
          'show menu', 'add favorite', 'edit favorite', 'toggle panel', 'view profile',
          'global actions', 'learn more', 'skip to main content', 'close', 'back',
          'user', 'guidance center', 'go to setup', 'toggle navigation menu'}
LISTCTRL = {'filter', 'filters', 'sort', 'list view controls', 'display as', 'refresh',
            'select all', 'chart', 'search this list', 'edit list filters', 'show actions',
            'select item', 'sort by'}


def shape_of(el: dict) -> str:
    ident = el.get('identification') or {}
    lbl = norm(ident.get('label_text') or '')
    et = (el.get('element_type') or '').lower()
    sect = norm((el.get('context') or {}).get('section') or '')
    if lbl in CHROME or sect in ('q branch', 'global header', 'header'):
        return 'console/app chrome'
    if 'utility' in sect or 'utility' in lbl:
        return 'utility bar'
    if lbl in LISTCTRL or et in ('columnheader', 'cell', 'row', 'grid', 'gridcell'):
        return 'list-view controls'
    if et in ('tab', 'tabpanel'):
        return 'tabset'
    if 'related' in sect or lbl in ('new', 'add', 'view all', 'add products'):
        return 'related-list actions'
    if et == 'link':
        return 'record/nav links'
    if 'path' in sect or 'stage' in sect:
        return 'path'
    if et in ('textbox', 'combobox', 'checkbox', 'textarea', 'listbox', 'radio', 'slider'):
        return 'custom LWC / unmapped input'
    if et == 'button':
        return 'button (unmapped)'
    return 'other'


# ---------------------------------------------------------------- one page
# ---------------------------------------------------------------- denominators (2026-09-22)
# The 21% figure (`metadata_coverage_of_predictions`) was quoted for three weeks as a ceiling on
# what metadata can predict. Measured 2026-09-22 (docs/audit/metadata-layer-value-2026-09-22.md):
# every rendered-not-predicted control was a button, a link or chrome, and on the one page with a
# verified denominator the UI API named 25/25 FIELD controls. The rate was a statement about how
# much of a page is fields. So the instrument now reports BOTH denominators side by side, and the
# contribution of each map LAYER (`source`), so a layer with no readers and no hits is visible as
# such rather than folded into one number.
FIELD_FAMILIES = frozenset({
    'input_field', 'textarea', 'date', 'datetime', 'lookup', 'combobox', 'picklist', 'dropdown',
    'checkbox', 'radio', 'email', 'number', 'search', 'output_field', 'toggle', 'currency',
    'phone', 'url', 'rich_text', 'richtext', 'time', 'address', 'name', 'geolocation',
})


def family_class(element_type) -> str:
    """'field' for a control a field layer could describe, else 'non-field' (buttons, links,
    tabs, headers, chrome, tables)."""
    return 'field' if (element_type or '') in FIELD_FAMILIES else 'non-field'


def breakdowns(preds: list, rendered: list, hit: list, miss: list, extra: list) -> dict:
    """The two denominators and the per-layer contribution for ONE page. Pure: no map, no DOM.

    by_family[class]  = {rendered, predicted_and_rendered, rendered_not_predicted}
                        over the RENDERED side, keyed by family_class(element_type).
    by_source[layer]  = {predicted, rendered, not_rendered, behind_closed_tab, unique}
                        over the PREDICTED side; `unique` counts hits that NO other layer also
                        predicted (the layer's irreplaceable contribution).
    """
    hit_norms = {p['norm'] for p in hit}
    by_family = {}
    for r in rendered:
        if not r.get('norm'):
            continue
        fc = family_class(r.get('element_type'))
        d = by_family.setdefault(fc, {'rendered': 0, 'predicted_and_rendered': 0,
                                      'rendered_not_predicted': 0})
        d['rendered'] += 1
        if r['norm'] in hit_norms:
            d['predicted_and_rendered'] += 1
        else:
            d['rendered_not_predicted'] += 1
    for fc, d in by_family.items():
        d['coverage'] = (d['predicted_and_rendered'] / d['rendered']) if d['rendered'] else None
    sources_per_norm = {}
    for p in preds:
        sources_per_norm.setdefault(p['norm'], set()).add(p.get('source'))
    by_source = {}
    for p in preds:
        d = by_source.setdefault(p.get('source') or 'unknown',
                                 {'predicted': 0, 'rendered': 0, 'not_rendered': 0,
                                  'behind_closed_tab': 0, 'unique': 0})
        d['predicted'] += 1
    for p in hit:
        d = by_source[p.get('source') or 'unknown']
        d['rendered'] += 1
        if len(sources_per_norm.get(p['norm'], ())) == 1:
            d['unique'] += 1
    for p in miss:
        d = by_source[p.get('source') or 'unknown']
        d['not_rendered'] += 1
        if p.get('behind_closed_tab'):
            d['behind_closed_tab'] += 1
    return {'by_family': by_family, 'by_source': by_source}


def family_basis_disclosure(rendered_total: int, by_family: dict) -> dict:
    """C1, 2026-09-22 (docs/audit/challenge-2026-09-22-prior-work/C1-f229-numbers.md): pure,
    no map, no DOM. `dom_explained_by_metadata` (computed by the caller from the corpus-wide
    `rendered_total` and `rendered_not_predicted`) silently counts every rendered control with
    no `norm` as EXPLAINED, because those controls never reach `rendered_not_predicted` (they
    are excluded from `extra` in `assess()`) -- yet `breakdowns()`'s own `by_family` denominator
    excludes those same controls from `rendered` entirely (`if not r.get('norm'): continue`).
    Neither number is changed here; this only names the gap and recomputes the same
    numerator/denominator SHAPE on `by_family`'s smaller, norm-only basis, so a reader can see
    both and understand why they differ.

    Returns {'rendered_without_norm': <n>, 'by_family_basis': {k, n, rate, wilson95}} -- `n` is
    always `by_family`'s own summed `rendered`, never `rendered_total` itself, so a page with
    zero norm-less controls degenerates exactly to `rendered_without_norm == 0` and the two
    rates coincide."""
    fam_rendered_total = sum(d['rendered'] for d in by_family.values())
    fam_hits_total = sum(d['predicted_and_rendered'] for d in by_family.values())
    return {
        'rendered_without_norm': rendered_total - fam_rendered_total,
        'by_family_basis': {
            'k': fam_hits_total, 'n': fam_rendered_total,
            'rate': (fam_hits_total / fam_rendered_total if fam_rendered_total else None),
            'wilson95': (wilson(fam_hits_total, fam_rendered_total)
                         if fam_rendered_total >= 10 else None),
        },
    }


def merge_breakdowns(rows: list) -> dict:
    """Sum per-page breakdowns into one; rates recomputed from the sums, never averaged."""
    fam, src = {}, {}
    for r in rows:
        for fc, d in (r.get('by_family') or {}).items():
            t = fam.setdefault(fc, {'rendered': 0, 'predicted_and_rendered': 0,
                                    'rendered_not_predicted': 0})
            for k in ('rendered', 'predicted_and_rendered', 'rendered_not_predicted'):
                t[k] += d.get(k, 0)
        for sname, d in (r.get('by_source') or {}).items():
            t = src.setdefault(sname, {'predicted': 0, 'rendered': 0, 'not_rendered': 0,
                                       'behind_closed_tab': 0, 'unique': 0})
            for k in t:
                t[k] += d.get(k, 0)
    for fc, t in fam.items():
        t['coverage'] = (t['predicted_and_rendered'] / t['rendered']) if t['rendered'] else None
        t['wilson95'] = wilson(t['predicted_and_rendered'], t['rendered']) if t['rendered'] >= 10 else None
    for sname, t in src.items():
        t['rate'] = (t['rendered'] / t['predicted']) if t['predicted'] else None
    return {'by_family': fam, 'by_source': src}



def assess(capture: str, org, obj_override=None) -> dict:
    with open(capture, errors='replace') as fh:
        html = fh.read()
    hdr = capture_header(html[:4000])
    path = hdr.get('path', '')
    fname = os.path.basename(capture)
    kind = page_kind(path, fname)
    obj = obj_override or object_from_path(path)

    els = parse_elements_from_html(html)
    rendered = []
    for e in els:
        lbl = ((e.get('identification') or {}).get('label_text') or '')
        hints = ((e.get('qforce_hints') or {}).get('locator_options') or [])
        rendered.append({
            'label': lbl, 'norm': norm(lbl),
            'element_type': e.get('element_type'),
            'first_hint': (hints[0].get('keyword') if hints else None),
            # stream 2A: the element's own FILL rung -- the intent-matched comparand for a
            # metadata prediction that names a fill keyword.
            'hint_fill': e.get('hint_fill'),
            'hint_verify': e.get('hint_verify'),
            'shape': shape_of(e),
        })

    row = {'capture': capture, 'org': org, 'object': obj, 'page_kind': kind,
           'path': path, 'rendered_total': len(rendered)}

    if not org or load_map(org) is None or not obj:
        row['status'] = COULD_NOT_TIE
        row['reason'] = ('no org attribution' if not org else
                         ('no map for org %s' % org if load_map(org) is None else
                          'no object in URL (%s)' % (path or 'no path header')))
        return row

    preds, notes = predict(org, obj, kind)
    if not preds:
        row['status'] = COULD_NOT_TIE
        row['reason'] = '; '.join(notes) or 'map predicts nothing for %s/%s' % (obj, kind)
        return row

    rnorms = set(r['norm'] for r in rendered if r['norm'])
    pnorms = set(p['norm'] for p in preds)
    hit = [p for p in preds if p['norm'] in rnorms]
    miss = [p for p in preds if p['norm'] not in rnorms]
    extra = [r for r in rendered if r['norm'] and r['norm'] not in pnorms]

    agree = dis = 0
    agree_intent = dis_intent = 0
    read_mode_skipped = 0
    dis_rows = []
    by_norm = {}
    for r in rendered:
        by_norm.setdefault(r['norm'], r)
    for p in hit:
        r = by_norm.get(p['norm'])
        if not r or not r.get('first_hint') or p['keyword'] in ('unrouted', 'component-specific'):
            continue
        # stream 2A: a READ-MODE control cannot answer a FILL question. Phase 1B made record-page
        # output fields parse (they were invisible before), and the map predicts how to FILL a
        # field -- it carries no notion of page MODE. Comparing "type this value" against a
        # rendered value that has no input is a page-kind question, not a keyword-routing
        # disagreement, so it is COULD-NOT-COMPARE and leaves the denominator with its count
        # stated. Measured the moment 1B landed: 50 of 116 disagreements were exactly this.
        read_mode = bool(r.get('hint_verify')) and not r.get('hint_fill')
        if read_mode and p['keyword'] not in ('ClickText', 'ClickItem'):
            read_mode_skipped += 1
            continue
        # the rendered side is compared INTENT-FIRST -- a metadata prediction that names a FILL
        # rung is answered by the element's own hint_fill, not by whichever locator strategy
        # happened to sort first. `first_hint` stays the legacy comparand.
        rendered_kw = r.get('hint_fill') or r['first_hint']
        if _same_keyword(p['keyword'], r['first_hint']):
            agree += 1
        else:
            dis += 1
            dis_rows.append({'label': p['label'], 'predicted': p['keyword'],
                             'rendered_hint': r['first_hint']})
        if _same_keyword(p['keyword'], rendered_kw, intent_aware=True):
            agree_intent += 1
        else:
            dis_intent += 1

    shapes = {}
    for r in extra:
        shapes[r['shape']] = shapes.get(r['shape'], 0) + 1

    row.update({
        'status': 'TIED',
        'predicted_total': len(preds),
        'predicted_and_rendered': len(hit),
        'predicted_not_rendered': len(miss),
        'rendered_not_predicted': len(extra),
        'coverage': len(hit) / len(preds) if preds else None,
        'keyword_agree': agree, 'keyword_disagree': dis,
        'keyword_agree_intent': agree_intent, 'keyword_disagree_intent': dis_intent,
        'keyword_read_mode_skipped': read_mode_skipped,
        'unpredicted_shapes': dict(sorted(shapes.items(), key=lambda kv: -kv[1])),
        # B5: the misses split into "the tab was never opened" and everything else. The second
        # number is the one that is actually a metadata question; the first was always a false
        # miss and is now SAID so rather than silently inflating the denominator.
        'predicted_not_rendered_behind_closed_tab':
            sum(1 for p in miss if p.get('behind_closed_tab')),
        'predicted_not_rendered_genuine':
            sum(1 for p in miss if not p.get('behind_closed_tab')),
        'coverage_excl_closed_tabs': (
            len(hit) / (len(hit) + sum(1 for p in miss if not p.get('behind_closed_tab')))
            if (len(hit) + sum(1 for p in miss if not p.get('behind_closed_tab'))) else None),
        **breakdowns(preds, rendered, hit, miss, extra),
        'missed_labels': [p['label'] for p in miss][:40],
        'keyword_disagreements': dis_rows[:15],
        'notes': notes,
    })
    return row


# ---------------------------------------------------------------- org attribution
ORG_BY_DIR = {
    'dev1-omnistudio': 'dev1', 'dev1-zoo-omni': 'dev1', 'dev1-experience': 'dev1',
    'fsc7f-omnistudio': 'fsc7f', 'slockard-zoo-v3': 'slockard',
    'slockard-recorder': 'slockard', 'cicd-demo': 'cicd-demo', 'aura-pack': 'slockard',
}
NO_ORG_DIR = {'web-datatables', 'web-material-angular', 'web-ant-design',
              'qweb-hard-site', 'customer-cpq'}


def org_for(capture: str):
    parts = os.path.normpath(capture).split(os.sep)
    fname = parts[-1]
    d = parts[-2] if len(parts) >= 2 else ''
    if d in NO_ORG_DIR:
        return None
    if '__' in fname:
        return fname.split('__', 1)[0]
    if d in ORG_BY_DIR:
        return ORG_BY_DIR[d]
    if d in ('components', 'wave3') and len(parts) >= 3:
        return ORG_BY_DIR.get(parts[-3])
    if d == 'dom-captures':
        return 'dev1'  # BREADTH.md org column, 2026-09-05
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--capture')
    ap.add_argument('--org')
    ap.add_argument('--object')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--captures-dir', default='docs/dom-captures')
    ap.add_argument('--corpus', help='a text file listing capture paths (one per line) -- a FROZEN corpus so a quoted '
                    'rate can be re-derived later; the default --all scan drifts as captures are added '
                    '(21 -> 141 between B5 and L2-K4 on 2026-09-07)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--no-b5-layers', action='store_true',
                    help='ignore the B5 page-inventory layers (app_chrome, related_list_actions, '
                         'list_view_chrome, control_tabs) even when the map carries them -- this '
                         'is how the BEFORE half of the before/after table is measured: same '
                         'tool, same captures, one switch')
    a = ap.parse_args(argv)
    if a.no_b5_layers:
        global PAGE_CHROME
        PAGE_CHROME = None

    if not a.all and not a.capture:
        ap.error('pass --capture <file> --org <alias>, or --all')

    if a.capture:
        rows = [assess(a.capture, a.org or org_for(a.capture), a.object)]
    else:
        files = []
        if a.corpus:
            # frozen list: the rate is re-derivable later whatever lands under docs/dom-captures
            with open(a.corpus, encoding='utf-8') as fh:
                files = [ln.strip() for ln in fh if ln.strip() and not ln.startswith('#')]
            missing = [f for f in files if not os.path.exists(f)]
            if missing:
                print('COULD-NOT-CHECK: %d corpus file(s) missing: %s' % (len(missing), missing[:3]), file=sys.stderr)
                files = [f for f in files if os.path.exists(f)]
        else:
            for root, _dirs, names in os.walk(a.captures_dir):
                for n in sorted(names):
                    if n.endswith('.html'):
                        files.append(os.path.join(root, n))
        rows = []
        for f in sorted(files):
            try:
                rows.append(assess(f, org_for(f)))
            except Exception as exc:  # a parse failure is could-not-tie, never a pass
                rows.append({'capture': f, 'status': COULD_NOT_TIE,
                             'reason': 'parse error: %s' % exc})

    tied = [r for r in rows if r.get('status') == 'TIED']
    P = sum(r['predicted_total'] for r in tied)
    H = sum(r['predicted_and_rendered'] for r in tied)
    R = sum(r['rendered_total'] for r in tied)
    E = sum(r['rendered_not_predicted'] for r in tied)
    KA = sum(r['keyword_agree'] for r in tied)
    KD = sum(r['keyword_disagree'] for r in tied)
    KAI = sum(r.get('keyword_agree_intent', 0) for r in tied)
    KDI = sum(r.get('keyword_disagree_intent', 0) for r in tied)
    KRM = sum(r.get('keyword_read_mode_skipped', 0) for r in tied)
    shapes = {}
    for r in tied:
        for k, v in r['unpredicted_shapes'].items():
            shapes[k] = shapes.get(k, 0) + v

    # C1, 2026-09-22 (docs/audit/challenge-2026-09-22-prior-work/C1-f229-numbers.md):
    # `breakdowns()` drops every rendered control with no `norm` from `by_family`'s own
    # denominator (unlabelled, matched to nothing), while `dom_explained_by_metadata` above
    # keeps `rendered_total` as-is and silently counts every one of those dropped controls as
    # EXPLAINED by metadata. Neither number is changed here -- both are disclosed side by side,
    # with the gap between their denominators named.
    bd = merge_breakdowns(tied)
    disclosure = family_basis_disclosure(R, bd['by_family'])

    summary = {
        'captures_total': len(rows), 'tied': len(tied),
        'could_not_tie': len(rows) - len(tied),
        'predicted_total': P, 'predicted_and_rendered': H,
        'predicted_not_rendered': P - H,
        'rendered_total': R, 'rendered_not_predicted': E,
        'rendered_without_norm': disclosure['rendered_without_norm'],
        'rendered_without_norm_note': (
            "rendered controls with no norm (unlabelled, matched to nothing) are excluded from "
            "by_family's own denominator but are still counted as EXPLAINED inside "
            "dom_explained_by_metadata (whose denominator is the unfiltered rendered_total); "
            "dom_explained_by_metadata_by_family_basis below is the same numerator/denominator "
            "shape recomputed on by_family's basis instead, and the two rates differ by exactly "
            "this gap."
        ),
        'rates': {
            'metadata_coverage_of_predictions': {
                'k': H, 'n': P, 'rate': (H / P if P else None),
                'wilson95': wilson(H, P) if P >= 10 else None},
            'dom_explained_by_metadata': {
                'k': R - E, 'n': R, 'rate': ((R - E) / R if R else None),
                'wilson95': wilson(R - E, R) if R >= 10 else None},
            'dom_explained_by_metadata_by_family_basis': disclosure['by_family_basis'],
            'keyword_agreement': {
                'k': KA, 'n': KA + KD, 'rate': (KA / (KA + KD) if (KA + KD) else None),
                'wilson95': wilson(KA, KA + KD) if (KA + KD) >= 10 else None},
            # stream 2A: the same population under the INTENT-AWARE comparison (a metadata fill
            # prediction is answered by the element's own hint_fill; two click strategies are one
            # answer). Reported beside the legacy rate, never instead of it.
            'keyword_agreement_intent_aware': {
                'k': KAI, 'n': KAI + KDI, 'rate': (KAI / (KAI + KDI) if (KAI + KDI) else None),
                'wilson95': wilson(KAI, KAI + KDI) if (KAI + KDI) >= 10 else None},
        },
        'keyword_read_mode_could_not_compare': KRM,
        'unpredicted_shapes': dict(sorted(shapes.items(), key=lambda kv: -kv[1])),
        **bd,
    }
    out = {'summary': summary, 'pages': rows}
    if a.out:
        d = os.path.dirname(a.out)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(a.out, 'w') as fh:
            json.dump(out, fh, indent=1)
    if a.json:
        print(json.dumps(out, indent=1))
        return 0
    print('captures %(captures_total)d | tied %(tied)d | COULD-NOT-TIE %(could_not_tie)d' % summary)
    print('rendered_without_norm: %d  (%s)'
          % (summary['rendered_without_norm'], summary['rendered_without_norm_note']))
    for name, d in summary['rates'].items():
        w = d['wilson95']
        if w:
            detail = '%.3f  95%% CI [%.3f, %.3f]' % (d['rate'], w[0], w[1])
        elif d['rate'] is not None:
            detail = '%.3f  (n<10, NOT PUBLISHED)' % d['rate']
        else:
            detail = 'COULD-NOT-CHECK'
        print('  %-34s %4s/%-5s %s' % (name, d['k'], d['n'], detail))
    print('\nDOM explained, by family class (the denominator that answers "can metadata name it"):')
    for fc, d in sorted(summary['by_family'].items()):
        w = d.get('wilson95')
        ci = ('  95%% CI [%.3f, %.3f]' % (w[0], w[1])) if w else ''
        print('  %-10s rendered %5d  predicted-and-rendered %5d  coverage %s%s'
              % (fc, d['rendered'], d['predicted_and_rendered'],
                 ('%.3f' % d['coverage']) if d['coverage'] is not None else 'COULD-NOT-CHECK', ci))
    print('\npredictions by map layer (rendered / predicted; unique = no other layer named it):')
    for sname, d in sorted(summary['by_source'].items(), key=lambda kv: -kv[1]['predicted']):
        print('  %-24s %5d / %-5d  unique %4d  behind closed tab %4d'
              % (sname, d['rendered'], d['predicted'], d['unique'], d['behind_closed_tab']))
    print('\nunpredicted DOM controls by shape:')
    for k, v in summary['unpredicted_shapes'].items():
        print('  %-32s %d' % (k, v))
    return 0


if __name__ == '__main__':
    sys.exit(main())
