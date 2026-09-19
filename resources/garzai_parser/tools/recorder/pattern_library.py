"""
Usage: python3 tools/recorder/pattern_library.py [-h] --review REVIEW [--library LIBRARY]
pattern_library -- the reusable interaction recipes and the bucket rule for the review loop.

Two things the user set on 2026-09-10 after four pages:

1. BUCKETS. A page is reviewed by shape, one representative per bucket, never every row: the Data
   Template detail page holds 464 sidebar object buttons that are one pattern with one parameter.
   `bucket(rows)` groups rows by `shape_key` (region, family, tag, first keyword, label source,
   stable class fragments / role); the representative is the first page-region member in DOM
   order. `live`, `robot` and `demo` work on representatives by default; a correction on a
   representative applies to its bucket (`correct --bucket`).

2. THE LIBRARY. A pattern that held on a page is cross-page and cross-org, so it lives here, not in
   the per-page POM store: `docs/recorder/patterns/library.json`, one entry per pattern with the
   match rule, the keyword form, the xpath form, the read-back, the wait signal, the known failure
   and the pages it was measured on. `match(row)` stamps a row with its pattern; `recipe(entry,
   row, value)` renders the two forms. The library never edits the parser (a review never does):
   it is the interaction layer on top of what the parser found.

Run: .venv-qweb/bin/python tools/recorder/pattern_library.py --review <review.json>   (prints the buckets)
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LIBRARY = os.path.join(_ROOT, 'docs', 'recorder', 'patterns', 'library.json')

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import disambiguation_args as DA   # noqa: E402  (index -> QWeb's numeric anchor, one converter)

_GENERATED = re.compile(r'\d{3,}|^(ng-|is-|_ng|slds-is-|cdk-)')


def _stable_classes(attrs: dict) -> str:
    return ' '.join(sorted(c for c in (attrs.get('class') or '').split() if not _GENERATED.search(c)))[:80]


def shape_key(row: dict) -> tuple:
    """What makes two controls 'the same shape': the fields that decide the keyword and the locator,
    never the label or the value (those are the one parameter that changes between members)."""
    attrs = row.get('attrs') or {}
    c0 = (row.get('calls') or [{}])[0]
    return (row.get('region') or 'page',
            row.get('family_corrected') or row.get('element_type') or '',
            row.get('tag') or '',
            row.get('keyword_corrected') or c0.get('keyword') or '',
            row.get('label_source') or '',
            _stable_classes(attrs) or attrs.get('role') or '',
            row.get('pattern') or '')


def bucket(rows: list[dict]) -> list[dict]:
    """rows -> buckets, biggest first; each carries its representative and its members (row numbers)."""
    groups: dict = collections.OrderedDict()
    for r in rows:
        groups.setdefault(shape_key(r), []).append(r)
    out = []
    for i, (k, members) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
        rep = members[0]
        out.append({'id': 'b%d' % i, 'shape': {'region': k[0], 'family': k[1], 'tag': k[2], 'keyword': k[3],
                                                 'label_source': k[4], 'classes': k[5], 'pattern': k[6]},
                    'count': len(members), 'representative': rep['n'], 'members': [m['n'] for m in members],
                    'example_label': rep.get('label_corrected') or rep.get('label') or ''})
    return out


def stamp(rows: list[dict]) -> list[dict]:
    """Stamp every row with its bucket id and whether it is the representative; return the buckets."""
    bs = bucket(rows)
    by_n = {r['n']: r for r in rows}
    for b in bs:
        for n in b['members']:
            by_n[n]['bucket'] = b['id']
            by_n[n]['representative'] = (n == b['representative'])
    return bs


def representatives(rows: list[dict]) -> list[dict]:
    if not any('bucket' in r for r in rows):
        stamp(rows)
    return [r for r in rows if r.get('representative')]


# ----------------------------------------------------------------------------- the library
def load_library(path: str = LIBRARY) -> list[dict]:
    try:
        return json.load(open(path)).get('patterns') or []
    except FileNotFoundError:
        return []


def _matches(rule: dict, row: dict) -> bool:
    attrs = row.get('attrs') or {}
    fam = row.get('family_corrected') or row.get('element_type')
    if rule.get('family') and fam not in (rule['family'] if isinstance(rule['family'], list) else [rule['family']]):
        return False
    if rule.get('tag') and row.get('tag') != rule['tag']:
        return False
    for k, v in (rule.get('attrs') or {}).items():
        if v == '*':
            if k not in attrs:
                return False
        elif attrs.get(k) != v:
            return False
    for pat in rule.get('attr_regex') or []:              # {"name": "title", "regex": "^Edit "}
        if not re.search(pat['regex'], attrs.get(pat['name']) or ''):
            return False
    for anc in rule.get('ancestor_tags') or []:
        if anc not in (row.get('raw_context') or []):
            return False
    if rule.get('label_source') and row.get('label_source') != rule['label_source']:
        return False
    if rule.get('group_size_min') and (row.get('group_size') or 1) < rule['group_size_min']:
        return False
    if rule.get('index_min') and (row.get('index') or 1) < rule['index_min']:
        return False
    if rule.get('raw_regex') and not re.search(rule['raw_regex'], row.get('raw') or ''):
        return False
    if rule.get('keyword'):
        c0 = (row.get('calls') or [{}])[0]
        if (row.get('keyword_corrected') or c0.get('keyword') or row.get('hint_fill') or row.get('hint_click')) != rule['keyword']:
            return False
    if rule.get('label_regex') and not re.search(rule['label_regex'], row.get('label_corrected') or row.get('label') or ''):
        return False
    return True


def match(row: dict, library: list[dict] | None = None) -> dict | None:
    """The first library entry whose match rule the row satisfies (entries are ordered specific -> general)."""
    for entry in (library if library is not None else load_library()):
        if _matches(entry.get('match') or {}, row):
            return entry
    return None


def _xp(xp: str) -> str:
    return 'xpath\\=' + re.sub(r'(?<!\\)=', r'\\=', xp)


def recipe(entry: dict, row: dict, value: str) -> tuple[list[str], list[str]]:
    """Render the entry's two forms for this row. Placeholders: {label} (the row's label),
    {value}, {index}, {anchor_kw}, and any key in row['pattern_args'] (e.g. {host_id}, found at
    build time).

    {anchor_kw} is D4's own slot, generic to every recipe (2026-09-18, the native-select gap):
    'a control that occurs once gets neither an anchor nor an index'; one whose label repeats
    (group_size > 1) carries QWeb's numeric anchor. It renders as '    anchor=<n>' (the leading
    four spaces baked in, so a template appends it bare) when the row repeats, else '' -- so one
    template covers both shapes and a single-occurrence row never carries a pure-cost anchor.
    Routed through `disambiguation_args.to_call_kwargs`, the one converter index becomes anchor
    through everywhere else in this codebase (compose_live._anchor_of, review_table.robot_call)."""
    args = dict(row.get('pattern_args') or {})
    args.update({'attr_%s' % k.replace('-', '_'): v for k, v in (row.get('attrs') or {}).items() if isinstance(v, str)})
    idx = row.get('index_corrected') if 'index_corrected' in row else row.get('index')
    args.update({'label': row.get('label_corrected') or (row.get('label') or ''), 'value': value,
                 'index': idx if idx else 1,
                 'xpath': row.get('xpath_corrected') or (row.get('xpath') or {}).get('value') or ''})
    anchor = DA.to_call_kwargs({'index': idx}).get('anchor') if idx and (row.get('group_size') or 1) > 1 else None
    args['anchor_kw'] = ('    anchor=%s' % anchor) if anchor else ''

    def render(lines):
        out = []
        for line in lines:
            try:
                s = line.format(**args)
            except KeyError as exc:
                out.append('# COULD-NOT-RENDER %s: no %s for this row' % (entry['id'], exc))
                continue
            # a line written with a bare xpath= in the library is escaped here, once
            out.append(re.sub(r'(?<![\\])\bxpath=([^\s].*?)(?=(?:\s{4}|$))', lambda m: _xp(m.group(1)), s))
        return out
    return render(entry.get('keyword_form') or []), render(entry.get('xpath_form') or [])


# ------------------------------------------------------- roster order (LOOP 3 / A4, 2026-09-20)
# The locator roster's per-platform order, measured once from the live verdicts already in
# docs/recorder/review/*/review.json and recorded under library.json['roster_order'] (never
# derived live -- this reads the committed measurement, docs/audit/roster-order-2026-09-20.md).
# Consumed ONLY when GZ_ROSTER_BY_PLATFORM=1 (default OFF): the composer keeps emitting the
# parser's keyword hint first everywhere until that flag is set, and even then only for a
# platform the measurement actually covers (a platform with status COULD-NOT-CHECK, e.g.
# OmniStudio, or one absent from the table, is never overridden -- the caller's own default form
# stands, per D13/D14: a hint describes, it never overrides silently).
def platform_of(org: str | None, url: str | None) -> str | None:
    """Classify (org, url) into the same buckets docs/audit/roster-order-2026-09-20.md measured:
    'copado_own' (Copado's own CI/CD app pages -- na.devops.copado.com, or a
    copado__/copado_labs__ managed-package object rendered in Lightning),
    'lightning_standard' (a standard Salesforce object/tab, no Copado package involved).
    Never guesses 'omnistudio' or 'visualforce' -- those are COULD-NOT-CHECK in the table and
    the caller's default form is left alone regardless of what this returns for them."""
    u = url or ''
    if 'devops.copado.com' in u or '/en/data-template-management' in u or '/en/commit/' in u:
        return 'copado_own'
    if 'copado__' in u or 'copado_labs__' in u:
        return 'copado_own'
    if org in ('cicd', 'cicd-demo'):
        return 'copado_own'
    if 'force.com' in u or '/lightning/' in u:
        return 'lightning_standard'
    return None


