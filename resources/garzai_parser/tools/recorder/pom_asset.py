"""pom_asset -- build the PERSISTENT page-object asset from committed captures, and measure it.

Usage:
  python3 tools/recorder/pom_asset.py build    --captures <dir|glob> --org <alias> [--state-root DIR]
  python3 tools/recorder/pom_asset.py lookup   --org <alias> --page-key '<key>' [--state-root DIR]
  python3 tools/recorder/pom_asset.py coverage --captures <dir|glob> --org <alias> [--bar 0.6]
                                               [--state-root DIR] [--json OUT]

WHY (measured, docs/recorder/evidence/metadata-dom-parity-2026-09-07.md and
app-scan-report-2026-09-07.md): the org map names 16.4% of what renders, 632 rendered buttons are
unmapped, and 0 of 172 scanned pages are metadata-predictable. No Salesforce metadata declares what
a custom LWC renders. So the knowledge must come from CAPTURED pages and be PERSISTED, keyed by
page, so a known page is never relearned.

THIS EXTENDS, IT DOES NOT REPLACE. The asset is the POM store that already exists:
  tools/recorder/pom/keys.py   -- the page key (org alias | url pattern | rt= | layout=)
  tools/recorder/pom/store.py  -- one JSON per page key, merged never overwritten, ladder rungs
                                  with per-rung verdict history
merge_session() already writes RECORDED knowledge into it. This module adds the second writer --
CAPTURE-derived knowledge -- so the 141 committed captures stop being dead bytes, plus the reader
(`lookup`) and the number (`coverage`).

`docs/dom-captures/*.pom.json` (13 files, minerVersion 1.0) are a per-CAPTURE precursor of the same
idea: same ladder shape (primary + backups), but keyed by capture filename, with no page key, no
verdict, no date, no provenance and no merge. They are an INPUT here, not a rival store.

The honest coverage number is HELD OUT. An asset built from a capture trivially "knows" that same
capture's controls -- the project's signature vacuous green. `coverage` therefore groups captures by
PAGE KEY, builds from all-but-one and scores the held-out one; a page key with a single capture is
COULD-NOT-CHECK, never a pass. `--self` prints the vacuous number too, labelled as vacuous.

Capability check (2026-09-07, W11): `garzai can "page object model asset persistent locators"`
returned skills (sf-dom-patterns, sf-metadata-locators) and `discover.py derive` -- no builder that
turns captures into page-keyed asset records. tools/recorder/pom/store.py is the provider being
extended.
"""
from __future__ import annotations

