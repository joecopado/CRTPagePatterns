"""Standalone (no `robot` import) DOM-capture orchestration -- extracted
2026-07-31 from browser_mcp/actions.py's `_parse_elements_from_html`, which
is now archived (see ../../_archived/browser_mcp/). This function itself
was never part of the archived interaction-primitive reimplementation
(click/type/visibility/readiness -- the piece confirmed to diverge from
real QWeb behavior, see qweb-live-interop-architecture memory) -- it only
ever produces a structured DOM-JSON snapshot for observation, same
orchestration as DomParserLibraryNew.py's `parse_elements_from_html` RF
keyword, just runnable as a plain function with no RF suite involved.
Live consumers: qforce-lite's inspect_page.py and examples/spatial_capture.py.

Keep in sync with DomParserLibraryNew.py's `parse_elements_from_html` if
its extraction order changes -- the underlying compiler/classifier/config
classes are imported directly (not copied), so only this orchestration
function itself can drift.
"""
import re
from bs4 import BeautifulSoup

from dom_config import DomConfiguration, template_provenance
from text_engine import DomTextEngine
from component_classifier import ComponentClassifier
from element_compiler import DomElementCompiler
from iframe_descent import collect_frame_elements


def _grid_emission_container(config):
    """Predicate matching the container tags the template says to explode."""
    spec = getattr(config, "GRID_DESCENDANT_EMISSION", None) or {}
    tags = {t.lower() for t in spec.get("containerTags", [])}
    # 2026-09-10 (six industry-page audits): a grid is recognised by ROLE as well -- the Aura
    # table[role=grid] list views and console Home task lists swallowed 60-90 controls per page
    roles = {r.lower() for r in spec.get("containerRoles", [])}

    def _match(tag):
        if not tag.name:
            return False
        if tag.name.lower() in tags:
            return True
        role = (tag.get("role") or "").lower() if hasattr(tag, "get") else ""
        return bool(roles) and role in roles

    return _match


def _rule_matches(tag, rule):
    name = (tag.name or "").lower()
    if rule.get("tags") and name not in [t.lower() for t in rule["tags"]]:
        return False
    roles = [r.lower() for r in rule.get("roles", [])]
    if roles and (tag.get("role") or "").lower() not in roles:
        return False
    for skip in rule.get("skipIfDescendantTags", []) or []:
        if tag.find(skip) is not None:
            return False
    return True


def _pierced_text(tag) -> str:
    """Visible text INCLUDING what sits under a `<template shadowroot>` block. bs4 >= 4.10 types every
    string inside a <template> as TemplateString and get_text() drops them by default -- so a datatable
    cell whose value renders inside a native shadow root (`lightning-primitive-custom-cell` -> lookup
    link) read as '' and the grid rule fell back to `data-cell-value="[object Object]"` (270 cells on the
    Copado user-story list, 22 on the health90 Contract page, 2026-09-11). Measured over the 17 industry
    captures: the compiler's own label rungs are NOT affected (1,648 -> 1,674 rows when every template
    string is unhidden, all 26 on the Contract grid); only this grid-cell text source was."""
    from bs4.element import NavigableString, TemplateString
    return tag.get_text(separator=' ', strip=True, types=(NavigableString, TemplateString))


def _rule_label(tag, rule, text_of, reject_patterns=()):
    for src in rule.get("labelFrom", []):
        if src == "text":
            v = text_of(tag)
        else:
            v = tag.get(src)
        if v and str(v).strip():
            v = str(v).strip()
            # template labelValueRejectPatterns (2026-09-11): `data-cell-value="[object Object]"` is a
            # stringified object, never a name -- fall through to the next source (the cell's text)
            if any(re.search(p, v) for p in reject_patterns or ()):
                continue
            return v, ("inner_text" if src == "text" else src.replace("-", "_"))
    return None, None


