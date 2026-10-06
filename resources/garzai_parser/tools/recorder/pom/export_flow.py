"""export_flow -- render a recorded session (merge_session shape, with `effect` / `state` /
`event.landed_url` annotations) as ONE chronological Robot suite: every interaction in the order it
happened, a `# PAGE:` header wherever the page key changes, a `# TRANSITION:` line on every
nav / modal / panel effect, a `# STATE:` line whenever the page state changes, and the live verdict
beside each step. Capability lookup 2026-09-15: review_table.py robot renders ONE PAGE from a review
table; pom.py draft renders a flow found by prompt; nothing rendered a session's transitions in
order, which is what a person needs to check "the steps execute in the modal they opened".

Usage: python3 tools/recorder/pom/export_flow.py <session.json> --out <suite.robot> [--org-suffix CICD]
       [--resource ../../resources/common.robot] [--hide-failed]

A CAUGHT-BUG or COULD-NOT-CHECK step is exported as a COMMENT carrying its reason (a locator
lesson is worth reading, never worth executing); `--hide-failed` drops them. Nothing here contacts
an org or a browser.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import keys as K  # noqa: E402

VERIFIED = {"VERIFIED-PASS", "PASS-GUARDED"}
KW_NAME = {"click_text": "ClickText", "type_text_clearing": "TypeText", "verify_text": "VerifyText",
           "click_checkbox": "ClickCheckbox", "click_item": "ClickItem", "click_element": "ClickElement",
           "ClickElement": "ClickElement", "pick_list": "PickList", "combo_box": "ComboBox",
           # qforce_lite click_item_first(attr_value, tag) is the READ-BACK wrapper around QWeb's
           # own ClickItem; exported un-mapped it wrote `click_item_first  Preview  button` into
           # the suite, which is not a CRT keyword and does not run (found live 2026-09-18 on the
           # copado-trial Data Template page, whose `Preview` control is icon-only and has no
           # visible text, so ClickText cannot reach it at all).
           "click_item_first": "ClickItem"}


def _kw_line(step: dict) -> str:
    c = step.get("chosen") or {}
    kw = KW_NAME.get(c.get("kw") or step.get("keyword") or "", c.get("kw") or step.get("keyword") or "")
    args = list(c.get("args") or step.get("args") or [])
    kwargs = dict(c.get("kwargs") or step.get("kwargs") or {})
    if (c.get("kw") or step.get("keyword")) == "click_item_first" and len(args) > 1:
        # click_item_first(attr_value, tag) -> ClickItem  attr_value  tag=<tag>: the second
        # positional is QWeb's `tag=`, and ClickItem silently finds NOTHING without it (CLAUDE.md).
        kwargs.setdefault("tag", args.pop(1))
    if kw == "VerifyText" and len(args) > 1:
        # qforce_lite verify_text(text, partial) -> QWeb VerifyText  text  partial_match=True
        partial = args.pop(1)
        if partial in (True, "True", "true"):
            kwargs["partial_match"] = True
    def cell(a):
        a = str(a)
        # a Robot argument that starts with `//` is an xpath: QWeb needs ONE backslash before every `=`
        # inside it (crt-qforce-qweb skill), or Robot reads `name=value` as a named argument.
        return a.replace("=", "\\=") if a.startswith("//") or a.startswith("xpath=") else a
    cells = [kw] + [cell(a) for a in args] + [f"{k}={('True' if v is True else 'False' if v is False else v)}" for k, v in kwargs.items()]
    return "    " + "    ".join(cells)


def _page_of(url: str | None, org: str | None) -> str:
    if not url:
        return "?"
    try:
        return K.page_key(url, org=org).get("key") or url
    except Exception:  # noqa: BLE001 -- a key failure must not stop an export
        return urlparse(url).netloc + urlparse(url).path


def _comment(first: str, text: str | None = None) -> list[str]:
    """`# ` every line of a possibly MULTI-LINE piece of prose, never just the first.

    CAUGHT-BUG 2026-09-18 (live-transitions review, copado-trial): a step that failed with
    `AmbiguousTextError` carries a reason whose body is four lines -- the two candidate xpaths and
    a `Fix:` sentence. Only the first was commented, so `  #1 <span> ...` and
    `Fix: pass anchor="N" ...` landed in the suite BODY, where Robot reads them as keyword calls.
    The exported suite did not parse, and nothing said so. A lesson comment that breaks the file
    it documents is worse than no comment.
    """
    body = (text if text is not None else "")
    lines = (first + body).splitlines() or [first]
    return [f"    # {lines[0]}".rstrip()] + [f"    #   {ln.strip()}".rstrip() for ln in lines[1:]]


def render(session: dict, org_suffix: str, resource: str, hide_failed: bool) -> str:
    org = session.get("org")
    steps = session.get("steps") or []
    states = session.get("states") or {}
    out = []
    out.append("*** Settings ***")
    out.append(f"Documentation                   {session.get('name')} -- every interaction in the order it was driven live,")
    out.append("...                              with the page it ran on, the transition it caused and the page state it needed.")
    out.append("...                              Generated by tools/recorder/pom/export_flow.py from the recorded session; edit the")
    out.append("...                              session or the store, never this file by hand.")
    out.append(f"Resource                        {resource}")
    out.append("Suite Setup                     Setup Browser")
    out.append("Suite Teardown                  End suite")
    out.append("")
    out.append("*** Test Cases ***")
    out.append(f"{session.get('name')}")
    out.extend(_comment(session.get("note") or ""))
    out.append(f"    ${{token}}=    JwtAuthenticate    ${{client_id{org_suffix}}}    ${{username{org_suffix}}}    ${{private_key{org_suffix}}}")
    out.append("    JwtLogin")
    page = None
    state = None
    first_url = None
    for s in steps:
        ev = s.get("event") or {}
        url = ev.get("url")
        pk = _page_of(url, org)
        if pk != page:
            out.append("")
            out.append(f"    # PAGE: {pk}")
            if page is None and url:
                first_url = url
                out.append(f"    GoTo    {url}")
            page = pk
            state = None
            desc = states.get(pk)
            if desc:
                for name, text in desc.items():
                    out.append(f"    #   state '{name}': {text}")
        st = s.get("state")
        if st and st != state:
            out.append(f"    # STATE: {st}")
            state = st
        verdict = s.get("verdict") or "COULD-NOT-CHECK"
        note = s.get("note")
        line = _kw_line(s)
        if verdict in VERIFIED:
            out.extend(_comment(verdict, f" -- {note}" if note else ""))
            out.append(line)
        else:
            if hide_failed:
                continue
            reason = (s.get("reason") or "").strip()
            if reason.startswith(verdict):
                reason = reason[len(verdict):].lstrip(": ").strip()
            out.extend(_comment(f"{verdict}: ", reason))
            out.extend(_comment(line.strip()))
        eff = s.get("effect") or {}
        if eff:
            kind = eff.get("kind")
            target = eff.get("target")
            if kind == "nav":
                out.append(f"    # TRANSITION: {pk} -> {_page_of(target, org)}")
            elif kind in ("modal", "panel"):
                out.append(f"    # TRANSITION: opens {kind} '{target}' on {pk}")
                landed = ev.get("landed_url")
                if landed and _page_of(landed, org) != pk:
                    out.append(f"    # TRANSITION: the {kind} is its own page: {_page_of(landed, org)}")
            elif kind == "state":
                out.append(f"    # STATE -> {target}")
                state = target
    out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("session")
    ap.add_argument("--out", required=True)
    ap.add_argument("--org-suffix", default="CICD", help="the CRT variable suffix of the org (crt/orgs.json)")
    ap.add_argument("--resource", default="../../resources/common.robot")
    ap.add_argument("--hide-failed", action="store_true")
    a = ap.parse_args(argv)
    with open(a.session) as f:
        session = json.load(f)
    text = render(session, a.org_suffix, a.resource, a.hide_failed)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(text)
    n_steps = sum(1 for s in session.get("steps") or [] if (s.get("verdict") or "") in VERIFIED)
    n_fail = len(session.get("steps") or []) - n_steps
    print(f"wrote {a.out}  ({n_steps} executable steps, {n_fail} lesson comments, "
          f"{text.count('# TRANSITION:')} transitions, {text.count('# PAGE:')} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
