import hashlib
import json
import os
import re

# Default capture template -- docs/recorder/PLAN.md's "Capture templates per
# application" section. Repo root is 4 levels up from this file
# (tools/interop/resources/pythonDom -> tools/interop/resources ->
# tools/interop -> tools -> repo root).
TEMPLATES_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..",
    "docs", "recorder", "templates",
))
DEFAULT_TEMPLATE_NAME = "salesforce-lightning"  # v1 -- do not change without a user decision
DEFAULT_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, DEFAULT_TEMPLATE_NAME + ".json")
TEMPLATE_ENV_VAR = "GARZAI_DOM_TEMPLATE"  # e.g. "salesforce-lightning.v2" -- unset means v1

# ---------------------------------------------------------------- selection --
# interop T18 2026-09-07. THE FINDING (user): v1 -- the LIVE parser -- picked its
# template by a hard-coded default or an env var and NEVER looked at the page,
# while only v3 detected by `frameworkMarkers`. A Salesforce template silently
# parsing a non-Salesforce page is indistinguishable from a parser bug, because
# no parse result said which template produced it.
#
# MARKER_CANDIDATES is the v1-lineage candidate ORDER; the markers themselves
# are never hard-coded here -- each candidate template declares its own
# `frameworkMarkers` (v3.load_template reads the same key, same meaning). The
# first candidate whose markers appear in the HTML wins; if none do, the page is
# not that framework and GENERIC_TEMPLATE_NAME is selected -- a negative
# detection is still a detection, so `selected_by` is still "markers".
MARKER_CANDIDATES = ("salesforce-lightning",)
GENERIC_TEMPLATE_NAME = "web-generic"  # v1-shape generic template (no Lightning assumptions)