def _emit_grid_descendants(container, config, compiler, seen_node_ids):
    """Walk one grid container in document order and emit whatever the template's
    `gridDescendantEmission.rules` declare. A rule with `"compile": true` runs the normal
    compiler (so a button/link keeps its real family and its qforce_hints); any other rule
    synthesises a minimal element with the declared family and label source -- cells and
    column headers are not interactive controls and get no fabricated hint, exactly as the
    container elements themselves already carry none."""
    spec = getattr(config, "GRID_DESCENDANT_EMISSION", None) or {}
    rules = spec.get("rules", [])
    if not rules:
        return
    for tag in container.find_all(True):
        if id(tag) in seen_node_ids or config._is_noise(tag):
            continue
        for rule in rules:
            if not _rule_matches(tag, rule):
                continue
            if rule.get("compile"):
                data = compiler._extract_element_data(tag)
                if data and data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
                    seen_node_ids.add(id(tag))
                    yield data
                break
            label, source = _rule_label(tag, rule, _pierced_text,
                                        getattr(config, "LABEL_VALUE_REJECT_PATTERNS", None) or ())
            if not label:
                break
            seen_node_ids.add(id(tag))
            family = rule.get("family") or "unknown"
            data = {
                "element_type": family,
                "element_details": {
                    "tag": tag.name,
                    "attributes": {k: v for k, v in (tag.attrs or {}).items()
                                   if k in ("role", "data-col-key-value", "data-row-key-value",
                                            "data-label", "scope", "aria-label")},
                },
                "identification": {"label_text": label, "label_source": source},
            }
            # template `valueFrom` (2026-09-11): a cell's label is its COLUMN, its text is the VALUE
            for vsrc in rule.get("valueFrom", []) or []:
                vv = _pierced_text(tag) if vsrc == "text" else tag.get(vsrc)
                vv = str(vv).strip() if vv else ""
                if vv and not any(re.search(p, vv) for p in (getattr(config, "LABEL_VALUE_REJECT_PATTERNS", None) or ())):
                    data["element_details"]["value"] = vv
                    break
            # stream 2A 2026-09-09: these synthesised elements bypassed the compiler entirely, so
            # they carried no keyword AND no reason -- 52 table_cell + 18 column_header over the
            # 144 committed captures, the largest single block of the 1,004 silent elements. They
            # still get no fabricated LOCATOR hint (they are not interactive controls, which is why
            # this branch exists), but the router now says which rung addresses them and why they
            # are not driven directly. Same table, same method the compiled path uses.
            hint_fill, hint_verify, hint_source, reason, _row = compiler._route_keywords(
                family, label)
            if hint_fill:
                data["hint_fill"] = hint_fill
            if hint_verify:
                data["hint_verify"] = hint_verify
            if hint_source:
                data["hint_source"] = hint_source
            if not hint_fill and not hint_verify:
                data["hint_reason"] = reason or (
                    "no keywordRouting row for family %r" % (family,))
            yield data
            break