def roster_order_for_platform(platform: str | None, library_path: str = LIBRARY) -> list[dict]:
    """The measured tier order for one platform, or [] when the platform is None, unmeasured, or
    marked COULD-NOT-CHECK in the table."""
    if not platform:
        return []
    try:
        doc = json.load(open(library_path)).get('roster_order') or {}
    except FileNotFoundError:
        return []
    entry = (doc.get('platforms') or {}).get(platform) or {}
    if entry.get('status') == 'COULD-NOT-CHECK':
        return []
    return entry.get('order') or []


def roster_form_for_platform(platform: str | None, default: str = 'keyword',
                             library_path: str = LIBRARY) -> str:
    """'keyword' or 'xpath' -- which GROUP (tools/recorder/crt_override/compose_live.py's binary
    `form` choice) the top-ranked tier for this platform belongs to, per
    library.json['roster_order']['tier_groups']. Returns `default` (today's fixed behaviour,
    keyword first) when there is no measurement for this platform, so an unmeasured platform is
    never silently reordered."""
    order = roster_order_for_platform(platform, library_path)
    if not order:
        return default
    top_tier = order[0].get('tier')
    try:
        groups = json.load(open(library_path)).get('roster_order', {}).get('tier_groups') or {}
    except FileNotFoundError:
        groups = {}
    for group_name, tiers in groups.items():
        if top_tier in tiers:
            return group_name
    return default


