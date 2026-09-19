#!/usr/bin/env python3
"""
Usage: python3 tools/qforce-lite/predict.py [-h] --sobject SOBJECT --org ORG [--surface {view,edit,create}] [--json] [--locators] [--source {describe,layout,page}] [--record-type-id RECORD_TYPE_ID] [--map MAP] [--allow-stale]
Deterministic metadata→keyword predictor for CRT Train mode.

Maps Salesforce field types to CRT keywords without touching the browser or page layout.
Predictions carry confidence levels:
  - 'certain': type→keyword is unambiguous, no DOM check needed
  - 'needs-dom-check': label may not match form, field may not be on layout, or picklist
                       may be record-type filtered

Usage:
    python3 predict.py --sobject Account --org dev2
    python3 predict.py --sobject Opportunity --org dev2 --json
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time

# P3 (org discovery, ORG-DISCOVERY-PLAN.md "Consumers read the map"): tools/qforce-lite/discovery/
# maplib.py is the ONE freshness/staleness resolver every map consumer shares -- see its docstring.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "discovery"))
import maplib  # noqa: E402

# BACKLOG row 70: chains.py is the ONE place the `reference` sub-kind table (OwnerId/CreatedById/
# LastModifiedById/RecordTypeId) lives -- see chains.REFERENCE_SUBKINDS. Safe to import at module
# scope: chains.py has no selenium/QWeb import at its own module level (those are lazy inside
# LiveBackend), so this does not drag a browser dependency into predict.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chains  # noqa: E402

# Layout-aware prediction (2026-08-30): fixes the measured 29.5% end-to-end gap
# documented in docs/crt-train/PREDICTABILITY.md. That gap was NOT a
# type-guessing problem -- control-type prediction is 100% correct (225/225)
# once a field renders. It is a POPULATION problem: describe_sobject() returns
# every createable field, but ~70% of those are not on the object's Create
# layout at all. predict_fields_layout_aware() below predicts only the fields
# the real Create layout says are present, using the UI API
# (GET .../ui-api/layout/<Object>?mode=Create) as the population source and
# describe_sobject() only for type info. See PREDICTABILITY-LAYOUT.md for the
# re-measurement this enabled.
UI_LAYOUT_CACHE_DIR = os.path.expanduser("~/.claude/state/ui-layout-cache")
UI_LAYOUT_TTL = 24 * 3600  # layouts change rarely; a day is cheap and safe
DEFAULT_API_VERSION = "60.0"

# Row 2 follow-up (2026-08-31): 38 of 66 layout-aware misses were
# CreatedDate/LastModifiedDate -- named on the UI API Create layout but
# absent from the rendered DOM entirely. RULE, derived from the data (see
# PREDICTABILITY-LAYOUT.md, dated section): across all 397 atoms in
# docs/crt-train/predictability-atoms-layout.jsonl, every CreatedDate/
# LastModifiedDate occurrence (39/39) has editable_for_new=False AND never
# renders (status is "miss"/"on_layout_but_not_rendered" or "page_blocked" --
# never "hit"). Checked for exceptions before generalizing, per project rule:
#   - editable_for_new=False alone is NOT the predicate -- CreatedById/
#     LastModifiedById (type=reference) carry the same flag and DO render,
#     as a read-only <div> (39/39 hits).
#   - type=="datetime" AND editable_for_new=False is NOT the predicate either
#     -- AI_Agent_Conversation__c's Newest_Message_Date__c and
#     Conversation_Start__c are both datetime, editable_for_new=False, and
#     BOTH render (hits).
# The only predicate with zero counter-examples across all 397 atoms is the
# two field names themselves.
LAYOUT_NEVER_RENDERED_FIELDS = frozenset({"CreatedDate", "LastModifiedDate"})

# Row 5 follow-up (UI-CASES-LOCAL.md §4 diff #1, 2026-09-01): predict.py
# --source layout was measured marking autonumber/system Name fields
# (PSBulkActionConfig__c.Name, SDO_SCOM_OOA_Commerce_Approval_Requests__c.Name,
# SDO_SCOM_OOA_Commerce_User_Requests__c.Name, Salesforce_Rewind_History_Record__c.Name,
# SDO_SFS_Vehicle_Inspection__c.Name, AI_Agent_Conversation__c.Name)
# `confidence: "certain"`, `keyword: "type_text_clearing"` even though the
# Create form never actually accepts a typed value there -- Salesforce
# assigns the value itself (e.g. 'CARN-0002'), so a generated sample never
# lands and a downstream save-record read-back sees a Name mismatch. Two
# describe signals, checked independently since neither alone was reliable
# across the 6 objects above: describe's own `autoNumber=True`, OR
# `nameField=True` combined with the LAYOUT's own `editableForNew=False`
# (a genuinely editable Name field -- Account.Name, CGC_Program__c.Name --
# always has editable_for_new=True on the real Create layout; checked as a
# counter-example before generalizing, per project rule).
def _is_autonumber_name_field(item: dict, field: dict | None) -> bool:
    if field is None:
        return False
    if field.get("autoNumber"):
        return True
    if field.get("nameField") and not item.get("editable_for_new"):
        return True
    return False


def _is_autonumber_name_field_from_map(item: dict, field: dict | None) -> bool:
    """Same predicate as _is_autonumber_name_field(), sourced from the map's field dict
    (discover.py build_inventory's `auto_number`/`name_field` keys) instead of a live describe."""
    if field is None:
        return False
    if field.get("auto_number"):
        return True
    if field.get("name_field") and not item.get("editable_for_new"):
        return True
    return False


def predict_fields_layout_aware_from_map(sobject: str, mp: dict,
                                          record_type_id: str | None = None) -> list[dict]:
    """Map-driven equivalent of predict_fields_layout_aware() -- ZERO org contact. Reads
    discover.py's cached `create_layout_items` (full per-field layout items, added in P3
    specifically so this function could exist) and `fields` (describe-shaped, thinned) for the
    object out of the org map, and reuses the exact same type_to_keyword()/build_locator_chain()
    the live path uses, so the two paths differ only in WHERE the field/layout facts came from --
    the prediction logic itself is not duplicated.

    `record_type_id`: when given AND the map carries a per-type layer for this object
    (`create_layout_items_by_record_type[record_type_id]`, BACKLOG row 107 / RECORD-TYPES.md §2),
    THAT type's own Create layout and picklist values are used -- never the flat/default layer,
    which measured live (Lead: 15/31/38 fields across its 3 types) under-reports every
    non-default type's field set. Falls back to the flat `create_layout_items` + the
    first-sorted-record-type picklist set (documented limitation, unchanged) when no
    `record_type_id` is given, or the map has no per-type layer for this object/type (e.g. the
    object has only one record type, so discover.py never fetched a per-type layer)."""
    entry = (mp.get("objects") or {}).get(sobject)
    if not entry or not isinstance(entry.get("inventory"), dict):
        raise RuntimeError(f"{sobject} not in map -- rebuild with `discover.py build --objects {sobject}`")
    inv = entry["inventory"]
    fields = (inv.get("fields") or {}).get("value")
    if fields is None:
        raise RuntimeError(f"{sobject}: map has no cached fields (describe could-not-check at build time)")

    layout_items = None
    layouts_by_rt = (inv.get("create_layout_items_by_record_type") or {}).get("value") or {}
    if record_type_id and record_type_id in layouts_by_rt and layouts_by_rt[record_type_id] is not None:
        layout_items = layouts_by_rt[record_type_id]
    if layout_items is None:
        layout_items = (inv.get("create_layout_items") or {}).get("value")
    if layout_items is None:
        raise RuntimeError(f"{sobject}: map has no cached create_layout_items -- rebuild the map "
                            f"(built before this key existed, or the live layout fetch failed)")

    picklists_by_rt = (inv.get("picklists_by_record_type") or {}).get("value") or {}
    if record_type_id and record_type_id in picklists_by_rt:
        picklist_values_by_field = picklists_by_rt[record_type_id]
    else:
        # The live path takes an explicit/default record type; when no record_type_id was
        # requested (or the map has no entry for the one given -- e.g. this object was never
        # fetched per-type) fall back to the first record type's picklist set (sorted for
        # determinism), same as the map's own object-level picklist view -- documented
        # limitation, not silent.
        picklist_values_by_field = picklists_by_rt.get(sorted(picklists_by_rt)[0]) if picklists_by_rt else {}

    # BACKLOG row 80: same compound grouping as the live path (predict_fields_layout_aware) --
    # the map's own create_layout_items is already flattened the same way (discover.py builds it
    # by calling this file's layout_create_items()), so the SAME name-shape detector applies.
    compound_rows, consumed = _detect_compound_groups(layout_items)
    results = list(compound_rows)
    for item in layout_items:
        api_name = item["api_name"]
        if api_name in consumed:
            continue
        field = fields.get(api_name)
        not_rendered = (api_name in LAYOUT_NEVER_RENDERED_FIELDS
                        or _is_autonumber_name_field_from_map(item, field))
        predicted_render = "not_rendered" if not_rendered else "rendered"

        if field is None:
            results.append({
                "field_name": api_name, "label": item["form_label"], "type": None, "keyword": None,
                "confidence": "not-createable-on-layout", "required": item["required"],
                "editable_for_new": item["editable_for_new"], "picklist_values": [], "length": None,
                "locators": build_locator_chain(api_name, item["form_label"], "string",
                                                 surface="create", sobject=sobject),
                "on_layout": True, "predicted_render": predicted_render,
            })
            continue

        field_type = field.get("type")
        if not_rendered:
            results.append({
                "field_name": api_name, "label": item["form_label"], "type": field_type,
                "keyword": None, "confidence": "predicted-not-rendered", "required": item["required"],
                "editable_for_new": item["editable_for_new"], "picklist_values": [],
                "length": field.get("length"), "locators": [], "on_layout": True,
                "predicted_render": predicted_render,
            })
            continue

        keyword, confidence = type_to_keyword(field_type, api_name=api_name)
        picklist_values = (picklist_values_by_field.get(api_name, [])
                            if field_type in ("picklist", "multipicklist") else [])
        locators = build_locator_chain(api_name, item["form_label"], field_type,
                                        surface="create", sobject=sobject)
        results.append({
            "field_name": api_name, "label": item["form_label"], "type": field_type,
            "keyword": keyword, "confidence": confidence, "required": item["required"],
            "editable_for_new": item["editable_for_new"], "picklist_values": picklist_values,
            "length": field.get("length"), "locators": locators, "on_layout": True,
            "predicted_render": predicted_render,
        })
    return results


def predict_fields_from_map(sobject: str, mp: dict, surface: str = "view") -> list[dict]:
    """Map-driven equivalent of predict_fields() (the --source describe path) -- ZERO org contact."""
    entry = (mp.get("objects") or {}).get(sobject)
    if not entry or not isinstance(entry.get("inventory"), dict):
        raise RuntimeError(f"{sobject} not in map -- rebuild with `discover.py build --objects {sobject}`")
    fields = (entry["inventory"].get("fields") or {}).get("value")
    if fields is None:
        raise RuntimeError(f"{sobject}: map has no cached fields")
    results = []
    for name, f in fields.items():
        if not f.get("createable"):
            continue
        field_type = f.get("type")
        keyword, confidence = type_to_keyword(field_type, api_name=name)
        required = not f.get("nillable", True) and f.get("createable")
        label = f.get("label") or name
        locators = build_locator_chain(name, label, field_type, surface=surface, sobject=sobject)
        results.append({
            "field_name": name, "label": label, "type": field_type, "keyword": keyword,
            "confidence": confidence, "required": required,
            # picklist values are not cached flat per-field outside a record type in the map --
            # documented limitation, matches the describe-source path's own note that describe's
            # picklist_values are not record-type-scoped anyway.
            "picklist_values": [], "length": f.get("length"), "locators": locators,
        })
    return results


# BACKLOG 80 / PB0 finding (docs/recorder/evidence/metadata-dom-parity-2026-09-07.md, "What
# predict.py lacks"): the map's `quick_actions[*].render` layer was already fetched and NEVER
# read by predict.py. `render.family` is a small, closed vocabulary (measured across dev1/
# slockard/fsc7f: aura-quick-action-layout, flow screen family/flowruntime, aura-component,
# feed-publisher, visualforce-iframe, or None) -- only the ones with a known, single button-open
# DOM shape route to a real keyword (ClickText on the action's own label); the rest (bare Aura
# components, unnamed families) are honestly could-not-check rather than guessed. This predicts
# the BUTTON only -- the form fields inside the opened action are metadata the map does not carry
# per-quick-action (BACKLOG follow-up), so they are NOT enumerated here.
QUICK_ACTION_FAMILY_KEYWORD = {
    "aura-quick-action-layout": "ClickText",
    "flowruntime": "ClickText",
    "flow screen family": "ClickText",
    "feed-publisher": "ClickText",
    "visualforce-iframe": "ClickText",
}


def predict_quick_actions_from_map(sobject: str, mp: dict) -> list[dict]:
    """Predict the OPEN-ACTION control for each quick action the map's `quick_actions` layer
    carries for `sobject` -- reads `render.family`/`render.keyword_family`, never re-derives them.
    ZERO org contact. Returns rows in the same shape as the field predictors (extra
    `source`/`quick_action_*` keys, `field_name`/`label` set to the action's own label so callers
    that just want "keyword" columns keep working)."""
    entry = (mp.get("objects") or {}).get(sobject)
    qa = ((entry or {}).get("quick_actions") or {}).get("value") or []
    rows: list[dict] = []
    for action in qa:
        label = action.get("label") or action.get("name")
        render = action.get("render") or {}
        family = render.get("family")
        keyword = QUICK_ACTION_FAMILY_KEYWORD.get(family)
        confidence = "certain" if keyword else "could-not-check"
        if keyword is None:
            keyword = "ClickText"
            confidence = "needs-dom-check"
        rows.append({
            "field_name": action.get("name"), "label": label, "type": "quick_action",
            "keyword": keyword, "confidence": confidence, "required": False,
            "editable_for_new": False, "picklist_values": [], "length": None, "locators": [],
            "on_layout": True, "predicted_render": "rendered",
            "source": "quick_actions",
            "quick_action_type": action.get("type"),
            "quick_action_family": family,
            "quick_action_keyword_family": render.get("keyword_family"),
            "quick_action_verdict": render.get("verdict"),
        })
    return rows


# BACKLOG 80 / PB0 finding: the `record_page` layer's per-tab `related_lists_named` was fetched
# and never turned into predicted controls (0/32 measured coverage on related-list pages). Every
# related list a tab names becomes ONE predicted control per list (the table itself, not its
# individual row actions -- BACKLOG follow-up: Layout XML relatedLists New/Add/View All buttons,
# named but not implemented here, out of this stream's scope). Each row carries `tab_label` /
# `behind_tab` so a DOM-parity tool can class a predicted-not-rendered miss as "behind an
# unopened tab" instead of a metadata error (the PB0 "tab-state awareness" gap). Chatter/Activity
# tabs are emitted as an explicit COULD-NOT-CHECK control -- no metadata describes their contents.
RELATED_LIST_KEYWORD = "ClickTableCell"
_CHATTER_ACTIVITY_TOKENS = ("activity", "feed", "chatter")


def _default_record_page(record_page_value: dict) -> dict | None:
    pages = record_page_value.get("pages") or {}
    if not pages:
        return None
    default_name = ((record_page_value.get("org_default") or {}).get("developer_name"))
    if default_name and default_name in pages:
        return pages[default_name]
    return next(iter(pages.values()))


def predict_record_page_regions_from_map(sobject: str, mp: dict) -> list[dict]:
    """Predict related-list and chatter/activity controls from the map's `record_page` layer's
    tabs -- ZERO org contact, ZERO new map layer (consumes what discover.py already fetches).
    Uses the org-default page (falls back to the first cached page) since the map does not key
    this call by app/profile the way `record_page.by_app` does."""
    entry = (mp.get("objects") or {}).get(sobject)
    rp_value = ((entry or {}).get("record_page") or {}).get("value") or {}
    page = _default_record_page(rp_value)
    if not page:
        return []
    rows: list[dict] = []
    for tab in page.get("tabs") or []:
        tab_label = tab.get("label")
        token = (tab.get("token") or "").lower()
        for related_list in tab.get("related_lists_named") or []:
            rows.append({
                "field_name": related_list, "label": related_list, "type": "related_list",
                "keyword": RELATED_LIST_KEYWORD, "confidence": "needs-dom-check",
                "required": False, "editable_for_new": False, "picklist_values": [],
                "length": None, "locators": [], "on_layout": True, "predicted_render": "rendered",
                "source": "record_page", "tab_label": tab_label, "behind_tab": tab_label,
            })
        if any(t in token for t in _CHATTER_ACTIVITY_TOKENS):
            rows.append({
                "field_name": tab.get("identifier"), "label": tab_label,
                "type": "chatter_or_activity", "keyword": None, "confidence": "could-not-check",
                "required": False, "editable_for_new": False, "picklist_values": [],
                "length": None, "locators": [], "on_layout": True, "predicted_render": "rendered",
                "source": "record_page", "tab_label": tab_label, "behind_tab": tab_label,
            })
    return rows


def predict_page_surface_from_map(sobject: str, mp: dict) -> list[dict]:
    """Combined quick-action + record-page-region predictions -- the two map layers PB0 named as
    read and never consumed. `--source page`."""
    return predict_quick_actions_from_map(sobject, mp) + predict_record_page_regions_from_map(sobject, mp)


def describe_sobject(sobject: str, org: str) -> dict:
    """Fetch sobject describe from sf CLI."""
    env = dict(os.environ, FORCE_COLOR="0", NO_COLOR="1")
    result = subprocess.run(
        ["sf", "sobject", "describe", "-o", org, "-s", sobject, "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    data = json.loads(result.stdout)
    if data.get("status") != 0:
        raise RuntimeError(f"describe failed: {data.get('message', 'unknown error')}")
    return data["result"]


def _sf_session_module():
    """Import tools/sf_session.py by path -- avoids requiring every caller of
    this module to fix sys.path first. tools/sf_session.py is THE mint-once,
    reuse-everywhere token source in this repo (see its own docstring: three
    org auto-containments were caused by tools that minted a session per
    call). NEVER shell out to `sf` directly here, and NEVER use a browser
    `sid` for this REST call -- a browser sid returns 401 INVALID_SESSION_ID
    on /services/data/vXX (memory: reference_browser_sid_not_valid_for_rest).
    """
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "sf_session.py"))
    spec = importlib.util.spec_from_file_location("sf_session", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _layout_cache_path(sobject: str, org: str, record_type_id: str | None) -> str:
    safe_obj = re.sub(r"[^A-Za-z0-9_]", "_", sobject)
    safe_org = re.sub(r"[^A-Za-z0-9_.-]", "_", org)
    rt = record_type_id or "default"
    d = os.path.join(UI_LAYOUT_CACHE_DIR, safe_org)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{safe_obj}__{rt}.json")


def fetch_create_layout(
    sobject: str,
    org: str,
    record_type_id: str | None = None,
    api_version: str = DEFAULT_API_VERSION,
    force: bool = False,
) -> dict:
    """GET /services/data/vXX.0/ui-api/layout/<Object>?mode=Create, cached.

    Cache: ~/.claude/state/ui-layout-cache/<org>/<Object>__<recordTypeId|default>.json,
    TTL 24h. Token comes from tools/sf_session.py's cached mint (never a fresh
    `sf` auth per call, never a browser sid).
    """
    cache_path = _layout_cache_path(sobject, org, record_type_id)
    if not force and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < UI_LAYOUT_TTL:
            with open(cache_path) as fh:
                return json.load(fh)

    sf_session = _sf_session_module()
    sess = sf_session.get(org)
    url = (
        f"{sess['instance_url'].rstrip('/')}/services/data/v{api_version}"
        f"/ui-api/layout/{sobject}?mode=Create"
    )
    if record_type_id:
        url += f"&recordTypeId={record_type_id}"

    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + sess["access_token"]}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise RuntimeError(
            f"ui-api layout fetch failed for {sobject} ({org}): {e.code} {body}"
        ) from e

    with open(cache_path, "w") as fh:
        json.dump(data, fh)
    return data


# BACKLOG row 80 (docs/crt-train/BACKLOG.md, follow-up to row 61 --
# feedback_metadata_first_dom_second_compound_controls_are_one_db_value_with_several_inputs):
# `type_to_keyword` already routes `datetime` -> `set_datetime` from METADATA alone, never the
# DOM. `address`/`name` do NOT reduce to one describe type the way `datetime` does -- an address
# compound arrives in describe/layout as SEVERAL separate createable sub-fields (BillingStreet,
# BillingCity, ...), each typed "string" on its own, and the Name compound the same way
# (Salutation/FirstName/LastName). The single-field type check in `type_to_keyword` cannot see
# that grouping -- it never receives more than one field at a time. So compound-GROUP detection
# lives here instead, keyed on the shape of a real ui-api Create layoutItem (measured live,
# `fixtures/predict/account_layout_create.json`): one layoutItem, several `Field`
# layoutComponents, e.g. label "Billing Address" grouping BillingStreet/BillingCity/
# BillingState/BillingPostalCode/BillingCountry. `layout_create_items()` above deliberately keeps
# flattening (one row per component -- other callers/tests depend on that flat shape unchanged);
# the grouping below is a SEPARATE pass over the same flat api_name list, done purely by API-NAME
# SHAPE so it works identically whether the flat list came from a live/fixture layout
# (`layout_create_items`) or the org map's own already-flattened `create_layout_items` cache
# (`predict_fields_layout_aware_from_map` -- discover.py never cached the layoutItem's legend, so
# a name-shape detector is the only signal available there too; this keeps the two population
# paths sharing ONE grouping function instead of drifting).
#
# A multi-component layoutItem is NOT always a compound -- e.g. Created By groups
# CreatedById+CreatedDate in one item (see cgc_program_c_layout_create.json), which is two
# unrelated fields shown together, not one DB value. The detector below only fires on the two
# known compound SHAPES (address-suffix family, Name-field family); anything else is left alone
# and falls through to the existing per-field path unchanged.
_ADDRESS_SUFFIX_RE = re.compile(r"^(.*)(Street|City|State|PostalCode|Country)$")

# Fixed field-name family for the Name compound (Contact/Lead) -- Salutation is a real picklist,
# the rest plain text; MiddleName/Suffix are org-setting-gated so not every org's layout carries
# them, hence "any 2+ present" rather than requiring the full set.
NAME_COMPOUND_FIELDS = frozenset({"Salutation", "FirstName", "MiddleName", "LastName", "Suffix"})


def _compound_groups_from_field_names(api_names: list[str]) -> dict[str, dict]:
    """Detect address/Name compound groups purely from api_name shape (metadata, never a DOM
    read -- feedback_metadata_first_dom_second_compound_controls...). Returns
    {api_name: {"kind": "address"|"name", "group_key": <address prefix, e.g. "Billing"|"Name">}}
    for every api_name that belongs to a detected 2+-member group; names outside any group are
    simply absent from the returned dict."""
    result: dict[str, dict] = {}

    by_prefix: dict[str, list[str]] = {}
    for n in api_names:
        m = _ADDRESS_SUFFIX_RE.match(n or "")
        if m:
            by_prefix.setdefault(m.group(1), []).append(n)
    for prefix, members in by_prefix.items():
        if len(members) >= 2:
            for n in members:
                result[n] = {"kind": "address", "group_key": prefix}

    name_members = [n for n in api_names if n in NAME_COMPOUND_FIELDS]
    if len(name_members) >= 2:
        for n in name_members:
            result[n] = {"kind": "name", "group_key": "Name"}

    return result


def _compound_legend(kind: str, group_key: str) -> str:
    """The fieldset <legend> text set_address/set_name key their DOM lookup on -- 'Billing
    Address'/'Shipping Address'/'Mailing Address' (measured live, KEYWORDS-BY-FIELD.md SS2.16) or
    plain 'Name' for the Name compound."""
    if kind == "name":
        return "Name"
    return f"{group_key} Address" if group_key else "Address"


def _detect_compound_groups(layout_items: list[dict]) -> tuple[list[dict], set[str]]:
    """Group a FLAT layout-items population (the shape both `layout_create_items()` and the map's
    cached `create_layout_items` share) into compound result rows. Returns
    (compound_result_rows, consumed_api_names) -- callers add the rows to their results and skip
    `consumed_api_names` in their existing per-field loop, so every non-compound field's handling
    (not_rendered, autonumber, reference sub-kinds, ...) is completely unchanged."""
    by_name = {it["api_name"]: it for it in layout_items if it.get("api_name")}
    compound_map = _compound_groups_from_field_names(list(by_name.keys()))

    groups: dict[tuple, list[str]] = {}
    for n, meta in compound_map.items():
        groups.setdefault((meta["kind"], meta["group_key"]), []).append(n)

    rows: list[dict] = []
    consumed: set[str] = set()
    for (kind, group_key), names in groups.items():
        members = [by_name[n] for n in sorted(names)]
        legend = _compound_legend(kind, group_key)
        keyword = "set_address" if kind == "address" else "set_name"
        sub_fields = {m["api_name"]: m["form_label"] for m in members}
        rows.append({
            "field_name": legend,
            "label": legend,
            "type": kind,
            "keyword": keyword,
            "confidence": "certain",
            "required": any(m.get("required") for m in members),
            "editable_for_new": any(m.get("editable_for_new") for m in members),
            "picklist_values": [],
            "length": None,
            "locators": [],
            "on_layout": True,
            "predicted_render": "rendered",
            "compound": True,
            "compound_kind": kind,
            "legend": legend,
            "sub_fields": sub_fields,
        })
        consumed.update(names)
    return rows, consumed


def layout_create_items(layout: dict) -> list[dict]:
    """Flatten a ui-api Create-mode layout response into field-level items.

    Only `componentType == "Field"` layoutComponents count -- a layout also
    carries `EmptySpace` and other non-field placeholders (measured live on
    CGC_Program__c: 24 layout components, 2 componentTypes, one of them
    EmptySpace). A field appears here even when `editableForNew` is False
    (e.g. Account's Owner ID renders read-only on /new but IS on the layout)
    because the scoring rule is "fields the layout says are on the Create
    form," not "fields you can type into" -- `editable_for_new` is carried
    through so a caller can filter further if it wants that stricter view.
    """
    items = []
    for section in layout.get("sections") or []:
        for row in section.get("layoutRows") or []:
            for li in row.get("layoutItems") or []:
                for lc in li.get("layoutComponents") or []:
                    if lc.get("componentType") != "Field":
                        continue
                    items.append(
                        {
                            "api_name": lc.get("apiName"),
                            # The layoutComponent/layoutItem label is the FORM
                            # label, not the describe label -- this is the
                            # fix for the 82/225 (36.4%) describe-label !=
                            # form-label mismatch documented in
                            # PREDICTABILITY.md §5.
                            "form_label": html.unescape(lc.get("label") or li.get("label") or ""),
                            "required": bool(li.get("required")),
                            "editable_for_new": bool(li.get("editableForNew")),
                            "section": section.get("heading"),
                        }
                    )
    return items


def predict_fields_layout_aware(
    sobject: str,
    org: str,
    record_type_id: str | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> list[dict]:
    """Layout-aware population: predict ONLY the fields the real Create
    layout says are present, typed via describe (never via describe for
    population -- see module docstring).

    Each result also carries `on_layout=True`, `required` and
    `editable_for_new` straight from the layout response, and its `label`
    is the FORM label (not describe's), which is also what
    `build_locator_chain`'s Strategy B needs to actually match text on the
    rendered page.
    """
    layout = fetch_create_layout(sobject, org, record_type_id, api_version)
    layout_items = layout_create_items(layout)
    describe = describe_sobject(sobject, org)
    describe_by_name = {f["name"]: f for f in describe["fields"]}

    # BACKLOG row 80: group address/Name compounds into ONE set_address/set_name prediction
    # before the per-field loop below ever sees their sub-fields -- see _detect_compound_groups.
    compound_rows, consumed = _detect_compound_groups(layout_items)
    results = list(compound_rows)
    for item in layout_items:
        api_name = item["api_name"]
        if api_name in consumed:
            continue
        field = describe_by_name.get(api_name)
        # Tri-state prediction of whether the layout item will actually show
        # up in the DOM: "not_rendered" is a POSITIVE prediction (this field
        # is on the layout but will never render, per
        # LAYOUT_NEVER_RENDERED_FIELDS), never a fallback for "we don't
        # know" -- that stays "rendered" (the pre-existing, default
        # assumption) so nothing already working changes behavior.
        not_rendered = (
            api_name in LAYOUT_NEVER_RENDERED_FIELDS
            or _is_autonumber_name_field(item, field)
        )
        predicted_render = "not_rendered" if not_rendered else "rendered"

        if field is None:
            # On the layout but not createable in describe (e.g. Owner ID
            # shown read-only for context). Still counts in the population
            # per the scoring rule -- report it, no keyword.
            results.append(
                {
                    "field_name": api_name,
                    "label": item["form_label"],
                    "type": None,
                    "keyword": None,
                    "confidence": "not-createable-on-layout",
                    "required": item["required"],
                    "editable_for_new": item["editable_for_new"],
                    "picklist_values": [],
                    "length": None,
                    "locators": build_locator_chain(
                        api_name, item["form_label"], "string",
                        surface="create", sobject=sobject,
                    ),
                    "on_layout": True,
                    "predicted_render": predicted_render,
                }
            )
            continue

        field_type = field["type"]
        if not_rendered:
            # Predicted absent from the DOM -- no keyword/locator is
            # meaningful for a field the prediction says will never be
            # there to click or type into. Still reported (population is
            # "on the layout"), just not as something to resolve live.
            results.append(
                {
                    "field_name": api_name,
                    "label": item["form_label"],
                    "type": field_type,
                    "keyword": None,
                    "confidence": "predicted-not-rendered",
                    "required": item["required"],
                    "editable_for_new": item["editable_for_new"],
                    "picklist_values": [],
                    "length": field.get("length"),
                    "locators": [],
                    "on_layout": True,
                    "predicted_render": predicted_render,
                }
            )
            continue

        keyword, confidence = type_to_keyword(field_type, api_name=api_name)
        picklist_values = []
        if field_type in ("picklist", "multipicklist"):
            picklist_values = [pv["value"] for pv in field.get("picklistValues", [])]
        locators = build_locator_chain(
            api_name, item["form_label"], field_type,
            surface="create", sobject=sobject,
        )
        results.append(
            {
                "field_name": api_name,
                "label": item["form_label"],
                "type": field_type,
                "keyword": keyword,
                "confidence": confidence,
                "required": item["required"],
                "editable_for_new": item["editable_for_new"],
                "picklist_values": picklist_values,
                "length": field.get("length"),
                "locators": locators,
                "on_layout": True,
                "predicted_render": predicted_render,
            }
        )
    return results


def type_to_keyword(field_type: str, api_name: str | None = None) -> tuple[str, str]:
    """Map Salesforce field type to CRT keyword.

    Returns: (keyword, confidence)
    confidence: 'certain', 'needs-dom-check', 'could-not-check', or 'unknown'

    `api_name` matters for exactly one type: `reference` renders FOUR different ways depending on
    the field's API NAME, not its describe type (POLYMORPHISM.md SS2, chains.REFERENCE_SUBKINDS).
    """
    # Exact type matches
    if field_type in ("string", "email", "phone", "url", "textarea"):
        return ("type_text_clearing", "certain")
    if field_type == "picklist":
        return ("pick_list", "needs-dom-check")
    if field_type == "multipicklist":
        # 2026-08-30: keywords_multipicklist.multi_pick_list exists (dual listbox, 3/3 live) --
        # route to it from METADATA, never to pick_list.
        return ("multi_pick_list", "certain")
    if field_type == "reference":
        # BACKLOG row 70 / KEYWORDS-BY-FIELD.md SS2.11's "Code/spec disagreement, named not
        # patched": this used to map every `reference` to combo_box regardless of api_name, while
        # chains.chain_for() refused OwnerId/CreatedById/LastModifiedById/RecordTypeId as
        # not-a-plain-lookup. Two routers, two answers, about the same measured fact
        # (POLYMORPHISM.md SS2: reference renders FOUR ways, chosen by API NAME). Now both read
        # the SAME table -- chains.REFERENCE_SUBKINDS -- so a caller cannot get "combo_box" from
        # predict.py and "refuses" from chains.py for the same field.
        if api_name in chains.REFERENCE_SUBKINDS:
            return (None, "could-not-check")
        return ("combo_box", "needs-dom-check")
    if field_type == "boolean":
        return ("click_checkbox", "certain")
    if field_type == "date":
        # Typed as MM/DD/YYYY, verified working today
        return ("type_text_clearing", "certain")
    if field_type == "datetime":
        # 2026-08-30 (user, watching the battery type "date & time" into the Date box): a datetime
        # is a COMPOUND control -- one database value, two inputs (Date text + a 15-minute Time
        # combobox under one legend). The metadata already says so; route to set_datetime here,
        # never to type_text_clearing. The DOM guard in the keyword is the backstop, not the router.
        return ("set_datetime", "certain")
    if field_type in ("currency", "double", "int", "percent"):
        # Numeric; reformats on blur, correct behavior
        return ("type_text_clearing", "certain")
    if field_type == "address":
        # BACKLOG row 80: the compound virtual field itself (e.g. BillingAddress) is almost never
        # createable=True on its own -- it is USUALLY its several sub-fields (BillingStreet,
        # BillingCity, ...) that carry the real describe type "string" and get grouped into one
        # set_address prediction by _detect_compound_groups() in the layout-aware population, not
        # by this per-field check. This branch is the safety net for the rarer case where an
        # "address"-typed field does reach type_to_keyword directly -- it must still never fall
        # to type_text_clearing (feedback_metadata_first_dom_second_compound_controls...).
        return ("set_address", "certain")
    if field_type == "long":
        # `long` is a plain numeric describe type (a Long int) -- same rendered control as int/
        # double, and it must never fall through to the "unknown" branch and be reported as an
        # unrouted metadata point. Grouped here rather than in the numeric tuple above only so
        # this comment has somewhere to live.
        return ("type_text_clearing", "certain")
    if field_type == "encryptedstring":
        # Classic encrypted text: a plain <input type="password"-ish> masked text box on the form.
        # Mechanism is type-a-string, so it routes to type_text_clearing -- but the READ-BACK is
        # the catch: the platform returns the MASKED value (asterisks) to describe/SOQL and to the
        # rendered form for anyone without "View Encrypted Data", so confirm.py's read-back cannot
        # prove what landed. needs-dom-check, never "certain".
        return ("type_text_clearing", "needs-dom-check")
    if field_type == "combobox":
        # describe type `combobox` is a picklist that also accepts a free-typed value. pick_list
        # drives the listbox half; the free-text half has no keyword on any org we own.
        return ("pick_list", "needs-dom-check")
    if field_type == "time":
        # Time-only field. set_datetime drives a DATE input plus a time combobox; there is no
        # time-ONLY keyword, and routing a time field to set_datetime would type into a date box
        # that does not exist. Stated gap, not a guess.
        return (None, "could-not-check")
    if field_type in ("base64", "id"):
        # base64 (Blob body) and id are never editable controls on a create/edit form -- the
        # platform renders no input for them. Not a gap in the keyword library: a gap by design.
        return (None, "could-not-check")
    if field_type == "location":
        # Geolocation: one createable describe field (e.g. Last_Position__c), a <legend>-grouped
        # Latitude/Longitude fieldset in the DOM. Mechanism is certain, live-measured
        # (KEYWORDS-BY-FIELD.md SS2.17, keywords_compound.set_geolocation); PERSISTENCE after
        # Save is could-not-check (BACKLOG-61-EVIDENCE.md SS3 -- the record was never saved in
        # that run) -- that caveat lives with the evidence, not as a lowered confidence here.
        return ("set_geolocation", "certain")

    # Unmapped types
    return (None, "unknown")


def control_family_keyword(point: str) -> tuple[str | None, str | None, str]:
    """Route a NON-FIELD metadata point -- a control family, a quick-action rendering family, or
    an OmniStudio element type -- to its keyword.

    `point` is the metadata point exactly as the routing table names it, e.g.
    "path / PathAssistant", "quick action: aura-quick-action-layout",
    "OmniStudio element: Multi-select", "table / datatable (related list, list view, custom)".

    Returns `(module, callable, status)`; `(None, None, "<gap reason>")` when the point is a
    stated gap, and `(None, None, "unknown metadata point: ...")` when the table has no row at
    all -- the tri-state again: routed / gap / could-not-check, never a silent None.

    predict.py stays THE routing surface an agent calls (type_to_keyword for describe types, this
    for everything else); the table itself lives in metadata_keywords.py, imported lazily here so
    predict.py keeps no import cycle and no extra module-scope cost. See
    docs/recorder/METADATA-KEYWORDS.md.
    """
    import metadata_keywords  # local: metadata_keywords imports predict, so never at module scope

    for row in metadata_keywords.build_table():
        if row["point"] != point:
            continue
        if row.get("callable"):
            return (row.get("module"), row["callable"], row.get("status") or "COULD-NOT-CHECK")
        if row.get("keyword"):
            # Robot-body keyword: named and drivable, but no Python callable to hand back.
            return (None, None,
                    f"robot-body keyword `{row['keyword']}` "
                    "(tools/recorder/library/garzai_recorder.robot)")
        return (None, None, row.get("gap") or "gap with no stated reason")
    return (None, None, f"unknown metadata point: {point!r} -- no row in "
                        "docs/recorder/METADATA-KEYWORDS.md")


def build_locator_chain(
    api_name: str, label: str, field_type: str, surface: str = "view",
    sobject: str = "Account"
) -> list[dict]:
    """Build ordered locator strategies for a field.

    Args:
        api_name: Field API name (from describe)
        label: Describe label (NOT form label)
        field_type: Salesforce field type
        surface: "view", "edit", or "create" — strategy A only on view/edit

    Returns: List of locator strategies, most-specific first:
      - Strategy A: data-target-selection-name (highest specificity, view/edit only)
      - Strategy B: form label xpath (high specificity, form label not describe label)
      - Strategy C: slds-form-element fallback (ambiguous, always last)

    Each has: xpath, strategy (A/B/C), unique (measured/unmeasured), confidence
    """
    locators = []

    # Strategy A: data-target-selection-name attribute (most specific)
    # Only appears on view/edit surfaces, NOT on create modal
    if surface in ("view", "edit"):
        locators.append({
            "xpath": f'//*[@data-target-selection-name="sfdc:RecordField.{sobject}.{api_name}"]',
            "strategy": "A",
            "unique": "10/10",
            "confidence": "certain",
            "note": f"data-target-selection-name unique selector for {api_name}",
        })

    # Strategy B: form label xpath (high specificity)
    # Uses FORM label, which differs from describe label → needs-dom-check
    #
    # BACKLOG row 69 / KEYWORDS-BY-FIELD.md SS3's "Code/spec disagreement, named not patched":
    # this used to (and, before that fix, literally did) emit a bare `text()` match, which
    # `~/.claude/skills/sf-metadata-locators/SKILL.md` SS3 measured at 0/11 on REQUIRED fields --
    # the required-field marker `*` is rendered as its OWN sibling DOM node inside the label
    # element, so the label element's own `text()` (direct text-node children only) does not
    # include the label string when that marker is present; only fields with no `*` ever matched.
    # The skill's corrected, measured form scopes to the label element by its SLDS class and
    # reads `normalize-space(.)` (ALL descendant text, not just direct text nodes) instead of
    # `normalize-space(text())` -- verified 6/6 on required fields, 10/10 unique overall. That is
    # the newer measurement and the form emitted here now; qforce_lite.py's own
    # `_field_xpath_chain` still carries the older intermediate `normalize-space(text())` fix and
    # is out of scope for this file (owned by a different stream).
    locators.append({
        "xpath": (f'//records-record-layout-item[.//*[contains(@class,'
                  f'"slds-form-element__label")][normalize-space(.)="{label}"]]'),
        "strategy": "B",
        "unique": "10/10",
        "confidence": "needs-dom-check",
        "note": f"Form label search; describe label may not match form rendering",
    })

    # Strategy C: slds-form-element fallback (ambiguous, always last)
    # Measured 0/10 unique (always matches 2 elements: container + label)
    locators.append({
        "xpath": f'//*[contains(@class,"slds-form-element")][.//*[text()="{label}"]]',
        "strategy": "C",
        "unique": "0/10",
        "confidence": "ambiguous",
        "note": "TRAP: always matches 2+ elements (container + label). Use A or B instead.",
    })

    return locators


def predict_fields(sobject: str, org: str, surface: str = "view") -> list[dict]:
    """Predict keywords and locators for all createable fields on sobject.

    Args:
        sobject: Salesforce object name
        org: Org alias
        surface: "view", "edit", or "create" for locator strategy selection

    Returns list of dicts with:
      - field_name: API name
      - label: describe label (NOT verified against form)
      - type: Salesforce field type
      - keyword: predicted CRT keyword
      - confidence: 'certain', 'needs-dom-check', or 'unknown'
      - required: True if nillable=false and createable=true
      - picklist_values: list of picklist options (if applicable)
      - locators: ordered list of locator strategies (if include_locators=True)
    """
    describe = describe_sobject(sobject, org)
    results = []

    for field in describe["fields"]:
        # Skip non-createable fields
        if not field.get("createable"):
            continue

        field_type = field["type"]
        keyword, confidence = type_to_keyword(field_type, api_name=field["name"])

        # A field is required if it cannot be null AND is createable
        required = not field.get("nillable", True) and field.get("createable")

        # Collect picklist values
        picklist_values = []
        if field_type in ("picklist", "multipicklist"):
            picklist_values = [pv["value"] for pv in field.get("picklistValues", [])]

        # Build locator chain
        locators = build_locator_chain(
            field["name"],
            field.get("label", ""),
            field_type,
            surface=surface,
            sobject=sobject,
        )

        results.append({
            "field_name": field["name"],
            "label": field.get("label", ""),
            "type": field_type,
            "keyword": keyword,
            "confidence": confidence,
            "required": required,
            "picklist_values": picklist_values,
            "length": field.get("length"),
            "locators": locators,
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Predict CRT keywords from Salesforce metadata"
    )
    parser.add_argument("--sobject", required=True, help="Salesforce object name")
    parser.add_argument("--org", required=True, help="Org alias (required -- never defaults; a silent dev2 default built a seed set in the wrong org on 2026-08-29)")
    parser.add_argument(
        "--surface",
        choices=["view", "edit", "create"],
        default="view",
        help="Record surface for locator strategy (default: view)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON (default: human-readable)"
    )
    parser.add_argument(
        "--locators",
        action="store_true",
        help="Include locator chains in human output (default: hidden)",
    )
    parser.add_argument(
        "--source",
        choices=["describe", "layout", "page"],
        default="describe",
        help=(
            "describe (default): every createable field, unfiltered by layout. "
            "layout: only fields the real Create-mode UI API layout has -- "
            "fixes the measured 70%% over-prediction (PREDICTABILITY-LAYOUT.md). "
            "page: quick actions + record-page related-list/chatter/activity regions "
            "from the map's quick_actions/record_page layers (map required, BACKLOG 80)."
        ),
    )
    parser.add_argument(
        "--record-type-id",
        default=None,
        help="Record type Id for --source layout (defaults to the object's default RT)",
    )
    parser.add_argument(
        "--map",
        default=None,
        help="path to an org map (tools/qforce-lite/discovery/discover.py build's output). "
             "Omit to auto-use ~/.claude/state/org-map/<org>.json when it is younger than 24h; "
             "pass a path to force it (subject to the 7-day staleness block, see --allow-stale).",
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        dest="allow_stale",
        help="use an explicitly-passed --map even if it is older than 7 days",
    )
    args = parser.parse_args()

    mp, map_status, blocked = maplib.resolve_map(args.org, args.map, args.allow_stale)
    # Always stderr: --json callers (generate.py's subprocess) parse stdout as JSON, and this line
    # must never land inside that payload.
    print(map_status, file=sys.stderr)
    if blocked:
        print(f"BLOCKED: {blocked}", file=sys.stderr)
        return 2

    try:
        if args.source == "page":
            if mp is None:
                print("Error: --source page requires an org map (no live fallback -- "
                      "quick_actions/record_page are map-only layers)", file=sys.stderr)
                return 1
            predictions = predict_page_surface_from_map(args.sobject, mp)
        elif mp is not None:
            if args.source == "layout":
                predictions = predict_fields_layout_aware_from_map(
                    args.sobject, mp, record_type_id=args.record_type_id
                )
            else:
                predictions = predict_fields_from_map(args.sobject, mp, surface=args.surface)
        elif args.source == "layout":
            predictions = predict_fields_layout_aware(
                args.sobject, args.org, record_type_id=args.record_type_id
            )
        else:
            predictions = predict_fields(args.sobject, args.org, surface=args.surface)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(predictions, indent=2))
    else:
        # Human-readable table format
        print(f"\nPredictions for {args.sobject} on {args.org} ({args.surface} surface):")
        print(f"  {len(predictions)} createable fields\n")

        # Group by keyword
        by_keyword = {}
        for p in predictions:
            kw = p["keyword"] or "UNKNOWN"
            if kw not in by_keyword:
                by_keyword[kw] = []
            by_keyword[kw].append(p)

        for keyword in sorted(by_keyword.keys()):
            fields = by_keyword[keyword]
            print(f"  {keyword}:")
            for p in fields:
                req = " [REQUIRED]" if p["required"] else ""
                conf = f" ({p['confidence']})" if p["confidence"] != "certain" else ""
                pv = ""
                if p["picklist_values"]:
                    pv = f" | values: {', '.join(p['picklist_values'][:3])}"
                    if len(p["picklist_values"]) > 3:
                        pv += f", +{len(p['picklist_values']) - 3}"
                print(f"    {p['field_name']:32} {p['label']:30}{req}{conf}{pv}")

                # Show locators if requested
                if args.locators:
                    for loc in p["locators"]:
                        print(f"      [{loc['strategy']}] {loc['note']}")

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