def _emit_row_controls(container, config, compiler, seen_node_ids):
    """PB2 2026-09-07 (row-select checkbox shape, docs/recorder/evidence/
    parser-battery-captures-2026-09-07.md): a lightning-datatable's header
    "select all" checkbox is compiled and emitted (it becomes the datatable
    element's own label), but the N per-row "Select Item <n>" checkboxes are
    every one of them inside the swallowed `datatable_descendants` set and
    were never emitted as their own addressable elements -- only as a
    boolean flag (`_row_controls.row_checkbox`, no label, no locator) in the
    per-row metadata `_extract_element_data` already writes. Reproduced live
    on 8 of 8 populated Lightning-datatable captures across all 5 orgs.

    Reuses DomConfiguration.ROW_CONTROL_SIGNATURES (already the source of
    truth for "does this row have a checkbox/radio selector", used by
    component_classifier._detect_row_controls for the metadata flag) so this
    stays one schema, not a second literal -- runs the SAME real compiler
    used everywhere else so the emitted element gets its real label (via
    aria-labelledby -> the "Select Item N" assistive-text span, same
    resolution rung the header checkbox already uses) and real qforce_hints.
    Elements emitted here are added to `seen_node_ids` so the later
    target_tags pass (which skips anything in `datatable_descendants`)
    never double-reports them."""
    signatures = getattr(config, "ROW_CONTROL_SIGNATURES", None) or []
    if not signatures:
        return
    row_tags = tuple({t for sig in signatures for t in (sig.get("tags") or [])})
    if not row_tags:
        return
    for tag in container.find_all(row_tags):
        if id(tag) in seen_node_ids or config._is_noise(tag):
            continue
        for sig in signatures:
            if (tag.name or "").lower() not in [t.lower() for t in sig.get("tags", [])]:
                continue
            attrs = sig.get("attributes", {})
            matched = True
            for attr_key, attr_value in attrs.items():
                tag_attr = tag.get(attr_key)
                if callable(attr_value):
                    if not attr_value(tag_attr):
                        matched = False
                        break
                elif tag_attr != attr_value:
                    matched = False
                    break
            if not matched:
                continue
            data = compiler._extract_element_data(tag)
            if data and data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
                seen_node_ids.add(id(tag))
                yield data
            break


class ElementList(list):
    """The element list, plus `.template` -- the PROVENANCE block naming the
    template file that produced this parse (interop T18, 2026-09-07).

    It is a `list` subclass on purpose. Every one of the 23 importers measured in
    docs/recorder/evidence/interop-T13-parser-head-to-head-2026-09-07.md consumes
    this return value as a plain list (iterate, len, index, `json.dumps`) and reads
    per-element keys off it; wrapping the result in a dict would break all of them,
    and copying the block onto every element would repeat one fact hundreds of times.
    A subclass keeps `json.dumps(elements)` byte-identical -- which is what
    tools/recorder/tests/templates/test_byte_equivalence.py pins -- while the
    provenance is one attribute away for any consumer that wants it.

    A consumer that loses the attribute (a `list(...)` copy, a JSON round trip) can
    always recover the block with `dom_config.provenance_for_html(html)`.
    """

    template: dict = {}