def find_pattern_args(entry: dict, node) -> dict:
    """Values the recipe needs from the capture (bs4 node): ancestor attributes named by the entry,
    e.g. {"host_id": {"ancestor": "cds-select-input", "attr": "id"}}."""
    out = {}
    for name, spec in (entry.get('args') or {}).items():
        if 'ancestor' in spec and node is not None:
            anc = node.find_parent(spec['ancestor'])
            if anc is not None and anc.get(spec.get('attr', 'id')):
                out[name] = anc.get(spec.get('attr', 'id'))
        elif 'attr' in spec and node is not None and node.get(spec['attr']):
            out[name] = node.get(spec['attr'])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--review', required=True)
    ap.add_argument('--library', default=LIBRARY)
    a = ap.parse_args(argv)
    review = json.load(open(a.review))
    rows = review['rows']
    lib = load_library(a.library)
    hits = collections.Counter()
    for r in rows:
        e = match(r, lib)
        if e:
            hits[e['id']] += 1
    bs = bucket(rows)
    print('%d rows -> %d buckets; library matches: %s' % (len(rows), len(bs), dict(hits) or 'none'))
    for b in bs:
        s = b['shape']
        print('%5d  %-6s %-13s %-7s %-14s %-16s %-30s rep row %-4d %r' % (
            b['count'], s['region'], s['family'], s['tag'], s['keyword'] or '-', s['label_source'] or '-',
            (s['pattern'] or s['classes'])[:30], b['representative'], b['example_label'][:40]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
