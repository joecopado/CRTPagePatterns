#!/usr/bin/env python3
"""Page-inventory layers: app_chrome, related_list_actions, list_view_chrome, control_tabs.

Usage:
  python3 tools/qforce-lite/discovery/page_chrome.py app-chrome   --org <alias> [--brief]
  python3 tools/qforce-lite/discovery/page_chrome.py list-view-chrome
  python3 tools/qforce-lite/discovery/page_chrome.py related-list-actions --org <alias> --object <Obj>
  python3 tools/qforce-lite/discovery/page_chrome.py control-tabs  --org <alias> --object <Obj>

WHY (stream B5, 2026-09-07, from PB0's measurement in
docs/recorder/evidence/metadata-dom-parity-2026-09-07.md): the org map explains **16.4%** of the
rendered DOM and only 18.6% of its own predictions render. The named causes were not metadata
defects -- they were whole categories of page furniture the map has no layer for:

  * 208 unpredicted controls were **console app / global header / utility bar chrome** -- org
    level, identical on every page of an app, and entirely absent from the map;
  * 17 named + a share of 632 unmapped buttons were **related-list actions** -- and the Layout XML
    the `page_layouts` transport ALREADY fetches carries `<relatedLists><relatedList>` with
    `customButtons` / `excludeButtons` / `fields` / `quickActions`, of which
    `layers/page_layouts.py` parses `layoutSections` only and discards the rest (113 such blocks
    sit unread in slockard's map today, 469 in dev1's);
  * 25 were **list-view chrome** -- a fixed platform vocabulary, no org call needed at all;
  * ~450 of 646 "predicted-not-rendered" were behind an **unopened Details/Related tab** -- a
    false miss, not a metadata error, and separable with an annotation rather than a new fetch.

PRIOR ART CHECKED (capability index, "org map layer related list actions app chrome utility bar
list view chrome tab annotation"): nothing covers these. The closest is `render_stack.app_shell`,
which computes navType/utilityBar/tabs ad hoc inside a per-object layer that is DEFAULT OFF and
populated on no map -- the fact exists as a function and has never existed as a cached fact.
`app_chrome` is the org-level persistence of it (an app shell is an org fact, not an object fact)
and REUSES `render_stack.utility_bar_components` rather than re-implementing the FlexiPage read.

COST. Three of the four layers cost ZERO API calls:
  * `related_list_actions` and `control_tabs` are OFFLINE derivations of `page_layouts.metadata`
    and `record_page` -- exactly the shape of `detail_layout_sections` (parse more of a response
    already paid for). That is also why `discover.py derive` exists: they can be BACKFILLED onto
    an existing map with no org contact, which `refresh` could never do (METADATA-CACHE.md: a
    refresh is a delta and never adds a layer).
  * `list_view_chrome` is a versioned platform CONSTANT -- Salesforce's list-view furniture is
    the same on every org and every object; recording it in the map (rather than hard-coding it
    in a consumer) is what lets a consumer say "this control is platform chrome" offline.
  * `app_chrome` is the only one that talks to an org: one Tooling query + one Metadata read per
    CustomApplication, then one FlexiPage read per DISTINCT utility bar.

TRI-STATE. `mapio.wrap`'s envelope admits exactly {live, offline, could-not-check} and a first
draft of this module invented a fourth word, `platform-default`, which `wrap()`'s own assert
caught (test_page_chrome.py, seen failing). A platform vocabulary is a fact derived with NO org
call, so its envelope word is **`offline`** -- and the precision that would have been lost is
carried INSIDE the value as `basis: "platform-constant"` / `tab_source: "platform-default"`.
Read that field before quoting one of these layers as an observation of a particular org: it is
not one. (Org-level layers written as plain dicts rather than through `wrap()` -- `app_chrome`,
`list_view_chrome` -- follow `app_visibility`'s precedent and may also say `partial`.)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]

from mapio import wrap, now_iso  # noqa: F401

# =============================================================================================
# Platform vocabularies -- VERSIONED constants, not observations.
# Bump the version string whenever a row changes so a consumer can tell two vintages apart.
# =============================================================================================

GLOBAL_HEADER_VERSION = "2026-09-07.1"

#: The Lightning global header, present on every page of every Lightning app. Labels are the
#: accessible names QWeb/the recorder actually resolve; a consumer lowercases with its own norm().
GLOBAL_HEADER_CONTROLS = [
    {"label": "App Launcher", "keyword": "ClickText", "role": "button"},
    {"label": "Search", "keyword": "TypeText", "role": "combobox"},
    {"label": "Favorites", "keyword": "ClickText", "role": "button"},
    {"label": "Add Favorite", "keyword": "ClickText", "role": "button"},
    {"label": "Edit Favorite", "keyword": "ClickText", "role": "button"},
    {"label": "Setup", "keyword": "ClickText", "role": "button"},
    {"label": "Go To Setup", "keyword": "ClickText", "role": "menuitem"},
    {"label": "Notifications", "keyword": "ClickText", "role": "button"},
    {"label": "Help", "keyword": "ClickText", "role": "button"},
    {"label": "Guidance Center", "keyword": "ClickText", "role": "button"},
    {"label": "View Profile", "keyword": "ClickText", "role": "button"},
    {"label": "User", "keyword": "ClickText", "role": "button"},
    {"label": "Global Actions", "keyword": "ClickText", "role": "button"},
    {"label": "Show Menu", "keyword": "ClickText", "role": "button"},
    {"label": "Toggle Navigation Menu", "keyword": "ClickText", "role": "button"},
    {"label": "Skip to main content", "keyword": "ClickText", "role": "link"},
    {"label": "Learn More", "keyword": "ClickText", "role": "link"},
]

#: Console-only shell furniture (navType == "Console"). A standard-nav app renders NONE of it,
#: which is precisely why this is per-app and not merged into the global header list.
CONSOLE_SHELL_CONTROLS = [
    {"label": "Close Tab", "keyword": "ClickText", "role": "button"},
    {"label": "Close", "keyword": "ClickText", "role": "button"},
    {"label": "Show Tabs", "keyword": "ClickText", "role": "button"},
    {"label": "Open Tab Menu", "keyword": "ClickText", "role": "button"},
    {"label": "Toggle Panel", "keyword": "ClickText", "role": "button"},
    {"label": "Toggle Side Panel", "keyword": "ClickText", "role": "button"},
    {"label": "Back", "keyword": "ClickText", "role": "button"},
    {"label": "History", "keyword": "ClickText", "role": "button"},
    {"label": "Most Recent Tabs", "keyword": "ClickText", "role": "button"},
    {"label": "Pop out", "keyword": "ClickText", "role": "button"},
    {"label": "Refresh Tab", "keyword": "ClickText", "role": "menuitem"},
]

LIST_VIEW_CHROME_VERSION = "2026-09-07.1"

#: The furniture around EVERY Lightning list-view / related-list-view page. Fixed platform
#: vocabulary -- 25 unpredicted controls in PB0's population were exactly this.
LIST_VIEW_CHROME_CONTROLS = [
    {"label": "Select a List View", "keyword": "ClickText", "role": "button"},
    {"label": "List View Controls", "keyword": "ClickText", "role": "button"},
    {"label": "Search this list", "keyword": "TypeText", "role": "searchbox"},
    {"label": "Filter", "keyword": "ClickText", "role": "button"},
    {"label": "Filters", "keyword": "ClickText", "role": "button"},
    {"label": "Edit List Filters", "keyword": "ClickText", "role": "button"},
    {"label": "Sort", "keyword": "ClickText", "role": "button"},
    {"label": "Sort by", "keyword": "ClickText", "role": "button"},
    {"label": "Display As", "keyword": "ClickText", "role": "button"},
    {"label": "Refresh", "keyword": "ClickText", "role": "button"},
    {"label": "Chart", "keyword": "ClickText", "role": "button"},
    {"label": "Charts", "keyword": "ClickText", "role": "button"},
    {"label": "Select All", "keyword": "ClickCheckbox", "role": "checkbox"},
    {"label": "Select Item", "keyword": "ClickCheckbox", "role": "checkbox"},
    {"label": "Show actions", "keyword": "ClickText", "role": "button"},
    {"label": "Printable View", "keyword": "ClickText", "role": "button"},
    {"label": "New", "keyword": "ClickText", "role": "button"},
    {"label": "Import", "keyword": "ClickText", "role": "button"},
    {"label": "Change Owner", "keyword": "ClickText", "role": "button"},
    {"label": "Pin this list view", "keyword": "ClickText", "role": "button"},
    {"label": "Update this list view", "keyword": "ClickText", "role": "menuitem"},
    {"label": "New List View", "keyword": "ClickText", "role": "menuitem"},
    {"label": "Clone", "keyword": "ClickText", "role": "menuitem"},
    {"label": "Rename", "keyword": "ClickText", "role": "menuitem"},
    {"label": "Sharing Settings", "keyword": "ClickText", "role": "menuitem"},
    {"label": "Select Columns to Display", "keyword": "ClickText", "role": "menuitem"},
]

#: The standard actions a related list renders when the layout removes none of them. A layout's
#: `<excludeButtons>` names the ones it takes AWAY (Salesforce's own "New"/"Add" spelling), so
#: this is the base set the exclusions are subtracted from.
RELATED_LIST_STANDARD_ACTIONS_VERSION = "2026-09-07.1"
RELATED_LIST_STANDARD_ACTIONS = ["New", "Add", "View All", "Show more"]

#: Standard record-page tabs on the platform's own record-home templates. Anything derived from
#: this is `platform-default`, never `live`.
TAB_DEFAULTS_VERSION = "2026-09-07.1"
STANDARD_RECORD_TABS = ["Related", "Details", "News", "Activity", "Chatter"]
#: Which tab a control predicted from a given map layer lands behind, on a standard record page.
SOURCE_TO_TAB = {
    "detail_layout_sections": "Details",
    "page_layouts": "Details",
    "related_list_actions": "Related",
    "quick_actions": None,          # highlights-panel action bar -- not behind any tab
    "navigation": None,             # app nav bar -- not behind any tab
    "record_page": None,            # a FlexiPage component names its own region
    "app_chrome": None,
    "list_view_chrome": None,
}


def list_view_chrome_layer() -> dict:
    """The list-view chrome vocabulary as a map fact. NO org contact -- a platform constant."""
    return {
        "verified": "offline",
        "basis": "platform-constant",
        "version": LIST_VIEW_CHROME_VERSION,
        "controls": LIST_VIEW_CHROME_CONTROLS,
        "control_count": len(LIST_VIEW_CHROME_CONTROLS),
        "source": "platform vocabulary (page_chrome.LIST_VIEW_CHROME_CONTROLS), no org call",
        "caveat": "basis=platform-constant is NOT a live observation of this org: a list view "
                  "whose layout removes a standard button still lists it here",
    }


# =============================================================================================
# app_chrome -- ORG LEVEL, per CustomApplication
# =============================================================================================

def _utility_items(md: dict) -> list:
    """`CustomApplication.Metadata.utilityBar` names a FlexiPage of Type='UtilityBar'; the items
    themselves live in that FlexiPage. Some orgs instead inline `utilityBarButtons`. Both are read
    here; neither being present is an honest empty (an app CAN have no utility bar), not a
    could-not-check."""
    items = []
    for key in ("utilityBarButtons", "utilityBar_items"):
        for it in (md.get(key) or []):
            if isinstance(it, dict):
                items.append({"label": it.get("label") or it.get("name"),
                              "component": it.get("componentName") or it.get("component")})
    return items


def app_chrome_layer(alias: str, apps: dict | None = None) -> dict:
    """{"verified","apps": {DeveloperName: {...}}, "global_header": {...}} -- the app shell every
    page of an app renders before any object-specific control exists.

    `apps` may be injected (DeveloperName -> CustomApplication Metadata blob) so this is
    unit-testable with no org; the default path fetches through `flexipage` and then reads each
    DISTINCT utility bar's FlexiPage once via `render_stack.utility_bar_components`."""
    src = ("Tooling CustomApplication.Metadata (navType/uiType/utilityBar/tabs) "
           "+ FlexiPage(UtilityBar)")
    unreadable: list = []
    if apps is None:
        try:
            import flexipage
            base, tok = flexipage.sess(alias)
            rows = flexipage.tq(base, tok,
                                "SELECT Id, DeveloperName, Label FROM CustomApplication "
                                "ORDER BY DeveloperName")
        except Exception as e:                       # noqa: BLE001 -- tri-state, never raise
            return {"verified": "could-not-check", "reason": str(e)[:200], "apps": {},
                    "source": src, "global_header": _global_header()}
        apps = {}
        for r in rows:
            try:
                md = flexipage.tooling_metadata(base, tok, "CustomApplication", r["Id"]) or {}
                md.setdefault("label", r.get("Label"))
                apps[r["DeveloperName"]] = md
            except Exception:                        # noqa: BLE001
                unreadable.append(r.get("DeveloperName"))
        bar_cache: dict = {}

        def _bar(name):
            if name not in bar_cache:
                try:
                    import render_stack as RS
                    got = RS.utility_bar_components(alias, name)
                    bar_cache[name] = ((got.get("value") or {}).get("components")
                                       if isinstance(got, dict) else None) or []
                except Exception:                    # noqa: BLE001
                    bar_cache[name] = []
            return bar_cache[name]
    else:
        def _bar(name):
            return []

    out_apps: dict = {}
    for name, md in sorted((apps or {}).items()):
        md = md or {}
        nav = md.get("navType")
        console = (nav == "Console") or bool(md.get("isServiceCloudConsole"))
        bar_name = md.get("utilityBar")
        items = _utility_items(md)
        components = _bar(bar_name) if bar_name else []
        out_apps[name] = {
            "label": md.get("label"),
            "nav_type": nav,
            "ui_type": md.get("uiType"),
            "console": console,
            # A console app renders workspace tabs AND subtabs; a standard-nav app renders
            # neither. This is the "subtab/tertiary tab capability" a consumer needs to decide
            # whether a `tab`-shaped control on the page is app chrome or page content.
            "subtabs_capable": console,
            "utility_bar": bar_name,
            "utility_items": items,
            "utility_components": components,
            "utility_item_count": len(items) or len(components),
            "tab_count": len(md.get("tabs") or []),
            "default_landing_tab": md.get("defaultLandingTab"),
            "workspace_tab_count": len(((md.get("workspaceConfig") or {}).get("mappings")) or []),
            "form_factors": sorted(md.get("formFactors") or []),
            # Everything a page of THIS app renders before any record control does.
            "chrome_controls": _chrome_controls(console, items, components),
        }
    verified = ("live" if (out_apps and not unreadable)
                else ("partial" if out_apps else "could-not-check"))
    return {
        "verified": verified,
        "source": src,
        "app_count": len(out_apps),
        "console_app_count": sum(1 for v in out_apps.values() if v["console"]),
        "apps_unreadable": sorted(x for x in unreadable if x),
        "global_header": _global_header(),
        "apps": out_apps,
    }