import argparse
import glob as _glob
import hashlib
import json
import os
import re
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for _p in ('tools/interop/resources/pythonDom', 'tools/benchmark', 'tools/qforce-lite',
           'tools/recorder'):
    _abs = os.path.join(_ROOT, _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

from capture_orchestration import parse_elements_from_html  # noqa: E402
import metadata_dom_parity as PARITY                        # noqa: E402
from pom import keys as K                                   # noqa: E402
from pom.store import Store, element_id, stable_attrs       # noqa: E402
from pom import store as STORE_MOD                          # noqa: E402  -- apply_capture_stamp

ASSET_VERSION = 1
SOURCE_CAPTURE = 'capture'

# Path shapes only Salesforce serves, used to classify a capture that carries no `host:` header.
# Measured over the committed corpus (docs/dom-captures, 2026-09-12): /lightning/ x11, /flow/ x1.
# Deliberately conservative -- a shape that is not proven Salesforce stays unknown, because a
# wrong "yes" attributes a third-party page to a real org's page-object model, while a wrong
# "no" merely files it under apps/unknown-host/ where it is visible and greppable.
SF_PATH = re.compile(r'^/(?:lightning|apex|flow|setup|servlet|secur|one|_ui|services)(?:/|$)')


# --------------------------------------------------------------------------- capture reading
def capture_meta(path: str) -> dict:
    head = open(path, errors='replace').read(4000)
    out = PARITY.capture_header(head)
    m = re.search(r'<!--\s*url:\s*(.*?)\s*-->', head)
    if m:
        out['url'] = m.group(1)
    m = re.search(r'<!--\s*org:\s*(.*?)\s*-->', head)
    if m:
        out['org'] = m.group(1)
    # The capture ALWAYS writes `<!-- host: ... -->` (cdp_capture.py), and this reader used to
    # ignore it. With no `url` the caller fabricated `https://unknown-host.lightning.force.com<path>`
    # -- a SALESFORCE host -- so `sf` became True, the holder's org alias became authoritative, and a
    # robotic.copado.com capture was filed under `slockard|/ai/...` in org-map/slockard/pom/ while
    # merge_session wrote the same page to apps/robotic.copado.com/pom/. One page, two records,
    # silently (measured 2026-09-12: 583 elements in one, 7 in the other).
    # The org alias belongs to the HOLDER -- `up.py <org>` binds one browser to one alias and stamps
    # every capture with it -- not to the page. They coincide for a Salesforce page in that org and
    # diverge for any third-party app driven from the same browser.
    if not out.get('url'):
        m = re.search(r'<!--\s*host:\s*(.*?)\s*-->', head)
        host = (m.group(1) if m else '').strip()
        if host and out.get('path'):
            out['url'] = 'https://%s%s' % (host, out['path'])
    out.update(state_stamp(head))
    return out


# THE STATE STAMP (user, 2026-09-18). cdp_capture.py writes exactly one line:
#   <!-- state: <name> | entered_via: <label> | host_url: <url> -->
# An older capture has no such line; it reads back as the default state with an unknown opener,
# which is the truth about it, not a silent zero.
_STAMP = re.compile(r'<!--\s*state:\s*(?P<state>.*?)\s*\|\s*entered_via:\s*(?P<via>.*?)\s*'
                    r'(?:\|\s*host_url:\s*(?P<host>.*?)\s*)?-->')


def state_stamp(head: str) -> dict:
    """{state, entered_via, host_url} off a capture header. Never raises, never invents."""
    m = _STAMP.search(head or '')
    if not m:
        return {'state': 'default', 'entered_via': 'unknown', 'host_url': '',
                'state_stamp_present': False}
    return {'state': (m.group('state') or 'default').strip() or 'default',
            'entered_via': (m.group('via') or 'unknown').strip() or 'unknown',
            'host_url': (m.group('host') or '').strip(),
            'state_stamp_present': True}


def template_provenance(path: str) -> dict:
    """T18: a record says which template rendered it -- name AND content hash. The name alone
    cannot tell two revisions of the same template apart."""
    body = open(path, 'rb').read()
    name = None
    try:
        import parser_scorecard as SC
        name = (SC.score_capture_v3(path) or {}).get('template')
    except Exception:
        name = None
    return {'name': name, 'hash': hashlib.sha1(body).hexdigest()[:12]}


_CTRL_CACHE: dict[str, list[dict]] = {}


def known_aliases() -> set:
    return {os.path.splitext(os.path.basename(f))[0]
            for f in _glob.glob(os.path.join(K.ORG_MAP_DIR, '*.json'))}


def org_for(path: str) -> str | None:
    """Org attribution, header first. metadata_dom_parity.org_for's `<prefix>__file.html` rule is
    the breadth convention; the zoo component captures use `Component__variant.html`, so that rule
    invents an org named after an LWC. An attribution is only accepted when it names an org we
    actually hold a map for (else None -- COULD-NOT-CHECK beats a wrong partition)."""
    hdr = capture_meta(path).get('org')
    if hdr:
        return hdr
    aliases = known_aliases()
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    fname = parts[-1]
    # the breadth `<org>__file.html` rule ONLY when the prefix names an org we hold a map for
    if '__' in fname and fname.split('__', 1)[0] in aliases:
        return fname.split('__', 1)[0]
    # else the directory attribution, walking up (components/ and wave3/ sit under the app dir)
    for d in reversed(parts[:-1]):
        if d in PARITY.NO_ORG_DIR:
            return None
        if d in PARITY.ORG_BY_DIR:
            return PARITY.ORG_BY_DIR[d]
        if d in aliases:
            return d
        if d == 'dom-captures':
            return 'dev1'          # BREADTH.md org column, 2026-09-05
    return None


def controls(path: str) -> list[dict]:
    """Rendered controls with a label -- the same denominator metadata_dom_parity uses, so the two
    halves of the coverage number are comparable."""
    if path in _CTRL_CACHE:
        return _CTRL_CACHE[path]
    els = parse_elements_from_html(open(path, errors='replace').read())
    out = []
    for e in els:
        ident = e.get('identification') or {}
        label = ident.get('label_text') or ''
        n = PARITY.norm(label)
        if not n:
            continue
        hints = ((e.get('qforce_hints') or {}).get('locator_options') or [])
        det = e.get('element_details') or {}
        out.append({
            'label': label, 'norm': n,
            'family': e.get('element_type'),
            'tag': det.get('tag'),
            'attrs': det.get('attributes') or {},
            'container': (e.get('context') or {}).get('section') or '',
            'shape': PARITY.shape_of(e),
            'hints': hints,
            # D14 2026-09-09: the ladder builder needs group_size/index/anchor_candidates,
            # so the block travels with the control instead of being re-derived.
            'disambiguation': e.get('disambiguation') or {},
        })
    _CTRL_CACHE[path] = out
    return out


def page_key_for(path: str, org: str | None) -> dict | None:
    meta = capture_meta(path)
    url = meta.get('url')
    org = org or org_for(path)
    if not url:
        p = meta.get('path')
        if not p:
            return None
        # No host header: classify from the PATH, which is real evidence, never from a made-up
        # hostname. This line used to fabricate `https://unknown-host.lightning.force.com<path>`
        # for EVERY hostless capture -- a SALESFORCE suffix -- so keys.page_key correctly read
        # `salesforce: True` off a lying input, took the org-alias branch, and filed a
        # robotic.copado.com page as `slockard|/ai/...` in org-map/slockard/pom/, rendering 583
        # third-party controls into that org's committed doc (measured 2026-09-12).
        # The org alias belongs to the HOLDER -- `up.py <org>` binds one browser to one alias and
        # stamps every capture with it -- never to the page. They coincide for a Salesforce page
        # in that org and diverge for any third-party app driven from the same browser.
        # A Salesforce-shaped path keeps the org-alias partition (dev1 and slockard share URL
        # patterns and must never collide -- user, 2026-09-05); anything else is an unknown host,
        # which keys.py partitions into apps/unknown-host/: plainly unknown, greppable, and
        # attributed to no org.
        if SF_PATH.match(p):
            url = 'https://unknown-host.lightning.force.com' + p
        else:
            url = 'https://unknown-host' + p
            org = None
    pk = K.page_key(url, org=org)
    pk['_capture'] = path
    pk['_org'] = org
    return pk


# --------------------------------------------------------------------------- record building
def ladder_from_hints(c: dict) -> list[dict]:
    """One rung per locator option the parser proposes, in its order, plus the read-back the
    project requires of any value-returning keyword (a rung with no read-back is not a rung).

    D14, 2026-09-09 (docs/DECISIONS.md). Two things changed here:

      * the rung's disambiguator for a REPEATED control is `index` -- the member's 1-based
        position among the same-label matches, which the parser now emits instead of a baked
        text anchor. An executor turns it into QWeb's numeric anchor (`anchor="<n>"`, which is
        QWeb's documented index mode -- QWeb/keywords/text.py:357, 929) when it builds the real
        call. A control that does NOT repeat gets neither: `kwargs` stays empty.
        The old code put `c['container']` -- the section heading -- into every rung's `anchor`
        whether the control repeated or not, which is both a prescription and, for 76.6% of
        controls, pure cost (CLAUDE.md: "a control that occurs once needs none").
      * every rung a CAPTURE produced is verdict-pending and says so: `last_verdict`
        'COULD-NOT-CHECK', `n_verified` 0, plus an explicit `verdict_pending` flag a drafter
        can read without inferring it from three counters. It clears on the first live
        read-back that `Store.merge_session` records.
    """
    rungs = []
    dis = c.get('disambiguation') or {}
    repeated = (dis.get('group_size') or 1) > 1
    index = dis.get('index') if repeated else None
    for i, h in enumerate(c['hints']):
        kw = h.get('keyword')
        if not kw:
            continue
        rungs.append({
            'kw': kw,
            'args': [h.get('locator') or c['label']],
            'kwargs': {'index': index} if index else {},
            'why': h.get('why'),
            'read_back': read_back_for(kw, c),
            # D14: the anchor TEXTS the page offers, as candidates a caller may choose --
            # never one elected by the parser. `anchor` stays None until a live run proves one.
            'anchor': None,
            'anchor_candidates': h.get('anchor_candidates') or dis.get('anchor_candidates') or [],
            'score': None,
            'n_verified': 0, 'n_failed': 0, 'n_unverified': 1,
            'last_verdict': 'COULD-NOT-CHECK',
            'verdict_pending': True,
            'confidence': h.get('confidence') or 'unverified',
            'last_seen': None,
            'failure_signal': None,
            'origin': SOURCE_CAPTURE,
            'rank': i,
        })
    return rungs


READ_BACK = {
    'TypeText': 'GetFieldValue', 'Type Text Clearing': 'GetFieldValue',
    'PickList': 'GetFieldValue', 'ComboBox': 'GetFieldValue',
    'Set Datetime': 'GetFieldValue', 'Omni Type': 'GetFieldValue',
    'Omni Select': 'GetFieldValue', 'ClickCheckbox': 'GetFieldValue',
}


def read_back_for(kw: str, c: dict) -> dict | None:
    rb = READ_BACK.get(kw)
    if not rb:
        return None
    return {'kw': rb, 'args': [c['label']], 'compare': 'equals-requested'}


def build_record(store: Store, pk: dict, cs: list[dict], meta: dict, tmpl: dict,
                 predicted_by_norm: dict, capture_rel: str) -> dict:
    rec = store._open(pk)
    rec.setdefault('asset', {})
    a = rec['asset']
    a['version'] = ASSET_VERSION
    a['built_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    a['builder'] = 'tools/recorder/pom_asset.py'
    a.setdefault('captures', [])
    if capture_rel not in a['captures']:
        a['captures'].append(capture_rel)
    a['template'] = tmpl
    a['invalidation'] = {
        'layout_hash': pk.get('layout_hash'),
        'template_hash': tmpl.get('hash'),
        'map_built_at': (K.load_org_map(pk.get('alias')) or {}).get('built_at'),
        'rule': ('STALE when the page key layout= component changes, when the template hash '
                 'changes, or when any rung read-back fails live'),
    }
    rec['page']['title'] = meta.get('title')
    rec['last_seen'] = a['built_at']
    # THE STATE STAMP travels from the capture header into the record (user, 2026-09-18). Until
    # now this writer recorded `states`/`links`/`opens`/`leads_to` NEVER -- a capture is one
    # instant of one state of a page and the record had no field saying which state that instant
    # was, so two captures of the same page in two states merged into one flat control set
    # (docs/audit/pom-states-and-modals-2026-09-18.md section 3, W2).
    a['state_stamp'] = {k: meta.get(k) for k in ('state', 'entered_via', 'host_url')}
    a['state_stamp']['present'] = bool(meta.get('state_stamp_present'))
    stamped_eids = []

    for c in cs:
        # On a single-surface app the "container" is whatever prose surrounded the control on this
        # visit (a chat message, a run card), not structure -- so it must not enter the identity or
        # every visit mints a new id and the asset relearns a page it already knows.
        eid = element_id(c['family'], c['label'], c['container'], c['attrs'],
                         drop_container=(K.single_surface_prefix(pk.get("host"), pk.get("pattern") or "")
                                         and not pk.get('salesforce')))
        el = rec['elements'].setdefault(eid, {})
        # a `capture-stamp` placeholder another page's stamp left behind for this control is
        # folded in here, so one control is never two records (store.absorb_stamp_placeholder)
        STORE_MOD.absorb_stamp_placeholder(rec, eid, c['label'])
        stamped_eids.append(eid)
        pred = predicted_by_norm.get(c['norm'])
        el.update({
            'family': c['family'], 'label': c['label'], 'container': c['container'],
            'attrs': stable_attrs(c['attrs']), 'tag': c['tag'], 'shape': c['shape'],
            'source': el.get('source') if el.get('source') in ('recorded', 'live') else SOURCE_CAPTURE,
            'evidence': sorted(set((el.get('evidence') or []) + [capture_rel])),
            'verdict': el.get('verdict') or 'COULD-NOT-CHECK',
            'verdict_date': el.get('verdict_date') or a['built_at'],
            'metadata': ({'api_name': pred.get('api_name'), 'predicted_keyword': pred.get('keyword'),
                          'meta_type': pred.get('meta_type')} if pred else None),
            'n_seen': (el.get('n_seen') or 0) + 1,
            'last_seen': a['built_at'],
        })
        el.setdefault('effects', {})
        existing = {(r.get('kw'), tuple(r.get('args') or [])) for r in (el.get('ladder') or [])}
        ladder = list(el.get('ladder') or [])
        for r in ladder_from_hints(c):
            if (r['kw'], tuple(r['args'])) not in existing:
                ladder.append(r)
        # metadata ROUTES the keyword; the asset supplies what metadata cannot see. When the map
        # names this control, its keyword goes on top of the ladder -- the parity run measured the
        # map right ~70% of the time where both name a control, and right about compound controls
        # (date -> Set Datetime) where the DOM hint alone says TypeText and half-sets the value.
        if pred and pred.get('keyword') not in (None, 'unrouted', 'component-specific'):
            mk = (pred['keyword'], tuple([c['label']]))
            dup = next((r for r in ladder
                        if (r.get('kw'), tuple(r.get('args') or [])) == mk), None)
            if dup is not None:
                # 2026-09-07 (stream P1, wave-2 close). When the map and the DOM hint land on the
                # SAME (keyword, args) the rung was silently skipped, so the control ended up with
                # NO metadata-origin rung at all -- the map agreeing with the DOM read as the map
                # never having spoken. Caught when P1's label policy made ClickText the DOM's first
                # hint for header controls the map also routes to ClickText: every metadata rung on
                # 04-account-new-record-modal.html vanished. Agreement is a CONFIRMATION, so the
                # existing rung is promoted and attributed, never dropped.
                dup['origin'] = 'metadata'
                dup['why'] = ('org map routes this control and the DOM hint agrees '
                              '(metadata routes, DOM backstops)')
                dup['rank'] = -1
                ladder.remove(dup)
                ladder.insert(0, dup)
            else:
                ladder.insert(0, {'kw': pred['keyword'], 'args': [c['label']], 'kwargs': {},
                                  'why': 'org map routes this control (metadata routes, DOM backstops)',
                                  'read_back': read_back_for(pred['keyword'], c),
                                  'anchor': c['container'] or None, 'score': None,
                                  'n_verified': 0, 'n_failed': 0, 'n_unverified': 1,
                                  'last_verdict': 'COULD-NOT-CHECK', 'last_seen': None,
                                  'failure_signal': None, 'origin': 'metadata', 'rank': -1})
        el['ladder'] = ladder
    rec['_stamp'] = STORE_MOD.apply_capture_stamp(
        store, rec, stamped_eids, state=meta.get('state'), entered_via=meta.get('entered_via'),
        host_url=meta.get('host_url'), org=pk.get('alias'), stamp=a['built_at'],
        evidence=capture_rel)
    return rec


def predictions_for(pk: dict, path: str) -> dict:
    """norm-label -> predicted control, from the org map. Empty when the map cannot tie."""
    org, obj = pk.get('alias'), pk.get('object')
    if not org or not obj:
        return {}
    try:
        preds, _ = PARITY.predict(org, obj, PARITY.page_kind(pk.get('pattern') or '',
                                                             os.path.basename(path)))
    except Exception:
        return {}
    return {p['norm']: p for p in preds if p.get('norm')}


# --------------------------------------------------------------------------- the reader
def verified_labels(capture: str, org: str | None = None, state_root: str | None = None) -> set:
    """NORMALISED labels on this capture's page key that a LIVE run has already resolved and
    read back -- the ONLY input that may turn a parser hint's `confidence` (or
    `disambiguation.resolution`) from 'unverified' into 'verified' (D14, 2026-09-09).

    A label qualifies when the POM store holds an element for this page key whose ladder has a
    rung with `n_verified` > 0. That counter is incremented in exactly one place --
    `Store.merge_session`, when a recorded step's own verdict was VERIFIED-PASS or
    PASS-GUARDED -- so 'verified' can only ever mean "a run did this and read the value back".
    A capture-derived rung (`origin: 'capture'`) never has it.

    Returns an empty set when there is no record, which is what an honest parse of a page
    nobody has driven should produce.

    Usage:
      from pom_asset import verified_labels
      parse_elements_from_html(html, verified_labels=verified_labels(capture, org))
    """
    pk = page_key_for(capture, org)
    if not pk:
        return set()
    store = Store(state_root=state_root)
    if state_root:
        pk = _repartition(store, pk)
    rec = store.get(pk['key'], org=pk.get('alias'))
    if rec is None:
        return set()
    out = set()
    for e in (rec.get('elements') or {}).values():
        if any((r.get('n_verified') or 0) > 0 for r in (e.get('ladder') or [])):
            n = PARITY.norm(e.get('label') or '')
            if n:
                out.add(n)
    return out


def consult(capture: str, org: str | None = None, state_root: str | None = None) -> dict:
    """THE READER. Before any consumer declares a page needs a recorded pass, ask the asset what it
    already knows about that page key -- and say which controls.

    `exclude_self`: a control whose ONLY evidence is this same capture is not knowledge, it is the
    capture read back to itself. Those are excluded, so a first-ever capture consults an asset that
    honestly knows nothing about it.
    """
    pk = page_key_for(capture, org)
    if not pk:
        return {'asset': 'COULD-NOT-CHECK', 'reason': 'no url/path header on the capture'}
    store = Store(state_root=state_root)
    if state_root:
        pk = _repartition(store, pk)
    rec = store.get(pk['key'], org=pk.get('alias'))
    cs = controls(capture)
    rendered = {c['norm'] for c in cs}
    if rec is None:
        return {'asset': 'MISS', 'page_key': pk['key'], 'rendered': len(rendered),
                'known': 0, 'known_labels': [], 'known_rate': 0.0,
                'reason': 'no asset record for this page key'}
    rel = os.path.relpath(os.path.abspath(capture), _ROOT)
    known = {}
    for e in (rec.get('elements') or {}).values():
        ev = [x for x in (e.get('evidence') or []) if x != rel]
        if not ev and (e.get('source') == SOURCE_CAPTURE):
            continue                        # only this capture vouches for it -- not knowledge
        n = PARITY.norm(e.get('label') or '')
        if n in rendered:
            known[n] = {'label': e.get('label'), 'family': e.get('family'),
                        'source': e.get('source'), 'verdict': e.get('verdict'),
                        'top_rung': (e.get('ladder') or [{}])[0].get('kw')}
    return {'asset': 'HIT' if known else 'MISS', 'page_key': pk['key'],
            'rendered': len(rendered), 'known': len(known),
            # D14 2026-09-09: the labels a LIVE run has verified on this page key. Hand them to
            # parse_elements_from_html(verified_labels=...) -- nothing else may say 'verified'.
            'verified_labels': sorted(verified_labels(capture, org, state_root)),
            'known_rate': round(len(known) / len(rendered), 3) if rendered else None,
            'known_labels': [v['label'] for v in list(known.values())[:25]],
            'known_detail': list(known.values())[:25],
            'evidence_captures': (rec.get('asset') or {}).get('captures', [])[:10],
            'built_at': (rec.get('asset') or {}).get('built_at'),
            'note': ('controls vouched for ONLY by this same capture are excluded -- an asset '
                     'cannot know a page from the page it is being asked about')}


# --------------------------------------------------------------------------- commands
def resolve_captures(spec: str) -> list[str]:
    if os.path.isdir(spec):
        return sorted(_glob.glob(os.path.join(spec, '**', '*.html'), recursive=True))
    return sorted(_glob.glob(spec, recursive=True))


def cmd_build(a) -> int:
    store = Store(state_root=a.state_root)
    caps = resolve_captures(a.captures)
    written, skipped = {}, []
    for path in caps:
        pk = page_key_for(path, a.org)
        if not pk:
            skipped.append((os.path.relpath(path, _ROOT), 'no url/path header -- not a page'))
            continue
        rel = os.path.relpath(path, _ROOT)
        if store.state_root != K.STATE:                    # scratch root: repartition
            pk = _repartition(store, pk)
        cs = controls(path)
        rec = build_record(store, pk, cs, capture_meta(path), template_provenance(path),
                           predictions_for(pk, path), rel)
        p = store.put(rec)
        written[pk['key']] = {'path': p, 'elements': len(rec['elements']), 'from_capture': len(cs),
                              # the state stamp: what this capture said, and what the store did
                              # with it. Printed, never only written -- a capture that could not
                              # name its opener says so on the caller's screen.
                              'state_stamp': rec.get('_stamp')}
    # never slice a JSON string to a length -- that is how a tool prints something no consumer
    # can parse and still looks like it worked. Trim the DATA, then dump.
    recs = dict(list(written.items())[:40])
    print(json.dumps({'captures': len(caps), 'page_keys': len(written),
                      'skipped': skipped[:10], 'skipped_n': len(skipped),
                      'records_shown': len(recs), 'records': recs}, indent=1))
    return 0


def _repartition(store: Store, pk: dict) -> dict:
    part = pk['alias'] or pk['host'] or 'unknown-host'
    base = store.org_map_dir if pk['alias'] else store.apps_dir
    pk['store_dir'] = os.path.join(base, part, 'pom')
    pk['path'] = os.path.join(pk['store_dir'], pk['slug'] + '.json')
    return pk


def cmd_lookup(a) -> int:
    store = Store(state_root=a.state_root)
    rec = store.get(a.page_key, org=a.org)
    if rec is None:
        print(json.dumps({'found': False, 'page_key': a.page_key,
                          'note': 'no asset record -- this page has never been captured or driven; '
                                  'it needs a recorded pass'}, indent=1))
        return 1
    omap = K.load_org_map(a.org)
    cur_layout = K.layout_hash(omap, (rec.get('page') or {}).get('object'),
                               (rec.get('page') or {}).get('record_type'))
    inv = (rec.get('asset') or {}).get('invalidation') or {}
    stale = bool(inv.get('layout_hash')) and cur_layout is not None and cur_layout != inv['layout_hash']
    print(json.dumps({'found': True, 'page_key': (rec.get('page') or {}).get('key'),
                      'stale': stale,
                      'stale_reason': ('layout hash %s -> %s' % (inv.get('layout_hash'), cur_layout))
                                      if stale else None,
                      'asset': rec.get('asset'),
                      'elements': len(rec.get('elements') or {}),
                      'controls': sorted({(e.get('label') or '') for e in (rec.get('elements') or {}).values()}),
                      # where the page's controls lead, and which states it has (store.py
                      # merge_session): a consult sees `Commit Changes` ->
                      # na.devops.copado.com|/en/commit/{id}, a page key in ANOTHER partition,
                      # without opening the render
                      'links': rec.get('links') or {},
                      'states': rec.get('states') or {},
                      'record': rec if a.full else '(pass --full for the whole record)',
                      'path': rec.get('_path')}, indent=1, default=str))
    return 0


def cmd_coverage(a) -> int:
    """Per page: rendered controls known from the ASSET, from METADATA, from neither.

    HELD OUT: the asset scoring a capture is built from the OTHER captures of the same page key.
    A page key with one capture is COULD-NOT-CHECK -- never counted as a pass.
    """
    caps = resolve_captures(a.captures)
    by_key: dict[str, list[str]] = {}
    info: dict[str, dict] = {}
    for path in caps:
        pk = page_key_for(path, a.org)
        if not pk:
            continue
        by_key.setdefault(pk['key'], []).append(path)
        info[path] = pk

    pages, cnc = [], []
    for key, paths in sorted(by_key.items()):
        for path in paths:
            pk = info[path]
            cs = controls(path)
            if not cs:
                cnc.append({'capture': os.path.relpath(path, _ROOT), 'page_key': key,
                            'reason': 'no labelled controls parsed'})
                continue
            others = [p for p in paths if p != path]
            if not others:
                cnc.append({'capture': os.path.relpath(path, _ROOT), 'page_key': key,
                            'reason': 'only capture of this page key -- an asset built from it '
                                      'would score itself (vacuous); held-out score impossible'})
                continue
            known = set()
            for o in others:
                known |= {c['norm'] for c in controls(o)}
            pred = set(predictions_for(pk, path))
            rendered = {c['norm'] for c in cs}
            asset_only = rendered & known - pred
            meta_only = rendered & pred - known
            both = rendered & known & pred
            neither = rendered - known - pred
            n = len(rendered)
            pages.append({
                'capture': os.path.relpath(path, _ROOT), 'page_key': key,
                'org': pk.get('alias'), 'object': pk.get('object'),
                'rendered': n, 'held_out_from': len(others),
                'metadata_tieable': bool(pred),
                'asset_only': len(asset_only), 'metadata_only': len(meta_only),
                'both': len(both), 'neither': len(neither),
                'metadata_alone': round(len(rendered & pred) / n, 3),
                'asset_plus_metadata': round(len(rendered & (known | pred)) / n, 3),
            })

    bar = a.bar
    before = sum(1 for p in pages if p['metadata_alone'] >= bar)
    after = sum(1 for p in pages if p['asset_plus_metadata'] >= bar)
    tie = [p for p in pages if p['metadata_tieable']]
    out = {
        'bar': bar,
        'method': 'held-out: the asset scoring a capture is built from the other captures of the '
                  'same page key; single-capture page keys are COULD-NOT-CHECK',
        'captures_scanned': len(caps),
        'page_keys': len(by_key),
        'scored_pages': len(pages),
        'could_not_check': len(cnc),
        'pages_at_bar_metadata_alone': before,
        'pages_at_bar_asset_plus_metadata': after,
        'mean_metadata_alone': round(sum(p['metadata_alone'] for p in pages) / len(pages), 3) if pages else None,
        'mean_asset_plus_metadata': round(sum(p['asset_plus_metadata'] for p in pages) / len(pages), 3) if pages else None,
        # The map can only say anything at all about an object page it holds. Quoting the whole
        # corpus makes the metadata half look worse than it is, so the tieable subset is separate.
        'metadata_tieable_pages': len(tie),
        'tieable_at_bar_metadata_alone': sum(1 for p in tie if p['metadata_alone'] >= bar),
        'tieable_at_bar_asset_plus_metadata': sum(1 for p in tie if p['asset_plus_metadata'] >= bar),
        'tieable_mean_metadata_alone': round(sum(p['metadata_alone'] for p in tie) / len(tie), 3) if tie else None,
        'tieable_mean_asset_plus_metadata': round(sum(p['asset_plus_metadata'] for p in tie) / len(tie), 3) if tie else None,
        'pages': pages,
        'could_not_check_rows': cnc[:40],
    }
    if a.self:
        out['vacuous_self_coverage'] = {
            'value': 1.0,
            'note': 'an asset built from a capture knows that capture by construction -- printed '
                    'only to name the trap; never quote it',
        }
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, 'w') as f:
            json.dump(out, f, indent=1)
    slim = dict(out)
    slim['pages'] = out['pages'][:25]
    slim['pages_shown'] = len(slim['pages'])
    print(json.dumps(slim, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    b = sub.add_parser('build', help='build asset records from captures')
    b.add_argument('--captures', required=True, help='directory or glob of .html captures')
    b.add_argument('--org', help='org alias (else the capture header / path attribution)')
    b.add_argument('--state-root', help='override ~/.claude/state (tests, evidence runs)')
    b.set_defaults(fn=cmd_build)

    l = sub.add_parser('lookup', help='return the asset record for a page key')
    l.add_argument('--org', required=True)
    l.add_argument('--page-key', required=True, dest='page_key')
    l.add_argument('--state-root')
    l.add_argument('--full', action='store_true', help='include the whole record, ladders and all')
    l.set_defaults(fn=cmd_lookup)

    c = sub.add_parser('coverage', help='per page: controls known from asset vs metadata vs neither')
    c.add_argument('--captures', required=True)
    c.add_argument('--org')
    c.add_argument('--bar', type=float, default=0.6)
    c.add_argument('--state-root')
    c.add_argument('--json', help='write the full result here')
    c.add_argument('--self', action='store_true', help='also print the vacuous self-coverage')
    c.set_defaults(fn=cmd_coverage)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
