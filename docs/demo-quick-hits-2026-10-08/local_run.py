#!/usr/bin/env python3
"""local_run -- run selected test cases of tests/demo-quick-hits.robot under REAL QWeb inside a headless holder.

Scratch instrument for the 2026-10-08 demo suite (not committed). Assumptions, written into the report:
  * the holder is already logged in, so JwtAuthenticate / JwtLogin are no-ops here;
  * `QForce.TypeText` is QWeb's own type_text (same assumption as override_proof.py);
  * ComboBox / PickList are the BRAIN's hardened versions (qforce_lite), not the licensed QForce;
  * UseModal sets QWeb's ActiveAreaXpath (the shim's mechanism).
Usage: local_run.py --org slockard --tests "02 Lookup,04 Picklist" --out DIR --suite CLONE/tests/demo-quick-hits.robot
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = "/Users/jgarza/agentic-crt-orchestrator"
STUB = '''"""proof-only QForce for demo-quick-hits local runs (NOT the licensed library)."""
import os, sys
sys.path.insert(0, "%(root)s/tools/qforce-lite")
sys.path.insert(0, "%(root)s/tools")
from QWeb.keywords.input_ import type_text
from QWeb.keywords import config as _qconfig
ROBOT_LIBRARY_SCOPE = "GLOBAL"
__all__ = ["type_text", "jwt_authenticate", "jwt_login", "get_instance_url", "query_records",
           "use_modal", "combo_box", "pick_list", "proof_screenshot"]

def _drv():
    from QWeb.internal import browser
    return browser.get_current_browser()

def jwt_authenticate(client_id=None, username=None, private_key=None, sandbox=False):
    return "local-holder-session"

def jwt_login(su_path=None):
    return None

def get_instance_url():
    return "/".join(_drv().current_url.split("/")[:3])

def query_records(soql, org_alias=None):
    import json, urllib.request, urllib.parse, sf_session
    s = sf_session.get(os.environ["GZ_LOCAL_ORG"])
    r = urllib.request.Request(s["instance_url"] + "/services/data/v62.0/query?q=" + urllib.parse.quote(soql),
                               headers={"Authorization": "Bearer " + s["access_token"]})
    return json.load(urllib.request.urlopen(r, timeout=30))

def use_modal(state):
    on = str(state).strip().lower() in ("on", "true", "1", "yes")
    _qconfig.set_config("ActiveAreaXpath", '//div[contains(@class,"slds-modal")]' if on else "//body")

def combo_box(locator, value, timeout=10, index=1, **kw):
    import qforce_lite
    return qforce_lite.combo_box(locator, value, timeout=timeout, index=index)

def pick_list(label, value, index=1, timeout=10):
    import qforce_lite
    return qforce_lite.pick_list(label, value, index=index, timeout=timeout)

def proof_screenshot(path):
    _drv().save_screenshot(path)
''' % {"root": ROOT}

RUNNER = '''import json, os, sys
cfg = json.loads(%(cfg)s)
os.environ["GZ_LOCAL_ORG"] = cfg["org"]
import robot
saved = sys.modules.pop("QForce", None)
rc = None
try:
    with open(cfg["console"], "w", encoding="utf-8") as fh:
        rc = robot.run(cfg["suite"], outputdir=cfg["outdir"], pythonpath=[cfg["stub_dir"]],
                       test=cfg["tests"], variable=cfg["variables"],
                       stdout=fh, stderr=fh, consolecolors="off", consolewidth=200)
finally:
    for m in [m for m in list(sys.modules) if m == "QForce" or m.startswith("QForce.")]:
        sys.modules.pop(m, None)
    if saved is not None:
        sys.modules["QForce"] = saved
result = {"rc": rc}
'''


def sh(cmd, timeout=600):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--slot", default="qh")
    ap.add_argument("--tests", required=True, help="comma separated name prefixes")
    ap.add_argument("--suite", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-path", default="/lightning/page/home")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    out = os.path.abspath(a.out)
    src = open(a.suite, encoding="utf-8").read()
    src = re.sub(r"^Suite Setup\s+Setup Browser\s*$", "Suite Setup                   Local Holder Setup", src, flags=re.M)
    src = re.sub(r"^Suite Teardown\s+End suite\s*$", "Suite Teardown                No Operation", src, flags=re.M)
    src += "\n\nLocal Holder Setup\n    Set Library Search Order    QForce    QWeb\n    SetConfig    DefaultTimeout    8s\n    SetConfig    Delay    0.3\n"
    copy = os.path.join(os.path.dirname(os.path.abspath(a.suite)), "_local_run_%s.robot" % a.org)
    open(copy, "w", encoding="utf-8").write(src)
    stub_dir = os.path.join(out, "qforce_stub")
    os.makedirs(os.path.join(stub_dir, "QForce"), exist_ok=True)
    open(os.path.join(stub_dir, "QForce", "__init__.py"), "w").write(STUB)
    names = []
    for line in src.splitlines():
        if line and not line.startswith((" ", "\t", "#", "*", ".")) and re.match(r"^\d\d |^Restore", line):
            names.append(line.strip())
    want = [t.strip() for t in a.tests.split(",")]
    tests = [n for n in names if any(n.startswith(w) for w in want)]
    print("tests:", tests)
    cfg = {"org": a.org, "suite": copy, "stub_dir": stub_dir, "outdir": os.path.join(out, "robot"),
           "console": os.path.join(out, "console.txt"), "tests": tests,
           "variables": ["client_idSlock:x", "usernameSlock:x", "private_keySlock:x",
                         "client_idHealthCloud:x", "usernameHealthCloud:x", "private_keyHealthCloud:x"]}
    runner = os.path.join(out, "runner.py")
    open(runner, "w").write(RUNNER % {"cfg": repr(json.dumps(cfg))})
    up = [sys.executable, ROOT + "/tools/interop/up.py"]
    try:
        rc, o = sh(up + [a.org, a.start_path, "--slot", a.slot], 300)
        print("up rc", rc)
        rc, o = sh(up + [a.org, "--slot", a.slot, "--op", "py", "--py-file", runner, "--timeout", "840", "--json"], 900)
        print("py rc", rc, o[-600:])
    finally:
        rc, o = sh(up + [a.org, "--slot", a.slot, "--down"], 120)
        print("down rc", rc)
        try:
            os.remove(copy)
        except OSError:
            pass


if __name__ == "__main__":
    main()