def _global_header() -> dict:
    return {"version": GLOBAL_HEADER_VERSION, "controls": GLOBAL_HEADER_CONTROLS,
            "control_count": len(GLOBAL_HEADER_CONTROLS),
            "verified": "platform-constant",
            "source": "platform vocabulary (page_chrome.GLOBAL_HEADER_CONTROLS), no org call"}


def _chrome_controls(console: bool, items: list, components: list) -> list:
    """Every chrome control a page of this app renders: the global header (always), the console
    shell (console apps only), and the app's own utility-bar items (which ARE org metadata)."""
    out = [dict(c, source="global_header") for c in GLOBAL_HEADER_CONTROLS]
    if console:
        out += [dict(c, source="console_shell") for c in CONSOLE_SHELL_CONTROLS]
    for it in items:
        if it.get("label"):
            out.append({"label": it["label"], "keyword": "ClickText", "role": "button",
                        "source": "utility_bar"})
    for comp in components:
        if isinstance(comp, str):
            out.append({"label": comp, "keyword": "ClickText", "role": "button",
                        "source": "utility_bar_component"})
    return out


def read_app_chrome(mp: dict) -> dict | None:
    """`org_level.app_chrome` out of a loaded map, or None. The ONE reader every consumer uses --
    a consumer that reaches into the raw dict is what makes a shape change silently break."""
    if not isinstance(mp, dict):
        return None
    entry = (mp.get("org_level") or {}).get("app_chrome")
    if not isinstance(entry, dict):
        return None
    val = entry.get("value") if "value" in entry else entry
    return val if isinstance(val, dict) else None