def parse_elements_from_html(raw_html: str, config=None,
                             verified_labels=None) -> "ElementList":
    """`verified_labels` (D14, 2026-09-09): normalised labels a LIVE run has already
    resolved and read back on this page key, from the POM store
    (`tools/recorder/pom_asset.verified_labels(capture, org)`). They are the ONLY way a
    hint's `confidence` or `disambiguation.resolution` becomes 'verified'; without them
    every hint is 'unverified', which is what a capture can honestly say."""
    # T18 2026-09-07: `html=raw_html` is what turns on PER-PAGE template
    # selection. Before this, v1 -- the LIVE parser -- loaded
    # salesforce-lightning.json for every page it was ever given and no result
    # said so, which made a wrong template indistinguishable from a parser bug.
    # A caller that passes its own `config` keeps full control (and its own
    # provenance travels with it, whatever it selected).
    config = config if config is not None else DomConfiguration(html=raw_html)
    text_engine = DomTextEngine()
    classifier = ComponentClassifier(config, text_engine)
    compiler = DomElementCompiler(config, text_engine, classifier,
                                  verified_labels=verified_labels)

    soup = BeautifulSoup(raw_html, "html.parser")
    # F8, wave-2 close stream P3 2026-09-07: form-error panels were extracted
    # only by DomParserLibraryNew, so no local tool calling this function ever
    # saw a validation error panel. `compiler.extract_form_errors` is now the
    # one implementation both entry points run, and it runs FIRST here exactly
    # as it did there, so the element order is unchanged on that path.
    elements = compiler.extract_form_errors(soup)
    elements.extend(_classify_soup(soup, config, text_engine, classifier, compiler))

    # 2026-09-07 iframe descent (docs/recorder/COPADO-GAPS-2026-09-07.md,
    # REVIEW-BRIEF-NEXT.md row C4c): a same-app cross-origin frame's content
    # is spliced INTO `raw_html` by tools/recorder/cdp_transport.py's
    # splice_cross_origin_frames, but <iframe> is a RAWTEXT HTML element --
    # `soup` above never parsed a single tag out of it. iframe_descent.py
    # finds those spliced blocks by regex, sub-parses them, and runs the
    # SAME `_classify_soup` pass on each one, tagging every element with
    # `frame`. Elements found this way are appended (never merged into the
    # dedup/annotate calls below until after this point) so a downstream
    # consumer sees exactly what a same-document reader would.
    elements.extend(collect_frame_elements(raw_html, soup, lambda s: _classify_soup(s, config, text_engine, classifier, compiler, is_frame_context=True)))

    # stream A3 2026-09-08 (user rule): QWeb resolves text by SUBSTRING for
    # EVERY text keyword, not only ClickText -- `type_text("Name", ...)` also
    # matches "Name (secondary)".  The collision table is seeded HERE, before
    # dedup, because the anchor ladder inside `_deduplicate_form_fields` reads
    # `group_size` to decide whether a control repeats, and a substring
    # collision has to count as a repeat for the ladder to run at all.
    compiler.seed_substring_collisions(elements, soup=soup)
    elements = compiler._deduplicate_form_fields(elements)

    # F8: the modal/background annotation lived only on the RF entry point.
    if any((el.get('context') or {}).get('is_in_modal') for el in elements):
        for el in elements:
            ctx = el.get('context') or {}
            if not ctx.get('is_in_modal'):
                ctx['is_background'] = True
                el['context'] = ctx

    compiler._annotate_ambiguous_hints(elements)
    # interop T17 2026-09-07: page-wide ClickText text-prefix collision check
    # (e.g. "Save" vs "Save & New") -- runs after the exact-duplicate pass
    # above so it never fights that pass's own confidence downgrade.
    # `soup` is handed over so the collision corpus includes the page's own
    # VISIBLE TEXT, not just parsed elements' labels -- F20, wave-2 close
    # stream P3 2026-09-07 (L2-R24 on web-ant-design/3-transfer-idle.html#55).
    compiler._annotate_click_text_prefix_collisions(elements, soup=soup)
    # stream A3 2026-09-08: the same rule for every OTHER text keyword whose
    # QWeb signature accepts `partial_match` (input_.py TypeText, checkbox.py
    # ClickCheckbox, dropdown.py DropDown/PickList, element.py ClickItem --
    # all read from the installed source, not assumed).  The anchor half was
    # already done by the seed above; this pins the flag.
    compiler.annotate_substring_collisions(elements)
    # D14 2026-09-09: LAST -- after every pass that could have written a
    # confidence value, so there is exactly one place the two allowed states
    # ('unverified' / 'verified') are decided, and only the POM store can say
    # 'verified'.
    compiler.stamp_resolution(elements)
    # T18 2026-09-07: the returned list carries its template provenance. The T17
    # annotation runs on the plain list FIRST, then the list is wrapped -- both
    # sides of this merge keep their behaviour.
    out = ElementList(elements)
    out.template = template_provenance(config)
    return out


