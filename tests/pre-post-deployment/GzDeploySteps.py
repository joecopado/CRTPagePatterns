"""GzDeploySteps -- the API half of the pre/post-deployment demo, as plain Robot keywords.

One JWT session (the same client_id / username / private_key the suite already logs in with), then:
    Installed Package Version    <package name>          -> "19.16"
    Flow Status                  <flow API name>         -> "Active" | "Inactive"
    Activate Flow / Deactivate Flow    <flow API name>   -> the latest version on / off (what the Activate button does)
    Assign Permission Set / Remove Permission Set    <permission set API name>    <username>
    User Id    <username>   and   Instance Url
Every id is queried at run time by API name, so the same suite runs in every environment.
"""
import json, time, urllib.error, urllib.parse, urllib.request
import jwt as _jwt

_S = {"token": None, "instance": None}
API = "v62.0"


def salesforce_api_session(client_id, username, private_key, login_url="https://login.salesforce.com"):
    """Mint the API session with the suite's own JWT triple (same as JwtAuthenticate)."""
    claims = {"iss": client_id, "sub": username, "aud": login_url.rstrip("/"), "exp": int(time.time()) + 180}
    assertion = _jwt.encode(claims, private_key, algorithm="RS256")
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": assertion}).encode()
    req = urllib.request.Request(login_url.rstrip("/") + "/services/oauth2/token", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=45) as r:
        tok = json.load(r)
    _S["token"], _S["instance"] = tok["access_token"], tok["instance_url"]
    return _S["instance"]


def instance_url():
    return _S["instance"]


def frontdoor_url():
    """Local runs only (no QForce): an already-signed-in URL for GoTo."""
    return _S["instance"] + "/secur/frontdoor.jsp?sid=" + _S["token"]


def _call(method, path, payload=None, tooling=False):
    base = _S["instance"] + "/services/data/" + API + ("/tooling" if tooling else "")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Authorization": "Bearer " + _S["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise AssertionError("%s %s -> HTTP %s: %s" % (method, path, e.code, e.read().decode()[:300]))
    return json.loads(raw) if raw else {}


def _query(soql, tooling=False):
    return _call("GET", "/query?q=" + urllib.parse.quote(soql), tooling=tooling)["records"]


def installed_package_version(package_name):
    rows = [r for r in _query("SELECT SubscriberPackage.Name, SubscriberPackageVersion.MajorVersion, "
                              "SubscriberPackageVersion.MinorVersion FROM InstalledSubscriberPackage", tooling=True)
            if r["SubscriberPackage"]["Name"] == package_name]
    if not rows:
        raise AssertionError("package '%s' is not installed in %s" % (package_name, _S["instance"]))
    v = rows[0]["SubscriberPackageVersion"]
    return "%s.%s" % (v["MajorVersion"], v["MinorVersion"])


def _flow(developer_name):
    rows = _query("SELECT Id, ActiveVersionId, LatestVersion.VersionNumber FROM FlowDefinition "
                  "WHERE DeveloperName = '%s'" % developer_name, tooling=True)
    if not rows:
        raise AssertionError("flow '%s' not found in %s" % (developer_name, _S["instance"]))
    return rows[0]


def flow_status(developer_name):
    return "Active" if _flow(developer_name)["ActiveVersionId"] else "Inactive"


def activate_flow(developer_name):
    f = _flow(developer_name)
    _call("PATCH", "/sobjects/FlowDefinition/" + f["Id"],
          {"Metadata": {"activeVersionNumber": f["LatestVersion"]["VersionNumber"]}}, tooling=True)
    return flow_status(developer_name)


def deactivate_flow(developer_name):
    f = _flow(developer_name)
    _call("PATCH", "/sobjects/FlowDefinition/" + f["Id"], {"Metadata": {"activeVersionNumber": 0}}, tooling=True)
    return flow_status(developer_name)


def user_id(username):
    rows = _query("SELECT Id FROM User WHERE Username = '%s'" % username)
    if not rows:
        raise AssertionError("user '%s' not found" % username)
    return rows[0]["Id"]


def _permset_id(name):
    rows = _query("SELECT Id FROM PermissionSet WHERE Name = '%s'" % name)
    if not rows:
        raise AssertionError("permission set '%s' not found" % name)
    return rows[0]["Id"]


def assign_permission_set(name, username):
    res = _call("POST", "/sobjects/PermissionSetAssignment",
                {"PermissionSetId": _permset_id(name), "AssigneeId": user_id(username)})
    return res.get("id")


def remove_permission_set(name, username):
    rows = _query("SELECT Id FROM PermissionSetAssignment WHERE PermissionSet.Name = '%s' AND Assignee.Username = '%s'"
                  % (name, username))
    for r in rows:
        _call("DELETE", "/sobjects/PermissionSetAssignment/" + r["Id"])
    return len(rows)