def read_list_view_chrome(mp: dict) -> dict | None:
    """`org_level.list_view_chrome` out of a loaded map, or None."""
    if not isinstance(mp, dict):
        return None
    entry = (mp.get("org_level") or {}).get("list_view_chrome")
    if not isinstance(entry, dict):
        return None
    val = entry.get("value") if "value" in entry else entry
    return val if isinstance(val, dict) else None


def app_chrome_controls(mp: dict, app: str | None = None) -> list:
    """Every chrome control the map says renders -- for one app, or the union across apps when no
    app is named (a capture usually cannot say which app it came from). A map with no app_chrome
    layer still returns the platform global header, because that much is true of every org."""
    layer = read_app_chrome(mp) or {}
    apps = layer.get("apps") or {}
    if app and app in apps:
        return list(apps[app].get("chrome_controls") or [])
    seen, out = set(), []
    for row in (apps.values() if apps else []):
        for c in (row.get("chrome_controls") or []):
            k = (c.get("label") or "").strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(c)
    if not out:
        out = [dict(c, source="global_header") for c in GLOBAL_HEADER_CONTROLS]
    return out


def list_view_chrome_controls(mp: dict) -> list:
    """The list-view chrome vocabulary from the map, falling back to the module constant."""
    layer = read_list_view_chrome(mp) or {}
    return list(layer.get("controls") or LIST_VIEW_CHROME_CONTROLS)


