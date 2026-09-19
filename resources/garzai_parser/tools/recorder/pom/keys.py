"""keys -- the page key: the identity a page has across sessions, days and orgs.

Usage: python3 tools/recorder/pom/keys.py <url> [--org alias] [--refresh-hosts]

A page key is `<partition>|<pattern>[|app=<app>][|rt=<RecordTypeId>][|layout=<hash8>]` where the
partition is the ORG ALIAS for Salesforce hosts (never the host -- dev1 and slockard share URL
patterns and must never collide; user, 2026-09-05) and the host for everything else. Record ids,
session tokens, counters and cache-busters are normalised out; the object, the action
(view/edit/new/list), the record type and the LIGHTNING APP are kept, because they decide what
renders.

D15 (user, 2026-09-18: "the app should [be in the key]. That is the only way we know sales
lightning vs sales console") REVERSES the 2026-09-15 collapse that folded `/lightning/app/<id>/r/…`
onto the bare `/lightning/r/…` key. Measured that night on cicd-demo: one key
`/lightning/r/copado__User_Story__c/{id}/view` held 128 controls learned in TWO Lightning apps, and
the store asserted a `Revenue Cloud Settings` control (and a 133-control modal behind it) that does
not exist on that page in the other app. The app is now a KEY SEGMENT -- the app's developer name
when the org map's `org_level.apps` layer can resolve the 06m DurableId, else the 06m id itself,
which is stable per org and is therefore identity, not a dynamic value. An app-LESS route keeps its
own key: a direct link and an in-app link are two different reachability stories, not one page.

Every DYNAMIC segment class is a placeholder, never a raw value (feedback rule
`page-keys-are-structural-and-carry-a-reachability-verdict`, user 2026-09-18: "storing a dynamic
value as a raw portion of a key is unmaintainable"): 15/18-char record ids `{id}`, dashed GUIDs
`{uuid}`, 16+ contiguous hex `{hash}`, per-session IPv4 `{ip}`, bare counters `{n}`, and an epoch
suffix `<name>_<10+ digits>` -> `<name>_{epoch}` (`vfFrameId_1757000000000`).

Two WRAPPERS are unwrapped to the page they carry rather than keyed as themselves:
  frontdoor/login  `?retURL=` / `?startURL=` (and the `&retURL=` form Salesforce also emits, which
                   urlparse leaves sitting in the PATH -- measured on slockard, two store records
                   keyed `slockard|/secur/frontdoor.jsp&retURL=/lightning/o/Account/list`)
  aloha            `/one/one.app#<base64 JSON>` whose `attributes.address` is the real route.
                   Before this, EVERY aloha-wrapped Visualforce page in an org collapsed into one
                   key and one element list (`cicd-demo|/one/one.app`; evidence
                   `docs/recorder/evidence/live-transitions-review-copado-2026-09-18.md` GAP 4).

Alias resolution never imports qforce_lite/selenium (this runs on up.py's light path): the
sandbox naming regex first (`co…--dev1.sandbox…` -> dev1), then a cached host-stem table built
once from `sf org list --json` (FORCE_COLOR=0) at ~/.claude/state/org-map/hosts.json.
Capability check (write guard, 2026-09-05): tools/capabilities/lookup.py found no page-key or
page-object store; the recorder skill and qforce-lite are consumers, not providers.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlparse

STATE = os.path.expanduser("~/.claude/state")
ORG_MAP_DIR = os.path.join(STATE, "org-map")
APPS_DIR = os.path.join(STATE, "apps")
HOSTS_CACHE = os.path.join(ORG_MAP_DIR, "hosts.json")

SF_HOST_SUFFIXES = (
    ".lightning.force.com", ".my.salesforce.com", ".my.salesforce-setup.com", ".my.site.com",
    ".vf.force.com", ".visualforce.com",
)
# APP ROOTS whose whole surface is ONE page: the chrome -- tab bar, chat box, sidebar, run
# controls -- is identical on every route beneath them, so every path under the prefix collapses to
# a single page key `<host>|<prefix>`. User decision 2026-09-12 for Copado AI: "we should do it as
# simply as robotic.copado.com/ai specifically, as that is where we are... different workspaces will
# have similar interfaces, it is a 1 size fits all."
#
# It is a PREFIX, not the bare host, and that distinction matters: `robotic.copado.com` also serves
# the Robotic Testing / PACE UI, which is a different interface. Collapsing the host would merge two
# unrelated apps into one page object. Add an entry only when the routes beneath it really do share
# one control set; a multi-layout app stays path-keyed.
SINGLE_SURFACE_APPS = {
    "robotic.copado.com": ("/ai",),
    "app.robotic.copado.com": ("/ai",),
}


def single_surface_prefix(host: str, pattern: str) -> str | None:
    """The app-root prefix `pattern` falls under, or None. `/ai` matches `/ai` and `/ai/...`,
    never `/airflow`."""
    for pre in SINGLE_SURFACE_APPS.get((host or "").lower(), ()):
        if pattern == pre or (pattern or "").startswith(pre + "/"):
            return pre
    return None

SF_ID = re.compile(r"^[a-zA-Z0-9]{15}([a-zA-Z0-9]{3})?$")
# A REAL record id always carries a digit: the 3-char key prefix is numeric-ish (001, 00Q, a1v,
# 06m) and the 2-char instance id + 9-char serial are base-62. Plain SF_ID matches any 15- or
# 18-character word, so an OBJECT name of exactly that length -- InsurancePolicy (15),
# ServiceAppointment (18), InteractionSummary (18) -- was read as an id. sf_pattern already guards
# its own branches against that (2026-09-10, three of seventeen industry pages); this is the same
# guard for the GENERIC segment normaliser, which had none.
LIKELY_SF_ID = re.compile(r"^(?=[a-zA-Z0-9]*\d)[a-zA-Z0-9]{15}([a-zA-Z0-9]{3})?$")
# `vfFrameId_1757000000000`, `<name>_<10+ digits>`: a millisecond/second epoch stamped into a
# segment at render time. CLAUDE.md's locator doctrine names the same shape as a never-a-locator
# generated value; it is a never-a-page-key value for the same reason.
EPOCH_SUFFIX = re.compile(r"^(.*[A-Za-z_-])_?\d{10,}$")
# A Lightning app addressed by its 06m DurableId. The app is IDENTITY (D15), not a dynamic value:
# the same id names the same app for the life of the org.
APP_DURABLE_ID = re.compile(r"^06m[a-zA-Z0-9]{12}([a-zA-Z0-9]{3})?$")
# 8-4-4-4-12 hex, the identifier shape non-Salesforce apps use for records in a URL path.
UUID_SEG = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
# Strict dotted-quad, every octet 0-255, so version-like segments (1.2.3, v1.0.0, 2026.09.12) and
# out-of-range shapes (999.1.1.1, 10.4.23.256) are left alone.
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_SEG = re.compile(r"^%s(?:\.%s){3}$" % (_OCTET, _OCTET))

# H9 / B3 (PAGE-SHEET-BUILD-2026-09-07.md SS3, WIRING-AUDIT-2026-09-07.md SS3): Salesforce
# redirects to the SHORT record URL after Save -- `/lightning/r/<Id>/view`, no object segment.
# Without this, sf_pattern's `/lightning/r/<Obj>/{id}/<action>` branch mis-assigns the ID itself
# to `object` (segs[2] is the id, not an object name), producing a unique, unmatchable key per
# record with no `layout=` component -- the POM can never accumulate on the page the coverage
# target ends on. Resolve the object from the id's 3-char key prefix: the org map's
# `inventory.key_prefix`/`keyPrefix` layer first (when it lands -- present on dev1 as of 2026-09-07; recache pending on slockard/fsc7f/health90
# as of 2026-09-07), then this table of PLATFORM-FIXED standard prefixes. A custom object's prefix
# is org-specific and NOT guessed here -- it stays COULD-NOT-CHECK (object=None) rather than a
# wrong resolution, which is worse than an unmatchable key.
STANDARD_KEY_PREFIXES = {
    "001": "Account", "003": "Contact", "005": "User", "006": "Opportunity", "00Q": "Lead",
    "500": "Case", "00T": "Task", "00U": "Event", "800": "Contract", "701": "Campaign",
    "0Q0": "Quote",
}


def object_for_record_id(rec_id: str, org_map: dict | None = None):
    """(object_or_None, source_or_None). Mirrors page_sheet/states.py's
    object_for_record_id/STANDARD_KEY_PREFIXES -- kept here too so keys.py needs no import
    of page_sheet (this module is on up.py's light client path and must stay import-light)."""
    if not rec_id or len(rec_id) < 3:
        return None, None
    prefix = rec_id[:3]
    if isinstance(org_map, dict):
        for name, obj in (org_map.get("objects") or {}).items():
            inv = obj.get("inventory") or {}
            for k in ("key_prefix", "keyPrefix"):
                v = inv.get(k)
                v = v.get("value") if isinstance(v, dict) else v
                if v == prefix:
                    return name, "org map objects.%s.inventory.%s" % (name, k)
    if prefix in STANDARD_KEY_PREFIXES:
        return STANDARD_KEY_PREFIXES[prefix], "platform-fixed standard key prefix %s" % prefix
    return None, None
SANDBOX = re.compile(r"--([A-Za-z0-9]+)\.sandbox\.")
DROP_PARAMS = {"count", "uid", "nooverride", "useRecordTypeCheck", "navigationLocation",
               "backgroundContext", "sid", "otp", "token", "ec", "_t", "ts", "cb"}


def is_salesforce_host(host: str) -> bool:
    h = (host or "").lower()
    return h.endswith(SF_HOST_SUFFIXES) or h in ("login.salesforce.com", "test.salesforce.com")


def host_stem(host: str) -> str:
    """'slockard-dev-ed.lightning.force.com' -> 'slockard-dev-ed';
    'co1787568012932--dev1.sandbox.lightning.force.com' -> 'co1787568012932--dev1'."""
    h = (host or "").lower()
    for suf in (".sandbox.lightning.force.com", ".sandbox.my.salesforce.com",
                ".sandbox.my.salesforce-setup.com") + SF_HOST_SUFFIXES:
        if h.endswith(suf):
            return h[: -len(suf)]
    return h


def _load_hosts_cache() -> dict:
    try:
        with open(HOSTS_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def refresh_hosts_cache() -> dict:
    """Build host-stem -> alias from `sf org list --json` (once; cached). Never prints tokens."""
    env = dict(os.environ, FORCE_COLOR="0", NO_COLOR="1")
    try:
        out = subprocess.run(["sf", "org", "list", "--json"], capture_output=True, text=True,
                             timeout=60, env=env).stdout
        data = json.loads(out).get("result", {})
    except Exception:
        return _load_hosts_cache()
    table: dict[str, str] = {}
    for group in data.values():
        if not isinstance(group, list):
            continue
        for o in group:
            if not isinstance(o, dict) or not o.get("alias") or not o.get("instanceUrl"):
                continue
            table[host_stem(urlparse(o["instanceUrl"]).hostname or "")] = o["alias"]
    os.makedirs(ORG_MAP_DIR, exist_ok=True)
    tmp = HOSTS_CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(table, f, indent=1, sort_keys=True)
    os.replace(tmp, HOSTS_CACHE)
    return table


def alias_for_host(host: str, refresh: bool = False) -> str | None:
    if not is_salesforce_host(host):
        return None
    m = SANDBOX.search(host or "")
    if m:
        return m.group(1)
    table = refresh_hosts_cache() if refresh else _load_hosts_cache()
    stem = host_stem(host)
    if stem in table:
        return table[stem]
    if not refresh and not table:
        return alias_for_host(host, refresh=True)
    return None


RET_IN_PATH = re.compile(r"[?&](retURL|startURL|returnUrl)=(.+)$")


def _unwrap_login(u) -> str | None:
    """frontdoor / login / ec=302 URLs carry the real destination in retURL/startURL.

    Salesforce also emits `/secur/frontdoor.jsp&retURL=/lightning/o/Account/list` -- an `&` where
    the `?` belongs -- and urlparse then leaves the whole thing in `path` with an EMPTY query, so
    the parse_qs branch never fires. Measured on the live slockard store 2026-09-18: two records
    keyed `slockard|/secur/frontdoor.jsp&retURL=/lightning/o/{Account,Contact}/list`, both 0
    elements, both orphans of a page the store already knows."""
    q = parse_qs(u.query)
    for k in ("retURL", "startURL", "returnUrl"):
        if k in q and q[k]:
            return unquote(q[k][0])
    m = RET_IN_PATH.search(u.path or "")
    if m:
        return unquote(m.group(2))
    return None


def _unwrap_aloha(u) -> str | None:
    """`/one/one.app#<base64 JSON>` -> the route its `attributes.address` carries, or None.

    The classic-page wrapper: the decoded fragment is
    `{"componentDef":"one:alohaPage","attributes":{"address":"https://…/apex/copado__GitCommitMain?
    userStoryId=…&variant=userstorycommit"},"state":{}}`. Keying the wrapper itself makes ONE bucket
    for every classic page in the org (GAP 4). Also accepts the un-encoded `#/…` fragment form."""
    if (u.path or "").rstrip("/") not in ("/one/one.app", "/one/one.app/", "/one/one.app"):
        if not (u.path or "").endswith("/one/one.app"):
            return None
    frag = u.fragment or ""
    if not frag:
        return None
    if frag.startswith("/"):
        return frag
    pad = frag + "=" * (-len(frag) % 4)
    for dec in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            data = json.loads(dec(pad).decode("utf-8", "replace"))
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        addr = ((data or {}).get("attributes") or {}).get("address")
        if isinstance(addr, str) and addr:
            return addr
    return None


def app_name(seg: str | None, org_map: dict | None = None) -> tuple[str | None, str | None]:
    """(app name for the key, source). A 06m DurableId resolves to the app's DEVELOPER NAME through
    the org map's `org_level.apps` layer when the map has it; otherwise the id is kept AS IS, because
    it is stable per org and is the identity -- guessing is worse than an honest opaque id.

    Measured 2026-09-18: of the org maps on this machine only **cicd-demo** carries the layer (55
    apps, each with `durable_id`); slockard, dev1 and copado-trial all have `org_level.apps: null`,
    so their app-scoped keys carry the raw 06m id until `discover.py` deepens that layer."""
    if not seg:
        return None, None
    if not APP_DURABLE_ID.match(seg):
        return seg, "url"          # already a developer name: standard__LightningSales, c__MyApp
    apps = ((org_map or {}).get("org_level") or {}).get("apps") or {}
    if isinstance(apps, dict):
        for name, v in apps.items():
            did = (v or {}).get("durable_id") if isinstance(v, dict) else None
            if did and (did == seg or did[:15] == seg[:15]):
                return name, "org map org_level.apps.%s.durable_id" % name
    return seg, "unresolved 06m DurableId (org map has no org_level.apps layer)"


def _norm_segment(seg: str) -> str:
    if LIKELY_SF_ID.match(seg):
        return "{id}"
    if re.fullmatch(r"\d+", seg):
        return "{n}"
    if re.fullmatch(r"[0-9a-f]{16,}", seg, re.I):
        return "{hash}"
    if IPV4_SEG.match(seg):
        # a per-SESSION host id in a path segment, same class as a GUID: the Copado AI IDE iframe is
        # na.agents.copado.com/session/<vm ip>/ide and the VM's IP changes every session
        # (10.4.23.167 one hour, 10.4.23.157 the next), so each session keyed as its own page.
        return "{ip}"
    if UUID_SEG.match(seg):
        # 2026-09-12: a dashed GUID is not 16+ contiguous hex, so it fell through and every
        # Copado AI run page got its own unmatchable key
        # (robotic.copado.com|/ai/workspaces/<guid>/chats/<guid>). That is the same failure H9/B3
        # documents for the Salesforce short record URL: the POM can never accumulate on a page
        # whose key is unique per visit. Non-Salesforce apps identify records this way as a rule.
        return "{uuid}"
    m = EPOCH_SUFFIX.match(seg)
    if m:
        # `vfFrameId_1757000000000` -> `vfFrameId_{epoch}`: the NAME is the page, the stamp is the
        # render. Keeps the readable half, which a bare {n} would have thrown away.
        return m.group(1).rstrip("_") + "_{epoch}"
    return seg


def sf_pattern(path: str, query: dict, org_map: dict | None = None) -> dict:
    """URL-first forms (skill sf-url-navigation) -> {pattern, object, action, record_type, app}."""
    segs = [s for s in path.split("/") if s]
    out: dict = {"pattern": None, "object": None, "action": None, "record_type": None, "app": None}
    rt = (query.get("recordTypeId") or [None])[0]
    # APP-SCOPED ROUTES. D15 (2026-09-18) -- Lightning serves the same ROUTE at two URLs --
    #   /lightning/app/06m7Q0000001l7SQAQ/r/copado__User_Story__c/a1v.../view   (navigated from within an app)
    #   /lightning/r/copado__User_Story__c/a1v.../view                          (a direct link)
    # Before this branch the first form fell into the generic `/lightning/app` case, which joins
    # segs[3:] RAW: the record id was never normalised, `object` came back None, and every visit
    # from inside the app minted its own unmatchable page key -- the same class of failure H9/B3
    # documents for the short record URL. The app id is kept in `app` (it is metadata about how
    # the page was reached, not about which page it is) and the route resolves as if it had been
    # opened directly -- but the app is now carried into the KEY as `|app=<name>` (page_key), so
    # the two forms produce TWO keys, which is D15's whole point: the same route in `Sales` and in
    # `Sales Console` renders different controls, and collapsing them let the store assert a
    # control that a reader on the other app cannot reach.
    if segs[:2] == ["lightning", "app"] and len(segs) > 3 and segs[3] in (
            "r", "o", "n", "page", "setup", "cmp"):
        inner = sf_pattern("/" + "/".join(["lightning"] + segs[3:]), query, org_map=org_map)
        inner["app"] = segs[2]
        return inner
    # 2026-09-10 (three of seventeen industry pages): an OBJECT name of exactly 15 or 18 characters
    # (InsurancePolicy, ServiceAppointment, InteractionSummary) matches the id regex, so the long form
    # was read as the short one and the key became /lightning/r/{id}/<real id> -- unmatchable. The
    # short form has no id in segs[3]; the long form always does.
    if (segs[:2] == ["lightning", "r"] and len(segs) >= 4 and SF_ID.match(segs[2])
            and not SF_ID.match(segs[3])):
        # H9/B3: the SHORT record URL Salesforce redirects to after Save -- no object segment,
        # segs[2] is the record id itself. Resolve the object from its key prefix so this page
        # key collapses onto the SAME key as the long `/lightning/r/<Obj>/<id>/view` form instead
        # of minting one unmatchable key per record.
        rec_id, action = segs[2], (segs[3] if len(segs) > 3 else "view")
        obj, src = object_for_record_id(rec_id, org_map=org_map)
        if obj:
            out.update(pattern=f"/lightning/r/{obj}/{{id}}/{action}", object=obj, action=action)
            out["record_type"] = rt
            out["key_prefix_source"] = src
            return out
        # could-not-check: keep the id in the pattern rather than guess -- unmatchable but honest
        out.update(pattern=f"/lightning/r/{{id}}/{action}", object=None, action=action,
                   could_not_check="short record URL (%s…) and no key-prefix resolution -- "
                                   "custom object prefixes are org-specific and not guessed"
                                   % rec_id[:3])
        out["record_type"] = rt
        return out
    if segs[:2] == ["lightning", "r"] and len(segs) >= 4:
        obj, ident = segs[2], segs[3]
        action = segs[4] if len(segs) > 4 else "view"
        if not SF_ID.match(ident):          # /lightning/r/<Obj>/<related>/… or a relationship
            action = "/".join(segs[3:])
        out.update(pattern=f"/lightning/r/{obj}/{{id}}/{action}", object=obj, action=action)
    elif segs[:2] == ["lightning", "o"] and len(segs) >= 4:
        obj, action = segs[2], segs[3]
        out.update(pattern=f"/lightning/o/{obj}/{action}", object=obj, action=action)
        if action == "list" and query.get("filterName"):
            out["pattern"] += "?filterName=" + query["filterName"][0]
    elif segs[:2] == ["lightning", "setup"]:
        out.update(pattern="/" + "/".join(_norm_segment(s) for s in segs[:4]), action="setup")
    elif segs[:2] == ["lightning", "page"]:
        out.update(pattern="/" + "/".join(segs[:3]), action="page")
    elif segs[:2] == ["lightning", "n"]:
        out.update(pattern="/" + "/".join(segs[:3]), action="tab")
    elif segs[:2] == ["lightning", "app"]:
        # D15: the app is no longer a `{id}` placeholder INSIDE the pattern (which erased which app
        # it was); it leaves the path and becomes the key's `app=` segment, so the app home pages of
        # two apps are two keys and both say which app they are.
        rest = "/" + "/".join(_norm_segment(x) for x in segs[3:]) if len(segs) > 3 else ""
        out.update(pattern="/lightning/app" + rest,
                   app=segs[2] if len(segs) > 2 else None, action="app")
    elif segs[:2] == ["lightning", "cmp"]:
        out.update(pattern="/" + "/".join(segs[:3]), action="cmp")
    elif segs[:1] == ["apex"]:
        # A classic page's query can carry a SELECTOR that picks the rendering
        # (`copado__GitCommitMain?variant=userstorycommit`). Same precedent as
        # `/lightning/o/<Obj>/list?filterName=…` above. A param whose value is a DYNAMIC value --
        # a record id, a uuid, a number, a hash -- is dropped, never placeholdered into the key:
        # `userStoryId=a1vd1000000EstN` says which record, not which page.
        sel = sorted((k, v[0]) for k, v in (query or {}).items()
                     if v and v[0] and _norm_segment(v[0]) == v[0] and not v[0].startswith("http"))
        pat = "/" + "/".join(segs[:2])
        if sel:
            pat += "?" + "&".join("%s=%s" % kv for kv in sel)
        out.update(pattern=pat, action="vf")
    elif segs and SF_ID.match(segs[0]):
        out.update(pattern="/{id}", action="classic")
    else:
        out.update(pattern="/" + "/".join(_norm_segment(s) for s in segs) or "/", action="other")
    out["record_type"] = rt
    return out


def web_pattern(u) -> dict:
    segs = [_norm_segment(s) for s in u.path.split("/") if s]
    pat = "/" + "/".join(segs) if segs else "/"
    if u.fragment:
        pat += "#" + "/".join(_norm_segment(s) for s in u.fragment.split("/"))
    return {"pattern": pat, "object": None, "action": "web", "record_type": None, "app": None}


def layout_hash(org_map: dict | None, sobject: str | None, record_type: str | None) -> str | None:
    """sha1[:8] of the object's create-layout items (+ record type) from the org map --
    the layout version a page key carries. None when the map has no layout for the object."""
    if not org_map or not sobject:
        return None
    obj = (org_map.get("objects") or {}).get(sobject) or {}
    inv = obj.get("inventory") or {}
    items = inv.get("create_layout_items") or inv.get("create_layout")
    if not items:
        return None
    blob = json.dumps({"items": items, "rt": record_type}, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:8]


# (path, mtime, size) -> parsed map. dev1.json is 110 MB and fsc7f.json 61 MB on this machine, and
# page_key loads a map on EVERY call: the store migration re-keying 155 records spent all its time
# re-parsing the same four files. Keyed on mtime+size like skeleton.py's cache, so it is never
# served stale after a `discover.py refresh`.
_MAP_CACHE: dict[str, tuple[float, int, dict | None]] = {}


def load_org_map(alias: str | None) -> dict | None:
    if not alias:
        return None
    p = os.path.join(ORG_MAP_DIR, f"{alias}.json")
    try:
        st = os.stat(p)
    except OSError:
        return None
    hit = _MAP_CACHE.get(p)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    try:
        with open(p) as f:
            data = json.load(f)
    except Exception:
        data = None
    _MAP_CACHE[p] = (st.st_mtime, st.st_size, data)
    return data


def page_key(url: str, org: str | None = None, org_map: dict | None = None,
             template_version: str | None = None, _depth: int = 0) -> dict:
    """The page key and everything it was derived from. Stable for the same page across visits."""
    u = urlparse(url or "")
    host = (u.hostname or "").lower()
    inner = _unwrap_login(u)
    if inner and _depth < 3 and (u.path.startswith("/secur/frontdoor.jsp") or "ec=302" in (u.query or "")
                                 or host in ("login.salesforce.com", "test.salesforce.com")):
        inner_url = inner if inner.startswith("http") else f"https://{host}{inner}"
        # the destination page is the identity; the login hop is not a page anyone tests
        return page_key(inner_url, org=org, org_map=org_map, template_version=template_version, _depth=_depth + 1)
    aloha = _unwrap_aloha(u)
    if aloha and _depth < 3:
        # the aloha wrapper is a frame around a classic page, not a page: key what it carries
        aloha_url = aloha if aloha.startswith("http") else f"https://{host}{aloha}"
        pk = page_key(aloha_url, org=org, org_map=org_map, template_version=template_version,
                      _depth=_depth + 1)
        pk["wrapper"] = "one:alohaPage"
        return pk
    sf = is_salesforce_host(host)
    alias = org if (org and sf) else (alias_for_host(host) if sf else None)
    if sf:
        org_map = org_map or load_org_map(alias)
    query = {k: v for k, v in parse_qs(u.query).items() if k not in DROP_PARAMS}
    info = sf_pattern(u.path, query, org_map=org_map) if sf else web_pattern(u)
    partition = alias or host
    pattern = info["pattern"]
    # SINGLE-SURFACE APPS (user, 2026-09-12): "different workspaces will have similar interfaces,
    # it is a one size fits all". An SPA whose chrome -- tab bar, chat box, sidebar, run controls --
    # is identical on every route gets ONE page key for the whole host, because splitting it by path
    # fragments one page object into copies of itself. Measured on robotic.copado.com: the same tab
    # button existed 7 times across chat/builder/skills routes, and a per-chat path key meant every
    # new chat started a fresh record that had to relearn a page the store already knew.
    # Salesforce is deliberately NOT eligible: its routes render genuinely different layouts.
    if not sf:
        _pre = single_surface_prefix(host, pattern)
        if _pre:
            pattern = _pre
    parts = [partition, pattern]
    app_seg, app_src = app_name(info.get("app"), org_map) if sf else (None, None)
    if app_seg:
        parts.append(f"app={app_seg}")
    if info.get("record_type"):
        parts.append(f"rt={info['record_type']}")
    lh = None
    if sf:
        lh = layout_hash(org_map, info.get("object"), info.get("record_type"))
        if lh:
            parts.append(f"layout={lh}")
    key = "|".join(parts)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("_")[:180]
    if sf and alias:
        store_dir = os.path.join(ORG_MAP_DIR, alias, "pom")
        render = os.path.join("docs", "org-map", f"{alias}-pom.md")
    else:
        store_dir = os.path.join(APPS_DIR, host or "unknown-host", "pom")
        render = os.path.join("docs", "recorder", "pom", f"{host or 'unknown-host'}.md")
    return {"key": key, "slug": slug, "partition": partition, "alias": alias, "host": host,
            "salesforce": sf, "pattern": info["pattern"], "object": info.get("object"),
            "action": info.get("action"), "record_type": info.get("record_type"),
            "app": info.get("app"), "app_name": app_seg, "app_source": app_src,
            "wrapper": None, "layout_hash": lh, "template_version": template_version,
            "store_dir": store_dir, "path": os.path.join(store_dir, slug + ".json"),
            "render": render,
            "note": None if (alias or not sf) else "salesforce host with no known alias -- partitioned by host; run keys.py --refresh-hosts"}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--org")
    ap.add_argument("--refresh-hosts", action="store_true", help="rebuild the host-stem -> alias cache from sf org list")
    a = ap.parse_args(argv)
    if a.refresh_hosts:
        t = refresh_hosts_cache()
        print(json.dumps({"hosts": len(t), "cache": HOSTS_CACHE}))
        if not a.url:
            return 0
    if not a.url:
        ap.print_help()
        return 2
    print(json.dumps(page_key(a.url, org=a.org), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
