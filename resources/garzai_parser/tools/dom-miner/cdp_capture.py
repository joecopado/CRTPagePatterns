#!/usr/bin/env python3
"""
Usage: python3 tools/dom-miner/cdp_capture.py [-h] [--org ORG] [--path PATH] [--url URL] --out OUT [--port PORT] [--settle SETTLE] [--wait-text WAIT_TEXT] [--click-text CLICK_TEXT] [--frames {on,off}] [--cross-origin-frames] [--target-id TARGET_ID] [--in-place] [--depth-cap DEPTH_CAP] [--lazy-timeout LAZY_TIMEOUT] [--state STATE] [--entered-via ENTERED_VIA] [--host-url HOST_URL] [--no-redact]
Capture a Salesforce Lightning page's *full* DOM (light + open shadow roots)
straight to disk over the Chrome DevTools Protocol.

Why CDP and not the agent's browser tool: a Lightning page serializes to
0.5-3 MB. Routing that through an agent transcript costs the same bytes twice
(read + write). CDP hands the string to this process, which writes the file --
the agent never sees the payload, only the summary line.

Why a custom serializer and not `outerHTML`: `outerHTML` excludes shadow
content *by spec* (open or closed), and a Lightning record page is ~90% shadow
DOM. This walks `element.shadowRoot` and emits each open root as a spec-shaped
`<template shadowrootmode="open">` so the saved file round-trips through any
HTML parser while still telling you which side of a shadow boundary a node is
on -- the single most important fact for QWeb locator planning.

Auth: never takes a session id as an argument. It shells out to
`sf org open -o <alias> --path <path> --url-only`, which mints a fresh
frontdoor URL locally; the URL is fed to Page.navigate inside this process and
never printed. Captures are scrubbed of anything token-shaped before writing.

Usage:
    cdp_capture.py --org dev2 --path /lightning/r/Account/<id>/view \
                   --out docs/dom-captures/account-record.html \
                   [--wait-text "Details"] [--port 9333] [--settle 6]
    cdp_capture.py --url https://...      # already-authenticated tab, no sf CLI
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import urllib.request

DEFAULT_PORT = 9333

# --------------------------------------------------------------------------
# The wait-text readiness probe's text extractor. A single JS function
# expression (not an IIFE -- callers wrap it in `(...)(document.body)`), doing
# the SAME "walk element.shadowRoot recursively" traversal `build_serializer`
# below already does for the full-page capture, but scoped to plain text: a
# depth-first walk collecting every text node's data, descending into an
# element's `shadowRoot` (open only -- a closed root is genuinely
# unreachable, same limit the full serializer has) in addition to its normal
# children, skipping `<script>`/`<style>`/`<template>` (their child text
# nodes are markup/CSS, not rendered page content, and polluted an early
# version of this fix with stylesheet source). `document.body.innerText`
# -- the light-DOM-only accessor this replaced -- never crosses into an open
# shadow root at all: measured live on slockard's Zoo_Screen_Components flow
# screen, `innerText` read ~370 chars of chrome while this walk read >12,000
# chars of the SAME live document, including the flow's own labels sitting
# inside `lightning-input`'s open shadow root.
# --------------------------------------------------------------------------
_SHADOW_PIERCING_TEXT_JS = r"""
function(root){
  var SKIP = {SCRIPT:1, STYLE:1, NOSCRIPT:1, TEMPLATE:1};
  var out = [];
  function walk(n){
    if (n.nodeType === 3) { out.push(n.nodeValue); return; }
    if (n.nodeType !== 1) return;
    if (SKIP[n.tagName]) return;
    if (n.shadowRoot) {
      var sc = n.shadowRoot.childNodes;
      for (var i = 0; i < sc.length; i++) walk(sc[i]);
    }
    var c = n.childNodes;
    for (var j = 0; j < c.length; j++) walk(c[j]);
  }
  walk(root);
  return out.join(' ');
}
"""

# --------------------------------------------------------------------------
# Lazy related-list readiness (2026-09-11, user's review of hc-provider-contract).
#
# `Upload Files` and `Drop Files` -- the Notes & Attachments related-list BODY --
# were absent from that capture entirely (0 occurrences) while the card HEADER was
# present: a record page's `laf-progressive-container` bodies load AFTER the header
# paints, and the capture serialized the gap. Nothing downstream can tell "this page
# has no Files" from "the Files card had not loaded yet" -- the vacuous green this
# project exists to prevent.
#
# So a capture WAITS: no `laf-progressive-container[aria-busy="true"]` anywhere, and
# every related-list card carries a body (a table, a list, a forceRelatedListPreview,
# or an explicit empty-state marker). Shadow-piercing, for the same reason the text
# probe above is: the cards are Aura but the bodies inside them are LWC.
#
# This is a READINESS wait, not a settle: on a page with no related lists it returns
# on the first poll (counts all zero) and costs one Runtime.evaluate. `--lazy-timeout 0`
# turns it off; a timeout still captures and records `lazy_wait: TIMEOUT` so
# tools/recorder/capture_completeness.py can name the cards that never filled in.
# --------------------------------------------------------------------------
# EXPAND COLLAPSED UI BEFORE SERIALIZING (2026-09-12).
#
# The Copado AI run page renders every node trace COLLAPSED. Measured on run 77803b40: all 5
# `details.workflow-node-trace` had open=false, the page's innerText was 6,748 chars, and the
# monitor reported "audit lines seen: 0" for three minutes on a perfectly healthy run. Forcing
# them open took the SAME page to 103,950 chars -- 15x -- and made the workflow's entire audit log
# readable. A capture that serializes the collapsed page loses that content silently: it parses
# cleanly and looks complete, which is this project's signature failure.
#
# This existed as a throwaway script EIGHT times in one session before it was put here (user:
# "why are you writing a method to expand chats for the Nth time today"). If a new collapsible
# shape turns up, it is added HERE with a test -- never re-derived at the call site.
#
# SAFETY, which is why this is narrow: `<details>` is opened by setAttribute, which cannot
# navigate. The aria-expanded pass clicks ONLY a <button> that owns an `aria-controls` (the ARIA
# disclosure pattern) and NEVER an <a>, because a link click navigates and "do not navigate away"
# is the standing rule for a page someone is watching. Everything is counted and reported, so an
# elision is never silent.
_EXPAND_JS = r"""
(function () {
  var roots = [document], i, r, out = {details: 0, details_opened: 0, toggles: 0,
                                        toggles_clicked: 0, skipped_links: 0,
                                        toggles_skipped_combobox: 0};
  for (i = 0; i < roots.length; i++) {
    r = roots[i];
    var all = r.querySelectorAll('*');
    for (var j = 0; j < all.length; j++) {
      if (all[j].shadowRoot) { roots.push(all[j].shadowRoot); }
    }
    var det = r.querySelectorAll('details');
    for (var k = 0; k < det.length; k++) {
      out.details++;
      if (!det[k].hasAttribute('open')) { det[k].setAttribute('open', ''); out.details_opened++; }
    }
    var tog = r.querySelectorAll('[aria-expanded="false"]');
    for (var m = 0; m < tog.length; m++) {
      var el = tog[m];
      out.toggles++;
      if (el.tagName === 'A') { out.skipped_links++; continue; }
      if (el.tagName !== 'BUTTON' || !el.hasAttribute('aria-controls')) { continue; }
      // A COMBOBOX IS NOT A DISCLOSURE (2026-09-22). A Lightning picklist renders as
      // <button role=combobox aria-expanded=false aria-controls=...> -- byte-for-byte the
      // disclosure pattern -- so this pass opened EVERY picklist on every page it captured, and
      // a keyword driven after the capture found the other lists open (the user: "expanding
      // picklists, but not doing anything with them"). Same for a menu button. Counted, never silent.
      var role = el.getAttribute('role') || '', pop = (el.getAttribute('aria-haspopup') || '').toLowerCase();
      if (role === 'combobox' || pop === 'listbox' || pop === 'menu' || pop === 'true') {
        out.toggles_skipped_combobox++; continue;
      }
      try { el.click(); out.toggles_clicked++; } catch (e) {}
    }
  }
  return JSON.stringify(out);
})()
"""

_LAZY_READY_JS = r"""
(function(){
  // Measured on the original hc-provider-contract capture (2026-09-11): the unloaded card is a
  // SKELETON -- `<laf-progressive-container aria-busy="true">` wrapping
  // `<lst-stencil-related-list-single>` whose <article class="... stencil">  carries only the
  // title <h2>. So a stencil is bodiless no matter what else it contains, and `ul`/`article` are
  // useless markers on their own (every card header has them).
  var BODY = {'TABLE':1, 'FORCERELATEDLISTPREVIEW':1, 'LI':1,
              'LIGHTNING-DATATABLE':1, 'LST-RELATED-LIST-BASIC-ROWS':1};
  var containers = 0, busy = 0, cards = 0, bodiless = [];
  // `each` descends into the node's OWN shadow root first. Skipping that was measured wrong live
  // 2026-09-11: under LWC synthetic shadow `container.children` is EMPTY (the content lives in the
  // shadow root), so a hasBody() that started at .children reported every loaded card bodiless.
  function each(root, fn){
    if (root.shadowRoot) each(root.shadowRoot, fn);
    var kids = root.children || [];
    for (var i = 0; i < kids.length; i++){ fn(kids[i]); each(kids[i], fn); }
  }
  function cls(e){ return (typeof e.className === 'string') ? e.className : ''; }
  // The Aura related-list card is an <article> carrying the class, NOT a custom tag.
  function isCard(e){
    return e.tagName === 'LST-RELATED-LIST-SINGLE-CONTAINER'
        || e.tagName === 'FORCERELATEDLISTCARDDESKTOP'
        || (e.tagName === 'ARTICLE' && cls(e).indexOf('forceRelatedListCardDesktop') > -1);
  }
  function isEmptyState(e){
    var c = cls(e);
    return c.indexOf('emptyContent') > -1 || c.indexOf('empty-content') > -1
        || c.indexOf('slds-illustration') > -1;
  }
  function hasBody(card){
    var stencil = false, marker = false;
    each(card, function(e){
      // the TAG only: `class="... stencil ..."` also lands on a LOADED Aura card's avatar
      // placeholder (measured on the nudged health90 capture) -- the class is not the signal
      if (e.tagName.indexOf('-STENCIL') > -1) stencil = true;
      if (BODY[e.tagName] || isEmptyState(e)) marker = true;
    });
    return !stencil && marker;
  }
  function name(card){
    var t = card.getAttribute('aria-label') || '';
    if (!t) { try { t = (card.innerText || '').trim().split('\n')[0]; } catch (err) { t = ''; } }
    return (t || card.tagName.toLowerCase()).slice(0, 60);
  }
  // `inside` keeps a nested Aura <article> from being counted a second time under its own
  // lst-related-list-single-container -- shadow boundaries make .closest() useless here.
  function walk(root, inside){
    if (root.shadowRoot) walk(root.shadowRoot, inside);
    var kids = root.children || [];
    for (var i = 0; i < kids.length; i++){
      var e = kids[i], mine = inside;
      if (e.tagName === 'LAF-PROGRESSIVE-CONTAINER') {
        containers++;
        if (e.getAttribute('aria-busy') === 'true') busy++;
      }
      if (!inside && isCard(e)) {
        cards++; mine = true;
        if (!hasBody(e)) bodiless.push(name(e));
      }
      walk(e, mine);
    }
  }
  walk(document, false);
  return JSON.stringify({containers: containers, busy: busy, cards: cards,
                         cards_without_body: bodiless});
})()
"""


# A `laf-progressive-container` is Salesforce's LOAD-WHEN-NEAR-THE-VIEWPORT wrapper: waiting alone
# never fills it in. Measured live 2026-09-11 on health90's Contract 00000101 -- 20.2 s of waiting
# left 1 container aria-busy and 3 cards bodiless (Contract Payment Agreements, Contract History,
# Notes & Attachments), exactly as the original capture had them. So the wait NUDGES: it scrolls each
# unfilled card into view the way a person reading the page does, then restores every scroll position
# it moved, so an in-place capture still serializes the document it was pointed at.
_LAZY_NUDGE_JS = r"""
(function(){
  var CARD = {'FORCERELATEDLISTCARDDESKTOP':1, 'LST-RELATED-LIST-SINGLE-CONTAINER':1,
              'LAF-PROGRESSIVE-CONTAINER':1};
  if (!window.__garzai_scroll) {
    window.__garzai_scroll = [];
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++){
      var e = all[i];
      if (e.scrollHeight > e.clientHeight + 4) window.__garzai_scroll.push([e, e.scrollTop]);
    }
    window.__garzai_scroll.push([document.scrollingElement || document.documentElement,
                                 (document.scrollingElement || document.documentElement).scrollTop]);
  }
  var n = 0;
  function each(root, fn){
    if (root.shadowRoot) each(root.shadowRoot, fn);
    var kids = root.children || [];
    for (var i = 0; i < kids.length; i++){ fn(kids[i]); each(kids[i], fn); }
  }
  each(document, function(e){
    if (!CARD[e.tagName]) return;
    n++;
    try { e.scrollIntoView({block: 'center'}); } catch (err) {}
  });
  return String(n);
})()
"""

_LAZY_RESTORE_JS = r"""
(function(){
  var saved = window.__garzai_scroll || [];
  for (var i = saved.length - 1; i >= 0; i--){
    try { saved[i][0].scrollTop = saved[i][1]; } catch (err) {}
  }
  window.__garzai_scroll = null;
  return String(saved.length);
})()
"""


def lazy_ready(state: dict) -> bool:
    """The readiness predicate, isolated so a test can run it over a fixture's counts without a
    browser: no related-list container is still busy AND every card the page rendered has a body."""
    return int(state.get('busy') or 0) == 0 and not (state.get('cards_without_body') or [])


# --------------------------------------------------------------------------
# The in-page serializer. Kept as a single JS expression so it can be shipped
# through Runtime.evaluate in one round trip.
# --------------------------------------------------------------------------
DEFAULT_MAX_DEPTH = 120


def build_serializer(max_depth: int = DEFAULT_MAX_DEPTH) -> str:
    """The in-page serializer, with the walk() depth cap as a parameter.

    Was a hardcoded `if(depth>80) return;` -- silent truncation, the failure class this repo
    forbids. Now: `max_depth` is substituted in, and the FIRST node that hits the cap (and every
    5th after, capped at 20 recorded) is pushed onto `stats.depthCapped` with its tag + a short
    ancestor-tag breadcrumb, so a caller can log a WARNING naming the node instead of silently
    losing subtree content. `docs/recorder/OMNISTUDIO.md` measured OmniStudio actual depth at 78
    under the old 80 cap -- default raised to 120 here for headroom."""
    return r"""