# =============================================================================================
# related_list_actions -- PER OBJECT, derived offline from page_layouts.metadata
# =============================================================================================

def parse_related_lists(metadata: dict | None) -> list | None:
    """[{name, fields, custom_buttons, exclude_buttons, quick_actions, sort_field, actions}] for
    one Layout Metadata blob's `<relatedLists>`. Returns None (not []) when `metadata` is missing
    or malformed -- never fabricate "this layout has no related lists" for a fetch that failed.

    `actions` is the RESOLVED action set a user sees: the platform's standard actions minus the
    layout's `excludeButtons`, plus its `customButtons` and `quickActions`."""
    if not isinstance(metadata, dict):
        return None
    rls = metadata.get("relatedLists")
    if rls is None:
        return None
    if isinstance(rls, dict):        # a layout with exactly one related list serialises as a dict
        rls = [rls]
    out = []
    for rl in rls:
        if not isinstance(rl, dict):
            continue

        def _lst(key, _rl=rl):
            v = _rl.get(key) or []
            return [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)]

        excluded = _lst("excludeButtons")
        custom = _lst("customButtons")
        quick = _lst("quickActions")
        standard = [a for a in RELATED_LIST_STANDARD_ACTIONS if a not in excluded]
        out.append({
            "name": rl.get("relatedList"),
            "fields": _lst("fields"),
            "custom_buttons": custom,
            "exclude_buttons": excluded,
            "quick_actions": quick,
            "sort_field": rl.get("sortField"),
            "sort_order": rl.get("sortOrder"),
            "actions": standard + custom + quick,
        })
    return out


