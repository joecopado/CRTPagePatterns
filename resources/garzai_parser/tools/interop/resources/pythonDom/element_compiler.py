import re

from bs4 import BeautifulSoup

# qforce_hints `confidence` -- HINTS DESCRIBE, THEY NEVER PRESCRIBE (user, 2026-09-09:
# "the hints are more detrimental than your independent judgements at run time";
# docs/DECISIONS.md D14).
#
# The five-tier scale that lived here (unique_structural / unique_on_this_page /
# ambiguous_needs_anchor / ambiguous_unresolved / anchored_unique) was a PREDICTION about
# what a call would do at run time, made from a static capture. It was measured wrong on a
# live page: docs/errors/entries/7627c1f2a9.json -- on slockard Zoo_Forms_Advanced the parser
# emitted anchor='Review' for one 'Deal Name' member and anchor='SLDS abbr convention
# (group A)' for another, both at `anchored_unique` with `anchor_is_unique: true` (the field's name then), and QWeb's
# proximity scorer resolved BOTH to the same field (the second type_text_clearing appended
# instead of clearing: 'ZooAnchorProof2ZooAnchorProof1'). The parser's uniqueness is a
# capture-TEXT property; QWeb's choice is geometric and live. A capture cannot know it.
#
# So there are exactly two values, and only one of them can ever be earned from a capture:
TIER_UNVERIFIED = 'unverified'   # the parser reports what is ON THE PAGE. No claim is made
                                 # that a call built from this hint resolves this element.
TIER_VERIFIED = 'verified'       # a LIVE run resolved this element with this rung and recorded
                                 # a read-back in the POM store (tools/recorder/pom/store.py:
                                 # a ladder rung with n_verified > 0 for this page key). Never
                                 # set by static analysis -- the caller supplies the verified
                                 # labels (`verified_labels=`) and this module only stamps them.
ALLOWED_CONFIDENCE = (TIER_UNVERIFIED, TIER_VERIFIED)

_CALL_TEMPLATES = {
    'PickList': 'pick_list("{locator}", "<value>")',
    'ComboBox': 'combo_box("{locator}", "<value>")',
    'TypeText': 'type_text("{locator}", "<value>")',
    'ClickText': 'click_text("{locator}")',
    # Real QWeb keyword (QWeb.keywords.text.click_item), not a qforce_lite
    # reimplementation -- ClickItem already exists in open-source QWeb
    # itself. tag= is REQUIRED here, always the element's literal HTML tag
    # (element_details.tag), never element_type (a behavioral/ARIA
    # classification -- e.g. an <a role="button"> classifies as element_type
    # "button" but its real tag is still "a"). Without tag=, real ClickItem
    # only searches a fixed allowlist (a, span, img, li, h1-h6, div, svg, p,
    # button, input[submit]) -- most Lightning/Aura custom elements
    # (lightning-*, c-*) fall outside that list and would silently fail to
    # be found, not error. Same practice already established in this
    # project's crt_relay.py for exactly this reason -- see
    # feedback-tag-required-for-element-targeting memory.
    'ClickItem': 'click_item("{locator}", tag="{tag}")',
    'ClickCheckbox': 'click_checkbox("{locator}", "on")',
    # stream 2A 2026-09-09: these two used to be the literal two-keyword strings
    # 'ClickTableCell / GetTableCell' and 'TypeText / ClickText'. A hint is ONE keyword -- fill vs
    # verify is the CALLER's intent and now rides on the element's `hint_fill`/`hint_verify`
    # fields, never inside a keyword name. Both names are also the canonical CRT rungs
    # (export._CRT_KW_MAP), which 'ClickTableCell' and 'TypeText / ClickText' were not:
    # a step carrying either exported as an anonymous custom body.
    'Click Table Cell': 'click_table_cell(row=<N>, col="{locator}")  # UseTable first',
    # Added 2026-09-07 alongside the parser-families fix (lookup/date/
    # datetime/richtext element_type branches) -- METADATA-KEYWORDS.md's
    # routing for the matching describe types (reference/date/datetime, and
    # the textarea+extraTypeInfo=richtextarea EXTRA_TYPE_POINTS row), same
    # keyword names tools/recorder/library/index.json already carries.
    'Aura Lookup': 'combo_box("{locator}", "<value>")',
    # stream 2A 2026-09-09: were 'set_datetime' and 'type_text_clearing (rich text)' -- python
    # CALLABLE names leaking into a field that must hold a CRT RUNG. Neither string is a rung in
    # export._CRT_KW_MAP, writer._KW_MAP or library/index.json, and both showed up as keyword
    # DISAGREEMENTS against the metadata router purely because of the spelling
    # (metadata_dom_parity: 'Set Datetime' vs 'set_datetime', 4 rows).
    'Set Datetime': 'set_datetime("{locator}", "<value>")',
    'Type Text Clearing': 'type_text_clearing("{locator}", "<value>")',
}


def _call_example(keyword: str, locator: str, tag: str = None) -> str:
    template = _CALL_TEMPLATES.get(keyword, '{keyword}("{locator}")')
    return template.format(keyword=keyword, locator=locator, tag=tag or 'UNKNOWN_TAG')


def actionable_summary(elements: list) -> list:
    """Low-noise view over the same qforce_hints data produced during
    parsing -- one row per keyword-bearing hint, reduced to the call shape and
    the disambiguators the page offers. Additive, not a replacement: the full
    element JSON (context/attributes/behavioral_metadata) stays available
    separately for deeper inspection.

    D14 (2026-09-09): this used to filter to the three "confident" tiers, which
    was the summary CLAIMING that those calls resolve. It no longer filters on
    a claim -- every hint the parser can name is listed with its `confidence`
    ('unverified' until a live read-back says otherwise), its `index` inside a
    repeated group, and the anchor CANDIDATES the page offers. The caller
    chooses; the parser describes."""
    summary = []
    for el in elements:
        hints = el.get('qforce_hints')
        if not hints:
            continue
        label = (el.get('identification') or {}).get('label_text')
        dis = el.get('disambiguation') or {}
        for hint in hints.get('locator_options', []):
            if not hint.get('keyword'):
                continue
            summary.append({
                'label': label,
                'keyword': hint.get('keyword'),
                'call_example': hint.get('call_example'),
                'confidence': hint.get('confidence'),
                'resolution': dis.get('resolution', TIER_UNVERIFIED),
                'group_size': dis.get('group_size', 1),
                'index': dis.get('index'),
                'anchor_candidates': hint.get('anchor_candidates'),
            })
    return summary