def _classify_soup(soup, config, text_engine, classifier, compiler, is_frame_context=False) -> list[dict]:
    """The full target-tags/interactive-roles/c-*/lightning-* classification
    pass, factored out of `parse_elements_from_html` (2026-09-07 iframe
    descent) so it can run identically over a same-app frame's sub-document
    via `iframe_descent.collect_frame_elements`. No dedup/ambiguity-
    annotation here -- those stay a single pass over the FULL combined
    element list in the caller, same as before this refactor.

    `is_frame_context=True` (frame sub-documents only, never the top-level
    document -- keeps every existing capture's byte-equivalence untouched)
    changes ONE thing: a classic-markup `<table>` used purely for CSS field
    layout (Visualforce's own generated forms, confirmed live on the
    backpromote-02/-03 captures -- 4 tables, 0 `data-id`/`data-test-id`/
    `data-row-key`, every real control a plain `<input>`/`<select>`) no
    longer swallows its own descendants into `datatable_descendants`. The
    swallow rule exists so a genuine data-grid table's row/cell TEXT isn't
    double-reported once as the table's own compiled row data and again as
    loose elements -- but Visualforce lays out real, individually-actionable
    form controls (Save/Cancel buttons, the "Is Back-Promotion" checkbox, two
    classic `_lkid` lookup inputs, a native `<select>`) inside `<table>`
    purely for alignment, and swallowing those left only the 4 empty table
    shells (measured: 0 of 13 inputs / 3 selects reachable). A table is
    judged layout-only, not a data grid, by containing a real
    input/select/textarea/button control directly -- no genuine Salesforce
    list-view/datatable ever does that; its cells hold text and links."""
    elements = []
    seen_node_ids = set()

    datatable_descendants = set()
    native_tables = set()

    for tag in soup.find_all(["lightning-datatable", "lightning-tree-grid"]):
        for child in tag.find_all(True):
            datatable_descendants.add(id(child))

    # Wildcard: ANY real <table> is a table, no data-test-id/data-id gate --
    # that gate used to mean a classic Aura-rendered table (no such
    # attributes, e.g. Salesforce Files' own list view) was silently
    # invisible to this parser entirely. Confirmed live 2026-07-29.
    for tag in soup.find_all("table"):
        native_tables.add(id(tag))
        is_layout_table = is_frame_context and tag.find(["input", "select", "textarea", "button"]) is not None
        if not is_layout_table:
            for child in tag.find_all(True):
                datatable_descendants.add(id(child))

    for tag in soup.find_all(["lightning-datatable", "lightning-tree-grid"]):
        if id(tag) in seen_node_ids:
            continue
        element_data = compiler._extract_element_data(tag)
        if element_data:
            seen_node_ids.add(id(tag))
            elements.append(element_data)

    # PB2 2026-09-07 -- ROW-SELECT CHECKBOX/RADIO EMISSION (see
    # _emit_row_controls' own docstring). Runs before the tree-grid
    # gridDescendantEmission pass below so a checkbox column inside a
    # lightning-tree-grid is claimed here (real element, real label) rather
    # than falling through to that pass's own "compile" rule set, which has
    # no row-control rule of its own.
    for tag in soup.find_all(["lightning-datatable", "lightning-tree-grid"]):
        for element_data in _emit_row_controls(tag, config, compiler, seen_node_ids):
            elements.append(element_data)

    # interop T16 2026-09-07 -- GRID DESCENDANT EMISSION.
    # T14 measured v1 at 0/18 controls inside a `lightning-tree-grid` (fragment AND
    # full page): the swallow above hides every column header, cell, caret and
    # column-action button behind two hintless container shells. The container's own
    # compiled row data is column-mapped cell TEXT only -- it carries no label for any
    # of them, so a keyword author reading v1's output saw nothing to click.
    # The rule is schema-driven (`gridDescendantEmission` in the template JSON, read
    # through DomConfiguration): which container tags are exploded, which descendants
    # are emitted, and where each one's label comes from. Descendants stay in
    # `datatable_descendants`, so this pass is the ONLY emitter for them and no later
    # pass can double-report a cell.
    for tag in soup.find_all(_grid_emission_container(config)):
        for element_data in _emit_grid_descendants(tag, config, compiler, seen_node_ids):
            elements.append(element_data)

    for tag in soup.find_all("table"):
        if id(tag) in native_tables and id(tag) not in seen_node_ids:
            element_data = compiler._extract_element_data(tag)
            if element_data:
                seen_node_ids.add(id(tag))
                elements.append(element_data)

    # F2 (2026-09-05): target_tags/interactive_roles now live on
    # DomConfiguration (template-driven, see dom_config.py's TARGET_TAGS /
    # INTERACTIVE_ROLES + docs/recorder/TEMPLATES.md) instead of being
    # hard-coded here. `config` (built above from DomConfiguration()) is
    # v1 by default; v2 widens both lists (label/option/iframe tags,
    # treeitem/tabpanel roles).
    target_tags = config.TARGET_TAGS

    for tag in soup.find_all(target_tags):
        if id(tag) in datatable_descendants or id(tag) in seen_node_ids or config._is_noise(tag) or config._is_shadow_wrapper(tag):
            continue
        element_data = compiler._extract_element_data(tag)
        if element_data and element_data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
            seen_node_ids.add(id(tag))
            elements.append(element_data)

    # 2026-09-10: structural containers (template key `structuralContainerRules`) -- a plain div
    # that IS a control by its shape (SLDS dueling list). Its option descendants stay skipped
    # (picklist_option is in SKIP_ELEMENT_TYPES), so the page gains exactly one row per control.
    for rule in (getattr(config, "STRUCTURAL_CONTAINER_RULES", None) or []):
        frags = rule.get("containerClassFragments") or []
        inside = {t.lower() for t in (rule.get("skipIfInsideTags") or [])}
        for tag in soup.find_all(lambda t: t.name and any(f in " ".join(t.get("class") or []) for f in frags)):
            if id(tag) in datatable_descendants or id(tag) in seen_node_ids or config._is_noise(tag) or config._is_shadow_wrapper(tag):
                continue
            if inside and tag.find_parent(lambda p: p.name and p.name.lower() in inside) is not None:
                continue      # the base component's own inner structure: its host row already exists
            element_data = compiler._extract_element_data(tag, is_custom=True)
            if element_data and element_data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
                seen_node_ids.add(id(tag))
                elements.append(element_data)

    interactive_roles = config.INTERACTIVE_ROLES
    for tag in soup.find_all(attrs={"role": lambda r: r in interactive_roles}):
        if id(tag) in datatable_descendants or id(tag) in seen_node_ids or config._is_noise(tag) or config._is_shadow_wrapper(tag):
            continue
        element_data = compiler._extract_element_data(tag, is_custom=True)
        if element_data and element_data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
            seen_node_ids.add(id(tag))
            elements.append(element_data)

    for tag in soup.find_all(lambda t: t.name and t.name.startswith("c-")):
        if id(tag) in datatable_descendants or id(tag) in seen_node_ids or config._is_noise(tag) or config._is_container_component(tag):
            continue
        element_data = compiler._extract_element_data(tag, is_custom=True)
        if element_data and element_data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
            seen_node_ids.add(id(tag))
            elements.append(element_data)

    # Wildcard pass for any lightning-* tag not already caught by the
    # explicit target_tags enum above -- ported from dom-parser.js's
    # WILDCARD_TAG_RE, which treats ANY lightning-*/c-* tag as presumptively
    # interactive rather than requiring it be named in an allowlist first.
    # The c-* wildcard already existed here; lightning-* did not, so any
    # lightning component not already enumerated in target_tags was
    # silently unreachable regardless of how interactive it actually was.
    for tag in soup.find_all(lambda t: t.name and t.name.startswith("lightning-")):
        if id(tag) in datatable_descendants or id(tag) in seen_node_ids or config._is_noise(tag) or config._is_shadow_wrapper(tag) or config._is_container_component(tag):
            continue
        element_data = compiler._extract_element_data(tag, is_custom=True)
        if element_data and element_data.get("element_type") not in config.SKIP_ELEMENT_TYPES:
            seen_node_ids.add(id(tag))
            elements.append(element_data)

    return elements