def build_related_list_actions(pl_by_obj: dict) -> dict:
    """{sobject: wrapped related_list_actions} from already-fetched `page_layouts` entries -- the
    same offline-derivation shape as `build_detail_layout_sections`, ZERO API calls. Inherits each
    page_layouts entry's own verified status rather than re-deriving one."""
    out = {}
    for obj, wrapped in (pl_by_obj or {}).items():
        rows = (wrapped or {}).get("value") if isinstance(wrapped, dict) else None
        rows = rows or []
        entries, controls, seen = [], [], set()
        for r in rows:
            rls = parse_related_lists(r.get("metadata"))
            entries.append({"layout_name": r.get("name"), "related_lists": rls,
                            "error": r.get("error")})
            for rl in (rls or []):
                for label in rl.get("actions") or []:
                    key = (label.strip().lower(), rl.get("name"))
                    if not label.strip() or key in seen:
                        continue
                    seen.add(key)
                    controls.append({"label": label, "related_list": rl.get("name"),
                                     "keyword": "ClickText", "tab": "Related",
                                     "source": "related_list_actions"})
        v = (wrapped.get("verified", "could-not-check")
             if isinstance(wrapped, dict) else "could-not-check")
        out[obj] = wrap({"layouts": entries, "controls": controls,
                         "related_list_count": sum(len(e.get("related_lists") or [])
                                                   for e in entries),
                         "control_count": len(controls),
                         "standard_actions_version": RELATED_LIST_STANDARD_ACTIONS_VERSION},
                        f"parsed-from-page_layouts.metadata.relatedLists:{obj}", v)
    return out