(function () {
  var MAXTEXT = 4000, MAXATTR = 400, MAXDEPTH = __MAX_DEPTH__;
  var SKIP = {SCRIPT:1, STYLE:1, NOSCRIPT:1, LINK:1, META:1, CANVAS:1};
  var stats = {nodes:0, shadowRoots:0, hiddenSkipped:0, iframes:0, crossOriginFrames:0, depthCapped:[],
               labels:0, inputs:0, customElements:0, closedRootSuspects:0, shadowDepthCapped:0};
  var inShadow = 0;   // >0 while walk() is inside an open shadow root (completeness counters)
  var SECRET = [
    /\b00D[A-Za-z0-9]{12,}\b/g,
    /(sid|sessionId|access_token|refresh_token|otp|token)=[^&"'\s<>]+/gi,
    /Bearer\s+[A-Za-z0-9._\-]{20,}/gi,
    // a PEM private key printed as page text (Copado AI node traces leak one in 6 of 23);
    // whitespace is already collapsed to spaces by the time a text node reaches scrub()
    /-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z]+ )?PRIVATE KEY-----/g,
    /\b3MVG9[A-Za-z0-9._\-]{20,}/g
  ];
  function scrub(s){ s = String(s); SECRET.forEach(function(r){ s = s.replace(r,'REDACTED'); }); return s; }
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function escA(s){ return esc(s).replace(/"/g,'&quot;'); }
  function attrs(el){
    var a=[],i,n,v;
    for(i=0;i<el.attributes.length;i++){
      n=el.attributes[i].name; v=el.attributes[i].value;
      if(n==='style'||n==='srcdoc') continue;   // style stays out (bulk); positioned nodes keep geometry below
      if(v&&v.length>MAXATTR) v=v.slice(0,MAXATTR)+'...';
      if(/^(src|href)$/.test(n)&&/^data:/.test(v)) v='data:...';
      a.push(' '+n+'="'+escA(scrub(v))+'"');
    }
    // geometry for positioned nodes (virtualized grids place cells by inline top/left): the parser
    // groups such siblings into rows (v3 structuralRows). Inline style only -- no computed-style cost.
    try{
      var st=el.style;
      if(st&&(st.top||st.left)&&/^-?[\d.]+px$/.test(st.top||'0px')&&/^-?[\d.]+px$/.test(st.left||'0px')){
        a.push(' data-garzai-pos="'+parseFloat(st.top||'0')+','+parseFloat(st.left||'0')+'"');
      }
    }catch(e){}
    return a.join('');
  }
  function visible(el){
    var cs; try{ cs=getComputedStyle(el);}catch(e){return true;}
    if(!cs) return true;
    if(cs.display==='none') return false;
    if(cs.visibility==='hidden' && el.tagName!=='INPUT') return false;
    return true;
  }
  function walk(node, depth, buf){
    if(node&&node.nodeType===1&&node.hasAttribute&&node.hasAttribute('data-garzai-overlay')) return; // recorder overlay host: tooling, not page
    if(depth>MAXDEPTH){
      if(inShadow>0) stats.shadowDepthCapped++;   // an OPEN root we found but did not finish walking
      if(stats.depthCapped.length<20 && node.nodeType===1){
        stats.depthCapped.push({tag:node.tagName, depth:depth,
          id:(node.id||''), cls:(node.className&&node.className.baseVal!==undefined?'':String(node.className||'')).slice(0,80)});
      }
      return;
    }
    if(node.nodeType===3){
      var t=scrub(node.nodeValue.replace(/\s+/g,' ')).trim();
      if(t) buf.push(esc(t.length>MAXTEXT ? t.slice(0,MAXTEXT)+'...' : t));
      return;
    }
    if(node.nodeType!==1) return;
    var tag=node.tagName;
    if(SKIP[tag]) return;
    if(!visible(node)){ stats.hiddenSkipped++; return; }
    stats.nodes++;
    var lower=tag.toLowerCase();
    // --- completeness counters (serializer side; T10 owns the metadata comparison) ---
    if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT') stats.inputs++;
    if(tag==='LABEL') stats.labels++;
    else { try{ var cn=(node.className&&node.className.baseVal!==undefined)?node.className.baseVal:node.className;
                if(cn && String(cn).indexOf('slds-form-element__label')>=0) stats.labels++; }catch(e){} }
    if(lower.indexOf('-')>0){
      stats.customElements++;
      // a custom element with NO open shadowRoot and no light children is either a closed root or
      // an empty host -- either way its interior is NOT in this capture. Never a silent skip.
      var _sr0=null; try{ _sr0=node.shadowRoot; }catch(e){}
      if(!_sr0 && node.childNodes.length===0) stats.closedRootSuspects++;
    }
    if(lower==='svg'){ buf.push('<svg'+attrs(node)+'></svg>'); return; }
    if(lower==='iframe'){
      // Salesforce Setup is Classic-in-a-same-origin-iframe. QWeb searches
      // frames transparently (@frame.all_frames), so the frame's content is
      // part of the "page" a test sees -- capture it inline.
      stats.iframes++;
      var fIdx = stats.iframes;
      buf.push('<iframe'+attrs(node)+'>');
      try{
        var d=node.contentDocument;
        if(d&&d.body){ buf.push('<!--frame-content-->'); walk(d.body, depth+1, buf); }
        else {
          // OOPIF: opaque from inside this page's JS. Tagged with idx+src so the OUT-OF-PAGE
          // Python caller (capture(), via tools/recorder/cdp_transport.FrameAttacher) can attach
          // to that frame's own CDP target, run this same SERIALIZER there, and splice the result
          // back in at this exact spot. See docs/recorder/FRAMES.md.
          stats.crossOriginFrames++;
          buf.push('<!--cross-origin-frame idx='+fIdx+' src="'+escA(scrub(node.getAttribute('src')||''))+'"-->');
        }
      }catch(e){
        stats.crossOriginFrames++;
        buf.push('<!--cross-origin-frame idx='+fIdx+' src="'+escA(scrub(node.getAttribute('src')||''))+'"-->');
      }
      buf.push('</iframe>');
      return;
    }
    buf.push('<'+lower+attrs(node)+'>');
    var sr=null; try{ sr=node.shadowRoot; }catch(e){}
    if(sr){
      stats.shadowRoots++;
      buf.push('<template shadowrootmode="open">');
      inShadow++;
      for(var k=0;k<sr.childNodes.length;k++) walk(sr.childNodes[k], depth+1, buf);
      inShadow--;
      buf.push('</template>');
    }
    for(var j=0;j<node.childNodes.length;j++) walk(node.childNodes[j], depth+1, buf);
    buf.push('</'+lower+'>');
  }
  var buf=[];
  walk(document.body, 0, buf);
  return JSON.stringify({
    html: buf.join(''),
    stats: stats,
    title: document.title,
    // W3 2026-09-08: `path` is the LANDED location at serialize time, and it now carries
    // location.hash too -- a console/one-page-app route can live entirely in the fragment,
    // and pathname+search alone erased it. The path the CALLER asked for is written
    // separately as `<!-- nav_path: -->`, never conflated with this.
    path: location.pathname + location.search.replace(/[?&](sid|otp|token)=[^&]*/gi,'')
          + (location.hash || ''),
    host: location.host
  });
})()
""".replace("__MAX_DEPTH__", str(int(max_depth)))


SERIALIZER = build_serializer()  # backward-compat module attribute; capture()/frame splice pass max_depth explicitly

PY_SECRETS = [
    re.compile(r"\b00D[A-Za-z0-9]{12,}\b"),
    re.compile(r"(sid|sessionId|access_token|refresh_token|otp|token)=[^&\"'\s<>]+", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}", re.I),
    re.compile(r"\b[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b"),
    # A PEM PRIVATE KEY rendered as page TEXT (R12 F1/F3, 2026-09-12). None of the rules above is
    # token-shaped enough to see it: Copado AI's run page prints the complete 2048-bit key in 6 of
    # 23 node traces, and 45 files on this machine captured one verbatim. Non-greedy, and
    # newline-tolerant because the JS serializer collapses a text node's whitespace to spaces
    # before this ever runs, so the armour may arrive on a single line.
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]*?"
               r"-----END (?:[A-Z]+ )?PRIVATE KEY-----"),
    # A connected-app / External Client App consumer key. Not an authenticator on its own, but it
    # is the one credential shape this repo has already committed once (R12 F6).
    re.compile(r"\b3MVG9[A-Za-z0-9._\-]{20,}"),
]


def scrub(text: str) -> str:
    for rx in PY_SECRETS:
        text = rx.sub("REDACTED", text)
    return text


# ------------------------------------------------------- the STATE STAMP (user, 2026-09-18)
# "What a capture lacks is a stamp saying which page state it was taken in and which control got
# it there. Add that one field and every capture becomes a state." Until now a capture was one
# instant of one state of a page with NO field saying which state that instant was, so two
# captures of the same page in two states merged into one flat control set with nothing to tell
# them apart (docs/audit/pom-states-and-modals-2026-09-18.md, W2 in section 3 -- the mechanism
# behind gap G1, 76 pages).
_DIALOG_OPEN = re.compile(r'<(\w[\w-]*)\b([^>]*\brole="dialog"[^>]*)>', re.I)
_HEADING = re.compile(r'<h[1-4]\b[^>]*>(.*?)</h[1-4]>', re.I | re.S)
_ANY_TAG = re.compile(r'<[^>]+>')
UNKNOWN_ENTERED_VIA = "unknown"
DEFAULT_STATE = "default"


def dialog_state_name(html: str) -> str | None:
    """The visible title of an OPEN modal dialog in a serialized capture, else None.

    NEVER guesses: a dialog with no `aria-label` and no heading inside it returns None, and the
    caller stamps `default` rather than inventing a state name a reader cannot check. The
    serializer already drops `display:none` subtrees, which removes most closed Lightning
    modals; `aria-hidden="true"` covers the rest.
    """
    for m in _DIALOG_OPEN.finditer(html or ""):
        attrs = m.group(2)
        if re.search(r'aria-hidden="true"', attrs, re.I):
            continue
        lab = re.search(r'aria-label="([^"]*)"', attrs, re.I)
        if lab and lab.group(1).strip():
            return " ".join(lab.group(1).split())
        h = _HEADING.search(html[m.end(): m.end() + 30000])
        if h:
            import html as _html
            txt = " ".join(_html.unescape(_ANY_TAG.sub(" ", h.group(1))).split())
            if txt:
                return txt
    return None


def _stamp_value(v: str | None, fallback: str) -> str:
    """One header field's value: no comment terminator, no newline, never silently empty."""
    s = " ".join(str(v or "").split()).replace("-->", "--&gt;")
    return scrub(s) if s else fallback


def frontdoor_url(org: str, path: str) -> str:
    """Mint a fresh frontdoor URL locally. Never returned to a caller's stdout."""
    out = subprocess.run(
        ["sf", "org", "open", "-o", org, "--path", path, "--url-only", "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)["result"]["url"]


def http_json(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return json.loads(r.read().decode())


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self._id = 0
        self.on_event = None  # optional (method:str, msg:dict)->bool ; True = event consumed, keep looping

    async def send(self, method, params=None, session_id=None):
        import websockets  # noqa: F401  (imported by caller)
        self._id += 1
        mid = self._id
        payload = {"id": mid, "method": method, "params": params or {}}
        if session_id:
            payload["sessionId"] = session_id
        await self.ws.send(json.dumps(payload))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            if self.on_event and self.on_event(msg.get("method"), msg):
                continue  # a Target.* attach/detach event, routed to FrameAttacher, not this reply
            # anything else unmatched (e.g. a stray Runtime event) is simply not the reply we want -- keep waiting


async def _splice_cross_origin_frames(c: "CDP", ws, html: str, settle: float,
                                       cross_origin_frames: bool = True,
                                       max_depth: int = DEFAULT_MAX_DEPTH) -> tuple[str, dict]:
    """Two paths to a cross-origin iframe's content, tried in order, per docs/recorder/FRAMES.md:

    1. CONTEXT path (tools/recorder/cdp_transport.FrameContextTracker) -- the case that actually
       matters, measured 2026-09-05: a cross-origin frame Chrome did NOT put on its own renderer
       process (no separate CDP target -- Target.getTargets shows nothing for it) still has its
       OWN JS execution context in the SAME target. `Page.getFrameTree` finds the frameId by
       matching the placeholder's `src`; `Runtime.evaluate({expression, contextId})` -- no
       sessionId, no attach -- runs SERIALIZER right there.
    2. SESSION path (tools/recorder/cdp_transport.FrameAttacher) -- the OOPIF case: a frame Chrome
       DID process-isolate gets its own CDP target; `Target.setAutoAttach({flatten:true})` +
       `sessionId`-tagged commands reach it, same mechanism as before this wave's context work.

    Whichever path resolves a given placeholder wins; `splice_cross_origin_frames` records which
    (`mode="context"` vs `mode="session"`) in the spliced wrapper so a reader can tell them apart.
    `cross_origin_frames` is ON by default (`--frames on|off`): a Visualforce surface served from
    the sibling `--<ns>.vf.force.com` domain is a cross-origin frame on EVERY Salesforce record
    page that embeds one, so an off-by-default flag meant every VF capture in the wave-3 set
    reported `crossOriginFrames:1, attempted:False` and the serializer never walked the body.
    Turning it off is now the explicit opt-out (it costs extra CDP round trips + a settle wait).

    STATS ARE NEVER A SILENT SKIP. The returned dict always carries:
      attempted   -- False only when frames are off or the page has no cross-origin placeholder
      reason      -- why, whenever attempted is False
      attached    -- child targets/frames Chrome reported that we could have serialized
      serialized  -- placeholders actually replaced with real frame markup
      failed      -- [{"url":..., "error":...}] per placeholder we could not resolve, with the
                     concrete exception text; a frame we never matched to a frameId/target at all
                     is recorded as "no frame matched this placeholder src", not dropped.
    """
    if not cross_origin_frames:
        return html, {"attempted": False, "reason": "frames off (--frames off)",
                      "attached": 0, "serialized": 0, "failed": []}
    if "<!--cross-origin-frame " not in html:
        return html, {"attempted": False, "reason": "no cross-origin frame placeholder in this document",
                      "attached": 0, "serialized": 0, "failed": []}
    import re
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from tools.recorder.cdp_transport import (  # noqa: E402
        FrameAttacher, FrameContextTracker, splice_cross_origin_frames)

    async def send(method, params=None, session_id=None):
        return await c.send(method, params, session_id=session_id)

    frames = FrameAttacher(send)
    contexts = FrameContextTracker(send)
    # CDP.send now offers every unmatched message to `on_event` before giving up on it, so a
    # Target.attachedToTarget / Runtime.executionContextCreated that arrives interleaved with an
    # unrelated reply is never silently dropped -- it reaches these trackers regardless of which
    # send() call happens to be the one awaiting a reply.
    c.on_event = lambda method, msg: frames.handle_cdp_event(msg) or contexts.handle_cdp_event(msg)

    await send("Page.enable")
    await contexts.load_frame_tree()
    await frames.start()
    await asyncio.sleep(max(settle, 1.5))  # let Chrome report existing OOPIFs + any new frame contexts

    placeholder_idx = {int(m.group("idx")): m.group("src")
                       for m in re.finditer(r'<!--cross-origin-frame idx=(?P<idx>\d+) src="(?P<src>[^"]*)"-->', html)}
    frame_htmls: dict[int, str] = {}
    frame_modes: dict[int, str] = {}
    failures: list[dict] = []          # every unresolved placeholder, with WHY -- never a silent skip
    non_top_frames = [fid for fid, f in contexts.frames.items() if f.get("parentId")]

    def _origin(u: str) -> str:
        m = re.match(r"(https?://[^/]+)", u or "")
        return m.group(1) if m else ""

    top_origin = _origin(next((f.get("url", "") for f in contexts.frames.values()
                               if not f.get("parentId")), ""))
    # A child frame whose ORIGIN differs from the top document's is, by definition, the thing the
    # serializer flagged with a `<!--cross-origin-frame-->` placeholder. Measured 2026-09-05 on
    # slockard's ZooClassicForm tab: the frame tree carried THREE frames (top + a same-origin
    # Lightning helper frame + the VF frame), so the older "exactly one non-top frame" fallback
    # below could not fire and the only VF surface on the page went unresolved. Filtering to
    # cross-origin children first makes the same page unambiguous again.
    cross_origin_children = [fid for fid in non_top_frames
                             if _origin(contexts.frames[fid].get("url", "")) not in ("", top_origin)]
    for idx, src in placeholder_idx.items():
        why: list[str] = []
        matched = contexts.frame_id_for_src(src)
        if matched:
            candidates = [matched]
        elif len(placeholder_idx) == 1:
            # measured 2026-09-05 on the customer QLE: the Aura `one:alohaPage` wrapper that hosts
            # the VF iframe does not set a plain `src` HTML attribute (it navigates the frame via
            # JS after creation), so recorder.js/cdp_capture's own placeholder src is empty --
            # `getAttribute('src')` cannot see what the page's own JS never wrote there. With a
            # single placeholder, the cross-origin children ARE the candidate set; measured the
            # same day on slockard's ZooClassicForm tab, Salesforce keeps TWO frames on the same
            # VF URL (the visible one plus a retained hidden sibling -- the serializer emits one
            # placeholder because it skips the display:none iframe), so requiring exactly one
            # candidate failed a page that was perfectly resolvable. TRY each candidate instead
            # and keep the first that yields a non-empty body; an empty one is the dead sibling.
            candidates = cross_origin_children or non_top_frames
        else:
            candidates = []
        if not candidates:
            why.append(
                "context path: no frameId matched this placeholder src; frame tree candidates: "
                + (", ".join(contexts.frames[f].get("url", "") or "(no url)"
                             for f in non_top_frames) or "(none)"))
        best_html = None
        for cand in candidates:
            try:
                # SERIALIZER's own top-level statement is `return JSON.stringify({...})` -- with
                # returnByValue:true, CDP hands back that STRING, not an object (the same shape
                # capture()'s own top-document call already json.loads()'d two dozen lines above;
                # missed here at first, measured 2026-09-05: the isinstance(value, dict) check
                # below silently skipped every real success because `value` was always a str).
                value = await contexts.evaluate_in_frame(cand, build_serializer(max_depth), timeout=15)
                if isinstance(value, str):
                    value = json.loads(value)
                if isinstance(value, dict) and value.get("html") is not None:
                    if value["html"].strip():
                        best_html = value["html"]
                        break
                    best_html = best_html if best_html is not None else value["html"]
                    why.append(f"context path: frame {cand} serialized EMPTY (retained hidden sibling?)")
                    continue
                why.append(f"context path: evaluate returned no html ({type(value).__name__})")
            except Exception as exc:                                  # noqa: BLE001
                # try the next candidate / fall through to the session path, remembering why
                why.append(f"context path: {exc}")
        if best_html is not None:
            frame_htmls[idx] = scrub(best_html)
            frame_modes[idx] = "context"
            continue
        target = next((f for f in frames.frames() if src and src in (f.get("url") or "")), None)
        if target is None and len(frames.frames()) == 1 and len(placeholder_idx) == 1:
            target = frames.frames()[0]  # single-iframe page: unambiguous even if src didn't match verbatim
        if target is None:
            why.append("session path: no attached OOPIF target matched this placeholder src")
            failures.append({"url": src, "error": "; ".join(why)})
            continue
        try:
            value = await frames.serialize(target["sessionId"], build_serializer(max_depth), timeout=15)
            if isinstance(value, str):
                value = json.loads(value)
            if isinstance(value, dict) and value.get("html") is not None:
                frame_htmls[idx] = scrub(value["html"])
                frame_modes[idx] = "session"
                continue
            why.append(f"session path: evaluate returned no html ({type(value).__name__})")
        except Exception as exc:                                      # noqa: BLE001
            why.append(f"session path: {exc}")
        # left as the placeholder -> COULD-NOT-CHECK, never silently dropped
        failures.append({"url": src, "error": "; ".join(why)})

    new_html, stats = splice_cross_origin_frames(html, frame_htmls, frame_modes)
    stats["attempted"] = True
    stats["by_mode"] = {"context": sum(1 for m in frame_modes.values() if m == "context"),
                         "session": sum(1 for m in frame_modes.values() if m == "session")}
    # `attached` counts everything we COULD have reached: OOPIF sessions Chrome auto-attached plus
    # the non-top frames Page.getFrameTree reported in this same renderer (the context path's
    # equivalent of an attach). `serialized` and `failed` always sum to the placeholder count.
    stats["attached"] = len(frames.frames()) + len(non_top_frames)
    stats["serialized"] = stats["spliced"]
    stats["failed"] = failures
    stats["attached_sessions"] = len(frames.frames())
    stats["frame_tree_frames"] = len(contexts.frames)
    return new_html, stats


def _pii_redact(html: str, org: str | None, no_redact: bool) -> tuple[str, dict]:
    """Write-path PII redaction (stream W1, 2026-09-07). Tokens are ALWAYS stripped -- `scrub()`
    above already did that and this is the belt-and-braces second pass. Emails/phones/person
    names/record ids are redacted, shape-preservingly, only when the org is SHARED or a CUSTOMER
    per tools/garzai/org_allowlist.json (cicd-demo, neo4j-acpdev): those captures carry other
    people's real records and this repo is pushed. An OWNED test org keeps its synthetic demo data
    so the fixtures stay realistic; `--no-redact` forces that off and is REFUSED on a shared org.

    Returns (html, provenance) -- provenance carries redacted:true|false and the counts, and the
    caller writes it into the capture header. See docs/audit/capture-pii-2026-09-07.md."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "guards"))
    try:
        import capture_pii
    except Exception as exc:                                          # noqa: BLE001
        return html, {"redacted": False, "reason": f"could-not-check: {type(exc).__name__}: {exc}"}
    shared = capture_pii.is_shared(org) if org else True   # unknown org -> treat as shared
    if no_redact:
        if shared:
            raise SystemExit(
                f"--no-redact refused: '{org}' is a shared/customer org in "
                f"tools/garzai/org_allowlist.json. Its captures carry other people's records and "
                f"this repo is pushed. --no-redact is for OWNED test orgs only.")
        return html, {"redacted": False, "reason": "--no-redact on an owned test org"}
    out, counts = capture_pii.redact_html(html, shared=shared)
    # redact_html stamps its own provenance comment; the header block below is the capture's own
    # record, so strip the duplicate and report the counts here instead.
    out = capture_pii.PROV_RX.sub("", out, count=1).lstrip("\n")
    return out, {"redacted": True, "org": org,
                 "scope": "shared/customer: tokens+PII" if shared else "owned: tokens only",
                 "counts": counts}


async def capture(url: str, out_path: str, port: int, settle: float,
                  wait_text: str | None, click_text: str | None = None,
                  cross_origin_frames: bool = True, in_place: bool = False,
                  max_depth: int = DEFAULT_MAX_DEPTH, target_id: str | None = None,
                  org: str | None = None, no_redact: bool = False,
                  lazy_timeout: float = 20.0, expand_collapsed: bool = True,
                  page_state: str | None = None, entered_via: str | None = None,
                  host_url: str | None = None):
    import websockets

    serializer = build_serializer(max_depth)

    targets = [t for t in http_json(port, "/json/list") if t["type"] == "page"]
    if not targets:
        raise SystemExit("no page target on the debug port")
    # `targets[0]` is an ARBITRARY /json/list ordering. With two tabs open that silently
    # serialized a different page than the one the holder was driving (S19d, three wasted round
    # trips), so up.py now names the holder's active target explicitly.
    if target_id:
        picked = next((t for t in targets if t.get("id") == target_id), None)
        if picked is None:
            raise SystemExit("target-id %r is not among the %d live page targets -- refusing to "
                             "capture a different tab" % (target_id, len(targets)))
    elif len(targets) > 1:
        print("WARNING: %d page targets and no --target-id; falling back to the first, which may "
              "not be the page you are driving." % len(targets), file=sys.stderr)
        picked = targets[0]
    else:
        picked = targets[0]
    ws_url = picked["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024,
                                ping_interval=None, close_timeout=5) as ws:
        c = CDP(ws)
        await c.send("Page.enable")
        await c.send("Runtime.enable")
        if in_place:
            print(f"NOTE: --in-place -- serializing the CURRENT document, no Page.navigate "
                  f"issued (target already at whatever URL the holder is on)", file=sys.stderr)
        else:
            await c.send("Page.navigate", {"url": url})
        # Lightning never reaches network-idle (telemetry churn), so poll for a
        # rendered signal instead of waiting on a load event.
        # Two Salesforce-specific deviations from generic readiness detection:
        #  * only *painted* spinners count -- Lightning leaves display:none
        #    spinner elements mounted permanently, so a raw querySelectorAll
        #    count never reaches zero;
        #  * require content-growth quiet -- an SPA nav reads "no spinner" while
        #    the datatable is still empty, with no visible spinner during that
        #    window (the same trap ClaudeAgentBridge's settle.py documents).
        ready, clicked = False, None
        if in_place and not wait_text:
            # In-place with no --wait-text means "capture whatever is on screen right now" --
            # the whole point of the flag is to keep a transient state (a driven click, an open
            # modal) that an 8s+ settle wait would let decay. Skip the poll entirely.
            ready = True
        else:
            deadline = asyncio.get_event_loop().time() + max(settle, 8)
            last_len, stable = -1, 0
            has_expr = f"t.indexOf({json.dumps(wait_text)})>-1" if wait_text else "true"
            # FIX 2026-09-07 (stream Q, defect 2): `document.body.innerText` is LIGHT-DOM
            # bound -- it does not descend into a Lightning component's own (open) shadow
            # root, even though the same content is right there in the composed/rendered
            # tree and is exactly what `--op capture`'s own serializer (this file's
            # `build_serializer`, which walks `element.shadowRoot`) sees and writes to disk.
            # Measured live on slockard's Zoo_Screen_Components flow screen (a
            # `flowruntime-input-label` inside an open shadow root): the captured HTML
            # contained the field's label text while this probe's `document.body.innerText`
            # read only ~370 chars of light-DOM chrome and reported `has:false` forever --
            # `ready` never flipped true and the caller got `ready: false` while the text was
            # already on the page. `_SHADOW_PIERCING_TEXT_JS` below is the same "walk
            # `element.shadowRoot` recursively" mechanism `build_serializer` already uses,
            # scoped down to plain text extraction (skips <script>/<style>/<template>, whose
            # child text nodes are not rendered content) so the probe sees what a person
            # looking at the rendered page sees, not just the light-DOM subset of it.
            probe = (
                "(function(){var s=0;"
                "document.querySelectorAll('lightning-spinner,.slds-spinner')"
                ".forEach(function(e){if(e.offsetParent!==null)s++;});"
                f"var t=({_SHADOW_PIERCING_TEXT_JS})(document.body);"
                f"return JSON.stringify({{spinners:s,len:t.length,has:{has_expr}}});}})()"
            )
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(1.0)
                r = await c.send("Runtime.evaluate", {"expression": probe, "returnByValue": True})
                st = json.loads(r["result"]["value"])
                stable = stable + 1 if st["len"] == last_len else 0
                last_len = st["len"]
                if st["spinners"] == 0 and st["len"] > 400 and st["has"] and stable >= 2:
                    ready = True
                    break
            await asyncio.sleep(1.5)

        if click_text:
            # Same resolution order QWeb's ClickText uses: clickables first,
            # then the deepest element whose own text matches. Used only to
            # reach a *view* that has no direct URL (e.g. a quick action).
            clicker = """
            (function(t){
              var CLICKABLE='button,a,label,[type=submit],[type=button],[role=tab],[role=button],[href]';
              function texts(root,out){
                root.querySelectorAll(CLICKABLE).forEach(function(e){
                  if((e.innerText||'').trim()===t) out.push(e);});
                root.querySelectorAll('*').forEach(function(e){
                  if(e.shadowRoot) texts(e.shadowRoot,out);});
                return out;
              }
              var hits=texts(document,[]);
              if(!hits.length) return 'MISS';
              hits[0].click(); return 'CLICKED';
            })(%s)""" % json.dumps(click_text)
            r = await c.send("Runtime.evaluate", {"expression": clicker, "returnByValue": True})
            clicked = r["result"].get("value")
            await asyncio.sleep(max(settle / 3, 8))

        # Lazy related-list bodies load AFTER their card header paints (user, 2026-09-11 --
        # `Upload Files`/`Drop Files` were 0 occurrences in hc-provider-contract/capture.html
        # while the Notes & Attachments header was there). Poll at 250 ms until nothing is
        # aria-busy and every card has a body, then serialize. Never a fixed sleep: the poll
        # returns on the first tick on a page that has no related lists at all.
        # Expand collapsed UI BEFORE the lazy-wait, so a card that only exists inside a
        # collapsed section gets its chance to load too.
        expand = {"status": "SKIPPED", "details": 0, "details_opened": 0, "toggles": 0,
                  "toggles_clicked": 0, "skipped_links": 0}
        if expand_collapsed:
            try:
                r = await c.send("Runtime.evaluate",
                                 {"expression": _EXPAND_JS, "returnByValue": True})
                expand = json.loads(r["result"]["value"])
                expand["status"] = "OK"
            except Exception:                                        # noqa: BLE001
                expand["status"] = "COULD-NOT-CHECK"

        lazy = {"status": "SKIPPED", "lazy_wait_ms": 0, "containers": 0, "busy": 0,
                "cards": 0, "cards_without_body": []}
        if lazy_timeout and lazy_timeout > 0:
            t0 = asyncio.get_event_loop().time()
            lazy_deadline = t0 + lazy_timeout
            state, nudged = {}, False
            while True:
                r = await c.send("Runtime.evaluate",
                                 {"expression": _LAZY_READY_JS, "returnByValue": True})
                try:
                    state = json.loads(r["result"]["value"])
                except Exception:                                    # noqa: BLE001
                    state = {}
                    break
                if lazy_ready(state) or asyncio.get_event_loop().time() >= lazy_deadline:
                    break
                # nudge the unfilled cards into the viewport -- a progressive container loads on
                # PROXIMITY, so waiting alone never fills it in (measured 2026-09-11)
                nudged = True
                await c.send("Runtime.evaluate",
                             {"expression": _LAZY_NUDGE_JS, "returnByValue": True})
                await asyncio.sleep(0.25)
            if nudged:                      # put every scroller back where the caller left it
                await c.send("Runtime.evaluate",
                             {"expression": _LAZY_RESTORE_JS, "returnByValue": True})
            elapsed = int((asyncio.get_event_loop().time() - t0) * 1000)
            lazy = {"status": ("OK" if lazy_ready(state) else "TIMEOUT") if state
                    else "COULD-NOT-CHECK",
                    "lazy_wait_ms": elapsed, "containers": state.get("containers", 0),
                    "busy": state.get("busy", 0), "cards": state.get("cards", 0),
                    "cards_without_body": state.get("cards_without_body", [])}
            if lazy["status"] == "TIMEOUT":
                print("WARNING: lazy related lists never settled in %.1fs -- %d container(s) still "
                      "aria-busy, %d card(s) with no body (%s). Capturing anyway; the header records "
                      "`lazy_wait: TIMEOUT`."
                      % (lazy_timeout, lazy["busy"], len(lazy["cards_without_body"]),
                         ", ".join(lazy["cards_without_body"][:5]) or "-"), file=sys.stderr)

        r = await c.send("Runtime.evaluate",
                         {"expression": serializer, "returnByValue": True, "timeout": 60000})
        payload = json.loads(r["result"]["value"])

        capped = payload["stats"].get("depthCapped") or []
        if capped:
            sample = ", ".join(f"{c_['tag']}{'#'+c_['id'] if c_.get('id') else ''}@depth{c_['depth']}"
                               for c_ in capped[:5])
            print(f"WARNING: depth cap ({max_depth}) hit on {len(capped)} node(s) -- subtree(s) "
                  f"truncated, not silently dropped: {sample}"
                  f"{' ...' if len(capped) > 5 else ''}", file=sys.stderr)

        html = scrub(payload["html"])
        html, frame_stats = await _splice_cross_origin_frames(c, ws, html, settle, cross_origin_frames,
                                                               max_depth=max_depth)

    # PII redaction runs AFTER the frame splice so a spliced cross-origin (Visualforce) frame's
    # body is redacted too -- before this ordering was fixed, VF content bypassed the scrubber.
    html, redaction = _pii_redact(html, org, no_redact)

    # What the caller asked for, as a bare path, so it compares to `payload['path']`.
    if in_place:
        requested_path = "(in-place: no navigation)"
    else:
        _m = re.match(r"https?://[^/]+(/.*)$", url or "")
        requested_path = _m.group(1) if _m else (url or "(unknown)")
    landed = payload["path"]
    path_matches = (requested_path.split("?")[0] == landed.split("?")[0]) if not in_place else None
    if path_matches is False:
        print(f"WARNING: capture landed on {landed!r}, not the requested {requested_path!r} -- "
              f"the `path:` header records the LANDED page; `nav_path:` records the request.",
              file=sys.stderr)

    # THE STATE STAMP. `--state` given by the driver wins; otherwise the state name is the visible
    # title of an open modal dialog, and `default` when no dialog is open. `entered_via` is the
    # control that got the page here (up.py derives it from the kept `--op kw` session) and
    # `host_url` is the page that control was clicked ON -- the same page for an in-page modal,
    # the host page for a routed one. Nothing is guessed: with nothing to derive this stamps
    # `state: default | entered_via: unknown`, which a reader can act on.
    # NB the parameter is `page_state`, not `state`: `state` is already a local in this
    # function (the lazy-related-list poll result). It shadowed the argument and the header
    # stamped the poll dict as the state name -- caught live 2026-09-18 on the first real
    # capture, which is exactly what a live proof is for.
    state_name = _stamp_value(page_state, "") or dialog_state_name(html) or DEFAULT_STATE
    state_name = _stamp_value(state_name, DEFAULT_STATE)
    entered_via_name = _stamp_value(entered_via, UNKNOWN_ENTERED_VIA)
    state_host_url = _stamp_value(host_url, "")

    header = (
        f"<!-- capture: {os.path.basename(out_path)} -->\n"
        f"<!-- title: {scrub(payload['title'])} -->\n"
        f"<!-- path: {scrub(payload['path'])} -->\n"
        # W3 2026-09-08 (docs/errors/entries/81737aba6d.json): `path` above is the page's
        # FINAL location; `nav_path` is what the caller ASKED for. They differ whenever the
        # browser did not end up where the request pointed -- a console subtab, a redirect,
        # a modal -- and conflating the two sent 21 of 40 witness rows to the wrong page.
        # Readers that need "where is this capture from" want `path`; readers replaying the
        # original request want `nav_path`.
        f"<!-- nav_path: {scrub(requested_path)} -->\n"
        # B5 (docs/recorder/WIRING-AUDIT-2026-09-07.md SS3): `path` above is
        # location.pathname+search ONLY -- it never carried a host, so every
        # downstream reader keyed on host (POM partitions, library `hosts`,
        # ranker weights) got null from the capture path. `host` is read
        # live from location.host (the page's real, current host -- correct
        # even under --in-place, which never re-navigates), not derived from
        # `path` or the caller's `--url` argument.
        f"<!-- host: {scrub(payload.get('host') or '')} -->\n"
        f"<!-- stats: {json.dumps(payload['stats'])} ready={ready} -->\n"
        # 2026-09-11: the lazy related-list wait, so a reader can tell "this page has no Files
        # card" from "the Files card had not loaded when we serialized". Status word first so it
        # is readable by eye (`lazy_wait: TIMEOUT`), the counts as JSON after it for a reader.
        f"<!-- lazy_wait: {lazy['status']} "
        f"{json.dumps({k: v for k, v in lazy.items() if k != 'status'}, sort_keys=True)} -->\n"
        # 2026-09-18 (user): which page STATE this capture was taken in, and which control got it
        # there. One line, three fields, `|`-separated so it reads by eye and parses by regex.
        f"<!-- state: {state_name} | entered_via: {entered_via_name} "
        f"| host_url: {state_host_url} -->\n"
        f"<!-- cross-origin-frames: {json.dumps(frame_stats)} -->\n"
        f"<!-- redaction: {json.dumps(redaction, sort_keys=True)} -->\n"
        "<!-- serialization: open shadow roots emitted as "
        "<template shadowrootmode=\"open\">; display:none subtrees dropped; "
        "script/style/svg-children dropped; secrets scrubbed; a spliced cross-origin frame is "
        "wrapped <template garzai-frame=\"src\" origin=\"cross\"> -->\n"
    )
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as fh:
        fh.write(header + html)
    print(json.dumps({"out": out_path, "bytes": len(html), "ready": ready, "clicked": clicked,
                      "title": payload["title"], "cross_origin_frames": frame_stats,
                      "landed": payload["path"], "nav_path": requested_path,
                      "path_matches": path_matches, "lazy_wait": lazy,
                      "state": state_name, "entered_via": entered_via_name,
                      "host_url": state_host_url,
                      "redaction": redaction, **payload["stats"]}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org")
    ap.add_argument("--path")
    ap.add_argument("--url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--settle", type=float, default=8)
    ap.add_argument("--wait-text")
    ap.add_argument("--click-text", help="after settle, ClickText-style click, then capture")
    ap.add_argument("--frames", choices=("on", "off"), default="on",
                     help="on (DEFAULT): walk every cross-origin iframe -- context path "
                          "(Runtime.evaluate with the frame's own executionContextId) first, then "
                          "the OOPIF session path (Target.setAutoAttach flatten) -- and splice its "
                          "serialize() output in place of the <!--cross-origin-frame--> placeholder, "
                          "under a `<!-- frame: <url> -->` marker. off: leave the placeholders as "
                          "COULD-NOT-CHECK markers. Either way the capture header carries "
                          "`cross-origin-frames: {attempted, attached, serialized, failed:[{url,error}]}` "
                          "-- an unresolved frame is always reported, never a silent skip. "
                          "See docs/recorder/FRAMES.md")
    ap.add_argument("--cross-origin-frames", action="store_true",
                     help="deprecated no-op alias for --frames on (kept for existing callers); "
                          "frame capture is ON by default now")
    ap.add_argument("--target-id", dest="target_id", default=None,
                    help="DevTools target id to serialize (up.py passes the holder's ACTIVE page; "
                         "without it, a multi-tab browser is captured by arbitrary list order)")
    ap.add_argument("--in-place", action="store_true",
                     help="serialize the CURRENT document -- no Page.navigate, so a driven state "
                          "(a click, an open modal) survives the capture. --url/--org/--path are "
                          "not required with this flag (the current page target is used as-is); "
                          "--wait-text is still honoured if given, otherwise no settle wait runs")
    ap.add_argument("--depth-cap", type=int, default=DEFAULT_MAX_DEPTH,
                     help=f"walk() depth cap passed into the serializer (default {DEFAULT_MAX_DEPTH}); "
                          "a node that hits it is logged as a WARNING (name + depth), never silently "
                          "dropped -- see stats.depthCapped in the output")
    ap.add_argument("--lazy-timeout", dest="lazy_timeout", type=float, default=20.0,
                     help="SECONDS to wait for lazy related-list bodies before serializing "
                          "(default 20; 0 turns the wait off). Polls at 250 ms until no "
                          "`laf-progressive-container` is aria-busy and every related-list card "
                          "(forceRelatedListCardDesktop / lst-related-list-single-container) has a "
                          "body. A page with no related lists returns on the first poll. On timeout "
                          "the capture still happens and the header records `lazy_wait: TIMEOUT` "
                          "with the cards that never filled in -- tools/recorder/"
                          "capture_completeness.py reports those as COULD-NOT-CHECK")
    ap.add_argument("--state", default=None,
                     help="the page STATE this capture is being taken in (a modal/panel title, a "
                          "tab name). Omitted: the visible title of an open modal dialog, else "
                          "`default`. Stamped into the header as "
                          "`<!-- state: X | entered_via: Y | host_url: Z -->` and into the JSON "
                          "summary, so pom_asset/review_table file the controls under that state "
                          "instead of flat on the page (user, 2026-09-18)")
    ap.add_argument("--entered-via", dest="entered_via", default=None,
                     help="the visible label of the control that got the page into this state "
                          "(or `nav`). Omitted: `unknown` -- never guessed")
    ap.add_argument("--host-url", dest="host_url", default=None,
                     help="the URL the --entered-via control was clicked ON. Same page for an "
                          "in-page modal; the host page for a routed one (a quick action, "
                          "/lightning/o/<Obj>/new), which is what lets the store write the LINK")
    ap.add_argument("--no-redact", action="store_true",
                     help="keep emails/phones/person names/record ids in the written capture. "
                          "OWNED test orgs only (dev1/slockard/fsc7f/health90/copado-trial) -- "
                          "REFUSED for a shared or customer org in tools/garzai/org_allowlist.json. "
                          "Session material (sid/token/Bearer/JWT/frontdoor) is stripped either "
                          "way, on every org, and cannot be kept.")
    a = ap.parse_args()
    if a.in_place:
        url = a.url or ""
    else:
        url = a.url or frontdoor_url(a.org, a.path)
    frames_on = (a.frames == "on") or a.cross_origin_frames
    asyncio.run(capture(url, a.out, a.port, a.settle, a.wait_text, a.click_text, frames_on,
                        in_place=a.in_place, max_depth=a.depth_cap,
                        target_id=(a.target_id or None),
                        org=a.org, no_redact=a.no_redact, lazy_timeout=a.lazy_timeout,
                        page_state=a.state, entered_via=a.entered_via,
                        host_url=a.host_url))


if __name__ == "__main__":
    sys.exit(main())
