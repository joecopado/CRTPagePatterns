import re
from bs4 import Comment, NavigableString

class ComponentClassifier:
    RUNTIME_ID_PREFIXES = [
        'help-message-', 'error-message-',
        'label-', 'listbox-', 'dropdown-element-', 'tooltip-',
        'slds-combobox-', 'slds-listbox-',
    ]

    AURA_RENDER_ID_RE = re.compile(r'^\d+:\d+;[a-z]$')
    # Visualforce AUTO-GENERATED component ids/names. Measured live 2026-09-06 (review T4,
    # slockard `/lightning/n/ZooClassicForm`): 39 of 92 classified controls carried a
    # `j_id0:j_id1:j_id2:j_id3:bottom:j_id4`-shaped name, and `_classify_id` stamped every one of
    # them `stable_component_id` -- so the recorder emitted them as the element's IDENTITY. They
    # are the JSF/VF view-tree auto-ids: they renumber whenever the page's component tree changes
    # (a recompile, a rerender, a conditionally rendered block), so a step keyed on one is a
    # silent future failure. A VF id the AUTHOR named (`thePage:theForm:saveButton`) has no
    # `j_idN` segment and stays stable -- only the auto segments are the tell.
    VF_AUTO_ID_RE = re.compile(r'(^|:)j_id\d+(:|$)')
    # ENTIRELY auto-generated: every colon segment is a `j_idN`. This is the unambiguous case --
    # nothing an author named survives in it, so the whole value is volatile and it is not
    # identification. A MIXED value (`j_id0:j_id1:...:backpromotionfield`, measured on the
    # copado-trial back-promotion modal) keeps an author-named leaf that IS the meaningful part;
    # dropping the whole name there would lose the only target, so it is left in place and the
    # volatile-prefix problem is a named open item (docs/recorder/evidence/interop-T4-2026-09-06.md).
    VF_ALL_AUTO_ID_RE = re.compile(r'^j_id\d+(:j_id\d+)*$')
    AURA_SUFFIXED_NAME_RE = re.compile(r'^(.+?)(:\d+;\w+|:\d+)$')
    RUNTIME_GARBAGE_RE = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*-\d+$')
    OUTPUT_ONLY_TYPES = {'output_field', 'record_view_form', 'badge', 'icon', 'pill'}

    def __init__(self, config, text_engine):
        self.config = config
        self.text_engine = text_engine

    # interop T20 2026-09-07: the runtime-garbage patterns are TEMPLATE data
    # (`dynamicValuePatterns`, read into DomConfiguration.DYNAMIC_VALUE_*), not
    # constants of this class, because they now apply to EVERY attribute the
    # hint ladder may cite -- not just `id`. The class constants above stay as
    # the code-default fallback for a config that predates the key.
    def _dynamic_value_prefixes(self):
        return getattr(self.config, 'DYNAMIC_VALUE_PREFIXES', None) or self.RUNTIME_ID_PREFIXES

    def _dynamic_value_regexes(self):
        cached = getattr(self, '_dyn_re_cache', None)
        raw = getattr(self.config, 'DYNAMIC_VALUE_PATTERNS', None)
        if raw is None:
            raw = [self.AURA_RENDER_ID_RE.pattern, self.VF_AUTO_ID_RE.pattern,
                   self.RUNTIME_GARBAGE_RE.pattern]
        if cached is not None and cached[0] == tuple(raw):
            return cached[1]
        compiled = []
        for pattern in raw:
            try:
                compiled.append(re.compile(pattern))
            except re.error:
                continue  # a malformed template pattern is ignored, never fatal
        self._dyn_re_cache = (tuple(raw), compiled)
        return compiled

    def dynamic_value_attributes(self):
        return set(getattr(self.config, 'DYNAMIC_VALUE_ATTRIBUTES', None) or ('id',))

    def is_dynamic_value(self, value) -> bool:
        """True when `value` is a COUNTER/UID-shaped generated string -- runtime
        garbage in whichever attribute it appears in. The user's finding
        (2026-09-07): the ClickItem rung offered
        `click_item("lgt-datatable-1-options-1", tag="input")` as "a stable
        attribute value (name)"; the check existed only for `id`."""
        if not value or not isinstance(value, str):
            return False
        if any(value.startswith(p) for p in self._dynamic_value_prefixes()):
            return True
        return any(rx.search(value) for rx in self._dynamic_value_regexes())

    def _structural_container_family(self, tag, classes):
        """2026-09-10: a family declared by STRUCTURE (template key `structuralContainerRules`):
        the tag's class carries one of `containerClassFragments` and it holds at least
        `minDescendantRoleCount` descendants with role `requiredDescendantRole`. The SLDS dueling
        list (div.slds-dueling-list, two role=listbox) is the first rule; `lightning-dual-listbox`
        keeps its own tag branch. Returns the family or None."""
        rules = getattr(self.config, 'STRUCTURAL_CONTAINER_RULES', None) or []
        for rule in rules:
            frags = rule.get('containerClassFragments') or []
            if not any(f in classes for f in frags):
                continue
            # the base component (lightning-dual-listbox) renders this same structure inside its
            # own host, which already classifies by tag -- never a second row for the same control
            inside = {t.lower() for t in (rule.get('skipIfInsideTags') or [])}
            if inside and tag.find_parent(lambda p: p.name and p.name.lower() in inside) is not None:
                continue
            role = rule.get('requiredDescendantRole')
            need = int(rule.get('minDescendantRoleCount') or 1)
            if role:
                found = tag.find_all(lambda n: getattr(n, 'name', None) and (n.get('role') or '').lower() == role)
                if len(found) < need:
                    continue
            return rule.get('family')
        return None

    def _record_layout_field_family(self, tag, tag_name):
        """Phase 1B 2026-09-09 -- the read-mode record-DETAIL field shape.

        `records-record-layout-item` wraps EVERY field on a Salesforce Record Home page, edit-mode
        and read-mode alike, so the tag name alone does not say which. Read-mode wraps a
        `test-id__output-root` div (this is the shape `docs/dom-captures/02-account-record-page.html`
        and `05-custom-object-record-page.html` measured 18/12 slds-form-element__label -> 0 fields
        against); edit-mode wraps a real editable control instead (e.g. `lightning-input-field`),
        which is a SEPARATE tag, classified on its own pass regardless of what this method returns.

        Returns the declared family (`output_field`) when a read-mode marker descendant is found;
        `'structural'` (dropped by SKIP_ELEMENT_TYPES, same as never being in TARGET_TAGS at all --
        no new noise) for a container tag with no marker; `None` when the tag isn't one of the
        configured container tags at all, so the generic classification chain keeps running.
        """
        rule = getattr(self.config, 'RECORD_LAYOUT_FIELD_RULES', None)
        if not rule:
            return None
        tags = {t.lower() for t in (rule.get('containerTags') or [])}
        if tag_name not in tags:
            return None
        markers = rule.get('readModeMarkerClassFragments') or []

        def _has_marker(node):
            if not getattr(node, 'name', None):
                return False
            classes = ' '.join(node.get('class') or [])
            return any(frag in classes for frag in markers)

        if markers and tag.find(_has_marker):
            return rule.get('family') or 'output_field'
        return 'structural'

    def _classify_id(self, id_val) -> str:
        if not id_val:
            return None
        if re.match(r'^[a-zA-Z0-9]{15}$', id_val) or re.match(r'^[a-zA-Z0-9]{18}$', id_val):
            return 'salesforce_record_id'
        if self.is_dynamic_value(id_val):
            return 'runtime_garbage'
        return 'stable_component_id'

    def _clean_name(self, raw_name) -> str:
        if not raw_name:
            return None
        match = self.AURA_SUFFIXED_NAME_RE.match(raw_name)
        if match:
            return match.group(1)
        return raw_name

    #: SLDS BEM: `slds-listbox__option` is the option element; `slds-listbox__option_plain` /
    #: `_entity` are its modifiers. `slds-listbox__option-text` (and `-text_entity`) is a
    #: DIFFERENT element class -- the option's inner text node -- and is not an option. F223.
    PICKLIST_OPTION_CLASS = 'slds-listbox__option'

    def _has_picklist_option_class(self, tag) -> bool:
        """True only when a class TOKEN is the option block or one of its `_modifier` forms."""
        base = self.PICKLIST_OPTION_CLASS
        for token in (tag.get('class') or []):
            token = (token or '').strip().lower()
            if token == base or token.startswith(base + '_'):
                return True
        return False

    def _classify_element_type(self, tag) -> str:
        if not tag or not hasattr(tag, 'name') or not tag.name:
            return 'unknown'

        tag_name = tag.name.lower()
        tag_type = (tag.get('type') or '').lower()
        role = (tag.get('role') or '').lower()
        classes = ' '.join(tag.get('class') or []).lower()

        # Real bug, found live 2026-07-31: a bare role="option" also matches
        # the SLDS Path component's stage tabs (<a role="option" class="tabHeader
        # slds-path__link">), which is a completely different, real,
        # interactive widget (the "click a stage name on the Path bar" way
        # of changing an Opportunity's Stage) -- not a transient picklist
        # dropdown option. Confirmed via a real Opportunity record: these
        # were silently dropped (element_type picklist_option is in
        # SKIP_ELEMENT_TYPES), even though the raw HTML genuinely has them.
        # `slds-listbox__option` alone (no bare role=="option") is left as
        # the strong, real signal for genuine picklist/combobox dropdown
        # options; a bare role="option" now also requires NOT being a Path
        # element (its own distinct `slds-path__` class family) before it's
        # treated as a picklist option.
        # F223 (2026-09-20): the rule above was a SUBSTRING test, and SLDS has a second,
        # unrelated class that starts with the same 21 characters -- `slds-listbox__option-text`,
        # which styles the TEXT ELEMENT INSIDE an option, not the option. OmniStudio stamps its
        # `_entity` variant on the combobox INPUT ITSELF:
        #     <input class="slds-input slds-listbox__option-text_entity" role="combobox"
        #            aria-haspopup="listbox" aria-label="Salutation">
        # so all four comboboxes on a real OmniScript step (Salutation, Phone Type, Nationality,
        # Taxpayer Identification Type) classified as `picklist_option`, which is in
        # SKIP_ELEMENT_TYPES, and were dropped before any signature could see them: 47 rows,
        # 0 dropdowns, no error anywhere. The recorder's own injected bundle already carries
        # `slds-listbox__option-text_entity` as an OmniStudio combobox HOST signal
        # (tools/recorder/inject/dist/families.generated.js), so the two resolvers disagreed.
        # The class is now matched as a CLASS TOKEN in its BEM forms -- the block itself
        # (`slds-listbox__option`) or one of its `_modifier` variants -- never as a prefix of a
        # different class; and a node carrying `role="combobox"` is the control, never an option
        # inside one, whatever it is styled with.
        if role != 'combobox' and self._has_picklist_option_class(tag):
            return 'picklist_option'
        if role == 'option' and 'slds-path__' not in classes:
            return 'picklist_option'

        # Phase 1B 2026-09-09 (docs/proposals/challenge-2026-09-08/C1-dom-extraction.md):
        # a record-DETAIL page's per-field container, template-driven (never a literal
        # `tag_name == 'records-record-layout-item'` branch on its own -- the tag list AND
        # the read-mode marker both come from RECORD_LAYOUT_FIELD_RULES / template key
        # `recordLayoutFieldRules`). See _record_layout_field_family's own docstring.
        record_layout_family = self._record_layout_field_family(tag, tag_name)
        if record_layout_family:
            return record_layout_family

        structural_family = self._structural_container_family(tag, classes)
        if structural_family:
            return structural_family

        if tag_name == 'lightning-input-field':
            return 'input_field'
        if tag_name == 'lightning-output-field':
            return 'output_field'
        if tag_name == 'lightning-record-edit-form':
            return 'record_edit_form'
        if tag_name == 'lightning-record-view-form':
            return 'record_view_form'
        if 'datatable' in tag_name or 'tree-grid' in tag_name:
            return 'datatable'
        if tag_name == 'lightning-tree':
            return 'tree'
        if tag_name == 'lightning-dual-listbox':
            return 'dual_listbox'
        if tag_name in ('lightning-checkbox-group', 'lightning-radio-group'):
            return tag_name.replace('lightning-', '')
        if tag_name == 'lightning-toggle':
            return 'toggle'
        if tag_name == 'lightning-slider':
            return 'slider'
        if tag_name == 'lightning-pill':
            return 'pill'
        if tag_name == 'lightning-badge':
            return 'badge'
        if tag_name == 'lightning-icon':
            return 'icon'

        if tag_name == 'table':
            # Wildcard, not a specific-attribute gate: a real <table> tag is
            # reason enough on its own -- the old data-test-id/data-id/
            # data-row-key gate here meant any classic Aura-rendered table
            # without one of those exact attributes (e.g. Salesforce Files'
            # own list view, which uses plain data-aura-rendered-by
            # throughout) was silently never classified as a table at all,
            # even though _find_table_rows already has its own generic
            # <tr>-with-non-empty-<td> fallback for exactly this case.
            return 'native_table'

        dropdown_info = self._detect_dropdown_type(tag)
        if dropdown_info:
            return 'dropdown'

        if 'textarea' in tag_name:
            return 'textarea'

        if tag_name in ('input', 'lightning-input'):
            if tag_type == 'checkbox':
                return 'checkbox'
            if tag_type == 'radio':
                return 'radio'
            if tag_type == 'password':
                return 'password_field'
            # 2026-09-07 iframe descent (docs/recorder/COPADO-GAPS-2026-09-07.md,
            # REVIEW-BRIEF-NEXT.md row C4c): classic Visualforce forms use
            # plain `<input type="submit"/type="button"/type="reset">` for
            # their real action buttons ("Save"/"Cancel" on the
            # backpromote-02/-03 New Promotion form) -- these fell through
            # to the default 'input_field' below, mislabeling a button as a
            # text field. No known golden capture depended on the old,
            # wrong classification (`grep type="submit"` across
            # docs/dom-captures hits 16 files, all of them Aura/VF captures
            # whose submit inputs were previously counted as loose
            # input_field -- corrected here, goldens regenerated in this
            # same commit).
            if tag_type in ('submit', 'button', 'reset'):
                return 'button'
            return 'input_field'

        if 'button' in tag_name or role == 'button' or 'slds-button' in classes:
            return 'button'

        if tag_name == 'a':
            return 'button' if role == 'button' else 'link'

        if role == 'checkbox':
            return 'checkbox'
        if role == 'radio':
            return 'radio'
        if role == 'treeitem':
            # B7 (2026-09-07, app_scan_report.py): `tree` blocks a Setup page in all 5 orgs
            # scanned (docs/dom-captures/slockard/sales-console/setup-home.html: 43
            # li[role="treeitem"], the onesetupNavTreeNode markup) -- previously had NO branch
            # here, so its own <a>/<button> children fell through to plain 'link'/'button'
            # and the li itself was dropped as non-interactive, leaving no element_type a
            # keyword could route on. This is the SAME v3 template family ("tree", role
            # treeitem -- docs/recorder/templates/salesforce-lightning.v3.json) used by the
            # OTHER parser (v3.py); this branch brings the pythonDom hint-ladder parser
            # (this file, dom_config.py's FAMILY_KEYWORDS['tree']) into agreement with it.
            return 'tree'

        # Parser families fix (2026-09-07, docs/recorder/COPADO-GAPS-2026-09-07.md
        # "The User Story Bug record-type form -- 91 unknown/custom elements"):
        # these stock lightning-* base components had NO branch here at all,
        # so every one of them fell through to plain 'unknown' -- not
        # Copado-specific, this hits ANY org's lookup/combobox/date/time/
        # richtext fields. Measured on the copado-trial 02b capture: 91
        # elements across exactly these tags, 0 left over once classified.
        #
        # lightning-lookup is the OUTER control and wins the classification;
        # its internal host (lightning-lookup-desktop) and the grouped-/base-
        # combobox it composes are shadow-wrapper duplicates of the SAME
        # control, not a second one -- 'internal' (SKIP_ELEMENT_TYPES) so
        # they never double-count. A standalone lightning-grouped-combobox or
        # lightning-base-combobox (no lookup ancestor) IS a real control in
        # its own right (e.g. a plain object/record-type picker) and gets the
        # 'combobox' family -- but only the outermost of the two: a
        # base-combobox nested inside a grouped-combobox is that
        # grouped-combobox's own shadow child, so it is 'internal' too.
        if tag_name == 'lightning-lookup':
            return 'lookup'
        if tag_name == 'lightning-lookup-desktop':
            return 'internal'
        if tag_name == 'lightning-grouped-combobox':
            return 'internal' if tag.find_parent('lightning-lookup') else 'combobox'
        if tag_name == 'lightning-base-combobox':
            # lightning-base-combobox is the shadow-DOM trigger every one of
            # these compound controls composes internally -- if any ancestor
            # here is already its own classified family (lookup/combobox/
            # picklist/date/time/datetime/richtext), this is that control's
            # OWN shadow child, not a second control. Measured live: all 21
            # base-combobox instances on the 02b capture fall under one of
            # these six ancestor tags (12 lookup, 3 combobox/picklist, 4
            # richtext toolbar font-picker, 2 time/datetime) -- 0 genuinely
            # standalone on this page, but a standalone one (e.g. a bare
            # object/record-type picker with no such ancestor) still gets
            # its own real 'combobox' classification below.
            internal_ancestor_tags = (
                'lightning-lookup', 'lightning-grouped-combobox', 'lightning-combobox',
                'lightning-picklist', 'lightning-datepicker', 'lightning-timepicker',
                'lightning-datetimepicker',
            )
            if tag.find_parent(lambda t: t.name in internal_ancestor_tags):
                return 'internal'
            return 'combobox'
        # lightning-datetimepicker is ITSELF a compound control that composes
        # a lightning-datepicker + lightning-timepicker as its two visible
        # inputs (confirmed live: both copado-trial instances nest exactly
        # one of each) -- the outer 'datetime' wins per the same OUTER-wins
        # rule as lookup/combobox above, so the nested date/time pickers are
        # 'internal', not a second and third control.
        if tag_name == 'lightning-datetimepicker':
            return 'datetime'
        if tag_name == 'lightning-datepicker':
            return 'internal' if tag.find_parent('lightning-datetimepicker') else 'date'
        if tag_name == 'lightning-timepicker':
            return 'internal' if tag.find_parent('lightning-datetimepicker') else 'time'
        if tag_name == 'lightning-quill':
            return 'richtext'
        if tag_name == 'lightning-focus-trap':
            return 'structural'
        # 2026-09-07 (docs/recorder/COPADO-GAPS-2026-09-07.md "Iframe / canvas
        # / Visualforce boundaries", REVIEW-BRIEF-NEXT.md row C4c): the frame
        # boundary itself is a real control family -- a consumer needs to
        # know it exists and what it is (src/title), even though QWeb itself
        # auto-penetrates iframes when clicking/typing -- no navigation step
        # (`switch_to.frame`, etc.) is needed or emitted anywhere in this
        # parser. See iframe_descent.py's `frame_label` for what the `frame`
        # field on elements found INSIDE this iframe is actually for
        # (disambiguation, not navigation).
        if tag_name == 'iframe':
            return 'iframe'

        if tag_name.startswith('c-omni'):
            return 'omniscript_element'

        if tag_name.startswith('c-'):
            if role in ('button', 'link'):
                return role
            if 'button' in tag_name:
                return 'button'
            if 'input' in tag_name:
                return 'input_field'
            return 'custom_component'

        return 'unknown'

    def _detect_dropdown_type(self, tag):
        if not tag or not hasattr(tag, 'name') or not tag.name:
            return None
        tag_name = tag.name.lower()

        for sig in self.config.DROPDOWN_SIGNATURES:
            tag_match = False
            if callable(sig['tags']):
                tag_match = sig['tags'](tag_name)
            elif isinstance(sig['tags'], list):
                tag_match = tag_name in sig['tags']

            if not tag_match:
                continue

            if 'attributes' in sig:
                attr_match = True
                for attr_key, attr_value in sig['attributes'].items():
                    tag_attr = tag.get(attr_key)
                    if callable(attr_value):
                        if not attr_value(tag_attr):
                            attr_match = False
                            break
                    elif tag_attr != attr_value:
                        attr_match = False
                        break
                if not attr_match:
                    continue

            return {
                'dropdown_type': sig['type'],
                'is_dynamic': sig.get('dynamic', True),
                'tag_name': tag_name,
            }
        return None

    def _detect_row_controls(self, tr) -> dict:
        """Given a <tr>, searches its descendants against
        DomConfiguration.ROW_CONTROL_SIGNATURES and returns the REAL,
        confirmed attribute value + tag for whatever is actually found --
        e.g. {"row_checkbox": {"tag": "input", "attribute_value": "checkbox"}}
        -- in place of a guessed xpath template. Same matching shape as
        _detect_dropdown_type, reused deliberately for consistency.
        """
        if not tr or not hasattr(tr, 'find_all'):
            return {}

        found = {}
        for sig in self.config.ROW_CONTROL_SIGNATURES:
            role = sig['role']
            if role in found:
                continue

            candidates = tr.find_all(sig['tags']) if isinstance(sig['tags'], list) else []
            for candidate in candidates:
                attr_match = True
                for attr_key, attr_value in sig.get('attributes', {}).items():
                    tag_attr = candidate.get(attr_key)
                    if callable(attr_value):
                        if not attr_value(tag_attr):
                            attr_match = False
                            break
                    elif tag_attr != attr_value:
                        attr_match = False
                        break
                if attr_match:
                    found[role] = {
                        'tag': candidate.name.lower() if candidate.name else '',
                        'attribute_value': candidate.get('type') or '',
                    }
                    break
        return found

    def _extract_dropdown_options(self, tag):
        if not tag:
            return None
        dropdown_info = self._detect_dropdown_type(tag)
        if not dropdown_info:
            return None

        dropdown_type = dropdown_info['dropdown_type']
        is_dynamic = dropdown_info['is_dynamic']

        if dropdown_type in ('html_select', 'aura_select', 'visualforce_select'):
            return self._extract_static_select_options(tag)

        if is_dynamic:
            if dropdown_type == 'lightning_combobox':
                return self._extract_lightning_combobox_options(tag)
            elif dropdown_type == 'slds_combobox':
                listbox = self._find_adjacent_listbox(tag)
                if listbox:
                    return self._extract_slds_listbox_options(listbox)
            elif dropdown_type == 'lightning_record_picklist':
                return self._extract_lightning_record_picklist_options(tag)
            elif dropdown_type == 'custom_lwc_combobox':
                parent = tag.find_parent()
                if parent:
                    listbox = parent.find(attrs={'role': 'listbox'})
                    if listbox:
                        return self._extract_slds_listbox_options(listbox)
            elif dropdown_type in ('cpq_dropdown', 'omnistudio_dropdown'):
                if tag.name == 'select':
                    return self._extract_static_select_options(tag)
                listbox = self._find_adjacent_listbox(tag)
                if listbox:
                    return self._extract_slds_listbox_options(listbox)
        return None

    def _extract_static_select_options(self, tag):
        if not tag or tag.name != 'select':
            return None
        options = []
        for opt in tag.find_all('option'):
            option_data = {
                'value': opt.get('value', ''),
                'label': opt.get_text(strip=True),
            }
            if opt.get('selected'):
                option_data['selected'] = True
            if opt.get('disabled'):
                option_data['disabled'] = True
            if option_data['label'] or option_data['value']:
                options.append(option_data)
        return options if options else None

    def _extract_lightning_combobox_options(self, tag):
        combobox = tag if tag.name == 'lightning-combobox' else tag.find_parent('lightning-combobox')
        if not combobox:
            return None
        option_items = combobox.find_all('lightning-base-combobox-item', {'role': 'option'})
        if not option_items:
            return None
        options = []
        for item in option_items:
            option_data = {
                'value': item.get('data-value', ''),
                'label': item.get_text(strip=True),
            }
            if item.get('aria-selected') == 'true':
                option_data['selected'] = True
            if option_data['label'] or option_data['value']:
                options.append(option_data)
        return options if options else None

    def _find_adjacent_listbox(self, tag):
        if not tag:
            return None
        listbox = tag.find_next_sibling(attrs={'role': 'listbox'})
        if listbox:
            return listbox
        parent = tag.parent
        if parent:
            listbox = parent.find_next_sibling(attrs={'role': 'listbox'})
            if listbox:
                return listbox
        container = tag.find_parent(attrs={'class': lambda c: c and 'slds-combobox' in (
            ' '.join(c) if isinstance(c, list) else c
        )})
        if container:
            listbox = container.find(attrs={'role': 'listbox'})
            if listbox:
                return listbox
        if parent and parent.parent:
            listbox = parent.parent.find(attrs={'role': 'listbox'})
            if listbox:
                return listbox
        return None

    def _extract_slds_listbox_options(self, listbox):
        if not listbox:
            return None
        option_elements = listbox.find_all(attrs={'role': 'option'})
        if not option_elements:
            return None
        options = []
        for opt in option_elements:
            option_data = {
                'value': opt.get('data-value', '') or opt.get('data-item-id', ''),
                'label': opt.get_text(strip=True),
            }
            if opt.get('aria-selected') == 'true':
                option_data['selected'] = True
            if option_data['label'] or option_data['value']:
                options.append(option_data)
        return options if options else None

    def _extract_lightning_record_picklist_options(self, tag):
        input_field = tag if tag.name == 'lightning-input-field' else tag.find_parent('lightning-input-field')
        if not input_field:
            return None
        combobox = input_field.find('lightning-combobox')
        if combobox:
            return self._extract_lightning_combobox_options(combobox)
        listbox = input_field.find(attrs={'role': 'listbox'})
        if listbox:
            return self._extract_slds_listbox_options(listbox)
        return None

    def _is_cell_noise(self, child) -> bool:
        if not hasattr(child, 'get'):
            return True
        if child.get('aria-hidden') == 'true':
            return True
        cell_noise_roles = {'presentation', 'img', 'separator', 'progressbar'}
        if child.get('role') in cell_noise_roles:
            return True
        cell_noise_tags = {'svg', 'lightning-icon', 'c-icon', 'lightning-primitive-icon'}
        if child.name and child.name.lower() in cell_noise_tags:
            return True
        cell_noise_classes = [
            'slds-assistive-text', 'sr-only', 'visually-hidden',
            'slds-hide', 'assistive-text', 'screen-reader-only',
        ]
        classes = ' '.join(child.get('class') or [])
        if any(c in classes for c in cell_noise_classes):
            return True
        if re.match(r'^Progress\s+\d+%$', child.get_text(strip=True), re.IGNORECASE):
            return True
        return False

    def _get_cell_text(self, td) -> str:
        cell_aria = td.get('aria-label') or td.get('title')
        if cell_aria and cell_aria.strip():
            return cell_aria.strip()

        direct_text_nodes = [
            n for n in td.children
            if isinstance(n, NavigableString) and not isinstance(n, Comment) and n.strip()
        ]

        visible_children = [
            c for c in td.children
            if hasattr(c, 'name') and c.name and not self._is_cell_noise(c)
        ]

        if direct_text_nodes:
            return direct_text_nodes[0].strip()

        if len(visible_children) == 1:
            child = visible_children[0]
            child_aria = child.get('aria-label') or child.get('title')
            if child_aria and child_aria.strip():
                return child_aria.strip()
            for node in child.children:
                if isinstance(node, NavigableString) and not isinstance(node, Comment) and node.strip():
                    return node.strip()
            visible_grandchildren = [
                g for g in child.children
                if hasattr(g, 'name') and g.name and not self._is_cell_noise(g)
            ]
            if len(visible_grandchildren) == 1:
                gc = visible_grandchildren[0]
                gc_aria = gc.get('aria-label') or gc.get('title')
                if gc_aria and gc_aria.strip():
                    return gc_aria.strip()
                for node in gc.children:
                    if isinstance(node, NavigableString) and not isinstance(node, Comment) and node.strip():
                        return node.strip()

        if len(visible_children) > 1:
            parts = []
            for child in visible_children:
                if len(parts) >= 2:
                    break
                if not list(child.children):
                    t = child.get_text(strip=True)
                    if t:
                        parts.append(t)
            if parts:
                return ''.join(parts)

        fallback = self.text_engine._get_safe_text(td, max_len=60)
        return fallback if fallback else None

    def _infer_cell_type(self, values) -> str:
        if not values:
            return 'unknown'
        sample = values[0]
        if re.match(r'^\$[\d,]+(\.\d+)?$', sample):
            return 'currency'
        if re.match(r'^\d{4}-\d{2}-\d{2}$', sample):
            return 'date'
        if re.match(r'^\d+%$', sample):
            return 'percent'
        if re.match(r'^(true|false|yes|no)$', sample, re.IGNORECASE):
            return 'boolean'
        if re.match(r'^\d+$', sample):
            return 'number'
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', sample):
            return 'email'
        if re.match(r'^https?://', sample):
            return 'url'
        return 'text'

    def _find_table_rows(self, table):
        """Scoped to <tbody> when present, and matches th+td cells, not
        td-only -- real Salesforce list-view tables routinely render a
        row's first data column as <th scope="row"> in the body (already
        confirmed for the live click_table_cell mechanism; this static
        parser had the exact same td-only bug independently, confirmed
        live 2026-07-29 against Salesforce Files' own list view, where it
        silently dropped/shifted every row by one column). Scoping to
        <tbody> (falling back to the whole table only if there's genuinely
        no <tbody>) keeps the widened th+td match from also picking up the
        <thead> row itself, which is real <tr> markup too."""
        tbody = table.find('tbody')
        search_root = tbody if tbody else table
        selectors_order = [
            {'data-id': True},
            {'data-test-id': True},
            {'data-row-key': True},
        ]
        for attrs in selectors_order:
            rows = search_root.find_all('tr', attrs=attrs)
            rows = [
                r for r in rows
                if r.find_all(['th', 'td']) and
                any(self._get_cell_text(c) for c in r.find_all(['th', 'td']))
            ]
            if rows:
                return rows
        rows = search_root.find_all('tr')
        rows = [
            r for r in rows
            if r.find_all(['th', 'td']) and
            any(self._get_cell_text(c) for c in r.find_all(['th', 'td']))
        ]
        return rows

    def _extract_row_data(self, tr, columns):
        row_obj = {}
        for key in ('data-id', 'data-test-id', 'data-row-key'):
            val = tr.get(key)
            if val:
                row_obj[f'_{key.replace("-", "_")}'] = val
        return row_obj

    def _extract_native_table(self, tag) -> dict:
        metadata = {}
        header_row = tag.find('tr')
        columns = []
        if header_row:
            for th in header_row.find_all(['th', 'td']):
                label = th.get('aria-label') or th.get_text(strip=True)
                data_label = th.get('data-label') or label
                if label:
                    columns.append({'label': label, 'data_label': data_label})

        all_rows = self._find_table_rows(tag)
        sample = []
        for tr in all_rows[:5]:
            row_obj = self._extract_row_data(tr, columns)
            cells = tr.find_all(['th', 'td'])
            for i, cell in enumerate(cells):
                col_label = columns[i]['label'] if i < len(columns) else f'col_{i}'
                data_label = cell.get('data-label') or col_label
                text = self._get_cell_text(cell)
                if text:
                    row_obj[data_label] = text
            if row_obj:
                sample.append(row_obj)

        column_schema = []
        for col in columns:
            values = [
                row.get(col['data_label'], '')
                for row in sample
                if row.get(col['data_label'])
            ]
            column_schema.append({
                'label': col['label'],
                'data_label': col['data_label'],
                'inferred_type': self._infer_cell_type(values),
            })

        metadata['columns'] = column_schema
        metadata['total_rows'] = len(all_rows)
        metadata['sample_rows'] = sample
        metadata['row_xpath_patterns'] = {
            'row_by_data_id': "//tr[@data-id='{value}']",
            'row_by_test_id': "//tr[@data-test-id='{value}']",
            'row_by_key': "//tr[@data-row-key='{value}']",
            'cell_by_label': "//tr[@data-id='{row_id}']//td[@data-label='{column}']",
            'cell_by_text': "//td[@data-label='{column}' and normalize-space()='{value}']",
            'cell_positional': "//tr[@data-id='{row_id}']/td[{index}]",
            'edit_button_by_row': "//tr[@data-id='{row_id}']//button[@title='Edit']",
            'row_containing_text': "//tr[.//td[normalize-space()='{value}']]",
        }
        return metadata