def read_related_list_actions(node: dict) -> dict | None:
    """The `related_list_actions` layer off one map object node, unwrapped, or None."""
    if not isinstance(node, dict):
        return None
    entry = node.get("related_list_actions")
    if not isinstance(entry, dict):
        return None
    val = entry.get("value") if "value" in entry else entry
    return val if isinstance(val, dict) else None


# =============================================================================================
# control_tabs -- PER OBJECT: which record-page tab a predicted control lives behind
# =============================================================================================

def build_control_tabs(record_page_by_obj: dict) -> dict:
    """{sobject: wrapped control_tabs}. Offline: reads the `record_page` layer already in the map.

    PB0's finding: ~450 of 646 predicted-not-rendered controls were behind an unopened tab. A
    record page lands on ONE tab; every control in another tab is genuinely not in the DOM, and
    scoring that as a metadata miss is wrong. This layer says, per control SOURCE, which tab the
    control lives behind, so a consumer can class a miss "behind tab X" instead.

    A FlexiPage that DECLARES tabs gives them live; a page on a platform record-home template
    declares none, and the platform's own tabset is used -- recorded as `platform-default`,
    never `live`."""
    out = {}
    for obj, wrapped in (record_page_by_obj or {}).items():
        rp = (wrapped or {}).get("value") if isinstance(wrapped, dict) else wrapped
        declared, page_names = [], []
        for page_name, page in ((rp or {}).get("pages") or {}).items():
            page_names.append(page_name)
            for t in ((page or {}).get("tabs") or []):
                lbl = t.get("label") if isinstance(t, dict) else str(t)
                if lbl and lbl not in declared:
                    declared.append(lbl)
        if declared:
            tabs, verified, tab_source = declared, "live", "flexipage-declared"
            source = "FlexiPage tabs (record_page.pages[*].tabs)"
            default_tab = declared[0]
        else:
            # `offline` is the envelope word (no org call); `tab_source` carries the precision --
            # see this module's TRI-STATE note. Never quote this as an observation of the org.
            tabs, verified, tab_source = list(STANDARD_RECORD_TABS), "offline", "platform-default"
            source = (f"platform record-home tabset (page_chrome.STANDARD_RECORD_TABS "
                      f"v{TAB_DEFAULTS_VERSION}) -- the FlexiPage declares no tabs")
            # A Lightning record page opens on the FIRST tab, which on the platform template is
            # Related -- which is exactly why layout fields (Details) so often do not render.
            default_tab = "Related"
        out[obj] = wrap({"tabs": tabs, "default_tab": default_tab,
                         "tab_source": tab_source,
                         "source_to_tab": dict(SOURCE_TO_TAB),
                         "pages": sorted(page_names),
                         "version": TAB_DEFAULTS_VERSION},
                        source, verified)
    return out