class DomElementCompiler:
    DESCRIPTION_CLASS_FRAGMENTS = [
        'changeRecordTypeItemDescription',
        'changeRecordTypeLabel',
        'slds-form-element__help',
        'slds-form-element__static',
        'helpText',
        'fieldDescription',
        'record-type-description',
        'option-description',
        'item-description',
    ]

    # Visible short-label text for radio/checkbox inputs wrapped in a <label>
    # (e.g. Salesforce's record-type-selection modal: a <label> containing
    # both a short slds-form-element__label span AND a longer description
    # div -- DESCRIPTION_CLASS_FRAGMENTS already grabs the latter, this list
    # is for the former, which previously had no resolution path at all.
    LABEL_CLASS_FRAGMENTS = [
        'slds-form-element__label',
        'slds-radio__label',
        'slds-checkbox__label',
    ]

    def __init__(self, config, text_engine, classifier, metadata_types=None,
                 verified_labels=None):
        self.config = config
        self.text_engine = text_engine
        self.classifier = classifier
        # D14 2026-09-09 -- the ONLY door through which a hint becomes
        # 'verified'. A set of NORMALISED labels (see `_norm_label`) that a
        # LIVE run already resolved and read back on this page key, supplied by
        # the caller from the POM store (`tools/recorder/pom_asset.py`'s
        # `verified_labels(capture, org)`, which reads a ladder rung's
        # `n_verified`). None -- the default, and what every parse of a saved
        # capture uses -- means nothing on this page has been verified, so every
        # hint stays 'unverified'. Static analysis never writes into this set.
        self.verified_labels = set(verified_labels or ())
        # stream 2A 2026-09-09 -- METADATA ROUTES FIRST, DOM FAMILY BACKSTOPS (CLAUDE.md).
        # {normalised field label -> describe type}, supplied by a caller that has the org map
        # (tools/qforce-lite/predict.py's population, or metadata_dom_parity's predictions). None
        # -- the default, and what every parse of a saved capture uses -- means DOM family only.
        # The parser never READS the org map itself: it stays platform-agnostic and dependency
        # free, so the map stays the caller's business and the routing table stays template data.
        self.metadata_types = {self._norm_label(k): v
                               for k, v in (metadata_types or {}).items()} or None

    # ------------------------------------------------------------------ keyword router (2A)
    _REQUIRED_MARK_RE = re.compile(r'[\*\u2022]|\(required\)|required', re.I)

    @classmethod
    def _norm_label(cls, label):
        """The SAME normalisation metadata_dom_parity.norm uses, so a label ties on both sides."""
        if not label:
            return ''
        s = cls._REQUIRED_MARK_RE.sub(' ', label).replace('\u00a0', ' ')
        s = re.sub(r'[:–—]+\s*$', '', s)
        return re.sub(r'\s+', ' ', s).strip().lower()

    def _routing(self):
        return getattr(self.config, 'KEYWORD_ROUTING', None) or {}

    def _routing_row(self, element_type):
        families = self._routing().get('families') or {}
        return families.get(element_type) or families.get('_default') or {}

    def _metadata_routing_row(self, label_text):
        """The describe-type row for this control, when a caller supplied the metadata. Returns
        (row, describe_type) or (None, None)."""
        if not self.metadata_types or not label_text:
            return None, None
        ftype = self.metadata_types.get(self._norm_label(label_text))
        if not ftype:
            return None, None
        row = (self._routing().get('metadataTypes') or {}).get(str(ftype).lower())
        return (row, ftype) if row else (None, None)

    def _route_keywords(self, element_type, label_text):
        """(hint_fill, hint_verify, hint_source, reason, row) for one control.

        Metadata type first when the caller supplied one, DOM family second -- and a family that
        routes SOMEWHERE but whose control carries no resolvable label yields the third state, not
        a keyword that cannot target anything (the rule _hints_for_family already established for
        the 14 labelless radios, applied to every family)."""
        row, ftype = self._metadata_routing_row(label_text)
        source = 'metadata'
        if row is None:
            row, source = self._routing_row(element_type), 'family'
        fill, verify = row.get('fill'), row.get('verify')
        reason = row.get('reason')
        if (fill or verify) and not label_text:
            reason = ("%s routes to %s, but this control has no resolvable label -- the keyword "
                      "cannot target it" % (ftype or element_type, fill or verify))
            fill = verify = None
            source = None
        elif not fill and not verify:
            source = None
        return fill, verify, source, reason, row

    # interop T10 2026-09-07 -- the two class-fragment lists and the
    # required-marker selectors are POLICY and live in the template
    # (`labelClassFragments` / `descriptionClassFragments` /
    # `requiredMarkerSelectors`), read through DomConfiguration. The class
    # attributes above stay as the fallback for a config that predates the
    # keys, so a template lacking them behaves exactly as before.
    def _label_class_fragments(self):
        return getattr(self.config, 'LABEL_CLASS_FRAGMENTS', None) or self.LABEL_CLASS_FRAGMENTS

    def _description_class_fragments(self):
        return getattr(self.config, 'DESCRIPTION_CLASS_FRAGMENTS', None) or self.DESCRIPTION_CLASS_FRAGMENTS

    def _required_marker_selectors(self):
        return getattr(self.config, 'REQUIRED_MARKER_SELECTORS', None) or [{'aria-hidden': 'true'}]

    def _extract_element_data(self, tag, is_custom=False) -> dict:
        if not tag:
            return None
        try:
            if self.config._is_container_component(tag):
                return None

            element_type = self.classifier._classify_element_type(tag)
            if element_type in self.config.SKIP_ELEMENT_TYPES:
                return None

            identification = self._get_identification(tag)
            label_text = identification.get('label_text', '')
            if label_text and any(b in label_text for b in self.config.SYSTEM_TEXT_BLACKLIST):
                return None

            behavioral_metadata = self._get_behavioral_metadata(tag, element_type)
            validation = self._fold_rendered_required(self._get_validation(tag), identification)

            dropdown_data = None
            if element_type == 'dropdown':
                dropdown_info = self.classifier._detect_dropdown_type(tag)
                dropdown_options = self.classifier._extract_dropdown_options(tag)
                dropdown_data = {
                    'dropdown_type': dropdown_info.get('dropdown_type') if dropdown_info else 'unknown',
                    'is_dynamic': dropdown_info.get('is_dynamic', True) if dropdown_info else True,
                }
                if dropdown_options:
                    dropdown_data['options'] = dropdown_options
                    dropdown_data['options_available'] = True
                else:
                    dropdown_data['options_available'] = False
                    dropdown_data['note'] = 'Options not in DOM — dropdown may be closed or loads dynamically'

            context = self._get_context_info(tag)
            is_output_only = element_type in self.classifier.OUTPUT_ONLY_TYPES
            key_attributes = self._get_key_attributes(tag)
            real_tag = tag.name.lower() if tag.name else 'unknown'
            qforce_hints = self._get_qforce_hints(element_type, identification, context, key_attributes, real_tag)

            element_data = {
                'element_type': element_type,
                'element_details': {
                    'tag': tag.name.lower() if tag.name else 'unknown',
                    'type': tag.get('type') or None,
                    'attributes': key_attributes,
                },
                'identification': identification,
            }

            if behavioral_metadata:
                element_data['behavioral_metadata'] = behavioral_metadata
            if validation:
                element_data['validation'] = validation
            if dropdown_data:
                element_data['dropdown'] = dropdown_data
            if context:
                element_data['context'] = context
            if is_output_only:
                element_data['is_output_only'] = True
            if qforce_hints:
                element_data['qforce_hints'] = qforce_hints

            # stream 2A 2026-09-09: FILL vs VERIFY is the caller's INTENT, so it rides here as two
            # named fields instead of inside a two-keyword `keyword` string. `hint_source` says
            # which router answered (metadata beats DOM family, CLAUDE.md). `hint_reason` is the
            # tri-state rule made structural: an element with a real family and NO keyword anywhere
            # states why -- 1,004 of them said nothing at all before this.
            # the variant sees EVERY attribute of the node (role, data-tabid...), not only the stable
            # key attributes -- the discriminator of a console tab is not a locator attribute
            all_attrs = {k: (' '.join(v) if isinstance(v, list) else v) for k, v in (tag.attrs or {}).items()}
            hint_fill, hint_verify, hint_source, hint_reason, _row = self._route_keywords(
                self._family_variant(element_type, identification, context, real_tag, all_attrs),
                (identification or {}).get('label_text'))
            if hint_fill:
                element_data['hint_fill'] = hint_fill
            if hint_verify:
                element_data['hint_verify'] = hint_verify
            # 2026-09-11: a routing row's `act` keyword (console-subtab -> Open Console Subtab, tree items ->
            # Click Tree Item) was routed and then dropped -- the review only ever saw the ClickText rung
            if isinstance(_row, dict) and _row.get('act'):
                element_data['hint_act'] = _row['act']
            if hint_source:
                element_data['hint_source'] = hint_source
            has_keyword = any(
                (h or {}).get('keyword')
                for h in ((qforce_hints or {}).get('locator_options') or []))
            if not hint_fill and not hint_verify and not has_keyword:
                element_data['hint_reason'] = hint_reason or (
                    "no keywordRouting row and no keyword hint resolved for family %r"
                    % (element_type,))

            pruned = self._prune_empty_values(element_data)
            # interop T10: the source node, kept only so _row_anchor can read
            # the surrounding row while annotating repeated groups. It is
            # stripped again at the end of _deduplicate_form_fields, so it
            # never reaches a caller or a serialized capture.
            pruned['_tag'] = tag
            return pruned
        except Exception:
            return None

    def _get_key_attributes(self, tag) -> dict:
        attrs = {}
        allowed = {
            'id', 'name', 'type', 'role', 'aria-label', 'aria-haspopup', 'aria-controls',
            'aria-expanded', 'aria-selected', 'aria-checked', 'aria-required', 'aria-disabled',
            'aria-invalid', 'aria-readonly', 'aria-multiselectable', 'aria-labelledby', 'aria-describedby',
            'data-testid', 'data-test-id', 'data-id', 'data-record-id', 'data-object-api-name',
            'data-field', 'data-field-name', 'data-value', 'data-col-key-value', 'data-tab-value',
            'data-label', 'data-aura-class', 'data-target-selection-name', 'field-label',
            'href', 'title', 'placeholder', 'value', 'inputmode',
            'maxlength', 'min', 'max', 'step',
            # 2026-09-07 iframe descent: the frame shell's own src (may be
            # empty on an Aura-managed VF iframe populated by JS, not a
            # literal src attribute -- confirmed live on both C4c/C4b
            # captures, see iframe_descent.py).
            'src',
        }
        meaningful_aura = re.compile(
            r'(forceOutput|forceInput|uiInput|runtime_|forceRecord|forceLookup|forceAction|forceSearch|forceList)',
            re.IGNORECASE,
        )
        # 2026-09-10 (five of seventeen industry-page audits): an HTML boolean attribute is TRUE
        # exactly when its value is empty (disabled="", readonly=""), and this loop dropped empty
        # values -- so a disabled button shipped as clickable and read VERIFIED-PASS on resolution.
        # Template `booleanStateAttributes` (default below); they are state, never a locator.
        booleans = set(getattr(self.config, 'BOOLEAN_STATE_ATTRIBUTES', None)
                       or ('disabled', 'readonly', 'checked', 'required', 'hidden'))
        for attr in sorted(allowed | booleans):
            val = tag.get(attr)
            if attr in booleans:
                if val is None:
                    continue
                # kept with the DOM's own value ('' when bare): a locator built from attrs
                # (`@disabled=""`) must match the live element; PRESENCE of the key means true
                attrs[attr] = '' if (val in ('', attr, True) or isinstance(val, list)) else str(val)
                continue
            if val is None or val == '':
                continue
            if isinstance(val, list):
                val = ' '.join(val)
            # 2026-09-06 (review T4): this checked ONLY `id`, so a Visualforce auto-generated
            # `name` ("j_id0:j_id1:j_id2:j_id3:bottom:j_id4") sailed through and became the
            # ClickItem locator the recorder emits -- an identity that renumbers on the next VF
            # recompile. `name` is a targeting source exactly like `id`, so it is classified
            # exactly like `id`.
            if attr == 'id' and self.classifier._classify_id(val) == 'runtime_garbage':
                continue
            if attr == 'name' and self.classifier.VF_ALL_AUTO_ID_RE.match(val):
                continue
            if attr == 'data-aura-class' and not meaningful_aura.search(val):
                continue
            attrs[attr] = val
        return attrs

    # ------------------------------------------------------------- labels ----
    # interop T10 2026-09-07: the label precedence order is POLICY, and policy
    # lives in the template (docs/recorder/templates/*.json `labelPrecedence`),
    # not in this file. Each entry below is a `label_source` name mapped to the
    # zero-cost-until-called producer of that candidate. The physical emission
    # order in _get_identification is unchanged -- only WHICH rung wins is
    # template-driven -- so a template that keeps the default order produces
    # byte-identical output (tests/templates/test_byte_equivalence.py).
    def _label_candidate(self, tag, source):
        if source == 'aria_label':
            v = tag.get('aria-label')
            return v.strip()[:100] if v and v.strip() else None
        if source == 'standard_label':
            return self._find_label_for_text(tag) or None
        if source == 'aria_labelledby':
            return self._find_aria_labelledby_text(tag) or None
        if source == 'form_element_label':
            return self._find_form_element_label(tag) or None
        if source == 'placeholder':
            v = tag.get('placeholder')
            return v.strip()[:100] if v and v.strip() else None
        if source == 'title_attr':
            v = tag.get('title')
            return v.strip()[:100] if v and v.strip() else None
        if source == 'sibling_label_text':
            tag_name = tag.name.lower() if tag.name else ''
            if tag_name == 'input' and (tag.get('type') or '').lower() in ('radio', 'checkbox'):
                return self._find_radio_label_text(tag) or None
            return None
        if source == 'label_span':
            return self._find_label_span_text(tag) or None
        if source == 'inner_text':
            tag_name = tag.name.lower() if tag.name else ''
            role = (tag.get('role') or '').lower()
            # wave-2 review close, stream P1 2026-09-07 -- CAUGHT BY ITS OWN TEST.
            # For most controls the element's own text is its NAME. For a value
            # display it is the VALUE: a Lightning picklist renders
            # <button role="combobox" aria-label="Industry">--None--</button>,
            # and promoting inner_text turned the labels of `Type` and `Industry`
            # on 04-account-new-record-modal.html into '--None--' -- the exact
            # label-vs-value confusion CLAUDE.md's "rule that matters most"
            # names (get_field_value("Stage") returning "Stage"), inverted. It
            # broke the org map's metadata->control routing, which matches on the
            # label. Roles listed in the template's `innerTextExcludedRoles`
            # therefore never claim the inner_text rung and fall through to their
            # accessible name.
            if role and role in self._inner_text_excluded_roles():
                return None
            if tag_name in ('button', 'a') or role == 'button':
                # wave-2 review close, stream P1 2026-09-07 (F11): was
                # _get_safe_text, which happily concatenated an
                # slds-assistive-text span onto the visible text
                # ('* More Show more navigation items', L2-R13).
                inner = self._visible_inner_text(tag)
                # 2026-09-10 (six of seventeen industry-page audits): a literal 60-char ceiling here
                # returned None for links whose visible text is 74-86 chars (learning cards, long
                # record links) -- no label and no call at all. Every other rung truncates at 100;
                # this one now does the same. Template `labelMaxLen` (default 100).
                cap = int(getattr(self.config, 'LABEL_MAX_LEN', None) or 100)
                if inner and 0 < len(inner):
                    return inner[:cap]
            return None
        if source == 'assistive_text':
            # 2026-09-10: a multi-control container never takes a screen-reader label stitched from
            # its children (c-zoo-base-inputs read "Select a date for Date Format: ... Select a date
            # for Date (secondary) ..." once label_span stopped claiming its first field's label)
            if self._is_multi_control_container(tag):
                return None
            return self._assistive_only_text(tag) or None
        return None

    def _resolve_label(self, tag):
        """(label_text, label_source) for `tag`, choosing the first rung of the
        template's `labelPrecedence` that produces a value. Returns (None, None)
        when no configured rung resolves."""
        # 2026-09-10: a structural control (template `structuralContainerRules`) names its own
        # label source -- the nearest PRECEDING element carrying the declared class fragment, outside
        # the control (the SLDS dueling list's slds-form-element__label "Entitled Services"; its first
        # inner span "Available" is a column heading, not the label a person reads).
        structural = self._structural_label(tag)
        if structural:
            return structural, 'form_element_label'
        order = getattr(self.config, 'LABEL_PRECEDENCE', None) or []
        for source in order:
            try:
                value = self._label_candidate(tag, source)
            except Exception:
                value = None
            if value:
                return value, source
        return None, None

    def _structural_label(self, tag):
        rules = getattr(self.config, 'STRUCTURAL_CONTAINER_RULES', None) or []
        classes = ' '.join(tag.get('class') or []).lower()
        for rule in rules:
            frag_label = rule.get('labelFromPrecedingClassFragment')
            if not frag_label or not any(f in classes for f in (rule.get('containerClassFragments') or [])):
                continue
            inside = set(id(n) for n in tag.find_all(True))
            for prev in tag.find_all_previous(True):
                if id(prev) in inside:
                    continue
                if frag_label in ' '.join(prev.get('class') or []):
                    # bs4 types strings under <template> (the capture's shadow roots) as
                    # TemplateString and get_text()/strings skip them: read the strings directly
                    from bs4 import NavigableString as _NS, Comment as _C
                    text = ' '.join(str(t).strip() for t in prev.descendants
                                    if isinstance(t, _NS) and not isinstance(t, _C) and str(t).strip())
                    if text:
                        return text[:100]
                    break
            return None
        return None

    def _get_identification(self, tag) -> dict:
        result = {}
        # The winner is chosen by the TEMPLATE's precedence; it is then emitted
        # at the physical position of its own rung below, exactly where the
        # pre-T10 hard-coded chain put it.
        won_text, won_source = self._resolve_label(tag)

        def _claim(source):
            if won_source == source and 'label_text' not in result:
                result['label_text'] = won_text
                result['label_source'] = source

        _claim('form_element_label')      # 2026-09-10: a structural control's declared label source

        aria_label = tag.get('aria-label')
        if aria_label and aria_label.strip():
            _claim('aria_label')
            result['aria_label'] = aria_label.strip()[:100]

        # 2026-09-07 (interop T4 follow-up, orchestrator): the TypeText gate in _get_qforce_hints
        # accepts 'standard_label' / 'aria_labelledby', but nothing ever PRODUCED them -- the
        # standard Lightning shape (<label class="slds-form-element__label" for="input-142">Phone</label>
        # beside the input) was never read, so 10 of 11 inputs on Zoo_Aura had no label at all and
        # TypeText was offered on 2 of 82 input fields across five pages. Measured before this branch.
        _claim('standard_label')
        _claim('aria_labelledby')

        placeholder = tag.get('placeholder')
        if placeholder and placeholder.strip():
            result['placeholder'] = placeholder.strip()[:100]
        _claim('placeholder')
        # wave-2 review close, stream P1 2026-09-07. `title` is now recorded
        # UNCONDITIONALLY, exactly as `aria_label` already was, and for the same
        # reason: since visible text outranks it, the title is usually no longer
        # the winning rung, but it is still a real identity the element carries
        # and downstream consumers (the loss audit's identity match, ClickItem's
        # attribute-value locator) need to see it. Dropping it the moment it
        # stopped winning would have turned a label-policy change into a
        # measured recall loss on controls the parser never stopped keeping.
        title = tag.get('title')
        if title and title.strip():
            result['title'] = title.strip()[:100]
        _claim('title_attr')

        el_id = tag.get('id')
        if el_id:
            id_type = self.classifier._classify_id(el_id)
            if id_type and id_type != 'runtime_garbage':
                result['id'] = el_id
                result['id_type'] = id_type

        name = tag.get('name')
        if name:
            # 2026-09-06 (review T4): `name` used to bypass the id classifier entirely, so a
            # Visualforce auto-generated `j_id0:j_id1:...` NAME became the recorder's targeting
            # key on 39 of 92 controls of slockard's ZooClassicForm. A name that classifies as
            # runtime garbage is not identification -- drop it rather than record a value that
            # renumbers on the next VF recompile.
            if not self.classifier.VF_ALL_AUTO_ID_RE.match(name):
                result['name'] = self.classifier._clean_name(name)

        description = self._find_description_text(tag)
        if description:
            result['description'] = description

        _claim('sibling_label_text')
        # label_span is not radio/checkbox-specific -- spans and divs get reused
        # as labels for all kinds of elements in Salesforce markup (table cells,
        # buttons, plain text holders), not just form inputs. Ported 2026-07-29
        # per direct user experience: "spans and divs are notoriously used as
        # tables, buttons and text holders in SF".
        _claim('label_span')
        _claim('inner_text')
        # wave-2 review close, stream P1 2026-09-07 (F11) -- LAST, by design:
        # screen-reader-only text is never what a person sees, so it labels a
        # control only when literally nothing else does (L2-R08's chevron-only
        # dropdown button). Its own label_source keeps that visible downstream.
        _claim('assistive_text')

        # interop T17 2026-09-07: captured UNCONDITIONALLY (not gated on which
        # rung won) so _get_qforce_hints can tell whether a title_attr/aria_label
        # value (an ACCESSIBLE NAME, not rendered text) is ALSO the element's own
        # rendered text -- e.g. a real <button>Save</button> vs an icon-only
        # <button title="Expand"> whose visible content is a bare chevron glyph.
        tag_name = tag.name.lower() if tag.name else ''
        role = (tag.get('role') or '').lower()
        if tag_name in ('button', 'a') or role == 'button':
            rendered = self._visible_rendered_text(tag)
            if rendered:
                result['rendered_text'] = rendered.strip()

        # F225 (the user, 2026-09-20): the page's REQUIRED MARKER is not part of the label.
        #   "the asterisk is commonly picked up by the recorder ... it's generally safe for just
        #    having the textual value. The asterisk mentions that this is a required field, but if
        #    that field then becomes optional later and we're referring to it with an asterisk, the
        #    test fails. The signal of knowing it is required is useful, but not a great locator."
        # So the marker comes OFF the locator and the fact it carried is kept as data. Measured
        # over the 146 committed captures: 10 labels of 13,782 (0.07%) across 6 captures, from
        # THREE different rungs -- `label_span` 7, `aria_label` 2, `standard_label` 1 -- which is
        # why this sits at the end of the one function that finalises a label rather than inside
        # any single rung. Two of them, `Close Date *` and `Owner Name *`, were silently
        # unmatchable against the page's own field list for exactly this reason.
        # Narrow on purpose: a LEADING or TRAILING `*`/bullet only. Never the word "required"
        # (that would maul a real label like "Required Approvals") and never a mid-string `*`.
        self._split_required_marker(result)
        return result

    #: a leading or trailing required marker -- the SLDS `*` and the bullet some themes use.
    _EDGE_REQUIRED_MARK_RE = re.compile(r'^[\s*\u2022]+|[\s*\u2022]+$')

    @classmethod
    def _split_required_marker(cls, identification: dict) -> None:
        """Strip the required marker off `label_text` IN PLACE and record what it meant.

        `label_required` is the fact the marker carried, kept because the user asked for it to
        survive: a reader (or the review table) can still see the page said this field is
        required, without the locator depending on it staying required tomorrow."""
        label = identification.get('label_text')
        if not label:
            return
        clean = cls._EDGE_REQUIRED_MARK_RE.sub('', label).strip()
        if clean and clean != label:
            identification['label_text'] = clean
            identification['label_required'] = True

    def _find_radio_label_text(self, tag) -> str:
        """Visible short label for a radio/checkbox <input> inside a <label>
        wrapper -- e.g. the "Lead" span sitting alongside the longer
        description text in Salesforce's record-type-selection modal.
        Deliberately excludes anything DESCRIPTION_CLASS_FRAGMENTS would also
        match, since some Aura components (changeRecordTypeLabel) use
        "label" in a class name that's actually the description."""
        if not tag:
            return ''

        def _matches_description_class(el):
            classes = ' '.join(el.get('class') or [])
            return any(frag in classes for frag in self._description_class_fragments())

        def _matches_label_class(el):
            classes = ' '.join(el.get('class') or [])
            if _matches_description_class(el):
                return False
            return any(frag in classes for frag in self._label_class_fragments())

        parent_label = tag.find_parent('label')
        if parent_label:
            for label_el in parent_label.find_all(True):
                if _matches_label_class(label_el):
                    text = self.text_engine._get_safe_text(label_el, max_len=100)
                    if text:
                        return text
        return ''

    def _visible_label_text(self, node) -> str:
        """Label text as a SIGHTED user reads it -- with the SLDS required marker and every
        other aria-hidden decoration removed. Lightning renders a required field's label as
        <label><abbr class="slds-required" aria-hidden="true" title="required">*</abbr>Account
        Name</label>; taking the raw text yields "* Account Name", and TypeText("* Account
        Name") resolves nothing. Measured on Zoo_Record_Forms__default 2026-09-07 (stream T9).
        """
        if node is None:
            return ''
        try:
            cloned = BeautifulSoup(str(node), 'html.parser').find(node.name)
        except Exception:
            cloned = None
        if cloned is None:
            return self.text_engine._get_safe_text(node, max_len=100)
        for selector in self._required_marker_selectors():
            try:
                for hidden in cloned.find_all(attrs=selector):
                    hidden.decompose()
            except Exception:
                continue
        return self.text_engine._get_safe_text(cloned, max_len=100)

    # interop T17 2026-09-07: what a SIGHTED user actually sees inside an
    # element -- unlike _get_safe_text (used for the raw candidate text of
    # every OTHER rung), this strips SLDS's screen-reader-only text (the
    # `<span class="slds-assistive-text">Expand</span>` SLDS glues inside an
    # icon-only button) before extracting text. Live-confirmed the caret
    # record needs this: the button carries no visible text at all (a bare
    # chevron <svg>), but a naive get_text() picks up the assistive-text
    # span's "Expand" -- identical to the title attribute -- which would
    # wrongly make _get_qforce_hints think the accessible name IS rendered
    # text and skip reordering ClickItem ahead of ClickText.
    # wave-2 review close, stream P1 2026-09-07 (F11): this tuple is now the
    # code-default FALLBACK only -- the live list is the template's
    # `assistiveTextClassFragments` (dom_config.ASSISTIVE_TEXT_CLASS_FRAGMENTS),
    # read through _assistive_text_class_fragments() below, because every
    # platform rule is template data (CLAUDE.md, docs/recorder/TEMPLATES.md).
    ASSISTIVE_TEXT_CLASS_FRAGMENTS = ('slds-assistive-text', 'sr-only', 'visually-hidden', 'slds-hidden')

    # wave-2 review close, stream P1 2026-09-07. Code-default fallback for the
    # template key `innerTextExcludedRoles` -- roles whose own rendered text is
    # the control's VALUE, not its name.
    INNER_TEXT_EXCLUDED_ROLES = ('combobox', 'listbox', 'textbox', 'searchbox',
                                 'spinbutton', 'slider', 'option')

    def _inner_text_excluded_roles(self):
        configured = getattr(self.config, 'INNER_TEXT_EXCLUDED_ROLES', None)
        if configured is None:
            return set(self.INNER_TEXT_EXCLUDED_ROLES)
        return set(configured)

    def _assistive_text_class_fragments(self):
        configured = getattr(self.config, 'ASSISTIVE_TEXT_CLASS_FRAGMENTS', None)
        if configured is None:
            return list(self.ASSISTIVE_TEXT_CLASS_FRAGMENTS)
        return list(configured)

    def _strip_assistive_text(self, tag):
        """A clone of `tag` with every screen-reader-only subtree removed.

        wave-2 review close, stream P1 2026-09-07 (F11). Nothing else is
        removed -- in particular aria-hidden="true" is LEFT IN PLACE, which is
        the difference from _visible_rendered_text below: Lightning's overflow
        nav renders `<abbr aria-hidden="true">*</abbr><span
        aria-hidden="true">More</span><span class="slds-assistive-text">Show
        more navigation items</span>`, and both aria-hidden spans are
        CSS-VISIBLE. A sighted person reads "* More"; stripping aria-hidden
        would leave "*" and stripping nothing leaves "* More Show more
        navigation items" (L2-R13, the record this was measured on).
        """
        if not tag:
            return None
        try:
            cloned = BeautifulSoup(str(tag), 'html.parser').find(tag.name)
        except Exception:
            return None
        if cloned is None:
            return None
        fragments = self._assistive_text_class_fragments()
        if not fragments:
            return cloned
        try:
            for el in cloned.find_all(True):
                classes = ' '.join(el.get('class') or [])
                if any(frag in classes for frag in fragments):
                    el.decompose()
        except Exception:
            return None
        return cloned

    def _visible_inner_text(self, tag, max_len=60) -> str:
        """The element's own text as a sighted person reads it (F6/R12/F11).

        Producer for the `inner_text` rung, which stream P1 moved to the FRONT
        of LABEL_PRECEDENCE. Returns '' for an element whose only text is
        screen-reader-only, so the precedence chain falls through to
        title_attr / aria_label for a genuinely icon-only control.
        """
        cloned = self._strip_assistive_text(tag)
        if cloned is None:
            return ''
        return self.text_engine._get_safe_text(cloned, max_len=max_len)

    def _assistive_only_text(self, tag, max_len=100) -> str:
        """Text found ONLY inside screen-reader-only spans (F11, last rung).

        Never a visible label -- but on a chevron-only dropdown button whose
        sole name is `<span class="slds-assistive-text">Customer Project
        Profiles List</span>` (L2-R08) it is the only handle that exists, so it
        is offered last and stamped `label_source: assistive_text` rather than
        silently passed off as rendered text.
        """
        if not tag:
            return ''
        fragments = self._assistive_text_class_fragments()
        if not fragments:
            return ''
        parts = []
        try:
            for el in tag.find_all(True):
                classes = ' '.join(el.get('class') or [])
                if any(frag in classes for frag in fragments):
                    text = self.text_engine._get_safe_text(el, max_len=max_len)
                    if text:
                        parts.append(text)
        except Exception:
            return ''
        joined = ' '.join(parts).strip()
        return joined[:max_len] if joined else ''

    def _visible_rendered_text(self, tag, max_len=100) -> str:
        if not tag:
            return ''
        try:
            cloned = BeautifulSoup(str(tag), 'html.parser').find(tag.name)
        except Exception:
            cloned = None
        if cloned is None:
            return ''
        try:
            for hidden in cloned.find_all(True):
                classes = ' '.join(hidden.get('class') or [])
                if any(frag in classes for frag in self._assistive_text_class_fragments()):
                    hidden.decompose()
                    continue
                if hidden.get('aria-hidden') == 'true':
                    hidden.decompose()
        except Exception:
            return ''
        return self.text_engine._get_safe_text(cloned, max_len=max_len)

    def _id_index(self, tag):
        """One {id: element} index per document, built lazily on first use (a <label for=> lookup
        from every input would otherwise walk the whole tree per element)."""
        root = tag
        while getattr(root, 'parent', None) is not None:
            root = root.parent
        cache = getattr(self, '_id_index_cache', None)
        if cache is None or cache[0] is not root:
            index = {}
            for el in root.find_all(True):
                el_id = el.get('id')
                if el_id and el_id not in index:
                    index[el_id] = el
            cache = (root, index)
            self._id_index_cache = cache
        return cache[1]

    def _find_label_for_text(self, tag) -> str:
        """<label for="<this tag's id>"> -- the standard HTML/Lightning association."""
        el_id = tag.get('id')
        if not el_id:
            return ''
        root = tag
        while getattr(root, 'parent', None) is not None:
            root = root.parent
        cache = getattr(self, '_label_for_cache', None)
        if cache is None or cache[0] is not root:
            index = {}
            for lab in root.find_all('label'):
                target = lab.get('for')
                if target and target not in index:
                    text = self._visible_label_text(lab)
                    if text:
                        index[target] = text
            cache = (root, index)
            self._label_for_cache = cache
        return cache[1].get(el_id, '')

    def _form_element_spec(self):
        return getattr(self.config, 'FORM_ELEMENT_LABEL', None) or {}

    def _form_element_of(self, node, spec):
        """The nearest ancestor that IS the form element (class carries the container fragment and
        none of the excluded sub-part fragments), or None."""
        frag = spec.get('containerClassFragment') or ''
        excl = spec.get('excludeContainerClassFragments') or []
        depth_cap = int(spec.get('maxClimb') or 8)
        depth = 0
        while node is not None and depth < depth_cap:
            classes = ' '.join(node.get('class') or []) if hasattr(node, 'get') else ''
            if frag and frag in classes and not any(e in classes for e in excl):
                return node
            node = getattr(node, 'parent', None)
            depth += 1
        return None

    def _is_multi_control_container(self, tag) -> bool:
        """2026-09-10: a wrapper around SEVERAL form elements that each hold a control is a
        container (c-zoo-nightmare-row: Start Date, End Date, Billable; c-zoo-base-inputs: a whole
        form), and a label inside one of those form elements belongs to that control, never to the
        container -- nor does the container get a screen-reader label stitched from its children.
        A wrapper around exactly ONE such form element IS that control (lightning-lookup,
        lightning-input: the parser keys off the LWC wrapper tag) and keeps its label. A read-mode
        record field (records-record-layout-item > slds-form-element with a value span, no input)
        also keeps its label -- measured on the record-page and 02b lookup tests. Template
        `formElementLabel.containerRowsNeverClaimIt` / `containerMinControls`."""
        fe_spec = self._form_element_spec()
        if not fe_spec or not fe_spec.get('containerRowsNeverClaimIt') or not tag:
            return False
        owners = []
        for fe in tag.find_all(lambda n: n is not tag and self._form_element_of(n, fe_spec) is n):
            if self._form_element_holds_a_control(fe) and not any(any(p is o for p in fe.parents) for o in owners):
                owners.append(fe)
        return len(owners) >= int(fe_spec.get('containerMinControls') or 2)

    def _form_element_holds_a_control(self, fe) -> bool:
        """Does this form element contain something the parser emits as a control -- a native
        input/select/textarea, or a structural control (template structuralContainerRules, e.g. the
        SLDS dueling list)? Its label then belongs to that control, never to a wrapper above."""
        if fe.find(['input', 'select', 'textarea']) is not None:
            return True
        frags = [f for rule in (getattr(self.config, 'STRUCTURAL_CONTAINER_RULES', None) or [])
                 for f in (rule.get('containerClassFragments') or [])]
        if frags and fe.find(lambda n: any(f in ' '.join(n.get('class') or []) for f in frags)) is not None:
            return True
        return False

    def _find_form_element_label(self, tag) -> str:
        """2026-09-10 (user, Zoo_Nightmare_Inputs): the standard SLDS shape --
        <div class="slds-form-element"><div class="slds-form-element__label-wrapper">
        <label class="slds-form-element__label">X</label></div><div class="slds-form-element__control">
        ...<input></div></div> -- carries no for=, and the label is neither an ancestor nor a
        descendant of the control, so standard_label and label_span never read it: 26 of 26 controls
        on that page parsed unlabelled. Climb to the enclosing form element and read its label element
        (the first label-class element OUTSIDE the control's own subtree); a form element with no
        label of its own climbs to the next (the Approved Budget from/to pair); a control sitting
        inside the label wrapper (the readonly helper beside Contract Term) is not the control and
        gets nothing. Everything here is the template's `formElementLabel`."""
        spec = self._form_element_spec()
        if not spec or not tag:
            return ''
        # 2026-09-10 late (twelve industry-page audits): the rung is for the CONTROL the label names --
        # a native form control, or a custom wrapper around exactly one. It labelled the inline-edit
        # PENCIL with the field's name (<button title="Edit Name"> inside the field's form element read
        # "Name": 56 rows on 4 pages, click_text('Name', index=2) CAUGHT-BUG live). Template `targetTags`.
        tt = spec.get('targetTags')
        if tt:
            name = (tag.name or '').lower()
            if name not in tt:
                wrapper_ok = (spec.get('wrapperMayBeTarget') and '-' in name
                              and len(tag.find_all(['input', 'select', 'textarea'])) == 1)
                if not wrapper_ok:
                    return ''
        # a control inside an excluded sub-part (the label wrapper's helper input) is not labelled
        for frag in spec.get('targetInsideExcludedClassFragments') or []:
            node = getattr(tag, 'parent', None)
            hops = 0
            while node is not None and hops < 4:
                if frag in ' '.join(node.get('class') or []):
                    return ''
                node = getattr(node, 'parent', None)
                hops += 1
        label_frags = spec.get('labelClassFragments') or self._label_class_fragments()
        inside = None
        node = getattr(tag, 'parent', None)
        climbs = 0
        while node is not None and climbs < int(spec.get('maxClimb') or 8):
            fe = self._form_element_of(node, spec)
            if fe is None:
                return ''
            if inside is None:
                inside = set(id(n) for n in tag.find_all(True)) | {id(tag)}
            for lab in fe.find_all(True):
                if id(lab) in inside:
                    continue
                classes = ' '.join(lab.get('class') or [])
                if not any(f in classes for f in label_frags):
                    continue
                if any(d in classes for d in self._description_class_fragments()):
                    continue
                # the label must not belong to ANOTHER control's form element nested inside this one
                other = self._form_element_of(getattr(lab, 'parent', None), spec)
                if other is not None and other is not fe and id(other) not in set(id(a) for a in tag.parents):
                    continue
                from bs4 import NavigableString as _NS, Comment as _C
                text = ' '.join(str(t).strip() for t in lab.descendants
                                if isinstance(t, _NS) and not isinstance(t, _C) and str(t).strip())
                text = text.strip()
                if text:
                    return text[:100]
            if not spec.get('climbWhenUnlabelled'):
                return ''
            node = getattr(fe, 'parent', None)
            climbs += 1
        return ''

    def _find_aria_labelledby_text(self, tag) -> str:
        """aria-labelledby="id1 id2" -> the referenced elements' text, joined."""
        ref = (tag.get('aria-labelledby') or '').strip()
        if not ref:
            return ''
        index = self._id_index(tag)
        parts = []
        for rid in ref.split():
            el = index.get(rid)
            if el is not None:
                text = self._visible_label_text(el)
                if text:
                    parts.append(text)
        return ' '.join(parts)[:100]

    def _find_label_span_text(self, tag) -> str:
        """General label-span lookup, not gated to any specific element
        type: checks the tag's own descendants, then an ancestor <label>
        wrapper, for a dedicated .slds-form-element__label (or
        slds-radio__label/slds-checkbox__label) span/div -- the cleanest
        source for a human-readable name when nothing else (aria-label,
        placeholder, title) resolved one. Ported from the legacy
        DomParserLibrary.py's _get_label_span_text, generalized beyond its
        original narrow radio/checkbox-only caller per direct user
        direction 2026-07-29."""
        if not tag:
            return ''

        def _matches_description_class(el):
            classes = ' '.join(el.get('class') or [])
            return any(frag in classes for frag in self._description_class_fragments())

        # 2026-09-10 (seven of seventeen industry-page audits): the highlights panel's fields
        # (records-highlights-details-item) name themselves with <p class="slds-text-title" title=..>,
        # not slds-form-element__label -- template recordLayoutFieldRules.labelClassFragmentsByTag
        per_tag = ((getattr(self.config, 'RECORD_LAYOUT_FIELD_RULES', None) or {}).get('labelClassFragmentsByTag') or {})
        extra = per_tag.get((tag.name or '').lower(), []) if getattr(tag, 'name', None) else []
        frags = list(self._label_class_fragments()) + list(extra)

        def _matches_label_class(el):
            classes = ' '.join(el.get('class') or [])
            if _matches_description_class(el):
                return False
            return any(frag in classes for frag in frags)

        fe_spec = self._form_element_spec()
        is_container = self._is_multi_control_container(tag)
        for descendant in tag.find_all(True):
            if _matches_label_class(descendant):
                if is_container:
                    owner = self._form_element_of(getattr(descendant, 'parent', None), fe_spec)
                    if owner is not None and owner is not tag and any(p is tag for p in owner.parents):
                        continue
                text = self.text_engine._get_safe_text(descendant, max_len=100)
                if text:
                    return text

        parent_label = tag.find_parent('label')
        if parent_label:
            for label_el in parent_label.find_all(True):
                if label_el is tag:
                    continue
                if _matches_label_class(label_el):
                    text = self.text_engine._get_safe_text(label_el, max_len=100)
                    if text:
                        return text
        return ''

    def _get_qforce_hints(self, element_type, identification, context, attributes, real_tag=None) -> dict:
        """Ranked locator recommendations, tied to how this project's own
        real keyword implementations (actions.py/qforce_lite.py) actually
        resolve elements -- not a generic aria_label/placeholder reliability
        scale. Each hint is a ready-to-use call shape (call_example), not a
        bare locator string -- 'locator' stays alongside it as the raw
        matched value, used both to build call_example and for cross-page
        uniqueness checking in _annotate_ambiguous_hints.

        D14 2026-09-09: the five-tier confidence scale settled 2026-07-29
        (unique_structural / unique_on_this_page / ambiguous_needs_anchor /
        ambiguous_unresolved / anchored_unique) is RETIRED. Every tier was a
        PREDICTION about what a call would resolve at run time, made from a
        static capture, and the top tier was measured wrong on a live page
        (docs/errors/entries/7627c1f2a9.json). Every hint built here is
        `unverified`; only `stamp_resolution`, fed the POM store's verified
        labels by the caller, can say otherwise. What ORDER the hints come in
        still matters and is unchanged -- the first rung is the one this
        module thinks a caller should try first, which is a description of
        the page, not a claim about the run. _annotate_ambiguous_hints, a
        second pass over the FULL element list in
        _parse_elements_from_html, confirms or downgrades those.

        real_tag is the element's literal HTML tag (element_details.tag),
        NOT element_type (a behavioral/ARIA classification -- see
        crt_relay.py's own docstring for the same distinction, confirmed
        live: an <a role="button"> classifies as element_type "button" but
        its real tag stays "a"). Only used to build ClickItem's call_example
        -- real QWeb's ClickItem needs the real tag whenever the target
        falls outside its tag-less default allowlist (a, span, img, li,
        h1-h6, div, svg, p, button, input[submit])."""
        label_text = identification.get('label_text')
        label_source = identification.get('label_source')
        rendered_text = identification.get('rendered_text')
        in_grid = bool(context and (context.get('is_in_datatable') or context.get('in_grid')))
        # data-value is the CURRENT VALUE of a combobox/picklist-shaped
        # control (e.g. a Font picker showing "Salesforce Sans") -- distinct
        # from label_text (the field's identity). Surfaced separately below
        # as `displayed_value` so a consumer can tell what a person actually
        # sees without confusing it with the locator. interop T17 2026-09-07.
        displayed_value = attributes.get('data-value') or None
        hints = []

        if in_grid:
            locator = "row/col coordinates (r{N}/c{M})"
            hints.append({
                'keyword': 'Click Table Cell',
                'locator': locator,
                'call_example': _call_example('Click Table Cell', locator),
                'confidence': TIER_UNVERIFIED,
                'why': "Inside a table/grid -- real Salesforce list/related-list rows routinely repeat "
                       "identical text across rows (same title, same owner name), so a text-based locator "
                       "can be genuinely ambiguous even when this element's own label looks unique in "
                       "isolation. Row/column position is the only address guaranteed unique by "
                       "construction. Confirmed live 2026-07-29 against Salesforce Files' own list view.",
                'caveats': ["Run UseTable first, on this table's own header label, to get the real "
                            "row/col coordinates -- this hint can't resolve them statically."],
            })

        reliable_label_sources = (
            'standard_label', 'aria_labelledby', 'form_element_label', 'wrapped_label', 'label_span', 'sibling_label_text',
        )
        if element_type == 'checkbox' and label_text:
            hints.append({
                'keyword': 'ClickCheckbox',
                'locator': label_text,
                'call_example': _call_example('ClickCheckbox', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': "Real ClickCheckbox is a component-specific mechanism, not a generic text/attribute "
                       "guess: it checks current state and no-ops if already correct, prefers the real SLDS "
                       "faux-span click target over the raw (often visually-hidden) input, and verifies the "
                       "final checked-state after clicking, raising if it didn't take.",
                'caveats': ['Pass value="on"/"off" for the target state.'],
            })
        elif (element_type in ('input_field', 'dropdown', 'textarea') and label_source in reliable_label_sources
              and attributes.get('role') != 'combobox'):
            keyword = 'PickList' if element_type == 'dropdown' else 'TypeText'
            confidence = TIER_UNVERIFIED
            hints.append({
                'keyword': keyword,
                'locator': label_text,
                'call_example': _call_example(keyword, label_text),
                'confidence': confidence,
                'why': f"Real associated label ({label_source}) -- matches {keyword}'s actual field-resolution "
                       "chain (label-based DOM/shadow search), not a guess at visible text."
                       + (" PickList resolves via a scoped lightning-combobox xpath keyed on this label, "
                          "which avoids generic text ambiguity by construction." if keyword == 'PickList' else ""),
                'caveats': [],
            })
        # NEW 2026-07-31: ComboBox never had a hint branch at all, in this
        # function's entire history -- confirmed live on a real Lead edit
        # form's "Address Search" field (tag=input type=text, role=combobox,
        # placeholder="Search Address"): it fell through every existing
        # branch (label_source was 'aria_label', not in
        # reliable_label_sources, so even a wrong TypeText assignment never
        # fired) straight to the generic ClickItem-only fallback -- silent,
        # not an error, so nothing flagged it was missing until read by eye.
        # Real bug this would have caused if TypeText HAD fired instead:
        # already documented elsewhere in this project (TypeText's blur
        # after typing closes a combobox-role field's live-filtered
        # dropdown before a result can be selected) -- so this is gated on
        # the real structural signal (role=="combobox" on an input_field),
        # not label_source reliability, and takes priority over TypeText
        # whenever both would otherwise apply.
        elif element_type == 'input_field' and attributes.get('role') == 'combobox':
            locator = label_text or identification.get('placeholder', '')
            hint = {
                'keyword': 'ComboBox',
                'locator': locator,
                'call_example': _call_example('ComboBox', locator),
                'confidence': TIER_UNVERIFIED,
                'why': "role=\"combobox\" on a text input is real QForce/QWeb ComboBox's actual shape -- a "
                       "type-to-search lookup with a live-filtered result dropdown, not a plain text field. "
                       "Field resolution reuses TypeText's real label-based chain, but the SELECT step needs "
                       "ComboBox's own shadow-DOM-aware result-matching, and critically must not blur after "
                       "typing (TypeText's default) -- blurring closes the live dropdown before a result can "
                       "be clicked.",
                'caveats': ["If this exact label doesn't resolve, try the field's placeholder text instead "
                            "(anchor= to the field's real label if more than one lookup shares that "
                            "placeholder) -- both are real, live-confirmed ComboBox locator strategies."],
            }
            if displayed_value:
                hint['displayed_value'] = displayed_value
            hints.append(hint)
        elif element_type == 'dropdown' and label_text:
            hint = {
                'keyword': 'PickList',
                'locator': label_text,
                'call_example': _call_example('PickList', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': "PickList resolves via a scoped lightning-combobox xpath keyed on this label -- "
                       "structurally unique regardless of how confidently the label itself was identified.",
                'caveats': ["Confirm this is the field's real label, not its currently displayed value or a "
                            "placeholder -- confirmed live: passing the placeholder finds the field but "
                            "fails to complete selection."],
            }
            # interop T17 2026-09-07 (Font combobox record, slockard-zoo-v3/
            # edit-modal-standard.html): data-value on a combobox/picklist is the
            # CURRENT DISPLAYED VALUE ("Salesforce Sans"), not the field's identity
            # -- surfaced alongside the label so a consumer can read what a person
            # sees without the record promoting the value into the locator.
            if displayed_value:
                hint['displayed_value'] = displayed_value
            hints.append(hint)

        # Added 2026-09-07 alongside the parser-families fix
        # (component_classifier.py's new lookup/combobox/date/datetime/time/
        # richtext element_type branches) -- these families had classify()
        # support but NO qforce_hints branch, so every one surfaced with
        # 'qforce_hints': None on both entry points (capture_orchestration.py
        # AND the Robot keyword, since both call this same compiler). Routed
        # per METADATA-KEYWORDS.md / tools/recorder/library/index.json, same
        # keyword names/callables already proven there -- not new keywords.
        elif element_type == 'lookup' and label_text:
            hints.append({
                'keyword': 'Aura Lookup',
                'locator': label_text,
                'call_example': _call_example('Aura Lookup', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': "lightning-lookup is the reference/lookup field shape METADATA-KEYWORDS.md routes "
                       "to combo_box via tools/recorder/library/index.json's 'Aura Lookup' entry -- same "
                       "mechanism as predict.type_to_keyword('reference') for a plain (non-OwnerId/"
                       "CreatedById/RecordTypeId) lookup.",
                'caveats': ["A type-to-search field -- combo_box types into it and selects from the "
                            "server-side-filtered result list; do not treat it as a plain text field."],
            })
        elif element_type == 'combobox' and label_text:
            hints.append({
                'keyword': 'ComboBox',
                'locator': label_text,
                'call_example': _call_example('ComboBox', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': "Standalone lightning-grouped-combobox/lightning-base-combobox (no lookup/"
                       "picklist/date/time ancestor already counting it) -- METADATA-KEYWORDS.md routes "
                       "the matching describe type 'combobox' to pick_list (a picklist that also accepts "
                       "free text); ComboBox/pick_list's real label-based resolution chain applies.",
                'caveats': [],
            })
        elif element_type in ('date', 'datetime') and label_text:
            hints.append({
                'keyword': 'Set Datetime',
                'locator': label_text,
                'call_example': _call_example('Set Datetime', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': ("lightning-datetimepicker is a COMPOUND control -- one database value, a date "
                        "input plus a 15-minute time combobox under one legend. predict.type_to_keyword"
                        "('datetime') routes it to set_datetime, never type_text_clearing; the DOM guard "
                        "inside the keyword is the backstop, not the router."
                        if element_type == 'datetime' else
                        "lightning-datepicker's field is typed as MM/DD/YYYY -- predict.type_to_keyword"
                        "('date') routes it 'certain' to type_text_clearing; set_datetime is offered here "
                        "too since a bare date field is also driveable through it (date-only args)."),
                'caveats': ["set_datetime types BOTH the date text and the time combobox in one call -- "
                            "for a date-only field with no time sibling, type_text_clearing is the plainer "
                            "path (predict.type_to_keyword's actual routing for describe type 'date')."],
            })
        elif element_type == 'time' and label_text:
            # stream 2A 2026-09-09: this used to offer the two-keyword string 'TypeText / ClickText'
            # for a shape whose OWN `why` says no keyword is proven for it. A hint that names two
            # keywords for a stated gap is worse than no hint -- the honest answer is the third
            # state, made visible, the same shape _hints_for_family already uses for a labelless
            # family member.
            hints.append({
                'keyword': None,
                'locator': label_text,
                'verdict': 'COULD-NOT-CHECK',
                'confidence': TIER_UNVERIFIED,
                'why': "predict.type_to_keyword('time') is a STATED could-not-check gap -- set_datetime "
                       "drives a date input plus a time combobox, and there is no time-ONLY keyword; "
                       "routing a standalone time field to set_datetime would type into a date box that "
                       "does not exist here.",
                'caveats': ["No proven keyword for a time-only field -- verify manually before automating."],
            })
        elif element_type == 'richtext' and label_text:
            hints.append({
                'keyword': 'Type Text Clearing',
                'locator': label_text,
                'call_example': _call_example('Type Text Clearing', label_text),
                'confidence': TIER_UNVERIFIED,
                'why': "lightning-quill's contenteditable is METADATA-KEYWORDS.md's "
                       "'textarea + extraTypeInfo=richtextarea' EXTRA_TYPE_POINTS row, routed to "
                       "qforce_lite.type_text_clearing (status VERIFIED-PASS) -- its rich-text branch "
                       "reads .innerText back off the contenteditable rather than reporting a pass blind.",
                'caveats': ["There is no <input>/<textarea> for a richtextarea field -- the plain text "
                            "branch was measured failing 3/3 live before this resolver existed."],
            })

        # ---- T12 2026-09-07: table-driven hint block, kept as its OWN
        # block (not folded into the elif chain above) so a sibling
        # stream's edits to that chain stay a mechanical merge. Covers
        # output_field / datatable / radio (P1 scorecard cut 5 -- 32, 29
        # and 48 controls respectively with a poor or absent hint) and
        # custom_component's explicit-absence hint. Reads
        # self.config.FAMILY_KEYWORDS / self.config.CUSTOM_COMPONENT_TAG_KEYWORDS
        # (dom_config.py 'familyKeywords'/'customComponentTagKeywords'
        # template keys) -- per the 2026-09-07 standing rule, the
        # family->keyword mapping is DATA, not a new literal branch.
        family_hint = self._hints_for_family(
            element_type, label_text, real_tag, identification=identification, context=context)
        if family_hint:
            hints.append(family_hint)

        if element_type in ('button', 'link') and label_text:
            confidence = TIER_UNVERIFIED
            caveats = (
                ["Pair with anchor=<nearby distinguishing text>, or prefer ClickTableCell above, given the "
                 "grid context -- real Salesforce grids routinely repeat identical row text."]
                if in_grid else []
            )
            hints.append({
                'keyword': 'ClickText',
                'locator': label_text,
                'call_example': _call_example('ClickText', label_text),
                'confidence': confidence,
                'why': "Resolves via ClickText's real text-search chain (light-DOM, then shadow-DOM tiers).",
                'caveats': caveats,
            })

        # Priority order per 2026-07-29 ground-truth mining against real New
        # Opportunity modal HTML (see qforce-lite-parser-design memory):
        # real ClickItem/find_by_attribute matches on attribute VALUE only,
        # doesn't care which named attribute it came from -- ranking here is
        # purely for CHOOSING the best candidate value to surface, not a
        # contradiction of that. data-target-selection-name/name/field-label
        # are tied to the real Salesforce field API name or an explicit
        # label attribute. title is a heavy, high-confidence candidate too
        # -- SLDS renders it as real tooltip text, directly human-legible
        # and stable across reloads, unlike the ephemeral render-counter
        # ids (`id="input-690"`-shaped) already excluded in
        # _get_key_attributes via _classify_id. data-label/data-value trail
        # as legacy fallbacks -- never explicitly confirmed stable. Even a
        # heavy-source attribute value could still repeat across identical
        # controls in a repeating list, same ambiguity risk class as
        # ClickText's visible text -- so `_annotate_ambiguous_hints` states
        # the page-wide count on it and `_annotate_anchors` gives it an index
        # when it repeats. (D14 2026-09-09: it used to be filed at the
        # provisional `unique_on_this_page` tier here and confirmed later;
        # there are no tiers to move between any more.)
        attr_candidates = [
            ('data-target-selection-name', attributes.get('data-target-selection-name')),
            ('name', attributes.get('name')),
            ('field-label', attributes.get('field-label')),
            ('title', attributes.get('title')),
            ('aria-label', attributes.get('aria-label')),
            ('data-label', attributes.get('data-label')),
            ('data-value', attributes.get('data-value')),
        ]
        # interop T20 2026-09-07 (user finding): the runtime-garbage test was
        # applied to `id` ONLY, so a counter-shaped generated `name`
        # ("lgt-datatable-1-options-1", the per-row Select checkbox on
        # slockard's Account list view) was offered here as "a stable attribute
        # value (name)". A generated value is not identification in ANY
        # attribute -- the candidate is dropped and the ladder falls through to
        # the next real one, exactly as it already did for `id`.
        attr_candidates = [
            (n, v) for n, v in attr_candidates
            if not (v and self.classifier.is_dynamic_value(v))
        ]
        attr_source, attr_value = next(((n, v) for n, v in attr_candidates if v), (None, None))
        # CORRECTED 2026-07-31: this used to be gated `and not hints` --
        # ClickItem's attribute-value hint only got generated when NO other
        # hint (e.g. ClickText) had already fired, treating it as a
        # last-resort fallback. Real bug, caught live by the user: a real
        # inline-edit-trigger button (title="Edit Opportunity Name", plus a
        # nested assistive-text span with identical inner text) had a
        # perfectly good ClickText hint AND a perfectly good, independently
        # resolving ClickItem-via-title-attribute hint available -- but only
        # the first ever got surfaced, silently discarding real
        # disambiguation power (ClickText and ClickItem use genuinely
        # different resolution mechanisms with different failure modes;
        # an icon-only control with the same attribute but no visible text
        # would need ClickItem specifically). Now offered whenever a stable
        # attribute value exists, independent of whether ClickText/etc.
        # already resolved -- not just as a fallback for when nothing else did.
        if attr_value:
            heavy_sources = {'data-target-selection-name', 'name', 'field-label', 'title', 'aria-label'}
            # 'input' is in ClickItem's tagless allowlist for SUBMIT BUTTONS
            # ONLY, per its real docstring -- confirmed live 2026-07-29: an
            # <input type="search"> (Salesforce's own list-view search box)
            # is NOT covered despite the tag name matching, and would
            # silently find nothing without tag= explicitly. Checking the
            # bare tag name alone (without also checking `type` for input)
            # was a real bug caught by this live test.
            tagless_safe_tags = {'a', 'span', 'img', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                  'div', 'svg', 'p', 'button'}
            is_tagless_safe = (
                real_tag in tagless_safe_tags
                or (real_tag == 'input' and attributes.get('type') == 'submit')
            )
            tag_caveat = (
                'Pass tag= explicitly regardless -- relying on the tagless default allowlist is '
                "incidental, not guaranteed, even when today's real tag happens to be in it."
                if is_tagless_safe else
                f'Real ClickItem (QWeb.keywords.text.click_item) needs tag="{real_tag}" here -- without '
                "it, it only searches a fixed allowlist (a, span, img, li, h1-h6, div, svg, p, button, "
                f"input[submit only]); \"{real_tag}\""
                + (f' type="{attributes.get("type")}"' if real_tag == 'input' else '')
                + " is outside that list, so a tagless call would silently find nothing, not error."
            )
            hints.append({
                'keyword': 'ClickItem',
                'locator': attr_value,
                # Explicit dedicated field, NOT just embedded in call_example
                # -- added 2026-08-26 after a cross-stream review (Stream 7,
                # via the live interop loop) found a consumer could read the
                # sibling top-level `element_type` field (a BEHAVIORAL/ARIA
                # classification -- an <a role="button"> classifies as
                # element_type "button") and mistake it for the real tag
                # ClickItem needs. real_tag (element_details.tag, the
                # literal HTML tag) was already correctly threaded into
                # call_example's `tag="..."` -- this just also surfaces it
                # as its own key so no consumer has to string-parse
                # call_example, and there's no field left doing double duty.
                'tag': real_tag,
                'call_example': _call_example('ClickItem', attr_value, tag=real_tag),
                'confidence': TIER_UNVERIFIED,
                'why': (f"A stable attribute value exists ({attr_source}, a heavy/high-confidence source)"
                        if attr_source in heavy_sources else
                        f"An attribute value exists ({attr_source}, a legacy/unconfirmed source)")
                       + (" -- offered alongside the text-based hint(s) above as an independent resolution "
                          "strategy, not just a fallback for when no visible-text label was found."
                          if hints else " -- no resolvable visible-text label was found, so this is the only "
                          "strategy available."),
                'caveats': [tag_caveat] if attr_source in heavy_sources else
                           [tag_caveat,
                            f"'{attr_source}' has not been directly confirmed stable across reloads -- prefer "
                             "a heavy-source hint if one becomes available."],
            })
            hints[-1]['why'] += (
                " -- real QWeb ClickItem (QWeb.keywords.text.click_item, already available, not a "
                "reimplementation) matches by attribute value (exact then partial), not visible text or "
                "attribute name, so it can reach icon-only controls ClickText can't."
            )

        if identification.get('placeholder') and not hints:
            # stream 2A 2026-09-09: was the two-keyword string 'TypeText / ClickText'. A placeholder
            # only ever appears on a control you can TYPE into, so the fill rung is the one keyword
            # this branch means; the ambiguity that string was carrying is about the LOCATOR, not
            # about which keyword, and it is already stated in the caveat below.
            hints.append({
                'keyword': 'TypeText',
                'locator': identification['placeholder'],
                'call_example': _call_example('TypeText', identification['placeholder']),
                'confidence': TIER_UNVERIFIED,
                'why': "Only a placeholder resolved -- placeholders are commonly reused across multiple "
                       "fields (e.g. generic 'Search...'), so this is a real fallback, not a confident pick.",
                'caveats': ["No stable label/attribute found -- verify this is actually the intended element "
                            "before relying on it."],
            })

        # wave-2 review close, stream P1 2026-09-07 (F11, L2-R08): when the
        # label came from the LAST rung -- screen-reader-only text -- every
        # hint built on it is targeting a string a sighted person cannot see,
        # and real QWeb click_text searches RENDERED text. That does not make
        # the hint useless (QWeb reads the accessibility tree too), but it must
        # never be offered as if it were visible text. The caveat text is
        # template data ('labelSourceCaveats'), keyed by label_source.
        caveats_by_source = getattr(self.config, 'LABEL_SOURCE_CAVEATS', None) or {}
        extra_caveat = caveats_by_source.get(label_source)
        if extra_caveat:
            for hint in hints:
                if hint.get('locator') == label_text:
                    hint.setdefault('caveats', [])
                    if extra_caveat not in hint['caveats']:
                        hint['caveats'] = list(hint['caveats']) + [extra_caveat]

        # interop T17 2026-09-07: a label sourced from title_attr/aria_label is
        # an ACCESSIBLE NAME, not rendered text -- ClickText (a rendered-text
        # search) is the wrong FIRST rung for it unless the same string is ALSO
        # present in the element's own rendered text (a real <button>Save</button>
        # whose aria-label happens to restate its own visible text). Order comes
        # from the template ('hintOrderByLabelSource'); HINT_ORDER_BY_LABEL_SOURCE
        # is the code-default fallback. Reordering is stable (Python sort) and
        # only moves keywords named in the configured order -- anything else
        # (family hints, ClickTableCell, etc.) keeps its relative position.
        if len(hints) > 1:
            hint_order = getattr(self.config, 'HINT_ORDER_BY_LABEL_SOURCE', None) or {}
            preferred = hint_order.get(label_source)
            label_is_rendered = bool(
                label_text and rendered_text
                and label_text.strip().lower() == rendered_text.strip().lower()
            )
            if preferred and not label_is_rendered:
                # Only permutes the SLOTS already occupied by keywords named in
                # `preferred` (e.g. ClickItem/ClickText) -- a plain full-list
                # sort would also drag an unrelated higher-priority hint (a
                # grid's ClickTableCell, a custom_component's explicit
                # COULD-NOT-CHECK placeholder) out of first place just because
                # its keyword/None isn't in `preferred`. Caught live:
                # test_datatable_first_hint_is_click_table_cell and
                # test_custom_component_with_no_known_family_gets_explicit_
                # could_not_check_not_nothing both broke on a naive full sort.
                idxs = [i for i, h in enumerate(hints) if h.get('keyword') in preferred]
                if len(idxs) > 1:
                    matched = sorted(
                        (hints[i] for i in idxs),
                        key=lambda h: preferred.index(h.get('keyword')),
                    )
                    for slot, h in zip(idxs, matched):
                        hints[slot] = h

        # wave-2 close, stream P3 2026-09-07 (R22; L2-R22 on
        # docs/dom-captures/slockard-zoo-v3/wave3/vf-form-tab.html#51).
        # `<a name="skiplink">` -- no href, no role, no tabindex, no onclick --
        # is a pure named-anchor skip TARGET, not a link. ClickItem resolved it
        # uniquely and offered it with no caveat at all: the
        # locator is correct and the click is a no-op, which is precisely
        # CLAUDE.md's "a green signal is not a correct result". A hint that
        # cannot act is worse than no hint, so the click rungs are dropped
        # (a non-click rung, e.g. a text read, is kept). Rule is a template key
        # (`nonActionableRules`), never a literal here.
        if hints and self._is_non_actionable(real_tag, attributes):
            hints = [h for h in hints if not str(h.get('keyword') or '').startswith('Click')]

        # stream 2A 2026-09-09: a control you FILL never leads with a blind click. Measured over
        # the 144 committed captures before this block: 114 non-click controls whose FIRST hint was
        # a click keyword -- 91 input_field (80 of them an input whose only label came from
        # aria-label, which the TypeText branch's label_source gate excludes), 22 radio, 1 dropdown.
        # Which families this applies to is TEMPLATE DATA (`keywordRouting.families.<f>.fillFirst`),
        # so a table family keeps its row/col hint first and a custom_component keeps its explicit
        # COULD-NOT-CHECK placeholder first.
        if not in_grid:
            # The family VARIANT, not the raw family (P1's F21): an OmniScript radio group is not a
            # Lightning radio input, and routing it to ClickCheckbox is the exact bug that finding
            # fixed. Caught by test_omnistudio_radio_routes_to_omni_radio_not_click_checkbox while
            # this call passed the raw `element_type`.
            hints = self._fill_hint_first(
                self._family_variant(element_type, identification, context, real_tag, attributes),
                hints, label_text, label_source)

        return {'locator_options': hints} if hints else None

    def _fill_hint_first(self, element_type, hints, label_text, label_source):
        """Put this family's FILL rung at rung 0, or state why there is none."""
        row = self._routing_row(element_type)
        if not row.get('fillFirst'):
            return hints
        fill = row.get('fill')
        if not fill:
            return hints
        idx = next((i for i, h in enumerate(hints) if h.get('keyword') == fill), None)
        if idx == 0:
            return hints
        if idx is not None:
            return [hints[idx]] + [h for i, h in enumerate(hints) if i != idx]
        if not label_text:
            # No label: the honest answer is the third state, made visible -- never a plausible
            # click on an unnamed control (CLAUDE.md's tri-state rule).
            return [{
                'keyword': None,
                'locator': None,
                'verdict': 'COULD-NOT-CHECK',
                'confidence': TIER_UNVERIFIED,
                'why': "%s is filled with %s, but this control has no resolvable label, so no "
                       "keyword can target it. The click rungs below resolve the NODE and would "
                       "not fill it." % (element_type, fill),
                'caveats': ["Find the visible label (sibling text / aria-label) or drive by "
                            "anchor; never click an unlabelled %s and call it filled."
                            % element_type],
            }] + hints
        caveat = ("This label came from %s, not a real <label> association -- confirm it resolves "
                  "before relying on the step." % (label_source or 'an unnamed source'))
        return [{
            'keyword': fill,
            'locator': label_text,
            'call_example': _call_example(fill, label_text),
            'confidence': TIER_UNVERIFIED,
            'why': row.get('why') or ("%s is the fill rung keywordRouting assigns to the %s family."
                                      % (fill, element_type)),
            'caveats': [] if label_source in ('standard_label', 'aria_labelledby', 'form_element_label',
                                              'wrapped_label', 'label_span',
                                              'sibling_label_text') else [caveat],
        }] + hints

    def _family_variant(self, element_type, identification, context, real_tag=None, attributes=None):
        """The FAMILY_KEYWORDS key to use for this control, honouring variants.

        wave-2 review close, stream P1 2026-09-07 (F21, L2-R27). An OmniScript
        radio group is not a Lightning/LEX radio input -- the 'radio' family's
        own caveat already SAID so while routing one to ClickCheckbox anyway.
        The marker that tells them apart is template data
        (dom_config.FAMILY_VARIANTS / template key 'familyVariants'), read
        here; there is deliberately no literal marker string in this file.
        """
        rules = getattr(self.config, 'FAMILY_VARIANTS', None) or []
        identification = identification or {}
        context = context or {}
        for rule in rules:
            if not isinstance(rule, dict) or rule.get('family') != element_type:
                continue
            variant = rule.get('variant')
            if not variant:
                continue
            checks = []
            patterns = rule.get('whenIdentificationMatches') or {}
            if patterns:
                checks.append(any(
                    isinstance(identification.get(field), str)
                    and re.search(pattern, identification.get(field))
                    for field, pattern in patterns.items()))
            keys = rule.get('whenContextKeys') or []
            if keys:
                checks.append(any(context.get(key) for key in keys))
            tags = rule.get('whenTagIs') or []
            if tags:
                # 2026-09-10: the control's REAL html tag (a native <select> is not a lightning-combobox)
                checks.append(bool(real_tag) and str(real_tag).lower() in {t.lower() for t in tags})
            attr_patterns = rule.get('whenAttrsMatch') or {}
            if attr_patterns:
                # 2026-09-11 (seven console-page audits): a console workspace tab is a[role=tab][data-tabid=ctabN]
                # -- the discriminator lives in ATTRIBUTES, which no earlier variant key could see, so every
                # tab routed to `link`/ClickText although familyKeywords already held console-subtab
                a = attributes or {}
                checks.append(all(isinstance(a.get(k), str) and re.search(p, a.get(k)) for k, p in attr_patterns.items()))
            if not checks:
                continue
            if all(checks) if rule.get('match') == 'all' else any(checks):
                return variant
        return element_type

    def _is_non_actionable(self, real_tag, attributes) -> bool:
        """True when the template declares this tag/attribute shape inert --
        a node a click resolves to and does nothing with. See
        DomConfiguration.NON_ACTIONABLE_RULES for the rule shape and the
        finding that produced it (R22, 2026-09-07)."""
        rules = getattr(self.config, 'NON_ACTIONABLE_RULES', None) or []
        tag = (real_tag or '').lower()
        attrs = attributes or {}
        for rule in rules:
            tags = [t.lower() for t in (rule.get('tags') or [])]
            if tags and tag not in tags:
                continue
            # Inert only if EVERY attribute the rule names as conferring
            # actionability is absent -- one of them present makes the node
            # real and the rule does not fire.
            absent = rule.get('absentAttributes') or []
            if absent and any(attrs.get(a) not in (None, '') for a in absent):
                continue
            required = rule.get('requiredAttributes') or []
            if required and any(attrs.get(a) in (None, '') for a in required):
                continue
            return True
        return False

    def _hints_for_family(self, element_type, label_text, real_tag,
                          identification=None, context=None) -> dict:
        """T12 2026-09-07: table-driven hint for a family with no branch in
        the elif chain above (output_field/datatable/radio), plus
        custom_component's explicit-absence hint. The mapping lives in
        self.config.FAMILY_KEYWORDS / self.config.CUSTOM_COMPONENT_TAG_KEYWORDS
        (dom_config.py, template keys 'familyKeywords'/
        'customComponentTagKeywords') -- this method only reads it and falls
        back to the class-attribute default when a template doesn't declare
        the key, the same fallback contract every other _TEMPLATE_KEYS entry
        already uses (dom_config.py's `if key in data`). Never a new literal
        branch per family -- that is the whole point of this being a table.
        """
        if element_type == 'custom_component':
            tag_table = getattr(self.config, 'CUSTOM_COMPONENT_TAG_KEYWORDS', None) or {}
            spec = next(
                (s for tag_frag, s in tag_table.items() if real_tag and tag_frag in real_tag),
                None,
            )
            if spec and label_text:
                return {
                    'keyword': spec['keyword'],
                    'locator': label_text,
                    'call_example': spec['call_template'].format(locator=label_text),
                    # D14: a TEMPLATE cannot declare a hint verified -- only a live read-back can.
                    'confidence': TIER_UNVERIFIED,
                    'why': spec['why'],
                    'caveats': spec.get('caveats', []),
                }
            # No known shape for this tag -- per the tri-state rule
            # (CLAUDE.md), the absence is the finding and must be VISIBLE,
            # never a silently omitted hint (P1 scorecard: 96/96
            # custom_component controls had 'qforce_hints': None).
            return {
                'keyword': None,
                'locator': label_text or None,
                'why': f"custom component <{real_tag or 'unknown'}> has no keyword family yet",
                'verdict': 'COULD-NOT-CHECK',
                'caveats': ["Check SHAPES-GUIDE.md for a newer match, or add this tag to "
                            "CUSTOM_COMPONENT_TAG_KEYWORDS once a real keyword is proven for it "
                            "-- never assume ClickText/ClickItem drive an unrecognized custom "
                            "element correctly."],
            }

        table = getattr(self.config, 'FAMILY_KEYWORDS', None) or {}
        # P1 2026-09-07 (F21): resolve the family's VARIANT (template-driven)
        # before the lookup -- an unmatched control keeps its own family name.
        element_type = self._family_variant(element_type, identification, context, real_tag)
        spec = table.get(element_type)
        if not spec:
            return None
        if not label_text:
            # 2026-09-07 L3-C on T12 (CAUGHT-BUG): 14 labelless radios fell through this `return None`
            # to the generic ClickItem hint -- the no-read-back click the row claimed to have closed.
            # A family keyword needs a label to resolve; without one the honest answer is the third
            # state, made visible, never a plausible click on an unnamed control.
            return {
                'keyword': None,
                'locator': None,
                'why': f"{element_type} has a keyword family ({spec['keyword']}) but this control "
                       "has no resolvable label; the keyword cannot target it",
                'verdict': 'COULD-NOT-CHECK',
                'caveats': ["Find the visible label (sibling text / aria-label) or drive by anchor; "
                            "never ClickItem an unlabelled " + element_type + "."],
            }
        return {
            'keyword': spec['keyword'],
            'locator': label_text,
            'call_example': spec['call_template'].format(locator=label_text),
            # D14: a TEMPLATE cannot declare a hint verified -- only a live read-back can.
            'confidence': TIER_UNVERIFIED,
            'why': spec['why'],
            'caveats': spec.get('caveats', []),
        }

    def _annotate_ambiguous_hints(self, elements) -> None:
        """Second pass over the FULL parsed element list -- states, on every
        hint whose raw `locator` value repeats on the page, HOW MANY elements
        that locator reaches and what disambiguator (if any) the hint carries.

        Built 2026-07-29 after live-confirming this failure mode: duplicate
        file-row titles and duplicate 'joe garza' owner links both looked like
        safe ClickText targets in isolation but were genuinely ambiguous in
        practice. D14 2026-09-09: it used to CONFIRM or DOWNGRADE a confidence
        tier here. There is no tier to move any more -- a hint is `unverified`
        until a live read-back says otherwise -- so this pass only describes."""
        # CORRECTED 2026-07-31: counts by ELEMENT, not by hint. One element
        # can now carry multiple hints sharing the same locator value (e.g.
        # ClickText and ClickItem both resolving via "Edit Opportunity
        # Name" -- see the same-day fix removing ClickItem's `and not
        # hints` gate). Counting raw hint occurrences made such an element
        # collide with ITSELF: live-confirmed, an element whose label was
        # genuinely unique on the page (count=1 via a direct DOM check) got
        # flagged "appears 2 times" purely because it had two hints, not
        # two elements. Deduping locators per-element before counting fixes
        # this without losing real cross-element collision detection.
        # wave-2 F5 (2026-09-07): this counting is now ONE shared helper --
        # `disambiguation.group_size` is stamped from the same numbers, so the
        # block and the caveat below can no longer contradict each other.
        locator_counts = self._page_locator_counts(elements)

        for el in elements:
            hints = el.get('qforce_hints')
            if not hints:
                continue
            for hint in hints.get('locator_options', []):
                # D14 2026-09-09: this gate used to be `confidence in (unique_on_this_page,
                # anchored_unique)` -- i.e. the pass only spoke to hints that CLAIMED to
                # resolve one element. There is no such claim any more, so every hint whose
                # locator repeats gets the count and the disambiguator it was given, stated
                # as fact rather than as a tier.
                locator = hint.get('locator')
                count = locator_counts.get(locator, 0) if locator else 0
                if count <= 1:
                    continue
                disambiguated_by = hint.get('disambiguated_by')
                if disambiguated_by == 'index':
                    hint.setdefault('caveats', []).append(
                        f"'{locator}' appears {count} times on this page with an identical value. "
                        "call_example carries index= (this member's 1-based position among the "
                        "same-label matches in DOM order), which addresses exactly one element but "
                        "is POSITIONAL -- it moves if the page's contents change. "
                        "`disambiguation.anchor_candidates` lists the anchor texts this page "
                        "offers instead; none of them has been resolved live, so none is baked in."
                    )
                    continue
                hint.setdefault('caveats', []).append(
                    f"CAUTION: '{locator}' appears {count} times on this page with an identical "
                    "value and this hint carries no disambiguator -- a bare QWeb call takes "
                    "DOM-order match #1. Add index= or an anchor from "
                    "`disambiguation.anchor_candidates` before relying on it."
                )

    def _annotate_click_text_prefix_collisions(self, elements, soup=None) -> None:
        """Second pass, page-wide: pins `partial_match=False` on any ClickText
        hint whose locator is a case-insensitive TEXT PREFIX of another
        rendered label on the same page. Real QWeb `click_text` defaults to
        substring matching (partial_match=True, confirmed live in
        tools/qforce-lite/qforce_lite.py and crt_parity_lint.py's D8 rule) --
        CLAUDE.md's own headline failure is exactly this: `ClickText("Save")`
        on an edit modal resolved "Save & New" first (3/3 measured), because
        "Save" is a text-prefix of "Save & New", not because the locator was
        ambiguous by count. `_annotate_ambiguous_hints` (above) already
        downgrades a locator that repeats EXACTLY; this catches the prefix
        case that pass cannot see. Finding: docs/dom-captures/slockard-zoo-v3/
        edit-modal-standard.html, <button name="SaveEdit"> label "Save"."""
        if not getattr(self.config, 'CLICK_TEXT_EXACT_WHEN_PREFIX_OF', True):
            return
        # wave-2 close, stream P3 2026-09-07 (F20; L2-R24 on
        # docs/dom-captures/web-ant-design/3-transfer-idle.html#55). This
        # comparison corpus was `label_text` ONLY -- the labels of parsed
        # CONTROLS. ClickText('Select') therefore shipped with no
        # partial_match=False even though the same page visibly renders
        # 'Select a group of items', 'Select item' and 'Selected items': those
        # are page text and non-control labels, invisible to a label-only pass,
        # yet real QWeb substring matching resolves them just the same. The
        # sources are a template key (`clickTextCollisionSources`) rather than
        # a literal here, per the schema-driven parser rule; the default adds
        # `rendered_text` -- what a person actually sees -- to `label_text`.
        # `title_attr` is deliberately NOT in the default: a tooltip is not
        # rendered text and QWeb's text resolution never matches it.
        sources = getattr(self.config, 'CLICK_TEXT_COLLISION_SOURCES', None) \
            or ['label_text', 'rendered_text']
        all_labels = [
            (el.get('identification') or {}).get(src)
            for el in elements
            for src in sources
        ]
        all_labels = [str(lbl).strip() for lbl in all_labels if lbl]
        # F20 continued: the corpus above is still only PARSED elements. On
        # docs/dom-captures/web-ant-design/3-transfer-idle.html the colliding
        # strings ('Select a group of items', 'Select item') live in a plain
        # documentation <td> -- no parsed element carries them in any
        # identification key, yet a person sees them and QWeb's substring
        # matcher resolves them. When the caller hands us the soup, every
        # visible text node on the page joins the comparison corpus.
        if soup is not None:
            all_labels.extend(self._visible_text_segments(soup))
        lowered = [lbl.lower() for lbl in all_labels]

        for el in elements:
            hints = el.get('qforce_hints')
            if not hints:
                continue
            for hint in hints.get('locator_options', []) or []:
                if hint.get('keyword') != 'ClickText':
                    continue
                locator = hint.get('locator')
                if not locator:
                    continue
                loc_lower = locator.strip().lower()
                collisions = sorted({
                    other for other, other_lower in zip(all_labels, lowered)
                    if other_lower != loc_lower and other_lower.startswith(loc_lower)
                })
                if not collisions:
                    continue
                example = hint.get('call_example')
                if example and example.endswith(')') and 'partial_match' not in example:
                    hint['call_example'] = example[:-1] + ', partial_match=False)'
                hint.setdefault('caveats', []).append(
                    "QWeb ClickText defaults to substring matching (partial_match=True) -- "
                    f"'{locator}' is a text-prefix of "
                    + ', '.join(f'\'{c}\'' for c in collisions)
                    + " also rendered on this page; call_example pins partial_match=False so "
                      "the exact control resolves, not the first substring match "
                      "(CLAUDE.md: ClickText(\"Save\") clicking \"Save & New\")."
                )

    def extract_form_errors(self, soup) -> list:
        """Salesforce form-error panels (forceFormPageError / records-record-
        edit-error) as `form_error_panel` elements.

        MOVED HERE from DomParserLibraryNew 2026-09-07 (F8, wave-2 close stream
        P3). It lived on the RF library only, so `capture_orchestration` --
        every local tool's entry point -- never reported a validation error
        panel at all, the mirror image of the T17/T20 passes the RF path was
        missing. Both entry points now run the one implementation.
        """
        results = []
        error_panels = soup.find_all(lambda t: t.name and ('forceFormPageError' in ' '.join(t.get('class') or []) or t.name == 'records-record-edit-error'))

        for dialog in soup.find_all(attrs={'role': 'dialog'}):
            if dialog.find('records-record-edit-error') and dialog not in error_panels:
                error_panels.append(dialog)

        for panel in error_panels:
            if panel.name == 'records-record-edit-error' and panel.find_parent(lambda t: t.name and 'forceFormPageError' in ' '.join(t.get('class') or [])):
                continue

            title_el = panel.find('h2')
            title_text = self.text_engine._get_safe_text(title_el) if title_el else 'Form Error'
            notification_el = panel.find(class_='genericNotification')
            notification_text = self.text_engine._get_safe_text(notification_el) if notification_el else None

            field_errors = []
            errors_list = panel.find('ul', class_='errorsList')
            if errors_list:
                for li in errors_list.find_all('li'):
                    field_label = li.get_text(strip=True)
                    if field_label:
                        anchor = li.find('a')
                        entry = {'field': field_label}
                        if anchor and anchor.get('data-index') is not None:
                            entry['index'] = int(anchor.get('data-index'))
                        field_errors.append(entry)

            if not field_errors:
                for li in panel.find_all('li'):
                    text = li.get_text(strip=True)
                    if text and len(text) < 80:
                        field_errors.append({'field': text})

            if not field_errors and not title_text:
                continue

            behavioral_metadata = {'is_error_panel': True}
            if notification_text:
                behavioral_metadata['error_message'] = notification_text
            if field_errors:
                behavioral_metadata['field_errors'] = field_errors

            element_data = {
                'element_type': 'form_error_panel',
                'element_details': {
                    'tag': panel.name.lower() if panel.name else 'div',
                    'type': None,
                    'attributes': {
                        'role': panel.get('role') or 'dialog',
                        'aria-label': panel.get('aria-label') or title_text,
                        'class': self._get_class_string(panel),
                    },
                },
                'identification': {
                    'label_text': title_text,
                    'label_source': 'inner_text',
                },
                'behavioral_metadata': behavioral_metadata,
                'context': {
                    'is_error_panel': True,
                    'is_in_modal': True,
                },
            }
            results.append(self._prune_empty_values(element_data))
        return results

    def _visible_text_segments(self, soup) -> list:
        """Every text node a person can actually read, for the prefix-collision
        corpus (F20, 2026-09-07). Script/style/template/head text is excluded
        because it is never rendered; `slds-assistive-text` is NOT excluded --
        QWeb's text resolution matches it, which is exactly why a screen-reader
        span can steal a ClickText. Bounds come from the containerAnchors
        template block so this stays one schema rather than a second literal."""
        spec = getattr(self.config, 'CONTAINER_ANCHORS', None) or {}
        max_len = int(spec.get('anchorMaxLen') or 60)
        min_len = int(spec.get('anchorMinLen') or 2)
        skip = {'script', 'style', 'template', 'head', 'title', 'noscript'}
        out = []
        try:
            nodes = soup.find_all(string=True)
        except Exception:
            return out
        for node in nodes:
            parent = getattr(node, 'parent', None)
            if parent is not None and (parent.name or '').lower() in skip:
                continue
            text = str(node).strip()
            if min_len <= len(text) <= max_len:
                out.append(text)
        return out

    def _find_description_text(self, tag) -> str:
        if not tag:
            return ''

        def _matches_description_class(el):
            classes = ' '.join(el.get('class') or [])
            return any(frag in classes for frag in self._description_class_fragments())

        parent = tag.parent
        if parent and hasattr(parent, 'find_all'):
            for sibling in parent.find_all(True, recursive=False):
                if sibling == tag:
                    continue
                if _matches_description_class(sibling):
                    text = self.text_engine._get_safe_text(sibling, max_len=300)
                    if text:
                        return text

        parent_label = tag.find_parent('label')
        if parent_label:
            for desc_el in parent_label.find_all(True):
                if _matches_description_class(desc_el):
                    text = self.text_engine._get_safe_text(desc_el, max_len=300)
                    if text:
                        return text

        describedby = tag.get('aria-describedby')
        if describedby:
            root = tag
            while root.parent:
                root = root.parent
            ref_el = root.find(id=describedby)
            if ref_el:
                text = self.text_engine._get_safe_text(ref_el, max_len=300)
                if text:
                    return text
        return ''

    def _get_behavioral_metadata(self, tag, element_type) -> dict:
        metadata = {}
        tag_name = tag.name.lower() if tag.name else ''

        if tag.get('required') is not None or tag.get('aria-required') == 'true':
            metadata['is_required'] = True
        if tag.get('disabled') is not None or tag.get('aria-disabled') == 'true':
            metadata['is_disabled'] = True
        if tag.get('readonly') is not None or tag.get('aria-readonly') == 'true':
            metadata['is_readonly'] = True

        def _has_error_signal(node):
            if not node or not hasattr(node, 'get'):
                return False
            classes = ' '.join(node.get('class') or [])
            return node.get('aria-invalid') == 'true' or 'slds-has-error' in classes

        error_found = _has_error_signal(tag)
        if not error_found:
            walker = tag.parent
            for _ in range(3):
                if not walker or not hasattr(walker, 'get'):
                    break
                if _has_error_signal(walker):
                    error_found = True
                    break
                walker = walker.parent if hasattr(walker, 'parent') else None
        if error_found:
            metadata['has_error'] = True

        for state in ('expanded', 'selected', 'checked'):
            val = tag.get(f'aria-{state}')
            if val is not None:
                metadata[f'is_{state}'] = val == 'true'

        VALUE_CAPTURE_TYPES = {'input_field', 'textarea', 'dropdown', 'toggle', 'slider', 'checkbox', 'radio', 'dual_listbox'}
        is_password = (tag.get('type') or '').lower() == 'password'
        if element_type in VALUE_CAPTURE_TYPES and not is_password:
            val = tag.get('value')
            if val is not None and val != '':
                metadata['current_value'] = val

        role = (tag.get('role') or '').lower()
        if role == 'combobox' or 'combobox' in tag_name:
            controls_id = tag.get('aria-controls')
            if controls_id:
                soup = tag.find_parent()
                while soup and soup.parent:
                    soup = soup.parent
                listbox = soup.find(id=controls_id) if soup else None
                if listbox:
                    options = [self.text_engine._get_safe_text(o) for o in listbox.find_all(attrs={'role': 'option'})]
                    options = [o for o in options if o]
                    if options:
                        metadata['available_options'] = options

        if tag_name == 'select':
            opts = []
            for o in tag.find_all('option'):
                opts.append({
                    'value': o.get('value', ''),
                    'label': o.get_text(strip=True),
                    'selected': o.get('selected') is not None,
                })
            if opts:
                metadata['available_options'] = opts

        if tag_name in ('lightning-datatable', 'lightning-tree-grid'):
            columns = []
            for th in tag.find_all('th', attrs={'role': 'columnheader'}):
                label = th.get('aria-label') or ''
                col_key = th.get('data-col-key-value') or ''
                if label and label not in ('Row Number', 'Action'):
                    columns.append({'label': label, 'col_key': col_key})

            # Two views over the same rows, not two datasets -- addresses a
            # real, live-confirmed gap (2026-07-29): unconditionally
            # materializing every column of every row doesn't scale, AND
            # unconditionally CAPPING rows silently loses any row past the
            # cap (a "click row N" request has no way to resolve N if N
            # wasn't kept at all). So: `row_index` stays CHEAP and COMPLETE
            # for every row (just the real rowheader/primary column -- the
            # one Salesforce itself marks role="rowheader", normally the
            # record name), while `rows` (full multi-column detail) is
            # capped at MAX_FULL_ROWS with a `note` when truncated. A row
            # beyond the cap is still locatable via `row_index`, then
            # addressable with ClickTableCell/UseTable using its real
            # row/column position -- no data silently disappears either way.
            MAX_FULL_ROWS = 20
            data_rows = []
            row_index = []
            all_trs = tag.find_all('tr', attrs={'data-row-key-value': True})
            for i, tr in enumerate(all_trs):
                row_obj = {}
                primary = None
                for cell in tr.find_all(['th', 'td'], attrs={'role': lambda r: r in ('rowheader', 'gridcell')}):
                    col_key = cell.get('data-col-key-value') or ''
                    matched = next((c for c in columns if c['col_key'] == col_key), None)
                    col_label = matched['label'] if matched else None
                    if not col_label:
                        continue
                    link = cell.find('a', href=re.compile(r'/lightning/r/'))
                    text = self.text_engine._get_safe_text(cell)
                    if not text:
                        continue
                    value = {'text': text, 'href': link.get('href')} if link else text
                    row_obj[col_label] = value
                    if primary is None and cell.get('role') == 'rowheader':
                        primary = {col_label: value}
                # Row-level interactive controls (checkbox/radio row-selectors)
                # live in the "Row Number"/"Action" pseudo-columns skipped
                # above -- they were previously invisible in this JSON
                # entirely (see ROW_CONTROL_SIGNATURES in dom_config.py for
                # why). Underscore-prefixed so it can never collide with a
                # real column label.
                row_controls = self.classifier._detect_row_controls(tr)
                if row_controls:
                    row_obj['_row_controls'] = row_controls
                if row_obj:
                    if primary:
                        row_index.append({'row': i, **primary})
                    if i < MAX_FULL_ROWS:
                        data_rows.append(row_obj)

            metadata['columns'] = [c['label'] for c in columns]
            metadata['row_count'] = len(row_index) or len(data_rows)
            metadata['row_index'] = row_index
            metadata['rows'] = data_rows
            if len(all_trs) > MAX_FULL_ROWS:
                metadata['note'] = (
                    f'Full column detail shown for the first {MAX_FULL_ROWS} of {len(all_trs)} rows -- '
                    'use row_index (primary/rowheader column, every row) to locate a row beyond that, '
                    'then ClickTableCell/UseTable with its real row position for direct interaction.'
                )
            metadata['row_xpath_patterns'] = {
                'by_name_column': "//th[@role='rowheader' and normalize-space()='{value}']",
                'row_link': "//a[contains(@href,'/lightning/r/') and @title='{value}']",
                'row_actions': "//tr[.//th[@role='rowheader' and normalize-space()='{value}']]//button[normalize-space()='Show Actions']",
                'row_checkbox': "//tr[.//th[@role='rowheader' and normalize-space()='{value}']]//input[@type='checkbox']",
            }

        if element_type == 'native_table':
            metadata.update(self.classifier._extract_native_table(tag))

        return metadata if metadata else None

    def _get_validation(self, tag) -> dict:
        rules = {}
        for attr in ('maxlength', 'minlength', 'min', 'max', 'pattern', 'inputmode', 'step'):
            val = tag.get(attr)
            if val is not None:
                key = attr.replace('length', '_length')
                rules[key] = val
        input_type = tag.get('type')
        if input_type and input_type != 'text':
            rules['format'] = input_type
        # F225 (the user, 2026-09-20): "the signal of knowing it is required is useful, but not a
        # great locator way." The marker comes off the LABEL (see _split_required_marker) and the
        # fact lands HERE, as data.
        #
        # Until this, nothing in the pipeline carried a DOM-side required signal at all. The only
        # `required` anywhere came from METADATA -- the org map's create-layout list, attached to a
        # PREDICTION, never to a captured control -- so "the org says this field is required" and
        # "this page is rendering it required" were two facts that never met. A field required on
        # the layout but not rendered required in a given state was invisible to both.
        #
        # Three signals, strongest first, all framework-agnostic: the ARIA contract, the HTML
        # boolean attribute, then (in _fold_rendered_required) the page's own rendered marker.
        aria_required = str(tag.get('aria-required') or '').strip().lower()
        if aria_required in ('true', 'false'):
            rules['required'] = aria_required == 'true'
            rules['required_source'] = 'aria-required'
        elif tag.get('required') is not None:
            rules['required'] = True
            rules['required_source'] = 'required attribute'
        return rules if rules else None

    @staticmethod
    def _fold_rendered_required(validation, identification):
        """The page's RENDERED marker as a last-resort required signal, and always the weakest.

        A control can render `*` and declare nothing: measured, `Owner Name` and `Close Date` on
        slockard__zoo__Zoo_Forms_Advanced carry the marker inside `aria-label` and have no
        `aria-required` and no `required` attribute. The marker is then the only thing the page
        said, so it counts -- but it never OVERRIDES an explicit declaration, including an explicit
        `aria-required="false"`, because a declaration is what the component MEANS and a marker is
        what a theme DREW. `required_source` says which of the three answered, so a reader can tell
        a contract from a decoration."""
        if not (identification or {}).get('label_required'):
            return validation
        folded = dict(validation or {})
        if 'required' not in folded:
            folded['required'] = True
            folded['required_source'] = 'rendered marker'
        return folded or None

    def _get_context_info(self, tag) -> dict:
        if not tag:
            return None
        context = {}

        modal = tag.find_parent(lambda t: t.name and (
            'slds-modal' in ' '.join(t.get('class') or []) or
            t.name in ('force-record-create-modal', 'records-lwc-modal-base')
        ))
        if modal:
            modal_header = modal.find('h2')
            context['modal_title'] = (
                self.text_engine._get_direct_text(modal_header) or
                self.text_engine._get_safe_text(modal_header)
            ) if modal_header else None
            context['is_in_modal'] = True

        form_section = tag.find_parent(lambda t: t.name and t.name in (
            'records-record-layout-section', 'force-form-section',
            'lightning-accordion-section',
        ) or (t.get('class') and 'slds-section' in ' '.join(t.get('class') or [])))
        if form_section:
            section_title = form_section.find(
                lambda t: t.name in ('legend', 'h3') or
                (t.get('class') and 'slds-section__title' in ' '.join(t.get('class') or []))
            )
            if section_title:
                context['form_section'] = (
                    self.text_engine._get_direct_text(section_title) or
                    self.text_engine._get_safe_text(section_title)
                )

        tab_panel = tag.find_parent(attrs={'role': 'tabpanel'})
        if tab_panel:
            tab_id = tab_panel.get('aria-labelledby')
            if tab_id:
                root = tab_panel
                while root.parent:
                    root = root.parent
                tab_el = root.find(id=tab_id)
                context['active_tab'] = self.text_engine._get_safe_text(tab_el) if tab_el else tab_panel.get('data-tab-value')
            else:
                context['active_tab'] = tab_panel.get('data-tab-value')

        related_list = tag.find_parent(lambda t: t.name and t.name in (
            'force-related-list-single-container', 'force-related-list-container', 'lightning-related-list',
        ))
        if related_list:
            title_el = related_list.find(['h2'])
            context['related_list'] = self.text_engine._get_safe_text(title_el) if title_el else None
            context['is_in_related_list'] = True

        datatable_row = tag.find_parent('tr', attrs={'data-row-key-value': True})
        if datatable_row:
            context['datatable_row_key'] = datatable_row.get('data-row-key-value')
            context['is_in_datatable'] = True
        elif self.config._in_grid_container(tag):
            # Wildcard sibling of the lightning-datatable-specific check
            # above -- catches classic Aura/native <table> and role=grid/
            # treegrid containers too, not just the one component that has
            # a real data-row-key-value to key off of. Needed so
            # _get_qforce_hints can recommend row/col addressing for ANY
            # table shape, not only lightning-datatable.
            context['in_grid'] = True

        quick_action = tag.find_parent(lambda t: t.name and t.name in (
            'force-quick-action-panel', 'forceActionBody',
        ) or (t.get('class') and 'forceActionBody' in ' '.join(t.get('class') or [])))
        if quick_action:
            qa_title = quick_action.find('h2')
            context['quick_action_title'] = self.text_engine._get_safe_text(qa_title) if qa_title else None
            context['is_in_quick_action'] = True

        for parent_type, parent_names in [('omni_step', ['c-omniscript-step']), ('flow_screen', ['runtime_platform_flow-screen-field', 'lightning-flow-screen'])]:
            found = tag.find_parent(lambda t: t.name and t.name in parent_names)
            if found:
                context[parent_type] = found.get('data-omni-step-name') or found.get('data-field-name') or found.get('name') or 'flow_screen'
                context[f'is_in_{parent_type.split("_")[0]}'] = True

        form = tag.find_parent('form')
        if form:
            form_name = form.get('name') or form.get('id')
            if form_name:
                context['form'] = form_name

        card = tag.find_parent('lightning-card')
        if card:
            card_title = card.get('title')
            if card_title:
                context['card'] = card_title

        if not context.get('form_section'):
            section = self._find_section_header(tag)
            if section:
                context['section'] = section

        return context if context else None

    def _find_section_header(self, tag) -> str:
        if not tag:
            return None
        parent = tag.parent
        for _ in range(10):
            if not parent:
                break
            if hasattr(parent, 'find'):
                for heading_tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'legend'):
                    heading = parent.find(heading_tag)
                    if heading:
                        text = self.text_engine._get_direct_text(heading)
                        if not text:
                            text = self.text_engine._get_safe_text(heading)
                        if text and len(text) < 100:
                            return text
            parent = parent.parent if hasattr(parent, 'parent') else None
        return None

    def _field_score(self, element_data) -> int:
        tag = element_data.get('element_details', {}).get('tag', '')
        attrs = element_data.get('element_details', {}).get('attributes', {})
        identification = element_data.get('identification', {})
        score = 0

        if tag in {'input', 'textarea', 'select', 'button', 'a'}:
            score += 10
        if re.match(r'^(lightning|c|runtime|force|lst|aura)-', tag):
            score -= 5

        rich_input_types = {'text', 'email', 'tel', 'number', 'date', 'datetime-local', 'time', 'url', 'password', 'search', 'month', 'week', 'color', 'range', 'file', 'checkbox', 'radio'}
        el_type = element_data.get('element_details', {}).get('type') or ''
        if el_type.lower() in rich_input_types:
            score += 5

        if attrs.get('name'):
            score += 3
        if identification.get('aria_label') or attrs.get('title'):
            score += 2
        if attrs.get('role') == 'combobox':
            score += 2
        return score

    COLLAPSIBLE_TYPES = {'input_field', 'dropdown', 'textarea', 'checkbox', 'radio', 'button'}

    def _deduplicate_form_fields(self, elements, dedupe='agent') -> list:
        """Group same-label controls in the same section.

        `dedupe='agent'` (the DEFAULT since interop T10, 2026-09-07) drops NO
        member. Each member of a repeated group is annotated with
        `disambiguation: {index, anchor, group_size}` so a caller told "click
        the caret next to Acme" can address the right one.

        `dedupe='presentation'` is the pre-T10 behaviour: collapse each group to
        its single highest-scoring member. It is a PRESENTATION mode -- fine for
        showing a human the distinct fields on a form, never correct for an
        agent that has to act. Measured on the 112 checked-in captures
        (docs/dom-captures): collapsing dropped 854 of 9612 elements, 57 of the
        112 captures lost at least one control, and 06-setup-permission-sets.html
        went from 41 "Expand" carets to 1 -- so "click the caret next to Acme"
        clicked whichever row happened to survive.
        """
        if dedupe == 'presentation':
            out = self._collapse_form_fields(elements)
        else:
            # interop T20 2026-09-07: anchors FIRST, groups second. The anchor
            # pass is the DEFAULT-ON rule ("every control inside a row / card /
            # fieldset carries the container's anchor", extended by the
            # coordinator to "every ClickItem carries an anchor whenever one
            # exists"); the repeated-group pass then only fills in `index` /
            # `group_size` for members the anchor pass could not resolve
            # uniquely, so index= stays the last resort it always was.
            out = self._annotate_anchors(elements)
            out = self._annotate_repeated_groups(out)
            # stream A3 2026-09-08: the LAST rung. Whatever the two passes above
            # could not resolve to exactly one element gets QWeb's numeric
            # anchor (index mode), so no repeated control is ever left with no
            # anchor at all and none of them self-anchors.
            out = self._settle_index_anchors(out)
        for el in out:
            el.pop('_tag', None)
        return out

    def _group_key(self, el):
        """(label, section) a control is grouped under, or None when the element
        is not a groupable form control."""
        label = (el.get('identification') or {}).get('label_text')
        if not label or el.get('element_type') not in self.COLLAPSIBLE_TYPES:
            return None
        context = el.get('context') or {}
        section = context.get('form_section') or context.get('modal_title') or '__global__'
        return (label, section)

    def _annotate_repeated_groups(self, elements) -> list:
        """Keep every element; stamp `disambiguation` on the members of any
        group with more than one member."""
        groups = {}
        for el in elements:
            key = self._group_key(el)
            if key is not None:
                groups.setdefault(key, []).append(el)

        # wave-2 F5 (2026-09-07): a "group" here is (label, section)-scoped, so
        # its member count is a LOWER BOUND on how often the control really
        # repeats on the page ('open in new tab': 20 members in one section, 40
        # on the page, and the caveat quoted 40 while group_size said 20).
        # group_size is the page-wide number, from the same counter the caveat
        # reads.
        locator_counts = self._page_locator_counts(elements)
        label_counts = self._page_label_counts(elements)

        def _size(el, members):
            return max(len(members),
                       self._page_group_size(el, locator_counts, label_counts))

        for key, members in groups.items():
            if len(members) < 2:
                continue
            anchors = [self._row_anchor(el) for el in members]
            counts = {}
            for a in anchors:
                if a:
                    counts[a] = counts.get(a, 0) + 1
            for position, el in enumerate(members):
                existing = el.get('disambiguation') or {}
                if existing.get('anchor_text_unique'):
                    # The T20 anchor pass already gave this member a
                    # confirmed-unique anchor and already rewrote its hints.
                    # Record the group facts and leave the call examples alone
                    # -- appending a second anchor= would produce a call QWeb
                    # cannot parse.
                    existing.setdefault('index', position + 1)
                    existing['group_size'] = _size(el, members)
                    el['disambiguation'] = existing
                    continue
                anchor = anchors[position]
                # Never fake uniqueness: an anchor that is not unique inside its
                # own group is reported as non-unique, and index= is the only
                # disambiguator offered for that member.
                unique = bool(anchor) and counts.get(anchor) == 1
                dis = {
                    # R17 (wave-2, 2026-09-07): `index` is 1-BASED and stays
                    # 1-based in every emitter, because QWeb has no `index=`
                    # parameter -- a NUMERIC `anchor` is its index mode and
                    # QWeb counts from 1 (QWeb/keywords/text.py:357, 929;
                    # `anchor: str = "1"`). The 5th of 6 "Clone Line" buttons
                    # is therefore index 5, and `_add_disambiguated_hints`
                    # emits anchor="5" for it -- the two never diverge.
                    'index': position + 1,
                    'group_size': _size(el, members),
                }
                if anchor:
                    dis['anchor'] = anchor
                    dis['anchor_text_unique'] = unique
                else:
                    dis['anchor_text_unique'] = False
                    dis['anchor_note'] = 'no distinguishing visible text found in this row/container'
                # 2026-09-10 (Zoo_Nightmare_Inputs): the T20 pass already walked this member's REAL
                # ancestor ladder; its candidates are kept, and a card/fieldset/row anchor it found
                # outranks this pass's row anchor. Measured before this branch: the three Pricing
                # 'Amount' fields lost their own box headings (List Price / Negotiated Discount /
                # Net to Customer) and were all stamped 'Kickoff Workshop', the page's first card.
                if existing.get('anchor_candidates'):
                    dis['anchor_candidates'] = existing['anchor_candidates']
                    if existing.get('anchor') and existing.get('anchor_scope') in ('card', 'fieldset', 'row'):
                        dis['anchor'] = existing['anchor']
                        dis['anchor_scope'] = existing['anchor_scope']
                        dis['anchor_text_unique'] = bool(existing.get('anchor_text_unique'))
                el['disambiguation'] = dis
                self._add_disambiguated_hints(el, dis)
        return elements

    # ------------------------------------------------- T20 anchor policy ----
    # stream 1C, 2026-09-08 (D4 NARROWED -- docs/DECISIONS.md, evidence:
    # docs/recorder/evidence/anchor-live-proof-2026-09-08.md +
    # docs/proposals/challenge-2026-09-08/C5-rf-qweb-vs-xpath.md Challenge 3):
    # T20's rule ("an anchor is computed for EVERY control that can have one --
    # not only for the members of a detected duplicate group") measured out to
    # 2,727 of 3,115 emitted anchors being the control's OWN label (a
    # self-anchor: QWeb's proximity scorer returns the first match, i.e. no
    # disambiguation, plus a wasted DOM pass) and 8,323 anchors over the
    # 144-capture corpus sitting on a control whose label is unique on the page
    # (group_size == 1) -- CLAUDE.md's own doctrine: "A control that occurs
    # once needs none." An anchor is CHEAP INSURANCE only when the control
    # actually repeats; on the 76.6% of controls with a page-unique label it is
    # PURE COST (a second DOM pass, no disambiguating value). own_label is
    # therefore RETIRED as a rung: a repeated control never anchors on itself,
    # and (this stream) a control that does not repeat gets no anchor
    # candidates at all -- see `_anchor_candidates`'s `repeated` gate.
    #
    # The ladder for a REPEATED control (group_size > 1), cheapest first:
    #
    #   row_cell        the unique cell in this control's table row (preferred:
    #                   the Name / first data-label cell whose text is unique
    #                   across the table's rows), verified unique among the
    #                   sibling rows of the same table
    #   legend_heading  the nearest enclosing fieldset legend / card or section
    #                   heading
    #   preceding_text  the nearest preceding visible text
    #
    # Uniqueness is never assumed: a container anchor must be unique among its
    # sibling containers, and a non-container anchor must make the pair
    # (locator value, anchor) unique across the page's own elements. An anchor
    # that fails its check is not emitted here; `_settle_index_anchors` is the
    # documented last resort for a control that still repeats after this
    # ladder (QWeb's numeric anchor/index mode), and stamps an explicit
    # COULD-NOT-DISAMBIGUATE note rather than ever leaving a silent gap.
    ANCHOR_ORDER = ('row_cell', 'legend_heading', 'preceding_text')
    ANCHOR_SCOPE_OF = {
        'row_cell': 'row',
        'legend_heading': 'fieldset',
        'preceding_text': 'preceding',
    }

    def _anchor_policy(self):
        cfg = getattr(self.config, 'CONTAINER_ANCHORS', None) or {}
        return cfg if isinstance(cfg, dict) else {}

    def _anchor_text_ok(self, text):
        policy = self._anchor_policy()
        lo = policy.get('anchorMinLen', 2)
        hi = policy.get('anchorMaxLen', 60)
        if not text:
            return None
        text = ' '.join(str(text).split())
        if not (lo <= len(text) <= hi):
            return None
        return text

    def _anchor_scope_spec(self, scope):
        for spec in self._anchor_policy().get('scopes', []) or []:
            if spec.get('scope') == scope:
                return spec
        return {}

    def _enclosing_row(self, tag):
        """The nearest table-row-shaped ancestor, recognised by the template's
        `row` scope spec (tags / roles), never by a hard-coded tag list."""
        spec = self._anchor_scope_spec('row')
        tags = set(spec.get('tags') or ['tr'])
        roles = set(spec.get('roles') or ['row'])
        depth_cap = self._anchor_policy().get('maxAncestorDepth', 12)
        node, depth = tag, 0
        while node is not None and depth < depth_cap:
            name = (getattr(node, 'name', '') or '').lower()
            role = (node.get('role') or '').lower() if hasattr(node, 'get') else ''
            if name in tags or role in roles:
                return node
            node = getattr(node, 'parent', None)
            depth += 1
        return None

    def _row_cell_anchor(self, row, own_label):
        """The unique cell in `row`: the preferred data-label cell first (a
        Lightning datatable stamps `data-label="Account Name"` on every body
        cell), then a link, then a row header, then any cell."""
        if row is None:
            return None
        spec = self._anchor_scope_spec('row')
        preferred = spec.get('dataLabelPreference') or []
        try:
            cells = row.find_all(['th', 'td'], limit=60)
        except Exception:
            return None

        def cell_text(cell):
            return self._anchor_text_ok(self.text_engine._get_safe_text(cell, max_len=80))

        by_label = {}
        for cell in cells:
            label = cell.get('data-label')
            if label and label not in by_label:
                text = cell_text(cell)
                if text and text != own_label:
                    by_label[label] = text
        for wanted in preferred:
            if wanted in by_label:
                return by_label[wanted]
        for order in (spec.get('anchorPreference') or []):
            if order == 'data_label_cell' and by_label:
                return next(iter(by_label.values()))
            if order == 'link_text':
                try:
                    for link in row.find_all('a', limit=20):
                        text = cell_text(link)
                        if text and text != own_label:
                            return text
                except Exception:
                    pass
            if order == 'header_cell':
                for cell in cells:
                    if (getattr(cell, 'name', '') or '').lower() == 'th':
                        text = cell_text(cell)
                        if text and text != own_label:
                            return text
            if order == 'cell_text':
                for cell in cells:
                    text = cell_text(cell)
                    if text and text != own_label:
                        return text
        return None

    def _legend_or_heading_anchor(self, tag, own_label):
        """Nearest enclosing fieldset <legend> or card/section heading.

        Returns `(text, scope)` -- wave-2 F16 (2026-09-07): this rung matches
        EITHER a real <fieldset> or a card/section, and the caller used to
        stamp the rung's own name ("fieldset") for both. Measured on the
        corpus: 603 of 659 `anchor_scope: "fieldset"` records were on pages
        with zero <fieldset>. The scope must name the ancestor kind actually
        matched, so this returns it rather than letting the caller guess.
        """
        depth_cap = self._anchor_policy().get('maxAncestorDepth', 12)
        card = self._anchor_scope_spec('card')
        card_tags = set(card.get('tags') or [])
        card_frags = card.get('classFragments') or []
        node, depth = getattr(tag, 'parent', None), 0
        while node is not None and depth < depth_cap:
            name = (getattr(node, 'name', '') or '').lower()
            classes = ' '.join(node.get('class') or []) if hasattr(node, 'get') else ''
            if name == 'fieldset':
                legend = node.find('legend')
                text = self._anchor_text_ok(
                    self.text_engine._get_safe_text(legend, max_len=80)) if legend else None
                if text and text != own_label:
                    return text, 'fieldset'
            if name in card_tags or any(f in classes for f in card_frags):
                heading = node.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading is None:
                    # 2026-09-10 (Zoo_Nightmare_Inputs): a card's heading is often a span/p carrying
                    # an SLDS heading class, not an h-tag -- template `headingClassFragments`
                    hfrags = card.get('headingClassFragments') or []
                    if hfrags:
                        heading = node.find(lambda n: n.name not in (None, 'script', 'style')
                                            and any(f in ' '.join(n.get('class') or []) for f in hfrags))
                text = self._anchor_text_ok(
                    self.text_engine._get_safe_text(heading, max_len=80)) if heading else None
                if text and text != own_label:
                    return text, 'card'
            node = getattr(node, 'parent', None)
            depth += 1
        return None

    def _preceding_text_anchor(self, tag, own_label):
        """Nearest preceding visible text -- the last resort, and the weakest:
        it is only offered when it makes the (locator, anchor) pair unique."""
        node = tag
        hops = 0
        while node is not None and hops < 40:
            prev = getattr(node, 'previous_element', None)
            node = prev
            hops += 1
            if prev is None:
                break
            if getattr(prev, 'name', None) in (None,):
                text = self._anchor_text_ok(str(prev))
                if text and text != own_label:
                    return text
        return None

    def _anchor_candidates(self, el):
        """(kind, text, scope) triples for `el` in ANCHOR_ORDER, cheapest
        first, with the rungs a template's `anchorPreference` did not ask for
        skipped.

        wave-2 F16 (2026-09-07): `scope` is carried per CANDIDATE, because the
        `legend_heading` rung resolves against either a real <fieldset> or a
        card/section and only the rung itself knows which ancestor it matched.
        """
        tag = el.get('_tag')
        if tag is None:
            return []
        # stream 1C 2026-09-08 (rule a, D4 narrowed): a control whose label is
        # unique on the page (group_size == 1) gets NO anchor argument at all
        # -- not row_cell, not legend_heading, not preceding_text. Measured
        # over the 144-capture corpus: 8,323 anchors sat on a control that did
        # not repeat, all pure cost (a second DOM pass, zero disambiguating
        # value -- QWeb already resolves it uniquely with no help). Template
        # key `containerAnchors.onlyWhenRepeated` (default true) is the gate;
        # a template that sets it false restores the pre-1C "anchor every
        # control" behaviour byte for byte.
        repeated = bool(getattr(self, '_a3_group_size', {}).get(id(el), 1) > 1)
        if not repeated and self._anchor_policy().get('onlyWhenRepeated', True):
            return []
        own_label = ((el.get('identification') or {}).get('label_text') or '').strip() or None
        out = []
        for kind in self.ANCHOR_ORDER:
            text = None
            scope = self.ANCHOR_SCOPE_OF.get(kind, kind)
            try:
                if kind == 'row_cell':
                    text = self._row_cell_anchor(self._enclosing_row(tag), own_label)
                elif kind == 'legend_heading':
                    found = self._legend_or_heading_anchor(tag, own_label)
                    if found:
                        text, scope = found
                elif kind == 'preceding_text':
                    text = self._preceding_text_anchor(tag, own_label)
            except Exception:
                text = None
            if text:
                out.append((kind, text, scope))
        return out

    def _resolution_keys(self, el):
        """Every string a keyword would put in its FIRST argument for this
        element -- what an anchor has to disambiguate.

        wave-2 F15 (2026-09-07): uniqueness used to be checked on
        `(primary locator, anchor)` alone. On health90's setup-home that made
        'Objects and Fields' a "unique" anchor for 19 of 32 Expand buttons: the
        buttons' *attribute* locators differed, so every pair was unique, while
        the call a caller actually makes -- ClickText("Expand",
        anchor="Objects and Fields") -- resolves 19 elements. The check is now
        on the RESOLUTION: an anchor is unique only when EVERY first-argument
        string this element offers, its label included, pairs with that anchor
        exactly once on the page.
        """
        keys = set()
        for hint in (el.get('qforce_hints') or {}).get('locator_options') or []:
            loc = hint.get('locator')
            if loc:
                keys.add(loc)
        label = (el.get('identification') or {}).get('label_text')
        if label:
            keys.add(label)
        return keys

    def _primary_locator(self, el):
        """The string a hint would put in QWeb's first argument -- what the
        (locator, anchor) uniqueness check is about."""
        hints = (el.get('qforce_hints') or {}).get('locator_options') or []
        for hint in hints:
            loc = hint.get('locator')
            if loc:
                return loc
        return ((el.get('identification') or {}).get('label_text') or None)

    def _annotate_anchors(self, elements):
        """Stamp `disambiguation: {anchor, anchor_scope, anchor_text_unique,
        group_size}` on every element an anchor can be computed for, and bake
        the confirmed-unique ones into the call examples."""
        policy = self._anchor_policy()
        if not policy.get('enabled', True):
            return elements

        # Sibling-container uniqueness for the `row` scope: an anchor cell text
        # must identify exactly ONE row of its own table.
        row_anchor_counts = {}
        per_el = {}
        # stream A3: group_size has to be known BEFORE the ladder runs, because
        # it decides whether the `own_label` rung is admissible at all.
        _lc = self._page_locator_counts(elements)
        _bc = self._page_label_counts(elements)
        self._a3_group_size = {
            id(el): self._page_group_size(el, _lc, _bc)
            for el in elements if isinstance(el, dict)
        }
        # ... and the element's 1-based position inside that group, captured
        # HERE rather than in `_settle_index_anchors`, because
        # `_settle_bare_click_items` drops the repeated-locator hints in
        # between: by settle time the very key that made group_size 4 is gone
        # from `_resolution_keys`, and every member came back index 1
        # (measured on 03-account-related-list-contacts.html).  A numeric
        # anchor that is 1 for every member is not an address.
        _order, self._a3_group_index = {}, {}
        for el in elements:
            if not isinstance(el, dict):
                continue
            best_key, best_n = None, 1
            for key in sorted(self._resolution_keys(el)):
                n = max(_lc.get(key, 1), _bc.get(key, 1))
                if n > best_n:
                    best_key, best_n = key, n
            if best_key is None:
                continue
            _order[best_key] = _order.get(best_key, 0) + 1
            self._a3_group_index[id(el)] = _order[best_key]
        for el in elements:
            if not isinstance(el, dict) or el.get('_tag') is None:
                continue
            cands = self._anchor_candidates(el)
            per_el[id(el)] = cands
            for kind, text, _scope in cands:
                if kind == 'row_cell':
                    row = self._enclosing_row(el['_tag'])
                    table = getattr(row, 'parent', None)
                    key = (id(table), text)
                    seen = row_anchor_counts.setdefault(key, set())
                    seen.add(id(row))

        # Page-wide (resolution key, anchor) counts for the non-container
        # rungs -- wave-2 F15: the check is on what the CALL resolves, so
        # every first-argument string the element offers (its label included)
        # is counted, not only the primary locator.
        pair_counts = {}
        locator_counts = self._page_locator_counts(elements)
        label_counts = self._page_label_counts(elements)
        # 2026-09-10: a grid's emitted CELLS (gridDescendantEmission's synthesised, hintless rows)
        # are not click targets, so they never count against a control's (locator, anchor) pair --
        # emitting lightning-datatable cells had made every row's own name a non-unique anchor
        cell_families = {r.get('family') for r in ((getattr(self.config, 'GRID_DESCENDANT_EMISSION', None) or {}).get('rules') or [])
                         if r.get('family') and not r.get('compile')}
        # 2026-09-11: a resolution key that is a TEMPLATE ('row/col coordinates (r{N}/c{M})', the
        # Click Table Cell hint's placeholder) is not a locator string; every cell control on a page
        # shares it, so pairing it with an anchor text made every row's own name non-unique the
        # moment the row's link was emitted beside its checkbox (Account list view, datatable emission)
        def _real_keys(el):
            return [k for k in self._resolution_keys(el) if '{' not in str(k)]
        for el in elements:
            if el.get('element_type') in cell_families:
                continue
            cands = per_el.get(id(el)) or []
            keys = _real_keys(el)
            for kind, text, _scope in cands:
                for key in keys:
                    pair_counts[(key, text)] = pair_counts.get((key, text), 0) + 1

        for el in elements:
            cands = per_el.get(id(el)) or []
            if not cands:
                continue
            keys = _real_keys(el)
            chosen = None
            candidates = []
            for kind, text, scope in cands:
                # The pair check is the RESOLUTION check and applies to every
                # rung, the container rungs included (wave-2 F15): a row anchor
                # unique among its own table's rows still resolves twice when
                # the SAME form is present on the host page and inside a
                # spliced same-app iframe (slockard-zoo-v3/wave3/
                # record-page-vf-iframe.html), and real QWeb auto-penetrates
                # iframes, so both copies are live targets for one call.
                unique = bool(keys) and all(
                    pair_counts.get((key, text), 0) == 1 for key in keys)
                if unique and kind == 'row_cell':
                    row = self._enclosing_row(el['_tag'])
                    table = getattr(row, 'parent', None)
                    unique = len(row_anchor_counts.get((id(table), text), ())) == 1
                # D14 2026-09-09: EVERY rung is recorded as a CANDIDATE, with
                # the uniqueness it was measured to have IN THE CAPTURE. The
                # loop no longer stops at the first unique one and no longer
                # elects a winner -- electing one is what produced two
                # "confirmed-unique" anchors resolving to a single live field
                # (docs/errors/entries/7627c1f2a9.json).
                candidates.append({'kind': kind, 'text': text, 'scope': scope,
                                   'text_unique': bool(unique)})
                if unique and chosen is None:
                    chosen = (kind, text, scope, True)
                if chosen is None:
                    chosen = (kind, text, scope, False)
            if chosen is None:
                continue
            kind, text, scope, unique = chosen
            dis = dict(el.get('disambiguation') or {})
            # `anchor`/`anchor_scope` are the TOP candidate the ladder saw, kept
            # so a reader has one to quote; `anchor_candidates` is the whole
            # list, and neither is baked into a call.
            dis['anchor'] = text
            dis['anchor_scope'] = scope
            # anchor_text_unique (was anchor_is_unique): what it ACTUALLY
            # measures -- the (resolution key, anchor text) pair occurs once in
            # THIS CAPTURE. It has never meant "QWeb will resolve this member".
            dis['anchor_text_unique'] = bool(unique)
            dis['anchor_candidates'] = candidates
            # wave-2 F5: group_size is the REAL count of this control on the
            # page -- the same number `_annotate_ambiguous_hints` puts in its
            # "appears N times" caveat -- never a defaulted 1.
            dis['group_size'] = max(
                dis.get('group_size') or 1,
                self._page_group_size(el, locator_counts, label_counts),
            )
            el['disambiguation'] = dis
            self._add_disambiguated_hints(el, dis)
        self._settle_bare_click_items(elements, locator_counts)
        return elements

    # ------------------------------------------- A3 index-anchor last rung ----
    def _settle_index_anchors(self, elements):
        """Close A_MISSING_ANCHOR and B_SELF_UNIQUE on every repeated control.

        Stream A3, 2026-09-08, against `tools/guards/anchor_policy.py` (stream
        A2), which measured 226 violations in the post-P2 output over the frozen
        112-capture corpus: 143 B_SELF_UNIQUE, 79 A_MISSING_ANCHOR. Stream 1C,
        2026-09-08 (rule c): own_label is retired (see `_anchor_candidates`),
        so a repeated control now walks only row_cell / legend_heading /
        preceding_text before landing here.

        The ladder above (row cell > legend/heading of a real ancestor > nearest
        preceding text) is text-anchoring, and text anchoring can genuinely
        fail: a page can carry four byte-identical rows with nothing
        distinguishing text anywhere in them. QWeb still has an address for
        that element -- its `anchor` parameter is documented as "Text near the
        element to be clicked **or index**" (QWeb/keywords/text.py:357, 929,
        `anchor: str = "1"`), so a NUMERIC anchor is index mode and counts
        from 1.

        So: any control with `group_size` > 1 whose block does not carry a
        resolved, non-self anchor gets `anchor` = its 1-based position inside the
        repeated group, `anchor_scope: "index"`, `disambiguation_status`
        stamped `COULD-NOT-DISAMBIGUATE: <n> matches` (rule c -- the text
        ladder that resolves a human-readable anchor came up empty; this is
        never a silent first-match), and a `why` that says the text ladder was
        walked and did not resolve. It is positional and it is the weakest rung
        -- `why` says that too -- but it resolves to exactly one element,
        which "no anchor at all" never does.
        """
        policy = self._anchor_policy()
        if not policy.get('enabled', True):
            return elements
        locator_counts = self._page_locator_counts(elements)
        label_counts = self._page_label_counts(elements)
        # DOM-ordered membership per resolution key -- the sequence QWeb's
        # numeric anchor counts through.
        order = {}
        for el in elements:
            if not isinstance(el, dict):
                continue
            for key in self._resolution_keys(el):
                order.setdefault(key, []).append(id(el))

        for el in elements:
            if not isinstance(el, dict):
                continue
            dis = dict(el.get('disambiguation') or {})
            if not dis:
                continue
            gs = dis.get('group_size') or 1
            if gs <= 1:
                continue
            anchor = dis.get('anchor')
            scope = dis.get('anchor_scope')
            # D14 2026-09-09: this used to `continue` here whenever the text
            # ladder had found an anchor whose (locator, anchor) pair was unique
            # IN THE CAPTURE -- so those members never got an index at all. The
            # third 'Deal Name' on slockard Zoo_Forms_Advanced left this pass
            # with no `index` key whatsoever, and the two that did carry one
            # carried a baked text anchor that resolved to the SAME live field
            # (docs/errors/entries/7627c1f2a9.json). Every member of a repeated
            # group now gets its position; the text rungs stay beside it as
            # CANDIDATES, and the caller chooses.

            keys = self._resolution_keys(el)
            best_key, best_n = None, 0
            for key in sorted(keys):
                n = max(locator_counts.get(key, 1), label_counts.get(key, 1))
                if n > best_n:
                    best_key, best_n = key, n
            # Only a key that REALLY repeats defines a sequence to count
            # through.  Measured while writing this pass: on
            # 03-account-related-list-contacts.html two different checkboxes
            # ('Select Item 2', 'Select Item 3') both came back index 1,
            # because each element's own key occurs once and its group_size 4
            # comes from the (label, section) group instead.  A numeric anchor
            # that is 1 for every member is not an address -- so when no
            # resolution key repeats, the position stamped by
            # `_annotate_repeated_groups` (the member's place in its own
            # group) is the number, and only a genuinely repeated key
            # overrides it.
            idx = None
            if best_key is not None and best_n > 1:
                try:
                    idx = order[best_key].index(id(el)) + 1
                except (KeyError, ValueError):
                    idx = None
            if idx is None:
                idx = (getattr(self, '_a3_group_index', {}).get(id(el))
                       or dis.get('index') or 1)

            tried = 'self-only' if scope == 'self' else (scope or 'none')
            dis['index'] = idx
            # D14: `anchor`/`anchor_scope` keep the TEXT candidate the ladder
            # actually found (or stay absent when it found none). They are
            # descriptions of the page, not the disambiguator being offered --
            # that is `index`, and `anchor_kind` says so.
            dis['anchor_kind'] = 'index'
            dis.pop('anchor_note', None)
            # stream 1C 2026-09-08 (rule c): "no rung yields a unique pair" is
            # never left silent. The disclosed, machine-greppable marker sits
            # alongside (not instead of) QWeb's numeric index anchor: an index
            # anchor genuinely resolves to exactly one element (never a silent
            # first-match), so it stays the resolution mechanism; the COULD-
            # NOT-DISAMBIGUATE marker records that the TEXT ladder -- the one
            # a person would read out loud -- came up empty and this is the
            # positional fallback, not a real anchor a caller can quote.
            if not dis.get('anchor_candidates'):
                dis['disambiguation_status'] = 'COULD-NOT-DISAMBIGUATE: %d matches' % gs
            dis['why'] = (
                'this control appears %d times on this page. The text-anchor ladder (row '
                'cell, then a real fieldset legend or card heading, then the nearest '
                'preceding text) reached %r and its candidates are listed in '
                'anchor_candidates -- NONE of them is baked into a call, because a '
                'capture cannot know which element QWeb\'s proximity scorer picks on the '
                'live page (measured: docs/errors/entries/7627c1f2a9.json, two '
                '"confirmed-unique" anchors resolving to one field). index=%d is this '
                'member\'s 1-based position in DOM order: it addresses exactly one '
                'element, it is positional, and it must be re-verified if the page\'s '
                'contents change.'
                % (gs, tried, idx))
            el['disambiguation'] = dis
            self._rebake_index_anchor(el, dis)
        return elements

    def _rebake_index_anchor(self, el, dis):
        """Rewrite this element's call examples onto `index=<n>`.

        Any `anchor="..."` an earlier pass wrote is STRIPPED, not appended to:
        D14 (2026-09-09) -- a text anchor chosen from a capture is a prediction
        about QWeb's live proximity scorer, and that prediction was measured
        wrong (docs/errors/entries/7627c1f2a9.json). The anchor texts survive as
        `anchor_candidates` on the hint and on `disambiguation`; the call shows
        the position, which is the one disambiguator a capture can actually
        establish.
        """
        import re as _re
        hints = (el.get('qforce_hints') or {}).get('locator_options') or []
        anchored = (self._anchor_policy().get('anchoredKeywords')
                    or ['ClickItem', 'ClickText', 'ClickCheckbox',
                        'Click Table Cell'])
        cands = dis.get('anchor_candidates') or []
        for hint in hints:
            if hint.get('keyword') not in anchored:
                continue
            if cands:
                hint['anchor_candidates'] = [dict(c) for c in cands]
            example = hint.get('call_example')
            if not example:
                continue
            call, sep, note = example.partition('  # ')
            call = call.rstrip()
            if not call.endswith(')'):
                continue
            call = _re.sub(r',\s*anchor="(?:[^"\\]|\\.)*"\s*\)$', ')', call)
            call = _re.sub(r',\s*index=\d+\s*\)$', ')', call)
            hint['call_example'] = (call[:-1] + ', index=%d)' % dis['index']
                                    + (sep + note if sep else ''))
            hint['disambiguated_by'] = 'index'
            why = hint.get('why') or ''
            if 'NO ANCHOR:' in why:
                why += (' -- CORRECTED (D14, 2026-09-09): a disambiguator IS now offered, '
                        'index=%d (this member\'s position among the same-label matches); '
                        'see disambiguation.why and disambiguation.anchor_candidates.'
                        % dis['index'])
                hint['why'] = why

    # ------------------------------------ A3 substring collisions (all kw) ----
    # The rule (user, 2026-09-08, relayed by the coordinator mid-task):
    # `partial_match=False` was pinned ONLY on ClickText
    # (`_annotate_click_text_prefix_collisions`).  QWeb's default is SUBSTRING
    # matching for EVERY text-resolving keyword -- the `partial_match` kwarg is
    # documented in the installed source on input_.py (TypeText), checkbox.py
    # (ClickCheckbox), dropdown.py (DropDown / PickList), element.py
    # (ClickItem / ClickElement) and text.py, all reaching the resolver through
    # **kwargs.  So on the Zoo pages `type_text("Name", ...)` also matches
    # "Name (secondary)", the EXACT repeat counter says group_size 1, and no
    # anchor is emitted at all: a bare call that silently types into the wrong
    # field, with every count in the record saying it is unique.
    #
    # Two consequences, both handled here:
    #   1. a locator that is a proper substring of another rendered string on
    #      the same page counts as REPEATED, so `group_size` > 1, so the anchor
    #      ladder runs and an anchor is emitted (A3's index rung guarantees one
    #      exists);
    #   2. every keyword in the template's `partialMatchKeywords` also carries
    #      `partial_match=False`.

    def _substring_policy(self):
        cfg = getattr(self.config, 'SUBSTRING_COLLISIONS', None) or {}
        return cfg if isinstance(cfg, dict) else {}

    def seed_substring_collisions(self, elements, soup=None):
        """Build the set of locator strings this page resolves ambiguously by
        SUBSTRING, and stash it for `_page_group_size`.

        Must run BEFORE `_deduplicate_form_fields`, because the anchor ladder
        inside it reads `group_size` to decide whether a control repeats.
        """
        policy = self._substring_policy()
        self._a3_substring_collisions = {}
        if not policy.get('enabled', True):
            return self._a3_substring_collisions
        min_len = int(policy.get('minLen') or 2)
        sources = policy.get('sources') or ['label_text', 'rendered_text']

        corpus = []
        for el in elements:
            if not isinstance(el, dict):
                continue
            ident = el.get('identification') or {}
            for src in sources:
                val = ident.get(src)
                if val:
                    corpus.append(' '.join(str(val).split()))
        if soup is not None:
            try:
                corpus.extend(self._visible_text_segments(soup))
            except Exception:
                pass
        corpus = [c for c in corpus if c]
        lowered = [c.lower() for c in corpus]

        # Every string a keyword would put in its first argument, page-wide.
        candidates = set()
        for el in elements:
            if not isinstance(el, dict):
                continue
            for key in self._resolution_keys(el):
                if key and len(str(key).strip()) >= min_len:
                    candidates.add(' '.join(str(key).split()))

        for cand in candidates:
            cl = cand.lower()
            hits = sorted({
                other for other, ol in zip(corpus, lowered)
                if ol != cl and cl in ol
            })
            if hits:
                self._a3_substring_collisions[cand] = hits[:6]
        return self._a3_substring_collisions

    def _substring_collisions_for(self, el):
        """The colliding strings for this element's own resolution keys."""
        table = getattr(self, '_a3_substring_collisions', None) or {}
        if not table:
            return None
        # `_resolution_keys` returns a SET.  Iterating it unsorted made WHICH
        # colliding key landed in the caveat vary between runs of the same
        # parse -- three captures flipped their golden digest on a re-run
        # (Zoo_Forms_Advanced, Zoo_Record_Forms__default,
        # Zoo_Record_Forms__edit_form_changed) with no input change at all.
        # A parser whose output depends on set iteration order is not a cache
        # anything can be diffed against.
        for key in sorted(k for k in self._resolution_keys(el) if k):
            norm = ' '.join(str(key).split())
            if norm and norm in table:
                return norm, table[norm]
        return None

    def annotate_substring_collisions(self, elements):
        """Pin `partial_match=False` on every keyword whose QWeb signature
        accepts it, for a locator this page resolves ambiguously by substring.

        Runs AFTER dedup (the hints exist only then).  The anchor half of the
        rule is already done: `_page_group_size` counted these as repeated, so
        `_annotate_anchors` walked the ladder and `_settle_index_anchors`
        guaranteed an anchor.
        """
        policy = self._substring_policy()
        if not policy.get('enabled', True):
            return elements
        accepting = policy.get('partialMatchKeywords') or []
        for el in elements:
            if not isinstance(el, dict):
                continue
            found = self._substring_collisions_for(el)
            if not found:
                continue
            locator, others = found
            for hint in (el.get('qforce_hints') or {}).get('locator_options') or []:
                if hint.get('keyword') not in accepting:
                    continue
                example = hint.get('call_example')
                if not example or not example.endswith(')'):
                    continue
                if 'partial_match' in example:
                    continue
                hint['call_example'] = example[:-1] + ', partial_match=False)'
                hint.setdefault('caveats', []).append(
                    "QWeb resolves text by SUBSTRING by default for this keyword too, not "
                    "only for ClickText -- '%s' is contained in %s also rendered on this "
                    "page, so the bare call can resolve the wrong control while the exact "
                    "repeat counter sees only one. call_example pins partial_match=False, "
                    "and disambiguation.group_size counts this control as repeated so an "
                    "anchor is emitted."
                    % (locator, ', '.join("'%s'" % o for o in others))
                )
        return elements

    def _page_locator_counts(self, elements):
        """How many ELEMENTS on this page offer each hint locator.

        The single source of truth for "appears N times": shared verbatim with
        `_annotate_ambiguous_hints`, whose caveat quotes this number, and with
        `disambiguation.group_size` (wave-2 F5, 2026-09-07 -- group_size said 1
        on 362 corpus records whose own caveat said the locator repeats).
        Locators are deduped PER ELEMENT first, so an element carrying two
        hints with the same locator never collides with itself.
        """
        counts: dict = {}
        for el in elements:
            hints = (el.get('qforce_hints') or {}).get('locator_options') if isinstance(el, dict) else None
            if not hints:
                continue
            own = {
                hint.get('locator') for hint in hints
                if hint.get('locator') and 'coordinates' not in str(hint.get('locator'))
            }
            for locator in own:
                counts[locator] = counts.get(locator, 0) + 1
        return counts

    def _page_label_counts(self, elements):
        """How many elements on this page carry each `label_text` -- the count
        a caller means by "this label appears N times". Counted separately from
        the hint locators because an element can render a repeated label and
        offer no hint at all."""
        counts: dict = {}
        for el in elements:
            if not isinstance(el, dict):
                continue
            label = (el.get('identification') or {}).get('label_text')
            if label:
                counts[label] = counts.get(label, 0) + 1
        return counts

    def _page_group_size(self, el, locator_counts, label_counts=None):
        """The real size of the repeated group `el` belongs to: the largest
        page-wide count among the strings a keyword would resolve it by."""
        best = 1
        table = getattr(self, '_a3_substring_collisions', None) or {}
        for key in self._resolution_keys(el):
            best = max(best, locator_counts.get(key, 1))
            if label_counts:
                best = max(best, label_counts.get(key, 1))
            # stream A3 2026-09-08: QWeb matches text by SUBSTRING, so a label
            # contained in another rendered string on the page resolves more
            # than one element even though the EXACT counters above see one.
            # `type_text("Name", ...)` on the Zoo pages also matches
            # "Name (secondary)" -- counted 1, anchored not at all, and it
            # typed into whichever came first.
            if key and ' '.join(str(key).split()) in table:
                best = max(best, 2)
        return best

    def _settle_bare_click_items(self, elements, locator_counts):
        """A ClickItem that STILL has no anchor is only defensible when its
        attribute value is unique on the page and the control has no visible
        text to anchor on. Otherwise it is a locator that resolves the wrong
        control silently, and it is dropped rather than offered."""
        for el in elements:
            hints = (el.get('qforce_hints') or {}).get('locator_options')
            if not hints:
                continue
            dis = el.get('disambiguation') or {}
            if dis.get('anchor_text_unique'):
                continue
            kept = []
            for hint in hints:
                if hint.get('keyword') != 'ClickItem' or hint.get('disambiguated_by'):
                    kept.append(hint)
                    continue
                loc = hint.get('locator')
                if locator_counts.get(loc, 0) <= 1:
                    # wave-2 F19 (2026-09-07): the sentence is DERIVED from
                    # this record's own disambiguation block, never templated.
                    # The old fixed string claimed "this attribute value is
                    # unique on the captured page" on 82 corpus records whose
                    # own group_size said the control repeats -- a
                    # contradiction inside one record, which is exactly the
                    # green-signal failure this file is written against.
                    group = dis.get('group_size') or 1
                    anchor = dis.get('anchor')
                    if group > 1:
                        state = (
                            "this control appears %d times on the page "
                            "(disambiguation.group_size) and this attribute value is what "
                            "separates this one from the other %d" % (group, group - 1)
                        )
                    else:
                        state = (
                            "this attribute value is unique on the captured page "
                            "(disambiguation.group_size 1)"
                        )
                    if anchor:
                        state += (
                            ", and the nearest text found ('%s') is NOT unique "
                            "(disambiguation.anchor_text_unique false)" % anchor
                        )
                    else:
                        state += ", and no anchor text was found in this control's container"
                    hint['why'] = (
                        (hint.get('why') or '') +
                        " -- NO ANCHOR: " + state + ", so the bare value is the only address "
                        "available. Re-verify it if the page's contents change; a ClickItem "
                        "without an anchor is the weakest rung offered."
                    )
                    kept.append(hint)
                else:
                    # Not unique AND not anchorable -- offering it would be the
                    # green-signal failure this codebase is named for.
                    continue
            el['qforce_hints']['locator_options'] = kept
            # stream 2A 2026-09-09: dropping the last rung must not drop the EXPLANATION with it.
            # An element whose only hint was a bare, repeated-locator ClickItem left here with an
            # empty locator_options and nothing said -- silence where a stated could-not-check
            # belongs (CLAUDE.md's tri-state rule). Measured on the qweb-hard-site captures, where
            # adding a real fill rung to the labelled input made its sibling's title-attribute
            # locator repeat and correctly retired 30 bare ClickItems.
            if hints and not kept and not el.get('hint_fill') and not el.get('hint_verify'):
                el['hint_reason'] = (
                    "the only rung offered was a ClickItem on an attribute value that resolves "
                    "more than one element on this page, with no anchor available -- it was "
                    "withdrawn rather than offered as a locator that silently hits the wrong "
                    "control. Anchor it, or address this element through the control that names "
                    "it.")

    def _row_anchor(self, el):
        """Nearest unique-looking visible text in this element's row/container --
        the string a caller would say out loud ("the caret next to Acme")."""
        tag = el.get('_tag') if isinstance(el, dict) else None
        if tag is None:
            tag = (el.get('context') or {}).get('_tag')
        if tag is None:
            return (el.get('context') or {}).get('row_anchor') or None
        own = ((el.get('identification') or {}).get('label_text') or '').strip()
        node = tag
        depth = 0
        while node is not None and depth < 8:
            name = (getattr(node, 'name', '') or '').lower()
            role = (node.get('role') or '').lower() if hasattr(node, 'get') else ''
            if name in ('tr', 'li', 'article') or role in ('row', 'listitem', 'option'):
                break
            node = getattr(node, 'parent', None)
            depth += 1
        if node is None:
            return None
        best = None
        try:
            for cell in node.find_all(['th', 'td', 'a', 'span'], limit=40):
                text = self.text_engine._get_safe_text(cell, max_len=60)
                if not text:
                    continue
                text = text.strip()
                if not text or text == own or len(text) < 2 or len(text) > 60:
                    continue
                if best is None or len(text) > len(best):
                    best = text
                if best and 3 <= len(best) <= 40:
                    break
        except Exception:
            return None
        return best

    def _add_disambiguated_hints(self, el, dis):
        """Describe this element's position in its repeated group on every call
        example, and list the anchor CANDIDATES the page offers -- never bake a
        chosen anchor in.

        D14, 2026-09-09 (docs/DECISIONS.md; docs/errors/entries/7627c1f2a9.json).
        This method used to write `anchor="<text>"` into `call_example` the
        moment the ladder found a text anchor whose (locator, anchor) pair was
        unique IN THE CAPTURE, and to promote the hint's confidence for it. Live
        on slockard Zoo_Forms_Advanced that was measured wrong: two 'Deal Name'
        members carried different "confirmed-unique" anchors and QWeb's
        proximity scorer -- which is geometric, and runs on the live page, not
        on the capture's text -- resolved BOTH to the same field. The second
        `type_text_clearing` appended instead of clearing.

        So the parser now emits what it can actually see:

          * `index=<n>` -- this member's 1-based position among the same-label
            matches in DOM order, for a control that REPEATS (group_size > 1).
            It is descriptive and it addresses exactly one element. It is NOT a
            QWeb argument: `click_text`/`click_item` take `anchor: str = "1"`
            and a NUMERIC anchor is QWeb's index mode (QWeb/keywords/text.py:357,
            929), so an executor translates `index=n` to `anchor="n"` when it
            builds the real call (`tools/recorder/pom_asset.ladder_from_hints`
            does exactly that). Keeping the two apart is the point: the hint
            describes a position, the executor prescribes a call.
          * `anchor_candidates` -- every (kind, text, scope, text_unique) triple
            the ladder found, in ladder order, as a SEPARATE field. A caller
            chooses one; the parser never does.
          * a control that does NOT repeat gets neither (CLAUDE.md locator
            doctrine: "a control that occurs once needs none").
        """
        hints = el.get('qforce_hints')
        if not hints:
            return
        # interop T20: only the keywords whose real QWeb signature takes
        # `anchor` are annotated -- a template's `anchoredKeywords`. A keyword
        # absent from that list keeps its pre-T20 call example byte for byte.
        anchored = (self._anchor_policy().get('anchoredKeywords')
                    or ['ClickItem', 'ClickText', 'ClickCheckbox',
                        'Click Table Cell'])
        cands = dis.get('anchor_candidates') or []
        repeated = (dis.get('group_size') or 1) > 1
        for hint in hints.get('locator_options', []) or []:
            if hint.get('keyword') not in anchored:
                continue
            if cands:
                hint['anchor_candidates'] = [dict(c) for c in cands]
            example = hint.get('call_example')
            if not example:
                continue
            # A1 2026-09-08: some call templates end in a trailing ` # ...`
            # note (GetFieldValue's "# read-back; verify_field(...) to assert"
            # is the whole of the 14-record GetFieldValue residue). The
            # `endswith(')')` test skipped every one of them, so the argument
            # was dropped for a purely cosmetic reason. Split the note off,
            # annotate the CALL, put the note back verbatim.
            call, sep, note = example.partition('  # ')
            call = call.rstrip()
            if not call.endswith(')'):
                continue
            # D14: a text anchor is never baked in again, so any anchor= a
            # previous pass wrote is stripped rather than appended to.
            call = re.sub(r',\s*anchor="(?:[^"\\]|\\.)*"\s*\)$', ')', call)
            if not repeated:
                hint['call_example'] = call + (sep + note if sep else '')
                hint.pop('disambiguated_by', None)
                continue
            if hint.get('disambiguated_by') == 'index' and 'index=' in call:
                hint['call_example'] = call + (sep + note if sep else '')
                continue
            hint['call_example'] = (call[:-1] + ', index=%d)' % (dis.get('index') or 1)
                                    + (sep + note if sep else ''))
            hint['disambiguated_by'] = 'index'

    # ------------------------------------------------ D14 resolution state ----
    def stamp_resolution(self, elements):
        """Stamp `disambiguation.resolution` and every hint's `confidence` with
        the only two values either field may hold: 'unverified' or 'verified'.

        'verified' comes from ONE place -- `self.verified_labels`, which the
        caller fills from the POM store when a live run has already resolved
        this element on this page key and recorded a read-back. Nothing in this
        file can promote a hint; a capture is not a run (D14, user 2026-09-09:
        "the hints are more detrimental than your independent judgements at run
        time"; docs/errors/entries/7627c1f2a9.json).
        """
        for el in elements:
            if not isinstance(el, dict):
                continue
            label = (el.get('identification') or {}).get('label_text') or ''
            state = (TIER_VERIFIED if self._norm_label(label) in self.verified_labels
                     else TIER_UNVERIFIED)
            dis = el.get('disambiguation')
            if isinstance(dis, dict):
                dis['resolution'] = state
            for hint in (el.get('qforce_hints') or {}).get('locator_options') or []:
                if hint.get('keyword'):
                    hint['confidence'] = state
        return elements

    def _collapse_form_fields(self, elements) -> list:
        COLLAPSIBLE_TYPES = self.COLLAPSIBLE_TYPES
        field_groups = {}
        keep_elements = []

        for el in elements:
            label = (el.get('identification') or {}).get('label_text')
            section = (el.get('context') or {}).get('form_section') or (el.get('context') or {}).get('modal_title') or '__global__'
            el_type = el.get('element_type')

            if el_type == 'custom_component' and not label and ((el.get('context') or {}).get('is_in_modal') or (el.get('context') or {}).get('form_section')):
                continue

            if not label or el_type not in COLLAPSIBLE_TYPES:
                keep_elements.append(el)
                continue

            group_key = f'{label}||{section}'
            if group_key not in field_groups:
                field_groups[group_key] = el
            else:
                existing = field_groups[group_key]
                if self._field_score(el) > self._field_score(existing):
                    merged_meta = {**(existing.get('behavioral_metadata') or {}), **(el.get('behavioral_metadata') or {})}
                    merged_validation = {**(existing.get('validation') or {}), **(el.get('validation') or {})}
                    merged = {**el}
                    merged['behavioral_metadata'] = merged_meta if merged_meta else merged.pop('behavioral_metadata', None)
                    merged['validation'] = merged_validation if merged_validation else merged.pop('validation', None)
                    field_groups[group_key] = merged

        return keep_elements + list(field_groups.values())

    def _get_class_string(self, tag) -> str:
        if not tag:
            return None
        try:
            css_class = tag.get('class', '')
            return ' '.join(css_class) if isinstance(css_class, list) else (css_class if css_class else None)
        except Exception:
            return None

    def _prune_empty_values(self, data):
        if isinstance(data, dict):
            return {k: v for k, v in ((k, self._prune_empty_values(v)) for k, v in data.items()) if v not in (None, {}, [])}
        elif isinstance(data, list):
            return [v for v in (self._prune_empty_values(item) for item in data) if v not in (None, {}, [])]
        return data