def _markers_of(path):
    """`frameworkMarkers` in either shape: v1's dict of {family: [marker, ...]}
    (plus a human 'note' string, ignored) or v3's plain list."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []
    fm = data.get("frameworkMarkers")
    if isinstance(fm, list):
        return [m for m in fm if isinstance(m, str)]
    if isinstance(fm, dict):
        out = []
        for v in fm.values():
            if isinstance(v, list):
                out.extend([m for m in v if isinstance(m, str)])
        return out
    return []


def select_template(html=None, template=None, template_path=None,
                    use_default_template=True, environ=None):
    """Resolve WHICH template a DomConfiguration should load, and say why.

    Precedence, most specific first:
      1. `template_path` / `template`  -> selected_by "param"
      2. GARZAI_DOM_TEMPLATE           -> selected_by "env"
      3. `frameworkMarkers` vs `html`  -> selected_by "markers"
      4. DEFAULT_TEMPLATE_NAME         -> selected_by "default"

    (2) is an override of (3) and (3) replaces the blind (4) -- before T18 only
    (1), (2) and (4) existed, which is exactly the finding this fixes. An
    explicit param stays the most specific so `from_template()` and every
    existing `template=` caller keep their current meaning.

    Returns (path, selected_by, markers_seen). `markers_seen` is the list of
    marker strings actually found in `html` (empty on a negative detection, and
    always empty when markers were not consulted).
    """
    environ = os.environ if environ is None else environ
    if template_path:
        return template_path, "param", []
    if template is not None:
        return _resolve_template_name_or_path(template), "param", []
    env_name = environ.get(TEMPLATE_ENV_VAR)
    if env_name:
        return _resolve_template_name_or_path(env_name), "env", []
    if html is not None:
        for name in MARKER_CANDIDATES:
            path = _resolve_template_name_or_path(name)
            seen = [m for m in _markers_of(path) if m in html]
            if seen:
                return path, "markers", seen
        return _resolve_template_name_or_path(GENERIC_TEMPLATE_NAME), "markers", []
    if use_default_template:
        return DEFAULT_TEMPLATE_PATH, "default", []
    return None, "none", []


# Templates that have been SUPERSEDED are stubbed rather than deleted (so a
# stale name fails loudly instead of silently parsing with different rules).
# A stub is a JSON object whose only meaningful key is `superseded_by`.
SUPERSEDED_KEY = "superseded_by"


class SupersededTemplate(RuntimeError):
    """Raised when a template file is a supersession stub. Names the successor."""


def _repo_rel(path):
    root = os.path.normpath(os.path.join(TEMPLATES_DIR, "..", "..", ".."))
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def template_provenance(config):
    """The provenance block: which template file actually produced a parse.

    {name, path, sha256, selected_by, markers_seen} -- `path` is repo-relative
    and `sha256` is the first 12 hex chars of the file's digest, so two runs
    that name the same template but read different bytes are distinguishable.
    A parse that fell through to the hard-coded class constants says so with
    name "hard-coded-fallback" and a null path.
    """
    path = getattr(config, "template_source", None)
    selected_by = getattr(config, "template_selected_by", "unknown")
    markers = list(getattr(config, "template_markers_seen", []) or [])
    if not path or path == "hard-coded-fallback" or not os.path.isfile(path):
        return {"name": "hard-coded-fallback", "path": None, "sha256": None,
                "selected_by": selected_by, "markers_seen": markers}
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()[:12]
    return {"name": os.path.basename(path)[:-5] if path.endswith(".json")
                    else os.path.basename(path),
            "path": _repo_rel(path),
            "sha256": digest,
            "selected_by": selected_by,
            "markers_seen": markers}


def provenance_for_html(html):
    """Provenance for the template `parse_elements_from_html(html)` WOULD select,
    without parsing. Used by `up.py --op capture`, which saves HTML and never
    parses it -- the capture result still names the template that will act."""
    return template_provenance(DomConfiguration(html=html))


def _resolve_template_name_or_path(name_or_path):
    """A template selector is either a real file path or a bare name that
    resolves to docs/recorder/templates/<name>.json (".json" optional)."""
    if not name_or_path:
        return None
    if os.path.isfile(name_or_path):
        return name_or_path
    fname = name_or_path if name_or_path.endswith(".json") else name_or_path + ".json"
    return os.path.join(TEMPLATES_DIR, fname)


class DomConfiguration:
    NOISE_TAGS = {
        'lightning-icon', 'lightning-badge', 'lightning-pill', 'lightning-spinner',
        'lightning-progress-indicator', 'lightning-helptext', 'lightning-formatted-text',
        'lightning-formatted-url', 'lightning-formatted-date-time',
        'lightning-formatted-number', 'lightning-formatted-phone',
        'lightning-formatted-email', 'lightning-formatted-rich-text',
        'lightning-primitive-icon', 'lightning-avatar',
        'lightning-primitive-cell-types', 'lightning-primitive-datatable-iedbug',
        'lightning-message-context-consumer', 'lightning-message-context-provider',
        'lightning-relative-date-time',
        # Parser families fix (2026-09-07, docs/recorder/COPADO-GAPS-2026-09-07.md
        # "The User Story Bug record-type form -- 91 unknown/custom elements"):
        # lightning-lookup's two internal service helpers are never rendered
        # controls -- a data-source adapter and a metadata-cache service that
        # the real lightning-lookup-desktop composes internally, no UI of
        # their own. Confirmed live on the copado-trial 02b capture: 12 of
        # each, always a descendant of a lightning-lookup that is itself
        # already classified ('lookup'). Noise, not 'unknown', so they never
        # count as unclassified elements OR as a second control.
        'lightning-lookup-data-source', 'lightning-lookup-metadata-service',
    }

    # Wildcard noise, not an enum -- lightning-primitive-* tags are ALWAYS
    # Lightning's own internal composition/shadow-DOM plumbing (e.g.
    # lightning-primitive-input-simple is the internal shadow child of a
    # real lightning-input), never a real interaction target on their own.
    # Confirmed live 2026-07-29: the new lightning-* wildcard pass in
    # actions.py's _parse_elements_from_html surfaced 15 of these as vague
    # 'unknown'-typed duplicate noise on a single record page before this
    # pattern existed. Listing each one individually in NOISE_TAGS would
    # just recreate the exact enum-vs-wildcard problem this whole pass was
    # meant to fix.
    NOISE_TAG_PATTERNS = [r'^lightning-primitive-']

    NOISE_ROLES = {
        'presentation', 'none', 'separator', 'progressbar',
        'status', 'log', 'alert', 'tooltip',
    }

    NOISE_CLASS_FRAGMENTS = [
        'slds-assistive-text', 'slds-hide', 'slds-is-collapsed',
        'forceRecordCoverPhoto', 'slds-col--padded',
        'slds-resize-handle', 'slds-drag-handle', 'slds-th__action-icon',
    ]

    SHADOW_WRAPPER_TAGS = {
        'lightning-input', 'lightning-textarea', 'lightning-combobox',
        'lightning-picklist', 'lightning-input-address', 'lightning-input-name',
        'lightning-input-field', 'lightning-input-rich-text',
        'lightning-input-location', 'lightning-button', 'lightning-button-icon',
        'lightning-button-menu', 'lightning-button-icon-stateful',
        'lightning-button-group', 'lightning-button-stateful',
        'lightning-popup', 'lst-list-view-manager-pin-button',
        'lst-list-view-manager-settings-menu',
        'lst-list-view-manager-display-switcher', 'lst-list-view-picker',
        'lightning-layout', 'lightning-layout-item', 'lightning-card',
        'lightning-accordion', 'lightning-accordion-section',
        'lightning-tab', 'lightning-tabset', 'lightning-tree',
        'lightning-tree-grid', 'lightning-progress-indicator',
        'lightning-progress-step',
    }

    # 'internal' -- a shadow-wrapper duplicate of a control already classified
    # via its OUTER element (lightning-lookup-desktop under lightning-lookup;
    # lightning-grouped-combobox/lightning-base-combobox nested one inside the
    # other, or inside a lightning-lookup). 'structural' -- a non-control
    # wrapper (lightning-focus-trap) with no interaction surface of its own.
    # Both added 2026-09-07 alongside the parser-families fix so these never
    # surface as spurious duplicate elements OR as 'unknown'.
    SKIP_ELEMENT_TYPES = {'picklist_option', 'internal', 'structural'}

    # stream 2A 2026-09-09 (attack plan Phase 2A, essay C2-keyword-assignment.md): THE keyword
    # router, as data. `families` maps a DOM family to its fill / verify / actuate rungs (or a
    # stated `reason` when it has none); `metadataTypes` maps a DESCRIBE TYPE to the same slots
    # and WINS over the family whenever a caller supplies the field's metadata type -- CLAUDE.md's
    # "metadata routes the keyword, DOM is the backstop". Empty here on purpose: the whole table
    # is template data (`keywordRouting`), and a template that omits the key gets an empty router
    # (every element then carries a stated hint_reason rather than a silent blank). Read by
    # element_compiler._route_keywords; never a literal branch there.
    KEYWORD_ROUTING = {}

    # T12 2026-09-07: family->keyword mapping for element_types that had NO
    # qforce_hints branch at all (P1 scorecard cut 5 -- output_field 32/32,
    # datatable 29/29, custom_component 96/96 all hintless; radio 48/48 got a
    # plain click keyword as its FIRST hint despite ClickCheckbox's real
    # state-verifying read-back already existing). Per the 2026-09-07 standing
    # rule this is a TEMPLATE KEY ('familyKeywords' in the template JSON,
    # read via _TEMPLATE_KEYS below) -- these class attributes are only the
    # code-default fallback for a template that doesn't declare the key, the
    # same fallback contract every other _TEMPLATE_KEYS entry already uses
    # (see __init__ below: `if key in data`). element_compiler.py's
    # _hints_for_family reads this table; it is never hard-coded there.
    FAMILY_KEYWORDS = {
        'output_field': {
            'keyword': 'GetFieldValue',
            'call_template': 'get_field_value("{locator}")  # read-back; '
                              'verify_field("{locator}", "<expected>") to assert',
            'why': ("output_field is a read-only rendered value (lightning-formatted-*/"
                    "slds-form-element__static) -- qforce_lite.get_field_value / "
                    "qforce_lite.verify_field are the real read-back getters (GetFieldValue/"
                    "VerifyField), never a click/type keyword."),
            'caveats': ["Confirm this is the field's real label, not its currently displayed "
                        "value -- get_field_value resolves by label text, the same chain "
                        "TypeText uses."],
        },
        'datatable': {
            'keyword': 'Click Table Cell',
            'call_template': 'click_table_cell(row=<N>, col="<column label>")  # UseTable first',
            'why': ("lightning-datatable/lightning-tree-grid resolves by real row/col "
                    "coordinates (garzai_tables.robot: Click Table Cell / Get Table Cell "
                    "Where / Table Row Count) -- the same structural mechanism the in_grid "
                    "branch above already uses for individual cells; a table-LEVEL hint was "
                    "previously never offered at all."),
            'caveats': ["Anchor/UseTable the specific grid first if more than one renders on "
                        "the page."],
        },
        'radio': {
            'keyword': 'ClickCheckbox',
            'call_template': 'click_checkbox("{locator}", "on")',
            'why': ("qforce_lite.click_checkbox re-reads the input's checked property after "
                    "the click -- the same faux-span-safe, state-verifying mechanism already "
                    "proven for Lightning checkbox inputs, real for radio inputs too (both are "
                    "VALUE_CAPTURE_TYPES). P1 scorecard measured 48/48 radio controls "
                    "surfacing a plain click keyword (ClickText/ClickItem, no read-back) as "
                    "their FIRST hint before this branch existed."),
            'caveats': ["Omni/OmniStudio radio groups use the dedicated 'Omni Radio' keyword "
                        "instead (no label[for], value-attribute only) -- this hint is for a "
                        "plain Lightning/LEX radio input."],
        },
        # wave-2 review close, stream P1 2026-09-07 (finding F21, L2-R27 on
        # fsc7f-omnistudio/02-home-flexcard-loancalculator.html#31): the 'radio'
        # entry above states its OWN caveat that an Omni radio group is a
        # different control, and then routed one to ClickCheckbox anyway. The
        # variant is selected by FAMILY_VARIANTS below (template key
        # 'familyVariants') -- the omni marker is DATA, never a literal here.
        'omni_radio': {
            'keyword': 'Omni Radio',
            'call_template': 'omni_radio("<data-omni-key of the OmniScript field>", "{locator}")',
            'why': ("An OmniScript radio group has no label[for] -- qforce_lite.keywords_omni."
                    "omni_radio resolves the input by its VALUE attribute inside the omni host "
                    "and re-reads which values ended up checked (_confirm_readback), which is "
                    "the only mechanism proven for this shape. ClickCheckbox's faux-span "
                    "pattern is for a plain Lightning/LEX radio input, as its own caveat says."),
            'caveats': ["The first argument is the OmniScript field's data-omni-key, not the "
                        "visible label -- read it off the c-omni-* host, never guess it.",
                        "{locator} must be the radio's VALUE attribute; on this shape the "
                        "rendered label and the value coincide, which is not guaranteed."],
        },
        'tree': {
            'keyword': 'Click Tree Item',
            'call_template': 'click_tree_item("{locator}")  # expand=True for a group\'s '
                              'chevron instead of a leaf\'s own link',
            'why': ("Setup's navigation tree (role='tree'/li[role='treeitem'], the "
                    "onesetupNavTreeNode markup) blocked a Setup page in all 5 orgs "
                    "app_scan_report.py scanned (stream B7, 2026-09-07) -- no keyword ever "
                    "routed this family. tools/qforce-lite/keywords_tree.py's "
                    "click_tree_item() reads back aria-expanded/aria-selected through "
                    "confirm.py and raises rather than passing on a click that did not take."),
            'caveats': ["A LEAF item's own <a> navigates on click; a PARENT/group item's <a> "
                        "is href='javascript:void(0)' and only its sibling "
                        "button[title='Expand'] does anything -- pass expand=True for a "
                        "parent, never for a leaf (click_tree_item raises "
                        "TreeItemNotActionable if the two are mismatched)."],
        },
        # Console families (stream W8, 2026-09-07, all four VERIFIED-PASS live on
        # slockard's Sales Console -- docs/recorder/evidence/console-families-2026-09-07.md,
        # SHAPES-GUIDE.md section 8b). Same table T12 seeded; never a literal branch.
        'console-subtab': {
            'keyword': 'Open Console Subtab',
            'call_template': 'open_console_subtab("{locator}")',
            'why': "A Lightning CONSOLE workspace tab is a.tabHeader.slds-context-bar__label-action[role=tab][data-tabid] whose label lives in @title as '<Record Name> | <Object Label>'. keywords_console.open_console_subtab reads BOTH aria-selected on the re-queried tab AND the landed URL against the tab's own href -- a console tab can highlight while the content pane stays on the previous record, so aria-selected alone is a vacuous pass. ClickText is the discouraged fallback: it carries no read-back and the record name also renders in the header and in every split-view row.",
            'caveats': [
                'The tab strip carries wsTabBarHidden while only ONE workspace tab is open -- the <a role=tab> exists and is clickable but is not visible, so never gate this on visibility.',
            ],
        },
        'console-tertiary-tab': {
            'keyword': 'Open Tertiary Tab',
            'call_template': 'open_tertiary_tab("{locator}", record_id="<18-char id>", sobject="<Object>", relationship="<RelName>")  # URL-first',
            'why': "A tertiary tab inside a console subtab is the SAME element type as a workspace tab and differs only by class (slds-tabs_default__link vs slds-context-bar__label-action); the two strips are siblings under .oneConsoleTabset, so scoping by ancestry does not work. URL-first is preferred where the related tab has a direct URL (/lightning/r/<obj>/<id>/related/<rel>/view, CLAUDE.md's standing directive); the click form is the fallback.",
            'caveats': [
                'An ordinary record-page tabset link also carries slds-tabs_default__link but carries neither tabHeader nor data-tabid -- that pair is the discriminator.',
                "Navigating to the related URL from inside a console sometimes opens a SIBLING WORKSPACE tab rather than a tertiary one; open_tertiary_tab returns level='tertiary'|'workspace' and never equates the two.",
            ],
        },
        'utility-bar-item': {
            'keyword': 'Open Utility Item',
            'call_template': 'open_utility_item("{locator}")',
            'why': "The console utility-bar button's aria-label is the EMPTY STRING, so an aria-label locator finds nothing and an aria-label read-back compares '' to '' and passes vacuously. The visible label exists only in span.label.bBody, and keywords_console.open_utility_item reads state back through aria-expanded, then a .oneUtilityBarPanel with aria-hidden='false', then RAISES UtilityStateUnreadable (COULD-NOT-CHECK) rather than passing.",
            'caveats': [
                'An app can render the utility container with no items at all -- that is COULD-NOT-CHECK, not a locator bug.',
            ],
        },
        'split-view-row': {
            'keyword': 'Select Split View Row',
            'call_template': 'select_split_view_row("{locator}")',
            'why': "A console split-view row is li[role='row'].slds-split-view__list-item containing a.slds-split-view__list-item-action[data-recordid] -- NOT role='option', which matches ZERO elements on a real split view (measured). keywords_console.select_split_view_row proves the click by comparing that data-recordid with the id in the landed URL: 'a record opened' is not 'THIS record opened'.",
            'caveats': [
                "The selected-class half is tri-state: where the org renders neither slds-is-selected nor aria-selected on the row, the keyword reports selected_state='could-not-check' instead of assuming it.",
            ],
        },
    }

    # custom_component sub-table: real tag substring -> known Aura/LWC family
    # keyword (SHAPES-GUIDE.md). A tag matching none of these gets the
    # explicit COULD-NOT-CHECK hint in _hints_for_family -- the absence is
    # visible, never silent (tri-state rule, CLAUDE.md).
    CUSTOM_COMPONENT_TAG_KEYWORDS = {
        'lightning-datatable': FAMILY_KEYWORDS['datatable'],
        'lightning-tree-grid': FAMILY_KEYWORDS['datatable'],
        'lightning-input-address': {
            'keyword': 'Set Address',
            'call_template': 'set_address("{locator}", street="<street>", city="<city>", '
                              'state="<state>", zip="<zip>", country="<country>")',
            'why': "lightning-input-address is a compound control (one value, several "
                   "sub-inputs) -- keywords_compound.set_address is the proven route "
                   "(BACKLOG 61), never a plain TypeText into the container.",
            'caveats': [],
        },
        'lightning-input-name': {
            'keyword': 'Set Name',
            'call_template': 'set_name("{locator}", first="<first>", last="<last>")',
            'why': "lightning-input-name is a compound control -- keywords_compound.set_name "
                   "is the proven route (BACKLOG 61), never a plain TypeText into the container.",
            'caveats': [],
        },
        'lightning-quill': {
            'keyword': 'Type Text Clearing',
            'call_template': 'type_text_clearing("{locator}", "<value>")',
            'why': "lightning-quill's contenteditable is METADATA-KEYWORDS.md's richtextarea "
                   "row, routed to qforce_lite.type_text_clearing.",
            'caveats': ["Reads back .innerText off the contenteditable rather than a plain "
                        "input value."],
        },
    }

    SYSTEM_TEXT_BLACKLIST = [
        'Skip to', 'Sorry to interrupt', 'CSS Error', 'Reload Page',
        'dismissError', 'auraErrorReload', 'Skip to Navigation',
        'Skip to Main Content', 'Accessibility Mode', 'Loading...',
        'Please wait', 'Processing',
    ]

    CONTAINER_PATTERNS = [
        r'^c-.*-(builder|wizard|container|wrapper|layout|page|manager|configurator)$',
        r'^flexipage-',
        r'^lightning-(layout|card|accordion|tab|tabset)',
        r'^(div|section|article|main|aside|nav|header|footer|form)$',
    ]

    CONTAINER_CHILD_THRESHOLD = 3
    CONTAINER_TEXT_THRESHOLD = 200

    # Wildcard interactivity/table detection, ported from the separate
    # dom-parser.js engine (~/Desktop/crt-dom-scanner) after it caught real
    # gaps this project's own Python port had: any lightning-*/c-* tag is
    # presumptively worth surfacing (matches that engine's WILDCARD_TAG_RE),
    # and any real <table> or role=grid/treegrid container is a table --
    # full stop, no data-test-id/data-id gate required. The old gate meant a
    # classic Aura-rendered table with no data-test-id/data-id (e.g.
    # Salesforce Files' own list view) was silently invisible to this
    # parser entirely, confirmed live 2026-07-29.
    WILDCARD_INTERACTIVE_TAG_PREFIXES = ('lightning-', 'c-')
    GRID_ROLE_VALUES = {'grid', 'treegrid'}

    # interop T16 2026-09-07 -- see capture_orchestration._emit_grid_descendants.
    # A `lightning-tree-grid`'s descendants are swallowed so a data grid's cell text is
    # not reported twice (once as the container's compiled rows, once loose). T14
    # measured what that costs: 0 of 18 ground-truth controls in the Zoo tree grid --
    # no column header, no cell, no caret, no column-action button. These rules say
    # which descendants come back out and where each one's label comes from. Fallback
    # only; `gridDescendantEmission` in the template JSON is the source of truth.
    GRID_DESCENDANT_EMISSION = {
        'containerTags': ['lightning-tree-grid'],
        'rules': [
            # Real controls: compiled normally, so they keep their family and hints.
            {'compile': True, 'tags': ['button', 'a']},
            # A column header's accessible name is on the <th> itself.
            {'family': 'column_header', 'tags': ['th'], 'roles': ['columnheader'],
             'labelFrom': ['aria-label', 'title']},
            # A cell's value. A cell that RENDERS a link (phone, record link) already
            # yielded that link above -- emitting the cell too would report the same
            # control twice under its raw stored value, so those are skipped.
            {'family': 'table_cell', 'tags': ['th', 'td'], 'roles': ['rowheader', 'gridcell'],
             'labelFrom': ['data-cell-value', 'text'], 'skipIfDescendantTags': ['a']},
        ],
    }

    # Phase 1B, 2026-09-09 (C1-dom-extraction.md, ATTACK-PLAN-2026-09-09.md): a standard
    # Salesforce record-DETAIL page (Record Home) renders each READ-MODE field as
    #   <records-record-layout-item field-label="Ticket Number" ...>
    #     <div class="... test-id__output-root ...">
    #       <div class="test-id__field-label-container slds-form-element__label ...">
    #         <span class="test-id__field-label">Ticket Number</span></div>
    #       <div class="slds-form-element__control">
    #         <span class="test-id__field-value slds-form-element__static ...">(slotted value)</span>
    #       </div>
    #     </div>
    #     <button class="test-id__inline-edit-trigger ..." title="Edit Ticket Number">(pencil)</button>
    #   </records-record-layout-item>
    # `records-record-layout-item` is not a `lightning-*`/`c-*` tag and carried no rule at all, so
    # 18/12 slds-form-element__label on 02-account-record-page.html/05-custom-object-record-page.html
    # parsed to ZERO output_field elements (measured, docs/proposals/challenge-2026-09-08/
    # C1-dom-extraction.md) -- the recorder fell back to VerifyText, the symptom the user saw live.
    # Read generically by component_classifier._record_layout_field_family: a container tag listed
    # here becomes `family` ONLY when one of its descendants carries a class matching
    # `readModeMarkerClassFragments` (the read-mode signal) -- an edit-mode field (no such marker,
    # e.g. a `<lightning-input-field>` inside the same container tag on a New/Edit form) is left
    # alone; its own real editable control is a separate tag, classified on its own pass either way.
    # Template key `recordLayoutFieldRules`.
    RECORD_LAYOUT_FIELD_RULES = {
        'containerTags': ['records-record-layout-item'],
        'readModeMarkerClassFragments': ['test-id__output-root'],
        'family': 'output_field',
    }

    # 2026-09-10 (user, Zoo_Nightmare_Inputs 'Entitled Services'): a control recognised by its
    # STRUCTURE, not its tag -- a container whose class carries a fragment and which holds at least
    # N descendants of a role (the SLDS dueling list: div.slds-dueling-list with two role=listbox).
    # Template key `structuralContainerRules`; read by capture_orchestration's candidate pass and
    # component_classifier._structural_container_family. Empty here: the default template carries it.
    STRUCTURAL_CONTAINER_RULES = []

    # 2026-09-10 (user, Zoo_Nightmare_Inputs): the SLDS form element's label sits in a sibling
    # label-wrapper with no for= -- neither an ancestor nor a descendant of the control, so no other
    # rung reads it and 26 of 26 controls on that page parsed unlabelled. Template key
    # `formElementLabel` (containerClassFragment, labelClassFragments, exclusions, climb); empty
    # here: the rung is inert until a template declares the shape.
    FORM_ELEMENT_LABEL = {}

    # 2026-09-10: every label rung truncates at this length (template `labelMaxLen`); the inner_text
    # rung used to REJECT anything over 60 characters outright (no label, no call).
    LABEL_MAX_LEN = 100

    # 2026-09-11: a label VALUE a rung must never accept (template `labelValueRejectPatterns`): a JS object the
    # framework stringified into an attribute (`data-cell-value="[object Object]"`, 22 cells on the health90
    # Contract page) is not a name; the rung falls through to the next source.
    LABEL_VALUE_REJECT_PATTERNS = [r"^\[object \w+\]$"]

    # 2026-09-10: HTML boolean attributes kept as state ('true'), never a locator (template booleanStateAttributes)
    BOOLEAN_STATE_ATTRIBUTES = ["disabled", "readonly", "checked", "required", "hidden"]

    # ---------------------------------------------------------------- labels --
    # 2026-09-07 (interop T10): the label policy used to be three hard-coded
    # literals inside DomElementCompiler. The standing rule from the user is
    # that the parser is platform-agnostic and SCHEMA-DRIVEN -- every
    # platform-specific rule lives in the template JSON and the parser READS
    # it. These four are the fallback only when a template lacks the key.
    #
    # LABEL_PRECEDENCE is the order the label_text winner is chosen in. The
    # names are the `label_source` values DomElementCompiler emits; an unknown
    # name in a template is ignored (forward-compatible), and a name omitted
    # from a template's list is never consulted at all.
    # wave-2 review close, stream P1 2026-09-07 (findings F6 + R12 + F11).
    # `inner_text` moved from LAST to FIRST. The user's rule: THE LABEL IS
    # WHAT A PERSON SEES -- a title tooltip or an ARIA accessible name is a
    # label only when nothing visible labels the control. Measured before the
    # move: 110 elements across the 144-capture corpus carried a title_attr
    # label while their OWN rendered_text said something different ('View All'
    # under the tooltip "Show all past activities in a new tab", 'EPT' over the
    # visible '1.93s', the setup 'Home' tab, a 'Learn more' link), and
    # aria_label 'Search' beat the visible 'Search...' (L2-R12).
    # `inner_text` only PRODUCES a value for button/a/role=button, so every
    # form control's aria_label/standard_label ordering is untouched, and an
    # icon-only control (no visible text) still falls through to title_attr --
    # pinned by permsets-cof.html#99 in the P1 test.
    # `assistive_text` is the new LAST rung: an slds-assistive-text /
    # sr-only span is not visible, so it can never be the label, but on a
    # chevron-only button it is the only handle there is -- kept, with a
    # label_source that says what it is (F11, L2-R08/L2-R13).
    LABEL_PRECEDENCE = [
        'inner_text',
        'aria_label',
        'standard_label',
        'aria_labelledby',
        'form_element_label',   # 2026-09-11: parity with the template (the rung landed 2026-09-10; a template lacking the key must behave like the template)
        'placeholder',
        'title_attr',
        'sibling_label_text',
        'label_span',
        'assistive_text',
    ]

    # wave-2 review close, stream P1 2026-09-07 (finding F21). A family whose
    # control shape has a recognisable VARIANT routes to that variant's entry
    # in FAMILY_KEYWORDS instead of the family default. Each rule:
    #   family      -- the element_type the parser classified
    #   variant     -- the FAMILY_KEYWORDS key to use instead
    #   whenIdentificationMatches -- {field: regex} over `identification`
    #   whenContextKeys           -- context keys whose presence marks the variant
    #   match       -- 'any' (default) or 'all' across the two conditions above
    # Template key 'familyVariants'. The omni marker lives HERE, as data --
    # never as an `if name.startswith('omni-radio')` in element_compiler.py.
    FAMILY_VARIANTS = [
        {
            'family': 'radio',
            'variant': 'omni_radio',
            'whenIdentificationMatches': {'name': r'^omni-radio-\d+$'},
            'whenContextKeys': ['omni_step'],
            'match': 'any',
        },
    ]

    # wave-2 review close, stream P1 2026-09-07 (finding F11). Class fragments
    # that mark an element as SCREEN-READER-ONLY -- rendered into the DOM,
    # never seen by a person. Text inside one of these is stripped out of every
    # visible-label candidate and is only offered by the `assistive_text` rung
    # of LABEL_PRECEDENCE, last, with its own label_source. This was a literal
    # tuple on DomElementCompiler (used by _visible_rendered_text alone), which
    # is why 'inner_text' happily concatenated 'Show more navigation items'
    # onto the visible '* More'. Template key 'assistiveTextClassFragments'.
    ASSISTIVE_TEXT_CLASS_FRAGMENTS = [
        'slds-assistive-text',
        'sr-only',
        'visually-hidden',
        'slds-hidden',
    ]

    # wave-2 review close, stream P1 2026-09-07. Roles whose own rendered text is
    # the control's VALUE rather than its NAME, so the `inner_text` rung must
    # never claim them: a Lightning picklist is
    # <button role="combobox" aria-label="Industry">--None--</button>, and
    # letting visible text win there labelled the field '--None--'. Template key
    # 'innerTextExcludedRoles'.
    INNER_TEXT_EXCLUDED_ROLES = [
        'combobox', 'listbox', 'textbox', 'searchbox', 'spinbutton', 'slider', 'option',
    ]

    # wave-2 review close, stream P1 2026-09-07 (F11, L2-R08). A caveat appended
    # to every hint whose locator IS the label, keyed by which rung produced
    # that label. Template key 'labelSourceCaveats'.
    LABEL_SOURCE_CAVEATS = {
        'assistive_text': (
            "This label came from SCREEN-READER-ONLY markup (an slds-assistive-text / sr-only "
            "span) -- nothing on this control is visible to a sighted person, so a "
            "rendered-text search may not find it. Confirm the click landed (read-back or the "
            "optical witness) before trusting this step."
        ),
    }

    # interop T17 2026-09-07 (finding: "the clicked item does not align with
    # what is displayed" -- caret record 06-setup-permission-sets.html,
    # 41 <button title="Expand"> matches, label_source title_attr). A label
    # that came from title_attr/aria_label is an ACCESSIBLE NAME, not
    # rendered text -- ClickText is a rendered-text search and is the wrong
    # FIRST rung for it. ClickItem (attribute-value match, real QWeb
    # click_item) is the right first rung whenever the label string is not
    # also present in the element's own rendered text. Keyed by
    # `label_source`; a source not listed here keeps the default rung order
    # produced by _get_qforce_hints (ClickText/family hints first, ClickItem
    # attribute hint appended after). Template key 'hintOrderByLabelSource',
    # read via _TEMPLATE_KEYS below -- this class dict is only the
    # code-default fallback for a template that omits the key.
    HINT_ORDER_BY_LABEL_SOURCE = {
        'title_attr': ['ClickItem', 'ClickText'],
        'aria_label': ['ClickItem', 'ClickText'],
    }

    # interop T17 2026-09-07 (Save/"Save & New" finding, coordinator mid-task
    # correction): real QWeb click_text defaults to substring matching
    # (partial_match=True) -- a ClickText hint whose locator is a text-prefix
    # of another rendered label on the same page (e.g. "Save" vs "Save & New")
    # gets `partial_match=False` pinned into its call_example, per
    # DomElementCompiler._annotate_click_text_prefix_collisions. Template key
    # 'clickTextExactWhenPrefixOf'; True is the default and only documented
    # value (False turns the pass off entirely, never used to weaken it).
    CLICK_TEXT_EXACT_WHEN_PREFIX_OF = True

    # wave-2 close, stream P3 2026-09-07 (F20; L2-R24 on
    # docs/dom-captures/web-ant-design/3-transfer-idle.html#55). Which
    # `identification` keys the prefix-collision pass above compares a
    # ClickText locator against. It was hard-wired to `label_text` -- the
    # labels of parsed CONTROLS -- so ClickText('Select') shipped bare while
    # the page visibly rendered 'Select a group of items' / 'Selected items'
    # (page text, not control labels). QWeb's substring matcher does not care
    # which of the two a string came from. `title_attr` is deliberately absent
    # from the default: a tooltip is not rendered text, and matching against it
    # would pin partial_match=False on collisions a person can never see.
    # Template key `clickTextCollisionSources`.
    CLICK_TEXT_COLLISION_SOURCES = ['label_text', 'rendered_text']

    # stream A3 2026-09-08 (user rule, relayed by the coordinator mid-task):
    # `partial_match=False` was pinned ONLY on ClickText. But QWeb's default is
    # SUBSTRING matching for every text-resolving keyword, not just click_text
    # -- confirmed in the installed source: the `partial_match` kwarg is
    # documented on input_.py (TypeText), checkbox.py (ClickCheckbox),
    # dropdown.py (DropDown / PickList), element.py (ClickItem / ClickElement)
    # and text.py.  So on the Zoo pages `type_text("Name", ...)` also matches
    # "Name (secondary)", while the EXACT repeat counter says group_size 1 and
    # no anchor is emitted at all.
    #
    # `substringCollisions` fixes both halves: a locator that is a proper
    # substring of another rendered string on the same page counts as REPEATED
    # (so the anchor ladder runs and an anchor is emitted), and every keyword
    # in `partialMatchKeywords` additionally carries `partial_match=False`.
    # `sources` mirrors clickTextCollisionSources; the page's visible text
    # segments join the corpus whenever the caller hands over the soup.
    # Set enabled:false to restore the pre-A3 output byte for byte.
    SUBSTRING_COLLISIONS = {
        'enabled': True,
        'sources': ['label_text', 'rendered_text'],
        'minLen': 2,
        'partialMatchKeywords': [
            'TypeText', 'ClickCheckbox', 'PickList',
            'ComboBox', 'ClickItem', 'ClickText', 'ClickElement',
        ],
    }

    # wave-2 close, stream P3 2026-09-07 (R22; L2-R22 on
    # docs/dom-captures/slockard-zoo-v3/wave3/vf-form-tab.html#51). A shape
    # that RESOLVES but cannot ACT. `<a name="skiplink">` carries no href, no
    # role, no tabindex and no onclick -- a classic named-anchor skip target
    # whose only child is a 1x1px spacer img. ClickItem('skiplink', tag='a')
    # found it, uniquely, and offered it with no caveat; clicking it produces
    # no navigation and no UI effect. Every click rung on a node matching one
    # of these rules is withheld (DomElementCompiler._is_non_actionable).
    #
    # A rule fires when the tag matches AND every `absentAttributes` entry is
    # absent AND every `requiredAttributes` entry is present. Keep rules
    # NARROW: withholding a hint from a real control is the worse error, so a
    # single actionability signal (href/role/tabindex/onclick) is enough to
    # spare the node. Measured over the frozen 112-capture corpus: 11 click
    # hints withheld, all on bare named anchors (docs/recorder/evidence/
    # wave2-close-P3-2026-09-07.md). Template key `nonActionableRules`; an
    # empty list disables the pass.
    NON_ACTIONABLE_RULES = [
        {
            '_why': 'bare named anchor (<a name="skiplink">) -- a skip target, not a link',
            'tags': ['a'],
            'requiredAttributes': ['name'],
            'absentAttributes': ['href', 'role', 'tabindex', 'onclick'],
        },
        {
            '_why': ('Phase 1B 2026-09-09: records-record-layout-item is the field CONTAINER on a '
                      'record-detail page -- its value/label are read by GetFieldValue/VerifyField, '
                      'never a click. The real click target beside it (the inline-edit pencil, '
                      'test-id__inline-edit-trigger) is already its own separate button element with '
                      'its own title="Edit <Field>" label -- this rule only withholds a Click* hint '
                      'the container itself would otherwise pick up via its stable field-label '
                      'attribute, so the pencil is never confused for the field\'s own click target.'),
            'tags': ['records-record-layout-item'],
        },
    ]

    LABEL_CLASS_FRAGMENTS = [
        'slds-form-element__label',
        'slds-radio__label',
        'slds-checkbox__label',
    ]

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

    # Decorations glued into a label's textContent that a sighted user does not
    # read -- the SLDS required marker above all. Each entry is a dict of
    # attributes matched with BeautifulSoup's find_all(attrs=...).
    REQUIRED_MARKER_SELECTORS = [
        {'aria-hidden': 'true'},
    ]

    def _is_any_table(self, tag) -> bool:
        if not tag or not hasattr(tag, 'name') or not tag.name:
            return False
        if tag.name.lower() == 'table':
            return True
        return (tag.get('role') or '').lower() in self.GRID_ROLE_VALUES

    def _in_grid_container(self, tag) -> bool:
        """Wildcard containment check -- is this element anywhere inside
        ANY table/grid, regardless of which specific component renders it.
        Mirrors dom-parser.js's `el.closest('table, [role="grid"],
        [role="treegrid"]')` in one shot instead of maintaining separate
        lightning-datatable-descendant and native-table-descendant sets."""
        if not tag:
            return False
        return tag.find_parent(self._is_any_table) is not None

    # F2 (2026-09-05): these two lists used to live as local variables inside
    # capture_orchestration.py's parse_elements_from_html -- moved onto
    # DomConfiguration so they are template-driven like everything else here.
    # Values below are EXACTLY what capture_orchestration.py hard-coded
    # before this move (verbatim), so v1/byte-equivalence is unaffected.
    TARGET_TAGS = [
        "button", "a", "input", "select", "textarea",
        "lightning-button", "lightning-button-icon", "lightning-button-menu",
        "lightning-input", "lightning-combobox", "lightning-dual-listbox",
        "lightning-checkbox", "lightning-checkbox-group", "lightning-radio-group",
        "lightning-slider", "lightning-toggle", "lightning-textarea",
        "lightning-pill", "lightning-badge",
        "lightning-record-edit-form", "lightning-record-view-form",
        "lightning-input-field", "lightning-output-field",
        "c-omniscript", "c-omni-input", "c-omni-select", "c-omni-button",
        # 2026-09-07 iframe descent (docs/recorder/COPADO-GAPS-2026-09-07.md
        # "Iframe / canvas / Visualforce boundaries", REVIEW-BRIEF-NEXT.md
        # row C4c): the <iframe> tag itself is a real, classifiable control
        # (family 'iframe', see component_classifier.py) so a consumer knows
        # a frame boundary exists here even before descending into it. The
        # elements INSIDE a same-app cross-origin frame are a separate
        # concern -- see iframe_descent.py -- this only adds the shell tag.
        "iframe",
        # Phase 1B 2026-09-09: the record-DETAIL field container (see
        # RECORD_LAYOUT_FIELD_RULES above). Only the read-mode ones (a
        # test-id__output-root descendant) actually classify as a real
        # element_type ('output_field'); every other records-record-layout-item
        # classifies 'structural' (component_classifier._record_layout_field_family)
        # and is dropped by SKIP_ELEMENT_TYPES exactly as before this addition.
        "records-record-layout-item",
    ]

    INTERACTIVE_ROLES = [
        "button", "link", "checkbox", "radio", "tab", "menuitem", "option",
        "switch", "textbox", "gridcell", "columnheader", "rowheader", "combobox",
    ]
    # NOTE (B8 2026-09-07): 'treeitem' is DELIBERATELY NOT in this default list -- v2's own
    # measurement (salesforce-lightning.v2.json's note_targetTagsAndInteractiveRoles) already
    # tried it and rejected it: "+56 <li role=treeitem> elements on setup-permission-sets.html
    # for only +4 net kept ... most Setup nav-tree items were already reachable by text match".
    # component_classifier.py's new role=='treeitem' -> 'tree' branch and this file's
    # FAMILY_KEYWORDS['tree'] entry are both still added below -- they are DORMANT under the
    # default template (no noise added) and become live the moment a template's own
    # `interactiveRoles` opts 'treeitem' in, which is the correct place to re-run that
    # noise-vs-recall measurement, not this class default.

    # interop T20 2026-09-07 (user finding). The runtime-garbage test existed
    # ONLY for `id` (j_id..., input-142). Every OTHER attribute the hint ladder
    # may cite bypassed it, so the ClickItem rung offered
    # `click_item("lgt-datatable-1-options-1", tag="input")` as "a stable
    # attribute value (name)" -- a counter-shaped generated NAME that renumbers
    # with the datatable instance. The rule is attribute-agnostic: a
    # counter/uid-shaped VALUE is runtime garbage wherever it appears, so the
    # patterns live here once and every citing site asks the same question.
    # Template key `dynamicValuePatterns`; these class attributes are only the
    # code-default fallback for a template that omits the key.
    #
    # FALSE-POSITIVE CONTRACT (measured, docs/recorder/evidence/
    # interop-T20-2026-09-07.md): the counter pattern is all-lowercase,
    # hyphen-segmented, digit-terminated, so real Salesforce API names
    # (`Zoo_Text__c`, `AccountId`, `Name`) and real author-chosen names
    # (`street`, `search-input`) do NOT match. Widen it only with a fresh
    # corpus false-positive count.
    DYNAMIC_VALUE_ATTRIBUTES = [
        'id', 'name', 'for', 'aria-controls', 'aria-labelledby',
        'data-target-selection-name', 'field-label', 'data-label', 'data-value',
    ]
    DYNAMIC_VALUE_PREFIXES = [
        'help-message-', 'error-message-',
        'label-', 'listbox-', 'dropdown-element-', 'tooltip-',
        'slds-combobox-', 'slds-listbox-',
    ]
    DYNAMIC_VALUE_PATTERNS = [
        r'^\d+:\d+;[a-z]$',                        # Aura render id (5:0;a)
        r'(^|:)j_id\d+(:|$)',                      # Visualforce view-tree auto id
        r'^[a-z][a-z0-9]*(-[a-z0-9]+)*-\d+$',      # counter/uid (input-142, lgt-datatable-1-options-1)
        r'^check-button-label-\d+(-\d+)*$',        # LDS datatable per-row label ids
        # wave-2 close, stream P3 2026-09-07 (F9; L2-R27 on fsc7f-omnistudio/
        # 03-applicationform-omniscript-postintake.html#10, L2-R05b, L2-R18 on
        # customer-cpq/qle-editlines-cof.html#33). Two generated SHAPES the
        # counter pattern above cannot match, both measured being offered as
        # PRIMARY locators: a 32-hex token (`data-target-selection-name=
        # "181c7013df09423d8f755b49c067f6f3"` on the App Launcher button, whose
        # own title="App Launcher" sat unused) and an epoch-suffixed name
        # (`vfFrameId_1788626362477`, a per-render Visualforce frame name,
        # offered as a confirmed-unique anchor -- a tier retired by D14,
        # 2026-09-09).
        # FALSE-POSITIVE CONTRACT, same as the counter pattern's: the hex rule
        # is 32 chars of LOWERCASE hex exactly -- a real API name is never that
        # (it needs an uppercase letter, an underscore, or a length other than
        # 32); the epoch rule needs an underscore followed by 10+ digits, which
        # `Zoo_Text__c` / `Account_Number__c` / `SaveEdit` do not have.
        # Measured over the frozen 112-capture corpus: 88 hex + 21 vfFrameId_
        # offenders before, 0 after, and 0 real names lost (see
        # docs/recorder/evidence/wave2-close-P3-2026-09-07.md).
        r'^[0-9a-f]{32}$',                         # 32-hex generated token
        r'^[A-Za-z][A-Za-z0-9]*_\d{10,}$',         # epoch-suffixed name (vfFrameId_1788626362477)
    ]

    # interop T20 2026-09-07 (user rule). EVERY control inside a row / card /
    # fieldset carries its container's anchor by DEFAULT -- not only when
    # identical duplicates are detected. Before this, `disambiguation` was
    # stamped only on repeated same-label groups, so the per-row Select
    # checkboxes on a list view (labels "Select Item 1".."Select Item N", all
    # distinct) got no anchor at all and the only row-specific string on offer
    # was the generated `name`. Each scope declares how its container node is
    # recognised and, in order, where its anchor text comes from.
    CONTAINER_ANCHORS = {
        'enabled': True,
        # stream 1C 2026-09-08 (D4 narrowed): a control whose label is unique
        # on the page (group_size == 1) gets no anchor candidates at all --
        # see element_compiler.py's `_anchor_candidates`. Measured over the
        # 144-capture corpus: 8,323 anchors sat on an already-unique control,
        # pure cost. Set false to restore the pre-1C "anchor every control"
        # behaviour byte for byte.
        'onlyWhenRepeated': True,
        'maxAncestorDepth': 12,
        'anchorMinLen': 2,
        'anchorMaxLen': 60,
        'scopes': [
            {
                'scope': 'row',
                'tags': ['tr'],
                'roles': ['row'],
                # A row's anchor is the unique cell in that row: the Name /
                # first data-label cell whose text is unique across the
                # table's rows, then a link, then any cell.
                'anchorPreference': [
                    'data_label_cell', 'link_text', 'header_cell', 'cell_text',
                ],
                'dataLabelPreference': [
                    'Name', 'Account Name', 'Contact Name', 'Title', 'Subject',
                    'Case Number', 'Opportunity Name', 'Full Name', 'Label',
                ],
            },
            {
                'scope': 'card',
                'tags': ['article'],
                'classFragments': ['slds-card'],
                'anchorPreference': ['heading'],
            },
            {
                'scope': 'fieldset',
                'tags': ['fieldset'],
                'anchorPreference': ['legend'],
            },
        ],
        # Which hint keywords take an `anchor=` argument. ClickTableCell is
        # listed because it already received one under the pre-T20 repeated-
        # group path; a keyword absent here is left byte-identical.
        # wave-2 F14 (2026-09-07): TypeText added -- read from the installed
        # QWeb source, not assumed: QWeb/keywords/input_.py:157-160 is
        # `type_text(locator, input_text, anchor: str = "1", ...)`. Without it
        # a record could carry a CONFIRMED-UNIQUE anchor and still emit a bare
        # `type_text("Zoo Time", "<value>")` downgraded to
        # ambiguous and unresolved (vf-form-tab.html#37) -- the hint ignoring the
        # record's own found anchor.
        # A1 2026-09-08: the four keywords below were the whole remaining F14
        # residue (92 records: Aura Lookup 41, ComboBox 36, GetFieldValue 14,
        # set_datetime 1). Each now really takes `anchor` -- read from the
        # callable, not assumed: `combo_box(locator, value, ..., anchor="1")`
        # already did (ComboBox and Aura Lookup both route to it,
        # tools/recorder/library/index.json), and
        # `qforce_lite.set_datetime(label, value, timeout, fail_fast_ms, anchor)`
        # / `get_field_value(label, index, tag, timeout, anchor)` gained one in
        # the same commit as this line. The wave-2 note that set_datetime was
        # NOT anchorable is superseded by that signature change, not ignored.
        'anchoredKeywords': [
            'ClickItem', 'ClickText', 'ClickCheckbox', 'Click Table Cell',
            'TypeText',
            'ComboBox', 'Aura Lookup', 'GetFieldValue', 'Set Datetime',
        ],

    }

    DROPDOWN_SIGNATURES = [
        {
            'tags': ['lightning-combobox', 'lightning-dual-listbox', 'lightning-picklist'],
            'type': 'lightning_combobox',
            'dynamic': True,
        },
        {
            'tags': ['lightning-input'],
            'attributes': {'type': 'combobox'},
            'type': 'lightning_input_combobox',
            'dynamic': True,
        },
        {
            'tags': ['select'],
            'type': 'html_select',
            'dynamic': False,
        },
        {
            'tags': ['select'],
            'attributes': {'class': lambda c: c and 'uiInput' in c},
            'type': 'aura_select',
            'dynamic': False,
        },
        {
            'tags': ['lightning-input-field'],
            'attributes': {'data-field-type': 'Picklist'},
            'type': 'lightning_record_picklist',
            'dynamic': True,
        },
        {
            'tags': lambda t: t and t.startswith('c-'),
            'attributes': {'role': 'combobox'},
            'type': 'custom_lwc_combobox',
            'dynamic': True,
        },
        {
            'tags': ['div', 'button'],
            'attributes': {'role': 'combobox', 'aria-haspopup': 'listbox'},
            'type': 'slds_combobox',
            'dynamic': True,
        },
        {
            'tags': ['select'],
            'attributes': {'id': lambda i: i and ('j_id' in i or ':' in i)},
            'type': 'visualforce_select',
            'dynamic': False,
        },
        {
            'tags': ['select', 'div'],
            'attributes': {'class': lambda c: c and ('sbqq' in c.lower() or 'sb-' in c.lower())},
            'type': 'cpq_dropdown',
            'dynamic': True,
        },
        {
            'tags': lambda t: t and t.startswith('c-omni'),
            'attributes': {'role': lambda r: r in ['combobox', 'listbox']},
            'type': 'omnistudio_dropdown',
            'dynamic': True,
        },
    ]

    # Row-level interactive controls inside a table row (lightning-datatable/
    # lightning-tree-grid), same declarative shape as DROPDOWN_SIGNATURES so
    # new control types (once confirmed live, e.g. a row-actions button) get
    # added as data here, not new Python branches. Added 2026-07-26 after
    # confirming live that a row-selection checkbox exists in the real
    # captured HTML but was invisible in the structured JSON output -- not a
    # Shadow DOM issue, a parser completeness gap (see element_compiler.py's
    # lightning-datatable row extraction, which only ever captured column-
    # mapped cell text, never row-level controls like this one).
    ROW_CONTROL_SIGNATURES = [
        {
            'role': 'row_checkbox',
            'tags': ['input'],
            'attributes': {'type': 'checkbox'},
        },
        {
            'role': 'row_radio',
            'tags': ['input'],
            'attributes': {'type': 'radio'},
        },
    ]

    # (attr on this class, key in the template JSON, caster) -- only the
    # plain-data constants. DROPDOWN_SIGNATURES / ROW_CONTROL_SIGNATURES
    # contain Python lambdas and are never template-driven (see the note
    # in docs/recorder/templates/salesforce-lightning.json).
    _TEMPLATE_KEYS = (
        ("NOISE_TAGS", "noiseTags", set),
        ("NOISE_TAG_PATTERNS", "noiseTagPatterns", list),
        ("NOISE_ROLES", "noiseRoles", set),
        ("NOISE_CLASS_FRAGMENTS", "noiseClassFragments", list),
        ("SHADOW_WRAPPER_TAGS", "shadowWrapperTags", set),
        ("SKIP_ELEMENT_TYPES", "skipElementTypes", set),
        ("SYSTEM_TEXT_BLACKLIST", "systemTextBlacklist", list),
        ("CONTAINER_PATTERNS", "containerPatterns", list),
        ("CONTAINER_CHILD_THRESHOLD", "containerChildThreshold", int),
        ("CONTAINER_TEXT_THRESHOLD", "containerTextThreshold", int),
        ("WILDCARD_INTERACTIVE_TAG_PREFIXES", "wildcardInteractiveTagPrefixes", tuple),
        ("GRID_ROLE_VALUES", "gridRoleValues", set),
        # interop T16 2026-09-07 -- tree-grid descendant emission, template-driven.
        ("GRID_DESCENDANT_EMISSION", "gridDescendantEmission", dict),
        # Phase 1B 2026-09-09 -- read-mode record-detail field classification, template-driven.
        ("RECORD_LAYOUT_FIELD_RULES", "recordLayoutFieldRules", dict),
        # 2026-09-10 -- structural (class + descendant-role) container families, template-driven.
        ("STRUCTURAL_CONTAINER_RULES", "structuralContainerRules", list),
        # 2026-09-10 -- the SLDS form-element label (label-wrapper + control, no for=), template-driven.
        ("FORM_ELEMENT_LABEL", "formElementLabel", dict),
        ("TARGET_TAGS", "targetTags", list),
        ("INTERACTIVE_ROLES", "interactiveRoles", list),
        # T12 2026-09-07 -- see FAMILY_KEYWORDS/CUSTOM_COMPONENT_TAG_KEYWORDS
        # above. dict is a new caster (every prior key was set/list/int/
        # tuple); dict(x) on an already-dict template value is a no-op copy,
        # same shape contract the others already have.
        ("FAMILY_KEYWORDS", "familyKeywords", dict),
        ("CUSTOM_COMPONENT_TAG_KEYWORDS", "customComponentTagKeywords", dict),
        # stream 2A 2026-09-09 -- THE keyword router as data. See KEYWORD_ROUTING above.
        ("KEYWORD_ROUTING", "keywordRouting", dict),
        # interop T17 2026-09-07 -- per-label-source hint rung order, template-driven.
        ("HINT_ORDER_BY_LABEL_SOURCE", "hintOrderByLabelSource", dict),
        ("CLICK_TEXT_EXACT_WHEN_PREFIX_OF", "clickTextExactWhenPrefixOf", bool),
        # wave-2 close, stream P3 2026-09-07 -- F20, see the class attribute.
        ("CLICK_TEXT_COLLISION_SOURCES", "clickTextCollisionSources", list),
        # stream A3 2026-09-08 -- substring collisions for EVERY text keyword.
        ("SUBSTRING_COLLISIONS", "substringCollisions", dict),
        # wave-2 close, stream P3 2026-09-07 -- R22, see the class attribute.
        ("NON_ACTIONABLE_RULES", "nonActionableRules", list),
        # interop T10 2026-09-07 -- the label policy layer, template-driven.
        ("LABEL_PRECEDENCE", "labelPrecedence", list),
        # 2026-09-10 -- the one label length; the inner_text rung's literal 60 dropped long link labels.
        ("LABEL_MAX_LEN", "labelMaxLen", int),
        ("LABEL_VALUE_REJECT_PATTERNS", "labelValueRejectPatterns", list),
        ("BOOLEAN_STATE_ATTRIBUTES", "booleanStateAttributes", list),
        # wave-2 review close, stream P1 2026-09-07 -- F11/F21, both data.
        ("ASSISTIVE_TEXT_CLASS_FRAGMENTS", "assistiveTextClassFragments", list),
        ("LABEL_SOURCE_CAVEATS", "labelSourceCaveats", dict),
        ("INNER_TEXT_EXCLUDED_ROLES", "innerTextExcludedRoles", list),
        ("FAMILY_VARIANTS", "familyVariants", list),
        ("LABEL_CLASS_FRAGMENTS", "labelClassFragments", list),
        ("DESCRIPTION_CLASS_FRAGMENTS", "descriptionClassFragments", list),
        ("REQUIRED_MARKER_SELECTORS", "requiredMarkerSelectors", list),
        # interop T20 2026-09-07 -- generated-value detection + container
        # anchors, both template-driven. `dynamicValuePatterns` is a dict
        # holding attributes/prefixes/patterns; it is unpacked by
        # `_apply_dynamic_value_template` below rather than by a caster,
        # because it fans out into three class attributes.
        ("CONTAINER_ANCHORS", "containerAnchors", dict),
    )

    def __init__(self, template=None, template_path=None, use_default_template=True,
                 html=None):
        """Data-driven per docs/recorder/PLAN.md's capture-templates section.

        Zero-arg construction (`DomConfiguration()`) keeps today's exact
        v1 behavior: `template` and `template_path` are both None, so the
        default template name is resolved as
        `template` param -> `GARZAI_DOM_TEMPLATE` env var -> "salesforce-lightning"
        (v1, DEFAULT_TEMPLATE_NAME) and loaded from
        docs/recorder/templates/<name>.json. If that file is missing,
        unreadable, or malformed, every constant silently falls through to
        the hard-coded class attributes above -- identical to pre-refactor
        behavior. Byte-equivalence across every saved capture under
        docs/dom-captures/** (with v1, the default) is enforced by
        tools/recorder/tests/templates/test_byte_equivalence.py.

        Pass `template="salesforce-lightning.v2"` (or set
        `GARZAI_DOM_TEMPLATE=salesforce-lightning.v2` in the environment) to
        opt into v2's wider target-tag/interactive-role coverage -- see
        docs/recorder/TEMPLATES.md for what that changes downstream. The
        user has not flipped the env var default; v1 stays default until
        they do.

        `html` (T18 2026-09-07) turns on PER-PAGE selection: with no param and
        no env var, the page's own markup is matched against each candidate
        template's `frameworkMarkers` and the template that actually describes
        the page is loaded -- see `select_template` for the full precedence and
        `template_provenance(config)` for the block that says which fired.

        `template_path` (or `DomConfiguration.from_template(path)`) loads an
        exact file path directly, bypassing name resolution -- used for
        templates outside docs/recorder/templates/ (e.g. a freshly learned
        one passed straight from `template.py learn`'s --out path).
        """
        self.template_source = "hard-coded-fallback"
        path, selected_by, markers_seen = select_template(
            html=html, template=template, template_path=template_path,
            use_default_template=use_default_template)
        self.template_selected_by = selected_by
        self.template_markers_seen = markers_seen
        data = None
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                self.template_source = path
            except (OSError, ValueError, TypeError):
                data = None
        # A SUPERSEDED template is refused loudly, naming its successor -- a
        # silent fall-through to the class constants would be a different
        # parse reported as the same one (T18 2026-09-07).
        if isinstance(data, dict) and SUPERSEDED_KEY in data:
            raise SupersededTemplate(
                "%s is superseded by %s (since %s) and is no longer loadable -- "
                "pass that template instead" % (path, data[SUPERSEDED_KEY],
                                                data.get("date", "unknown date")))
        self.template_data = data
        if data is not None:
            for attr, key, caster in self._TEMPLATE_KEYS:
                if key in data:
                    setattr(self, attr, self._cast_template_value(
                        attr, key, caster, data))
            self._apply_dynamic_value_template(data.get("dynamicValuePatterns"))

    # A dict-valued template key is a REGISTRY (familyKeywords,
    # customComponentTagKeywords, hintOrderByLabelSource) or a settings BLOCK
    # (gridDescendantEmission, containerAnchors). Before 2026-09-07 a template
    # that declared one replaced the class default WHOLESALE, so a template
    # naming one family silently dropped the other seven and an author who
    # wanted to ADD a family had to restate every default (F2, L2-K09 on W8-4).
    # Dict keys now MERGE over the defaults at the TOP level -- a sub-key the
    # template declares wins entirely (no deep merge: a declared 'scopes' list
    # or one family's whole hint block replaces the default's, which is what an
    # author editing one entry means). A template that genuinely wants the old
    # wholesale replacement says so with `"<key>_replace": true`.
    TEMPLATE_REPLACE_SUFFIX = "_replace"

    def _cast_template_value(self, attr, key, caster, data):
        value = data[key]
        if caster is not dict or not isinstance(value, dict):
            return caster(value)
        if data.get(key + self.TEMPLATE_REPLACE_SUFFIX) is True:
            return dict(value)
        default = getattr(self.__class__, attr, None)
        if not isinstance(default, dict):
            return dict(value)
        merged = dict(default)
        merged.update(value)
        return merged

    def _apply_dynamic_value_template(self, block):
        """`dynamicValuePatterns` fans out into three class attributes, so it
        gets its own unpacker rather than a _TEMPLATE_KEYS caster. A key the
        template omits keeps the code default; an empty list is honoured (it
        DISABLES that half), which is how a template opts out deliberately."""
        if not isinstance(block, dict):
            return
        if isinstance(block.get("attributes"), list):
            self.DYNAMIC_VALUE_ATTRIBUTES = list(block["attributes"])
        if isinstance(block.get("prefixes"), list):
            self.DYNAMIC_VALUE_PREFIXES = list(block["prefixes"])
        if isinstance(block.get("patterns"), list):
            self.DYNAMIC_VALUE_PATTERNS = list(block["patterns"])

    @classmethod
    def from_template(cls, path):
        """Build a DomConfiguration from a specific template JSON file
        (docs/recorder/PLAN.md schema). Raises the same way `open`/`json.load`
        would if the path is bad -- callers that want a silent fallback
        should use the zero-arg constructor instead."""
        return cls(template_path=path)

    def _is_noise(self, tag) -> bool:
        if not tag or not hasattr(tag, 'name') or not tag.name:
            return True
        tag_name = tag.name.lower()
        role = (tag.get('role') or '').lower()
        classes = ' '.join(tag.get('class') or [])

        if tag_name in self.NOISE_TAGS:
            return True
        if any(re.match(pattern, tag_name) for pattern in self.NOISE_TAG_PATTERNS):
            return True
        if role in self.NOISE_ROLES:
            return True
        if any(f in classes for f in self.NOISE_CLASS_FRAGMENTS):
            return True
        return False

    def _is_shadow_wrapper(self, tag) -> bool:
        if not tag or not hasattr(tag, 'name') or not tag.name:
            return False
        return tag.name.lower() in self.SHADOW_WRAPPER_TAGS

    def _is_container_component(self, tag) -> bool:
        # 2026-09-10: a container the template declares a CONTROL by structure (structuralContainerRules,
        # e.g. the SLDS dueling list) is never dropped as a mere container.
        try:
            _cls = " ".join(tag.get("class") or []).lower()
            for _rule in (getattr(self, "STRUCTURAL_CONTAINER_RULES", None) or []):
                if any(f in _cls for f in (_rule.get("containerClassFragments") or [])):
                    return False
        except Exception:
            pass
        if not tag or not hasattr(tag, 'name'):
            return False
        tag_name = tag.name.lower()
        for pattern in self.CONTAINER_PATTERNS:
            if re.match(pattern, tag_name):
                if tag_name.startswith('c-'):
                    return self._validate_custom_container(tag)
                return True
        return False

    def _validate_custom_container(self, tag) -> bool:
        if not tag:
            return False
        interactive_children = tag.find_all([
            'button', 'input', 'select', 'textarea', 'a',
            'lightning-button', 'lightning-input', 'lightning-combobox',
        ])
        if len(interactive_children) >= self.CONTAINER_CHILD_THRESHOLD:
            return True
        text = tag.get_text(strip=True)
        if len(text) >= self.CONTAINER_TEXT_THRESHOLD:
            return True
        nested_custom = tag.find_all(lambda t: t.name and t.name.startswith('c-'))
        if len(nested_custom) >= 2:
            return True
        return False