def tab_for(control_source: str, control_tabs: dict | None) -> str | None:
    """Which tab a predicted control from `control_source` lives behind, or None for a control
    that is not behind any tab (an action-bar button, the app nav). Reads the per-object
    `control_tabs` layer when there is one and falls back to the platform mapping."""
    mapping = dict(SOURCE_TO_TAB)
    if isinstance(control_tabs, dict):
        got = control_tabs.get("source_to_tab")
        if isinstance(got, dict):
            mapping.update(got)
    return mapping.get(control_source)


def read_control_tabs(node: dict) -> dict | None:
    """The `control_tabs` layer off one map object node, unwrapped, or None."""
    if not isinstance(node, dict):
        return None
    entry = node.get("control_tabs")
    if not isinstance(entry, dict):
        return None
    val = entry.get("value") if "value" in entry else entry
    return val if isinstance(val, dict) else None


# =============================================================================================
# CLI
# =============================================================================================

def _load_map(alias: str) -> dict:
    from mapio import MAP_DIR
    return json.loads((Path(MAP_DIR) / f"{alias}.json").read_text())


def _cmd_app_chrome(a) -> int:
    layer = app_chrome_layer(a.org)
    if a.brief:
        layer = {k: v for k, v in layer.items() if k not in ("apps", "global_header")}
        layer["note"] = "--brief: per-app detail and the global-header vocabulary omitted"
    print(json.dumps(layer, indent=1))
    return 0


def _cmd_list_view_chrome(a) -> int:
    print(json.dumps(list_view_chrome_layer(), indent=1))
    return 0


def _cmd_related(a) -> int:
    mp = _load_map(a.org)
    node = (mp.get("objects") or {}).get(a.object) or {}
    print(json.dumps(build_related_list_actions({a.object: node.get("page_layouts")})[a.object],
                     indent=1))
    return 0


def _cmd_tabs(a) -> int:
    mp = _load_map(a.org)
    node = (mp.get("objects") or {}).get(a.object) or {}
    print(json.dumps(build_control_tabs({a.object: node.get("record_page")})[a.object], indent=1))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true", help="emit JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("app-chrome", help="org-level app shell layer (LIVE org call)")
    p1.add_argument("--org", required=True)
    p1.add_argument("--brief", action="store_true", help="omit the per-app detail")
    p1.set_defaults(func=_cmd_app_chrome)

    p2 = sub.add_parser("list-view-chrome", help="the platform list-view vocabulary (no org call)")
    p2.set_defaults(func=_cmd_list_view_chrome)

    p3 = sub.add_parser("related-list-actions",
                        help="derive one object's related-list actions from the map (no org call)")
    p3.add_argument("--org", required=True)
    p3.add_argument("--object", required=True)
    p3.set_defaults(func=_cmd_related)

    p4 = sub.add_parser("control-tabs",
                        help="derive one object's record-page tab annotation (no org call)")
    p4.add_argument("--org", required=True)
    p4.add_argument("--object", required=True)
    p4.set_defaults(func=_cmd_tabs)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
