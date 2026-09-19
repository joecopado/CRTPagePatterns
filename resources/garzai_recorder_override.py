"""garzai_recorder_override -- GarzAI composition inside CRT Live Testing (experiment, 2026-09-18).

Import-time (Robot parses Settings before Suite Setup opens the browser):
  1. patch /home/services/ui-recorder/content.bundle.js: the two
     `this.pushStep(r,event,ctx?this.handler.getXPathForElement(ctx):undefined)` call sites become
     `window.__gzCompose(this,r,event,ctx)`, and a small function appended to the bundle POSTs
     {rendered, xpath} to http://127.0.0.1:18077/compose and pushes the returned line (or the
     recorder's own line on any error, so nothing gets worse). A backup is kept beside the file.
  2. start the composer: an HTTP server thread in THIS process. It resolves the event's absolute
     xpath in the live browser through QWeb's own driver, matches the element by DOM identity
     (===) against the embedded GarzAI rows for the Zoo Nightmare Inputs page, and answers with
     our verified line, values carried over from the recorder's line.

Run-time, the third branch (2026-09-18h): a page NOBODY reviewed, and an event the embedded rows and
their recipes do not name, falls to
     `resources/garzai_parser/` -- the parser's own import closure, shipped beside this file. One
     capture of the live page through the SAME serializer `up.py --op capture` uses, the existing
     JSON parser and pattern library over it, the recorded element matched among the parsed rows by
     DOM identity, and the parser's proposed call marked `# unverified: parser proposal`, with the
     xpath form offered as a dormant backup. The bundle is imported LAZILY on the first event that
     needs it -- never at parse time -- so a missing or broken bundle degrades to exactly the
     previous behaviour (embedded rows answer, everything else passes through) with the reason in
     `Gz Override Status`.

Keywords: `Gz Override Status` (what was patched, how many events composed, whether the parser
bundle loaded and how many proposals it has made, last decisions), `Gz Override Org` (the alias the
parser stamps on its own capture), `Gz Override Restore` (put the original bundle back).
Log: /home/services/log/gz_override.log.
"""
import json, os, re, shutil, sys, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROWS = json.loads('[{"n": 0, "label": "Toggle Panel", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-label=\\"Toggle Panel\\" and @title=\\"Menu\\"]", "group_size": 2, "index": 1, "attrs": {"aria-expanded": "false", "aria-label": "Toggle Panel", "title": "Menu"}, "kw": "ClickItem", "locator": "Menu", "xpath": "//button[@aria-label=\\"Toggle Panel\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Skip to Main Content"], "kw_note": "ClickItem resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 1, "label": "Show menu", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @type=\\"button\\" and @value=\\"\\"]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "type": "button"}, "kw": "ClickText", "locator": "Show menu", "xpath": "(//*[normalize-space(text())=\\"Developer Edition\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 2, "label": "Search...", "type": "button", "identity_xpath": "//button[@aria-label=\\"Search\\" and @type=\\"button\\"]", "group_size": 2, "index": 1, "attrs": {"aria-label": "Search", "type": "button"}, "kw": "ClickText", "locator": "Search...", "xpath": "//button[@aria-label=\\"Search\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Show menu"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 3, "label": "Add favorite", "type": "button", "identity_xpath": "//button[@aria-label=\\"Add favorite\\" and @aria-pressed=\\"false\\" and @type=\\"button\\"]", "attrs": {"aria-label": "Add favorite", "type": "button"}, "kw": "ClickItem", "locator": "Add favorite", "xpath": "//button[@aria-label=\\"Add favorite\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickItem resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 4, "label": "Favorites list", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"false\\" and @type=\\"button\\"]", "attrs": {"aria-haspopup": "false", "type": "button"}, "kw": "ClickText", "locator": "Favorites list", "xpath": "(//*[normalize-space(text())=\\"Add favorite\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 5, "label": "Global Actions", "type": "button", "identity_xpath": "//a[@aria-describedby=\\"\\" and @aria-disabled=\\"false\\" and @aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @aria-labelledby=\\"\\" and @href=\\"javascript:void(0);\\" and @role=\\"button\\" and @tabindex=\\"0\\" and @title=\\"\\"][.//text()[normalize-space(.)=\\"Global Actions\\"]]", "attrs": {"aria-controls": "119:639;a", "aria-disabled": "false", "aria-expanded": "false", "aria-haspopup": "true", "href": "javascript:void(0);", "role": "button"}, "kw": "ClickText", "locator": "Global Actions", "xpath": "(//*[normalize-space(text())=\\"Favorites list\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 6, "label": "Guidance Center", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"dialog\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"Guidance Center\\"]]", "attrs": {"aria-haspopup": "dialog", "type": "button"}, "kw": "ClickText", "locator": "Guidance Center", "xpath": "(//*[normalize-space(text())=\\"Global Actions\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 7, "label": "Salesforce Help", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"true\\" and @title=\\"\\" and @type=\\"button\\"]", "attrs": {"aria-haspopup": "true", "type": "button"}, "kw": "ClickText", "locator": "Salesforce Help", "xpath": "(//*[normalize-space(text())=\\"Guidance Center\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 8, "label": "Setup", "type": "button", "identity_xpath": "//a[@aria-describedby=\\"\\" and @aria-disabled=\\"false\\" and @aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @aria-labelledby=\\"\\" and @href=\\"javascript:void(0);\\" and @role=\\"button\\" and @tabindex=\\"0\\" and @title=\\"\\"][.//text()[normalize-space(.)=\\"Setup\\"]]", "attrs": {"aria-controls": "191:219;a", "aria-disabled": "false", "aria-expanded": "false", "aria-haspopup": "true", "href": "javascript:void(0);", "role": "button"}, "kw": "ClickText", "locator": "Setup", "xpath": "(//*[normalize-space(text())=\\"Salesforce Help\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 9, "label": "Notifications", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"dialog\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"Notifications\\"]]", "attrs": {"aria-haspopup": "dialog", "type": "button"}, "kw": "ClickText", "locator": "Notifications", "xpath": "(//*[normalize-space(text())=\\"Setup\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 10, "label": "View profile", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"true\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"View profile\\"]]", "attrs": {"aria-haspopup": "true", "type": "button"}, "kw": "ClickText", "locator": "View profile", "xpath": "(//*[normalize-space(text())=\\"Notifications\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 11, "label": "App Launcher", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-haspopup=\\"dialog\\" and @title=\\"App Launcher\\"]", "attrs": {"aria-expanded": "false", "aria-haspopup": "dialog", "data-target-selection-name": "181c7013df09423d8f755b49c067f6f3", "title": "App Launcher"}, "kw": "ClickItem", "locator": "App Launcher", "xpath": "//button[@title=\\"App Launcher\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickItem resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 12, "label": "Home", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/page/home\\" and @tabindex=\\"0\\" and @title=\\"Home\\"]", "attrs": {"href": "/lightning/page/home", "title": "Home"}, "kw": "ClickText", "locator": "Home", "xpath": "//a[@title=\\"Home\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 13, "label": "Opportunities", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Opportunity/home\\" and @tabindex=\\"0\\" and @title=\\"Opportunities\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Opportunity/home", "title": "Opportunities"}, "kw": "ClickText", "locator": "Opportunities", "xpath": "//a[@title=\\"Opportunities\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Home"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 14, "label": "Opportunities List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Opportunities List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Opportunities List", "xpath": "(//*[normalize-space(text())=\\"Opportunities\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 15, "label": "Leads", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Lead/home\\" and @tabindex=\\"0\\" and @title=\\"Leads\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Lead/home", "title": "Leads"}, "kw": "ClickText", "locator": "Leads", "xpath": "//a[@title=\\"Leads\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Opportunities List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 16, "label": "Leads List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Leads List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Leads List", "xpath": "(//*[normalize-space(text())=\\"Leads\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 17, "label": "Tasks", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Task/home\\" and @tabindex=\\"0\\" and @title=\\"Tasks\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Task/home", "title": "Tasks"}, "kw": "ClickText", "locator": "Tasks", "xpath": "//a[@title=\\"Tasks\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Leads List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 18, "label": "Tasks List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Tasks List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Tasks List", "xpath": "(//*[normalize-space(text())=\\"Tasks\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 19, "label": "Files", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/ContentDocument/home\\" and @tabindex=\\"0\\" and @title=\\"Files\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/ContentDocument/home", "title": "Files"}, "kw": "ClickText", "locator": "Files", "xpath": "//a[@title=\\"Files\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Tasks List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 20, "label": "Files List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Files List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Files List", "xpath": "(//*[normalize-space(text())=\\"Files\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 21, "label": "Accounts", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Account/home\\" and @tabindex=\\"0\\" and @title=\\"Accounts\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Account/home", "title": "Accounts"}, "kw": "ClickText", "locator": "Accounts", "xpath": "//a[@title=\\"Accounts\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Files List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 22, "label": "Accounts List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Accounts List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Accounts List", "xpath": "(//*[normalize-space(text())=\\"Accounts\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 23, "label": "Contacts", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Contact/home\\" and @tabindex=\\"0\\" and @title=\\"Contacts\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Contact/home", "title": "Contacts"}, "kw": "ClickText", "locator": "Contacts", "xpath": "//a[@title=\\"Contacts\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Accounts List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 24, "label": "Contacts List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Contacts List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Contacts List", "xpath": "(//*[normalize-space(text())=\\"Contacts\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 25, "label": "Campaigns", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Campaign/home\\" and @tabindex=\\"0\\" and @title=\\"Campaigns\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Campaign/home", "title": "Campaigns"}, "kw": "ClickText", "locator": "Campaigns", "xpath": "//a[@title=\\"Campaigns\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contacts List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 26, "label": "Campaigns List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Campaigns List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Campaigns List", "xpath": "(//*[normalize-space(text())=\\"Campaigns\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 27, "label": "Dashboards", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Dashboard/home\\" and @tabindex=\\"0\\" and @title=\\"Dashboards\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Dashboard/home", "title": "Dashboards"}, "kw": "ClickText", "locator": "Dashboards", "xpath": "//a[@title=\\"Dashboards\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Campaigns List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 28, "label": "Dashboards List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Dashboards List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Dashboards List", "xpath": "(//*[normalize-space(text())=\\"Dashboards\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 29, "label": "Reports", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Report/home\\" and @tabindex=\\"0\\" and @title=\\"Reports\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Report/home", "title": "Reports"}, "kw": "ClickText", "locator": "Reports", "xpath": "//a[@title=\\"Reports\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Dashboards List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 30, "label": "Reports List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Reports List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Reports List", "xpath": "(//*[normalize-space(text())=\\"Reports\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 31, "label": "Chatter", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/page/chatter\\" and @tabindex=\\"0\\" and @title=\\"Chatter\\"]", "attrs": {"href": "/lightning/page/chatter", "title": "Chatter"}, "kw": "ClickText", "locator": "Chatter", "xpath": "//a[@title=\\"Chatter\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 32, "label": "Groups", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/CollaborationGroup/home\\" and @tabindex=\\"0\\" and @title=\\"Groups\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/CollaborationGroup/home", "title": "Groups"}, "kw": "ClickText", "locator": "Groups", "xpath": "//a[@title=\\"Groups\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Chatter"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 33, "label": "Groups List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Groups List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Groups List", "xpath": "(//*[normalize-space(text())=\\"Groups\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 34, "label": "Calendar", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Event/home\\" and @tabindex=\\"0\\" and @title=\\"Calendar\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/o/Event/home", "title": "Calendar"}, "kw": "ClickText", "locator": "Calendar", "xpath": "//a[@title=\\"Calendar\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Groups List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 35, "label": "Calendar List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Calendar List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Calendar List", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 36, "label": "Zoo \\u00b7 Nightmare inputs", "type": "link", "identity_xpath": "//a[@aria-current=\\"page\\" and @draggable=\\"false\\" and @href=\\"/lightning/n/Zoo_Nightmare_Inputs\\" and @tabindex=\\"0\\" and @title=\\"Zoo \\u00b7 Nightmare inputs\\"]", "group_size": 2, "index": 1, "attrs": {"href": "/lightning/n/Zoo_Nightmare_Inputs", "title": "Zoo \\u00b7 Nightmare inputs"}, "kw": "ClickText", "locator": "Zoo \\u00b7 Nightmare inputs", "xpath": "//a[@title=\\"Zoo \\u00b7 Nightmare inputs\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Calendar List"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 37, "label": "Zoo \\u00b7 Nightmare inputs List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Zoo \\u00b7 Nightmare inputs List\\"]]", "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "Zoo \\u00b7 Nightmare inputs List", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::a[normalize-space(.)=\\"Zoo \\u00b7 Nightmare inputs List\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 38, "label": "Close tab", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Close tab\\"]]", "attrs": {"data-id": "temp-1789057327358"}, "kw": "ClickText", "locator": "Close tab", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::button)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 39, "label": "More", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"*\\"]]", "group_size": 2, "index": 1, "attrs": {"aria-expanded": "false", "aria-haspopup": "true", "role": "button"}, "kw": "ClickText", "locator": "More", "xpath": "//a[.//text()[normalize-space(.)=\\"More\\"]]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "COULD-NOT-CHECK", "anchors": ["Close tab"], "kw_note": "COULD-NOT-CHECK: identity xpath matched None QWeb-visible live, 0 in the DOM (QWebElementNotFoundError: Unable to find element for locator /", "xp_date": "2026-09-11T08:44:30"}, {"n": 40, "label": "Personalize your nav bar", "type": "button", "identity_xpath": "//button[@title=\\"Personalize your nav bar\\" and @type=\\"button\\"]", "attrs": {"title": "Personalize your nav bar", "type": "button"}, "kw": "ClickItem", "locator": "Personalize your nav bar", "xpath": "//button[@title=\\"Personalize your nav bar\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickItem resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 41, "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @type=\\"text\\"])[1]", "attrs": {"readonly": "", "type": "text"}, "xpath": "//*[normalize-space(text())=\\"Contract Term\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 42, "label": "Contract Term", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[2]", "group_size": 2, "index": 1, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Contract Term", "xpath": "(//c-zoo-nightmare-inputs//input[@type=\\"text\\"])[2]", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms"], "kw_note": "QWeb\'s input resolver (TypeText anchor=1) landed on a DIFFERENT node -- index mode did not reach this member", "xp_date": "2026-09-11T08:44:30"}, {"n": 43, "label": "Renewal Notice (days)", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[3]", "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Renewal Notice (days)", "xpath": "(//*[normalize-space(text())=\\"Renewal Notice (days)\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "QWeb\'s input resolver (TypeText) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 44, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[4]", "group_size": 3, "index": 1, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"List Price\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["List Price"], "kw_note": "QWeb\'s input resolver (TypeText anchor=1) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 45, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[5]", "group_size": 3, "index": 2, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"Negotiated Discount\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Negotiated Discount"], "kw_note": "QWeb\'s input resolver (TypeText anchor=2) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 46, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[6]", "group_size": 3, "index": 3, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"Net to Customer\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Net to Customer"], "kw_note": "QWeb\'s input resolver (TypeText anchor=3) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 47, "label": "Approved Budget", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[7]", "group_size": 2, "index": 1, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Approved Budget", "xpath": "(//*[normalize-space(text())=\\"Approved Budget\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "Approval Envelope"], "kw_note": "QWeb\'s input resolver (TypeText anchor=1) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 48, "label": "Approved Budget", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[8]", "group_size": 2, "index": 2, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Approved Budget", "xpath": "(//*[normalize-space(text())=\\"to\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "to"], "kw_note": "QWeb\'s input resolver (TypeText anchor=2) landed on a DIFFERENT node -- index mode did not reach this member", "xp_date": "2026-09-11T08:44:30"}, {"n": 49, "type": "button", "identity_xpath": "(//button)[13]", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 50, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[9]", "group_size": 4, "index": 1, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Kickoff Workshop", "\\u2014 Seattle HQ"], "kw_note": "QWeb\'s input resolver (TypeText anchor=1) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 51, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[10]", "group_size": 4, "index": 1, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Kickoff Workshop", "Start Date"], "kw_note": "QWeb\'s input resolver (TypeText anchor=1) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 52, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[1]", "group_size": 4, "index": 1, "attrs": {"type": "checkbox"}, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Kickoff Workshop", "End Date"], "kw_note": "QWeb\'s checkbox resolver landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 53, "type": "button", "identity_xpath": "(//button)[14]", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 54, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[11]", "group_size": 4, "index": 2, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Discovery Review", "\\u2014 Seattle HQ"], "kw_note": "QWeb\'s input resolver (TypeText anchor=2) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 55, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[12]", "group_size": 4, "index": 2, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Discovery Review", "Start Date"], "kw_note": "QWeb\'s input resolver (TypeText anchor=2) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 56, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[2]", "group_size": 4, "index": 2, "attrs": {"type": "checkbox"}, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Discovery Review", "End Date"], "kw_note": "QWeb\'s checkbox resolver landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 57, "type": "button", "identity_xpath": "(//button)[15]", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 58, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[13]", "group_size": 4, "index": 3, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Integration Checkpoint", "\\u2014 Portland Annex"], "kw_note": "QWeb\'s input resolver (TypeText anchor=3) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 59, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[14]", "group_size": 4, "index": 3, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Integration Checkpoint", "Start Date"], "kw_note": "QWeb\'s input resolver (TypeText anchor=3) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 60, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[3]", "group_size": 4, "index": 3, "attrs": {"type": "checkbox"}, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Integration Checkpoint", "End Date"], "kw_note": "QWeb\'s checkbox resolver landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 61, "type": "button", "identity_xpath": "(//button)[16]", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 62, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[15]", "group_size": 4, "index": 4, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Go-Live Support", "\\u2014 Remote"], "kw_note": "QWeb\'s input resolver (TypeText anchor=4) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 63, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[16]", "group_size": 4, "index": 4, "attrs": {"type": "text"}, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Go-Live Support", "Start Date"], "kw_note": "QWeb\'s input resolver (TypeText anchor=4) landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 64, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[4]", "group_size": 4, "index": 4, "attrs": {"type": "checkbox"}, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Go-Live Support", "End Date"], "kw_note": "QWeb\'s checkbox resolver landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 65, "label": "Add Line", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Add Line\\"]])[1]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Add Line", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Add Line\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "Billable to customer"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 66, "label": "Add Line", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Add Line\\"]])[2]", "group_size": 2, "index": 2, "kw": "ClickText", "locator": "Add Line", "xpath": "(//c-zoo-nightmare-inputs//button)[6]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "Billable to customer"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 67, "label": "Save", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Save\\"]])[1]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Save", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Save\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "Add Line"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 68, "label": "Save & New", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Save & New\\"]]", "kw": "ClickText", "locator": "Save & New", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Save & New\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 69, "label": "Save", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Save\\"]])[2]", "group_size": 2, "index": 2, "kw": "ClickText", "locator": "Save", "xpath": "(//*[normalize-space(text())=\\"Save & New\\"]/following::button)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Contract Terms", "Save & New"], "kw_note": "ClickText resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 70, "label": "Territory", "type": "dropdown", "identity_xpath": "//select[.//text()[normalize-space(.)=\\"--None--\\"]]", "group_size": 2, "index": 1, "kw": "DropDown", "locator": "Territory", "xpath": "(//*[normalize-space(text())=\\"Territory & Coverage\\"]/following::select)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "anchors": ["Territory & Coverage", "Seven controls. One of them is a real <select>. Six are not."], "kw_note": "QWeb\'s dropdown resolver landed on this <select>", "xp_date": "2026-09-11T08:44:30"}, {"n": 71, "label": "Territory", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[1]", "group_size": 2, "index": 2, "attrs": {"readonly": "", "role": "combobox", "type": "text"}, "kw": "TypeText", "locator": "Territory", "xpath": "(//*[normalize-space(text())=\\"Territory & Coverage\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "anchors": ["Territory & Coverage", "Southeast"], "kw_note": "combo_box has no resolve-only entry point; the drive step is the proof", "xp_date": "2026-09-11T08:44:30"}, {"n": 72, "label": "Coverage Owner", "type": "input_field", "identity_xpath": "//input[@aria-autocomplete=\\"list\\" and @role=\\"combobox\\" and @type=\\"text\\"]", "attrs": {"role": "combobox", "type": "text"}, "kw": "TypeText", "locator": "Coverage Owner", "xpath": "(//*[normalize-space(text())=\\"Coverage Owner\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "combo_box has no resolve-only entry point; the drive step is the proof", "xp_date": "2026-09-11T08:44:30"}, {"n": 73, "label": "Product Lines Covered", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[2]", "attrs": {"readonly": "", "role": "combobox", "type": "text"}, "kw": "TypeText", "locator": "Product Lines Covered", "xpath": "(//*[normalize-space(text())=\\"Revenue Cloud\\"]/following::input[@type=\\"text\\"])[1]", "corrected": "ClickElement    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Product Lines Covered\\"]/following::input[@type\\\\=\\"text\\"])[1] ;; ClickText    Agentforce ;; VerifyText    Agentforce    timeout=5", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS", "kw_note": "ClickElement resolution landed on a DIFFERENT node", "xp_date": "2026-09-11T08:44:30"}, {"n": 74, "label": "Support Tier", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[3]", "attrs": {"readonly": "", "role": "combobox", "type": "text"}, "kw": "TypeText", "locator": "Support Tier", "xpath": "(//*[normalize-space(text())=\\"Support Tier\\"]/following::input[@type=\\"text\\"])[1]", "corrected": "ClickElement    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Support Tier\\"]/following::input[@type\\\\=\\"text\\"])[1] ;; ClickText    Premier Success ;; VerifyInputValue    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Support Tier\\"]/following::input[@type\\\\=\\"text\\"])[1]    Premier Success", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "combo_box has no resolve-only entry point; the drive step is the proof", "xp_date": "2026-09-11T08:44:30"}, {"n": 75, "label": "Escalation Regions", "type": "dropdown", "identity_xpath": "//select[@multiple=\\"\\" and @size=\\"4\\"]", "kw": "DropDown", "locator": "Escalation Regions", "xpath": "(//*[normalize-space(text())=\\"Escalation Regions\\"]/following::select)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "QWeb\'s dropdown resolver landed on this <select>", "xp_date": "2026-09-11T08:44:30"}, {"n": 76, "label": "Dismiss", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Dismiss\\"]]", "kw": "ClickText", "locator": "Dismiss", "xpath": "(//*[normalize-space(text())=\\"Just so you know\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "COULD-NOT-CHECK", "kw_note": "COULD-NOT-CHECK: identity xpath matched None QWeb-visible live, 1 in the DOM (QWebElementNotFoundError: Unable to find element for locator /", "xp_date": "2026-09-11T08:44:30"}, {"n": 77, "label": "Entitled Services", "type": "dual_listbox", "identity_xpath": "//div[@data-aura-class=\\"navexDesktopLayoutContainer lafAppLayoutHost forceAccess forceStyle oneOne\\"]", "kw": "Multi Pick List", "locator": "Entitled Services", "corrected": "ClickText    Health Check    partial_match=False ;; ClickElement    xpath\\\\=//*[normalize-space(text())\\\\=\\"Entitled Services\\"]/following::*[contains(@class,\\"zn-arrow-r\\")][1] ;; VerifyText    Health Check    anchor=Selected", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS", "kw_note": "Multi Pick List resolution landed on this node", "xp_date": "2026-09-11T08:44:30"}, {"n": 78, "type": "input_field", "identity_xpath": "//c-zoo-nightmare-inputs", "xpath": "(//*[normalize-space(text())=\\"More\\"]/following::c-zoo-nightmare-inputs)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 79, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Kickoff Workshop\\"]]", "xpath": "(//*[normalize-space(text())=\\"Onsite Schedule\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 80, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Discovery Review\\"]]", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 81, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Integration Checkpoint\\"]]", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 82, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Go-Live Support\\"]]", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}, {"n": 83, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-combos", "xpath": "(//*[normalize-space(text())=\\"Save & New\\"]/following::c-zoo-nightmare-combos)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS", "kw_note": "no keyword or no label", "xp_date": "2026-09-11T08:44:30"}]')
PAGE_PATTERN = "/lightning/n/Zoo_Nightmare_Inputs"   # the ONLY page the embedded rows and recipe steps describe
PAGE_PARTITION = "slockard"  # ... in the ONLY partition they were measured in (pom/keys.py)
PAGE_HOST_STEMS = json.loads('["slockard-dev-ed"]')  # host stems `pom.keys` resolved to that partition at build time
FE_SPEC = json.loads('{"_why": "2026-09-10 (user, Zoo_Nightmare_Inputs): the standard SLDS form element -- <div class=slds-form-element><div class=slds-form-element__label-wrapper><label class=slds-form-element__label>X</label></div><div class=slds-form-element__control>...<input></div></div> -- carries NO for= and the label is neither an ancestor nor a descendant of the control, so standard_label/label_span never read it: every one of the page\'s 26 inputs, selects and checkboxes parsed with no label (review raw_had: cousin labels x19). The rung climbs to the nearest form-element ancestor and reads its label element; a form element with no label of its own (the Approved Budget from/to pair) climbs to the next one. An input INSIDE the label wrapper (the readonly helper beside Contract Term) is not the control and gets no label.", "containerClassFragment": "slds-form-element", "excludeContainerClassFragments": ["slds-form-element__control", "slds-form-element__label-wrapper", "slds-form-element__help", "slds-form-element__icon", "slds-form-element__static", "slds-form-element__row"], "labelClassFragments": ["slds-form-element__label", "slds-checkbox__label", "slds-radio__label"], "targetInsideExcludedClassFragments": ["slds-form-element__label-wrapper", "slds-form-element__help-preview"], "climbWhenUnlabelled": true, "maxClimb": 8, "containerRowsNeverClaimIt": true, "targetTags": ["input", "select", "textarea"], "_why_targetTags": "2026-09-10 late (twelve industry-page audits): the rung labelled the inline-edit PENCIL with the field\'s name -- <button title=\\"Edit Name\\"> inside the field\'s slds-form-element read \'Name\' (56 rows on 4 pages, measured CAUGHT-BUG live: click_text(\'Name\', index=2) lands elsewhere) and every output field gained a phantom group_size 2. The rung is for the CONTROL the label names: a native form control, or a custom wrapper around exactly one. Buttons and links inside a form element keep their own title/text.", "wrapperMayBeTarget": true}')  # the template's own formElementLabel block, for the page-side describer
GEN_SPEC = json.loads('{"prefixes": ["help-message-", "error-message-", "label-", "listbox-", "dropdown-element-", "tooltip-", "slds-combobox-", "slds-listbox-"], "patterns": ["^\\\\d+:\\\\d+;[a-z]$", "(^|:)j_id\\\\d+(:|$)", "^[a-z][a-z0-9]*(-[a-z0-9]+)*-\\\\d+$", "^[a-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*-\\\\d+$", "^ctab\\\\d+$", "^tabOperation-", "^tooltip-bubble_", "^check-button-label-\\\\d+(-\\\\d+)*$", "^[0-9a-f]{32}$", "^[A-Za-z][A-Za-z0-9]*_\\\\d{10,}$"]}')  # the template's own dynamicValuePatterns (D5), for the descriptor

# --- tools/recorder/crt_override/descriptor.py, spliced in VERBATIM by the generator ------------
"""descriptor -- identity by what the page can SAY about the element it just recorded.

Usage (library):
    from descriptor import describe_js, RESOLVE_JS, NONCE_ATTR, find_row
    js   = describe_js(spec)          # the page-side `window.__gzDescribe`, spec = the template's
                                      # formElementLabel block (no fork: the data comes from there)
    el   = drv.execute_script(RESOLVE_JS, nonce)     # the stamped element, open shadow roots too
    row, why = find_row(rows, descriptor)            # which reviewed/parsed row it is

Why this module exists (2026-09-18, ledger F40/F42/F44):

  * F44 -- the composer matched a recorded element to a review row by an identity XPATH that is
    POSITIONAL over the whole page: `(//input[@type="text"])[3]`. One extra text input in the DOM
    (an App Launcher search box left after use, an Add Line row) shifts every index, so none of the
    seven Nightmare inputs matched its row and both Save clicks missed row 67.
  * F42 -- the same positional xpaths resolve to exactly ONE element on ANY page, so on a Lead form
    `Last Name` matched the Zoo page's `Renewal Notice (days)` with a confident backup line.
  * F40 -- Lightning Setup controls sit in native shadow roots; xpath from the driver reaches none
    of them, so no identity of any kind could be established and no proposal was possible.

So identity stops being an xpath the composer re-evaluates. The page stamps the element it recorded
with a one-shot attribute (`data-gz-ev="<nonce>"`, removed after 10 s) and sends a DESCRIPTOR of it.
The composer finds the element by the nonce with ONE shadow-piercing walk -- never by xpath -- and
names the row by LABEL + FAMILY, which is what a person reads and what neither an extra input nor a
different page can quietly change.

The match rule is `tools/recorder/pom/match.py` -- the ONE rule for "does the store already know
this control?" -- applied to a list of rows instead of a POM record: the same label normalisation
(whitespace collapsed, case folded, a trailing live count dropped, a prefix NEVER a match) and the
same family compatibility (button/link/menuitem/tab are one click family; input/textarea/combobox
one type family). It is imported when the POM package is importable and reproduced here when it is
not (the generated CRT library ships alone, without the parser bundle); `test_descriptor_match.py`
fails if the two ever disagree.

Nothing here decides a LINE. It answers which row, and says how it knows -- `label`, `attribute` or
`positional` -- so a decision can be read and argued with.
"""

import json
import re

NONCE_ATTR = 'data-gz-ev'
NONCE_TTL_MS = 10000

# ----------------------------------------------------------------------------- the match rule
try:                                                     # the ONE rule, when it can be imported
    from pom.match import norm_label, families_compatible, CLICK_FAMILIES, TYPE_FAMILIES
except Exception:                                        # ... and its stated twin when it cannot
    CLICK_FAMILIES = {'button', 'link', 'menuitem', 'tab', 'click', 'a'}
    TYPE_FAMILIES = {'input', 'input_field', 'textarea', 'combobox', 'text', 'type', 'search'}
    _COUNT_SUFFIX = re.compile(r'\s*\(\d+\)\s*$')

    def norm_label(s):
        s = re.sub(r'\s+', ' ', (s or '')).strip().strip('*').strip()
        s = _COUNT_SUFFIX.sub('', s)
        return s.casefold()

    def families_compatible(want, have):
        if not want or not have:
            return True
        w, h = want.casefold(), have.casefold()
        if w == h:
            return True
        if w in CLICK_FAMILIES and h in CLICK_FAMILIES:
            return True
        if w in TYPE_FAMILIES and h in TYPE_FAMILIES:
            return True
        return False


_COUNT_SUFFIX_RX = re.compile(r'\s*\(\d+\)\s*$')


def norm_label_exact(s) -> str:
    """`norm_label` WITHOUT the trailing-count strip.

    The two differ only for a label that ENDS in `(n)`, and that difference is a measured wrong
    answer: a control the page calls `Amount (2)` matched a row called `Amount` and was reported as
    a plain label match (challenge D10 finding 10, 2026-09-19). The strip exists for live counts on
    related-list buttons (`Dependency Analysis (2)`), so it stays -- but a match that NEEDED it is
    said out loud in the `why`, never passed off as an exact agreement."""
    return re.sub(r'\s+', ' ', (s or '')).strip().strip('*').strip().casefold()


# D5 -- "this value changes per render", the ONE judgement, never a second opinion.
# `review_table.is_generated` reads the TEMPLATE's own `dynamicValuePatterns`; it is imported when
# the parser is importable, and when it is not (the generated CRT library ships alone inside a CRT
# container) the generator hands the SAME template block to `set_generated_rules` at import time.
# The literals below are only the floor for a library built before either of those existed.
try:
    from review_table import is_generated as _rt_is_generated
except Exception:
    _rt_is_generated = None

_GEN_PREFIXES = ('j_id', 'temp-', 'input-', 'lgt-', 'vfFrameId_')
_GEN_PATTERNS = [re.compile(p) for p in (
    r'^\d+:\d+;[a-z]$',                  # aria-controls="119:639;a"
    r'(^|:)j_id\d+(:|$)',                 # a Visualforce view-state id
    r'^[a-z][a-z0-9]*(-[a-z0-9]+)*-\d+$',  # lgt-datatable-1-options-1, input-123
    r'^[0-9a-f]{32}$',                    # a 32-hex token
    r'^[0-9a-f]{8}-[0-9a-f]{4}-',         # a uuid
    r'^[A-Za-z][A-Za-z0-9]*_\d{10,}$',    # vfFrameId_1788626362477
)]


def set_generated_rules(prefixes, patterns) -> int:
    """Adopt the TEMPLATE's own dynamicValuePatterns (the generated library calls this once).

    Returns how many patterns were adopted; anything unreadable leaves the floor in place, because
    a rule that cannot be read is not a reason to stop refusing generated values."""
    global _GEN_PREFIXES, _GEN_PATTERNS
    try:
        pats = [re.compile(p) for p in (patterns or [])]
    except Exception:
        return 0
    if not pats:
        return 0
    _GEN_PREFIXES = tuple(prefixes or ())
    _GEN_PATTERNS = pats
    return len(pats)


def is_generated(value) -> bool:
    """True when this attribute VALUE changes per render, so it can never be an identity (D5)."""
    if _rt_is_generated is not None:
        return bool(_rt_is_generated(value))
    v = str(value or '')
    if not v:
        return False
    if any(v.startswith(pre) for pre in _GEN_PREFIXES):
        return True
    return any(rx.search(v) for rx in _GEN_PATTERNS)


# The rungs a descriptor offers as "the label a person reads", in order. The first four are the
# locator doctrine's own order (visible text, aria-label, title only for icon-only controls); the
# association comes first because a form control's own text is empty.
LABEL_RUNGS = ('label', 'text', 'aria_label', 'title', 'placeholder')


def label_candidates(desc: dict) -> list:
    """[(text, rung)] for this descriptor, best first. `title` and `placeholder` are last: the
    locator doctrine allows a tooltip only for an icon-only control with no visible text."""
    out = []
    for rung in LABEL_RUNGS:
        v = (desc or {}).get(rung)
        if v and str(v).strip():
            out.append((str(v).strip(), rung))
    return out


def _default_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of the GENERATED library's embedded table."""
    return (row.get('label'), row.get('type'), row.get('index'), row.get('group_size'))


def parsed_get(row: dict) -> tuple:
    """(label, family, index, group_size) for a row of `review_table.build_rows`."""
    return (row.get('label_corrected') or row.get('label'),
            row.get('family_corrected') or row.get('element_type'),
            row.get('index_corrected') if 'index_corrected' in row else row.get('index'),
            row.get('group_size'))


# ----------------------------------------------------------------------------- the class rule
# `families_compatible` folds button / link / menuitem / tab / option into ONE click family, which
# is right for "can this row be clicked" and wrong for "is this the SAME control". Measured
# 2026-09-19 on fsc7f: the user picked `Home` in the OmniScript's Phone Type combobox (an `li`
# option, descriptor family `button`) and the descriptor branch claimed parser row 11 -- the app
# navigation's `Home` link (family `link`, tag `a`, region `chrome`; measured on the committed
# capture docs/dom-captures/fsc7f-omnistudio/01-applicationform-record-omniscript.html, row 11,
# group_size 2) -- so a correct stock line `ClickText    Home` was DEGRADED into
# `ClickText    Home    anchor=1    partial_match=False`, which at run time clicks the nav link and
# leaves the form untouched. The F42 class (a confident wrong answer) arriving through the label door.
#
# So a label match must also agree on the CONTROL CLASS, one step finer than the family: an option
# in a listbox is never a tab and never a navigation link.
_OPTION_ROLES = {'option', 'treeitem'}
_OPTION_TAGS = {'li', 'option'}
_NAV_ROLES = {'tab', 'menuitem', 'link', 'treeitem'}


def control_class(tag, role, family=None) -> str:
    """`option` / `nav` / `button` / `other` -- one step finer than the family, from whatever the
    side in hand can say. `other` is the unknown and agrees with everything."""
    t, r = str(tag or '').casefold(), str(role or '').casefold()
    f = str(family or '').casefold()
    if r in _OPTION_ROLES or t in _OPTION_TAGS:
        return 'option'
    if r in _NAV_ROLES or t == 'a' or f in ('link', 'tab', 'menuitem'):
        return 'nav'
    if t in ('button', 'input') or f == 'button':
        return 'button'
    return 'other'


def has_class_evidence(tag, role, family) -> bool:
    """True when this side said ANYTHING about what kind of control it is. `control_class` folds
    "nothing was supplied" and "something unrecognised" into the same `other`, and `other` agrees
    with everything -- so a side that carries no tag, no role and no family used to claim any row
    with the same label text (challenge 2026-09-19b case 11c). `other` is what the describer
    yields for a closed shadow root or a describe that threw."""
    return any(str(x or '').strip() for x in (tag, role, family))


def row_has_class_evidence(row: dict) -> bool:
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    return has_class_evidence(row.get('tag_corrected') or row.get('tag'), attrs.get('role'),
                              row.get('family_corrected') or row.get('element_type')
                              or row.get('type'))


def desc_has_class_evidence(desc: dict) -> bool:
    return has_class_evidence(desc.get('tag'), desc.get('role'), desc.get('family'))


def classes_agree(a: str, b: str) -> bool:
    """Two control classes name the same kind of control. `other` agrees with everything;
    `option` agrees only with `option`."""
    if a == 'other' or b == 'other':
        return True
    return a == b


def row_class(row: dict) -> str:
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    return control_class(row.get('tag_corrected') or row.get('tag'), attrs.get('role'),
                         row.get('family_corrected') or row.get('element_type') or row.get('type'))


def desc_class(desc: dict) -> str:
    return control_class(desc.get('tag'), desc.get('role'), desc.get('family'))


# The app chrome is the nav bar, the global header, the utility bar and the search box -- the
# parser already says so per row (`region`, from the template's own `chromeContainers`). A chrome
# row may only answer for an element that is ITSELF in the chrome, and the element's own path is
# the evidence: when the descriptor carries no path the rule does not fire, because an unknown is
# COULD-NOT-CHECK, never a refusal.
_CHROME_PATH_FRAGMENTS = ('one-appnav', 'one-app-nav-bar', 'onesearch', 'one-search',
                          'oneutilitybar', 'one-utility', 'globalheader', 'global-header',
                          'navigationmenuitem', 'one-tab-bar')


def _in_chrome_path(path: str) -> bool:
    p = str(path or '').casefold()
    return any(frag in p for frag in _CHROME_PATH_FRAGMENTS)


def row_may_claim(row: dict, desc: dict):
    """(True, None) when this row may answer for this descriptor's element, or (False, why not).

    Three refusals, all measured (fsc7f 2026-09-19, ledger F42's class):
      * A SIDE THAT SAID NOTHING AT ALL about what kind of control it is -- no tag, no role, no
        family -- leaves a label-text match as the only evidence, and that is COULD-NOT-CHECK, not
        agreement (challenge 2026-09-19b case 11c: `control_class` folds "nothing supplied" and
        "something unrecognised" into the same `other`, `other` agreed with everything, and an
        unstamped chrome row claimed an element the page could not class);
      * the control classes disagree -- a listbox option is not a tab and not a nav link;
      * the row lives in the app chrome while the element's own path does not.

    NARROWED FROM THE REPORT'S WORDING, BY MEASUREMENT. The challenge report's rule line reads
    "two `other` classes are COULD-NOT-CHECK". Implemented literally that refuses EVERY ordinary
    form field: `control_class` returns `other` for family `input_field` on both sides, so
    `tools/recorder/tests/challenge/test_challenge_composer_guards.py` went 7 red -- the composer
    stopped matching the reviewed rows at all. The defect the report actually measured is a side
    with NO class evidence, which is what this refuses; a stamped-but-unrecognised pair still
    agrees, because both sides did say something and they said the same thing.
    """
    rc, dc = row_class(row), desc_class(desc)
    if not desc_has_class_evidence(desc):
        return False, ('COULD-NOT-CHECK: the page could not class this element (no tag, no role, '
                       'no family), so a label-text match is the only evidence there is')
    if not row_has_class_evidence(row):
        return False, ('COULD-NOT-CHECK: the row carries no tag, no role and no family, so a '
                       'label-text match is the only evidence there is')
    if not classes_agree(rc, dc):
        return False, 'the row is a %s and the element is a %s' % (rc, dc)
    path = desc.get('xpath') or desc.get('alt_xpath') or ''
    if str(row.get('region') or '').casefold() == 'chrome' and path and not _in_chrome_path(path):
        return False, 'the row is in the app chrome and the element is not (...%s)' % str(path)[-50:]
    return True, None


def find_row(rows, desc: dict, get=_default_get):
    """(row, why) -- the row this descriptor names, by label + family, or (None, why not).

    A label that occurs once names its row outright. A label that repeats is settled by the
    descriptor's `label_index`: the element's 1-based position among the same-label, family-
    compatible controls in DOM order, counted BY THE PAGE, against the row's own `index` (the
    parser's position among the same-label matches). When the two disagree, or the page could not
    count, nothing is returned -- an ambiguous label is a COULD-NOT-DISAMBIGUATE, never a guess.

    A same-label row must ALSO pass `row_may_claim`: the control classes have to agree (a listbox
    option is not a tab and not a navigation link) and a row in the app chrome may not answer for
    an element outside it. Refusing leaves (None, why), which is the caller's signal to let the
    STOCK recorder line stand unchanged -- a plain `ClickText    Home` is a better answer than a
    confident wrong one (fsc7f 2026-09-19, ledger F42's class).
    """
    if not rows or not desc:
        return None, 'no descriptor'
    fam = desc.get('family')
    tried, refused = [], []
    for text, rung in label_candidates(desc):
        want = norm_label(text)
        if not want:
            continue
        cands = [r for r in rows
                 if norm_label(get(r)[0]) == want and families_compatible(fam, get(r)[1])]
        # ... and the class rule, one step finer than the family (F42's class, 2026-09-19)
        kept, refused_here = [], []
        for r in cands:
            ok, why_not = row_may_claim(r, desc)
            if ok:
                kept.append(r)
            else:
                refused_here.append(why_not)
        refused.extend(refused_here)
        cands = kept
        tried.append('%s=%r -> %d%s' % (rung, text[:40], len(cands),
                                        (' (%d refused: %s)' % (len(refused_here), refused_here[0]))
                                        if refused_here else ''))
        if not cands:
            continue

        def _rung(row, _rung_name=rung, _text=text):
            """The rung name, marked when the trailing-count strip is what made it agree."""
            if norm_label_exact(get(row)[0]) == norm_label_exact(_text):
                return _rung_name
            return '%s, count-normalised' % _rung_name

        if len(cands) == 1:
            return cands[0], 'label (%s) %r' % (_rung(cands[0]), text[:40])
        idx = desc.get('label_index')
        if idx:
            hits = [r for r in cands if (get(r)[2] or 1) == idx]
            if len(hits) == 1:
                return hits[0], 'label (%s) %r + page index %d of %s' % (
                    _rung(hits[0]), text[:40], idx, desc.get('label_group_size'))
        return None, ('COULD-NOT-DISAMBIGUATE: %d rows carry label %r and the page counted index %r'
                      % (len(cands), text[:40], idx))
    why = 'no row carries this descriptor label (%s)' % ('; '.join(tried) or 'none offered')
    if refused:
        # SAY WHY IT WAS REFUSED. A silent refusal reads exactly like "the page has no such row",
        # and the difference is the whole of F42: one is a control we could not name, the other is
        # a control we deliberately declined to mis-name.
        why += '; refused %d same-label row(s): %s' % (len(refused), '; '.join(refused[:3]))
    return None, why


def attribute_identity(desc, row, refused=None):
    """The stable attribute this descriptor and this row AGREE on, or None.

    NEVER a generated value, and that is now ENFORCED here rather than delegated. The docstring
    used to promise it and the function checked nothing: it trusted whatever the row carried, so a
    per-render `id="input-123"` or `name="j_id0:form:x"` that agreed on both sides became a
    confident `attribute` identity -- D5's forbidden locator as an identity (challenge D10
    finding 12, 2026-09-19). `is_generated` is now called on BOTH sides and a flagged pair is
    skipped.

    `refused` -- an optional list; the stated reason for each skipped pair is appended to it, so a
    caller can put "it agreed on a generated value" in its decision rather than reporting a silent
    miss."""
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    for key, dkey in (('name', 'name'), ('aria-label', 'aria_label'), ('data-testid', 'data_testid'),
                      ('title', 'title'), ('placeholder', 'placeholder'), ('id', 'id')):
        want, have = desc.get(dkey), attrs.get(key)
        if want and have and str(want) == str(have):
            if is_generated(str(want)) or is_generated(str(have)):
                if refused is not None:
                    refused.append("@%s=%r is a GENERATED value (changes per render): "
                                   "not an identity" % (key, want))
                continue
            return '@%s=%r' % (key, want)
    return None


# ----------------------------------------------------------------------------- the page side
RESOLVE_JS = """
var want = arguments[0];
function walk(root){
  var el = null;
  try { el = root.querySelector('[%s="' + want + '"]'); } catch (e) { el = null; }
  if (el) { return el; }
  var all = root.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var sr = all[i].shadowRoot;
    if (sr) { var r = walk(sr); if (r) { return r; } }
  }
  return null;
}
return walk(document);
""" % NONCE_ATTR

# The page-side describer. `__GZ_FE_SPEC__` is the template's own `formElementLabel` block
# (docs/recorder/templates/*.json): the SLDS shape whose label is a cousin of its control, which is
# every labelled control on Zoo_Nightmare_Inputs and most of a Lightning record page. It is injected
# by the generator, never restated here -- a fork of the parser's label rungs is exactly what this
# module must not become.
DESCRIBE_JS_TEMPLATE = r"""
;(function(){
var FE = __GZ_FE_SPEC__;
var SCAN_SELECTOR = 'input,select,textarea,button,a,[role],[contenteditable="true"]';
var SCAN_CAP = 1200;
function cls(el){ try { return (el.getAttribute && el.getAttribute('class')) || ''; } catch(e){ return ''; } }
function hasFrag(el, frags){ var c = cls(el); for (var i=0;i<(frags||[]).length;i++){ if (c.indexOf(frags[i])>=0) return true; } return false; }
function isFormElement(el){ var c = cls(el); if (c.indexOf(FE.containerClassFragment)<0) return false;
  var ex = FE.excludeContainerClassFragments||[]; for (var i=0;i<ex.length;i++){ if (c.indexOf(ex[i])>=0) return false; } return true; }
function txt(el){ var t=''; try { t = el.innerText || el.textContent || ''; } catch(e){} return t.replace(/\s+/g,' ').trim(); }
/* Is this element actually RENDERED? The describer used to read `innerText || textContent` off any
   element a label rung pointed at, so a `display:none` <span> named by aria-labelledby still yielded
   its text -- while the serializer that takes OUR capture drops display:none subtrees, so the parser
   never saw that label and the row was unlabelled. The two halves read the same page and disagreed
   about what is on it (challenge D10 finding 11, 2026-09-19). offsetParent alone is not enough: it
   is null for a position:fixed element that IS on screen, hence the client-rect fallback. When the
   question cannot be asked at all the answer is YES -- a describer must not silently drop a label
   because a browser threw. */
function shown(el){ try { if (!el) return false; if (el.offsetParent !== null) return true; var r = el.getClientRects ? el.getClientRects() : null; if (r && r.length) return true; var d = el.ownerDocument; if (!d || !d.defaultView || !d.defaultView.getComputedStyle) return true; var cs = d.defaultView.getComputedStyle(el); if (!cs) return true; return !(cs.display === 'none' || cs.visibility === 'hidden'); } catch(e){ return true; } }
function vtxt(el){ return shown(el) ? txt(el) : ''; }
function up(el){ if (!el) return null; if (el.parentElement) return el.parentElement;
  var p = el.parentNode; return (p && p.host) ? p.host : null; }
function esc(s){ try { return (window.CSS && CSS.escape) ? CSS.escape(String(s)) : String(s).replace(/["\\]/g,'\\$&'); } catch(e){ return String(s); } }
function attr(el,k){ try { var v = el.getAttribute(k); return (v===null||v==='') ? null : v; } catch(e){ return null; } }
function formElementLabel(el){
  var tags = FE.targetTags || [], tag = el.tagName.toLowerCase();
  if (tags.length && tags.indexOf(tag) < 0){
    var wrapper = FE.wrapperMayBeTarget && tag.indexOf('-')>0 &&
                  el.querySelectorAll('input,select,textarea').length === 1;
    if (!wrapper) return '';
  }
  var p = up(el), hops = 0;
  while (p && hops < 4){ if (hasFrag(p, FE.targetInsideExcludedClassFragments)) return ''; p = up(p); hops++; }
  var cur = up(el), h = 0, max = FE.maxClimb || 8;
  while (cur && h < max){
    if (isFormElement(cur)){
      var all = cur.querySelectorAll('*');
      for (var i=0;i<all.length;i++){
        var c = all[i], toks = cls(c).split(/\s+/), hit = false, frs = FE.labelClassFragments || [];
        for (var j=0;j<frs.length;j++){ if (toks.indexOf(frs[j])>=0){ hit = true; break; } }
        if (hit && c !== el && !c.contains(el)){ var t = vtxt(c); if (t) return t; }
      }
    }
    cur = up(cur); h++;
  }
  return '';
}
function nearestLabel(el){
  var root = el.getRootNode ? el.getRootNode() : document;
  try { var id = attr(el,'id');
        if (id){ var l = root.querySelector('label[for="'+esc(id)+'"]'); if (l){ var t=vtxt(l); if (t) return [t,'label_for']; } } } catch(e){}
  try { var lb = attr(el,'aria-labelledby');
        if (lb){ var parts = lb.split(/\s+/), out = [];
          for (var i=0;i<parts.length;i++){ var n = null;
            try { n = root.getElementById ? root.getElementById(parts[i]) : root.querySelector('#'+esc(parts[i])); } catch(e){}
            if (n) out.push(vtxt(n)); }
          var t2 = out.join(' ').trim(); if (t2) return [t2,'aria_labelledby']; } } catch(e){}
  try { var a = el.closest ? el.closest('label') : null; if (a){ var t3 = vtxt(a); if (t3) return [t3,'wrapping_label']; } } catch(e){}
  var fe = formElementLabel(el); if (fe) return [fe,'form_element_label'];
  try { var s = el.previousElementSibling, g = 0;
        while (s && g < 3){ if (s.tagName === 'LABEL' || hasFrag(s, FE.labelClassFragments)){ var t4 = vtxt(s); if (t4) return [t4,'sibling_label']; } s = s.previousElementSibling; g++; } } catch(e){}
  return ['', null];
}
function familyOf(el){
  var tag = el.tagName.toLowerCase(), ty = (attr(el,'type')||'').toLowerCase(), role = (attr(el,'role')||'').toLowerCase();
  if (tag === 'select') return 'dropdown';
  if (tag === 'textarea') return 'input_field';
  if (tag === 'input'){ if (ty === 'checkbox') return 'checkbox'; if (ty === 'radio') return 'radio';
                        if (ty === 'button' || ty === 'submit' || ty === 'reset') return 'button'; return 'input_field'; }
  if (tag === 'button' || tag === 'a') return 'button';
  if (role === 'button' || role === 'tab' || role === 'menuitem' || role === 'option' || role === 'link') return 'button';
  if (role === 'combobox' || role === 'textbox' || role === 'searchbox') return 'input_field';
  if (role === 'checkbox' || role === 'switch') return 'checkbox';
  return tag;
}
var CLICKF = {button:1, link:1, menuitem:1, tab:1, click:1, a:1};
var TYPEF  = {input:1, input_field:1, textarea:1, combobox:1, text:1, type:1, search:1};
function compat(a,b){ if (!a || !b) return true; if (a === b) return true;
  if (CLICKF[a] && CLICKF[b]) return true; if (TYPEF[a] && TYPEF[b]) return true; return false; }
function norm(s){ return String(s||'').replace(/\s+/g,' ').trim().replace(/^\*|\*$/g,'').trim().replace(/\s*\(\d+\)\s*$/,'').toLowerCase(); }
function controls(){
  /* ONE depth-first walk, shadow content inlined right after its host, so the list is in the page's
     own reading order -- the order the parser sees in a capture (shadow roots serialise in place as
     <template>). Collecting a root's own matches first and descending afterwards counted a control
     at shadow depth 2 before one at depth 1 and the index disagreed with the review's. */
  var out = [], capped = false;
  function walk(root){
    if (capped) return;
    var all; try { all = root.querySelectorAll('*'); } catch(e){ all = []; }
    for (var i=0;i<all.length;i++){
      var e = all[i], hit = false;
      try { hit = e.matches && e.matches(SCAN_SELECTOR); } catch(err){ hit = false; }
      if (hit){ out.push(e); if (out.length >= SCAN_CAP){ capped = true; return; } }
      if (e.shadowRoot){ walk(e.shadowRoot); if (capped) return; }
    }
  }
  walk(document);
  return {list: out, capped: capped};
}
function labelIndex(el, label, fam){
  if (!label) return null;
  var want = norm(label), c = controls(), k = 0, found = null;
  for (var i=0;i<c.list.length;i++){
    var e = c.list[i];
    if (!compat(fam, familyOf(e))) continue;
    var L = nearestLabel(e)[0] || txt(e).slice(0,80);
    if (norm(L) !== want) continue;
    k++;
    if (e === el) found = k;
  }
  return {index: found, group_size: k, scanned: c.list.length, capped: c.capped};
}
/* The OmniStudio element's own metadata id. `data-omni-key` equals `OmniProcessElement.Name`. This
   walks UP -- through shadow hosts, via the same `up()` every label rung uses. It is what
   `keywords_omni.__host` resolves, which makes it the first argument of `Omni Type` / `Omni Date`;
   without it the composer leaves the stock TypeText line alone (measured 2026-09-19: TypeText's
   clear does not clear an OmniScript text input and the value APPENDS, so the keyword choice is not
   cosmetic).

   WHERE THE KEY ACTUALLY SITS, measured on the committed fsc7f captures (2026-09-19, build n2):
   in an OmniScript the attribute is on the `runtime_omnistudio_omniscript-omniscript-<type>`
   ELEMENT host -- every one of the 14 `data-omni-key` occurrences in
   docs/dom-captures/fsc7f-omnistudio/03-applicationform-omniscript-postintake.html is on such a
   host (`-omniscript-step`, `-omniscript-ip-action`, `-omniscript-text-block`, ...), NOT on the
   `runtime_omnistudio_common-*` control one level below it.

   WHY THE DATE PICKER MISSED IT (build n, run 5: `omniKey` returned null for Date of Birth and the
   fill fell back to the stock TypeText). It was the HOP CAP, not a missing attribute. The date
   input sits EIGHT div levels inside `runtime_omnistudio_common-date-picker`'s shadow root -- the
   live recording's own path tail is `.../-date-picker[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]
   /div[2]/input[1]`, and 02-home-flexcard-loancalculator.html shows the same nesting. So the input
   is 9 hops below the date-picker host, 10 below `runtime_omnistudio_common-input` and ~11 below
   the omniscript element that carries the key; the old `h < 8` cap stopped three hops short and
   returned null silently. The cap is raised to the measured depth plus headroom, and the walk stops
   AT the omniscript element boundary -- if that host has no key, there is none to find and climbing
   into the container would return a neighbouring element's key, which is worse than none.
   TWO boundaries, because not every `data-omni-key` names a CONTROL. A container carries one too
   (`-omniscript-step` is keyed `ApplicationSummary`; `runtime_omnistudio-flexcard` is keyed
   `ApplicationSummaryFC`, both measured in capture 03), and handing a container's key to
   `Omni Type` would drive whatever input that container happens to hold first -- the six-times bug
   in a new costume. So a CONTAINER stops the walk WITHOUT reading, and only the OmniScript ELEMENT
   host stops it after reading. Reaching either with nothing is null, which the composer already
   says out loud and answers with the stock TypeText line. */
var OMNI_KEY_MAX_HOPS = 20;
/* THE CAP GETS ITS OWN ANSWER (challenge 2026-09-19b case 12). `null` used to mean BOTH "this
   element genuinely carries no key" and "the walk gave up before it got there", and the composer
   reported the first for the second -- a false statement of fact, on a page where the key existed.
   Stopping on the cap now returns this sentinel; `__gzDescribe` turns it into `omni_key: null`
   PLUS `omni_key_capped: <hops>`, so the composer can say "not reached within N hops". */
var OMNI_KEY_CAP = '__gz_omni_key_cap__';
var OMNI_KEY_CONTAINER_RX = /^(runtime_omnistudio-(flexcard|omniscript|generated-omniscript)|runtime_omnistudio_flexcards-|runtime_omnistudio_omniscript-omniscript-(container|step)$)/;
var OMNI_KEY_ELEMENT_RX = /^runtime_omnistudio_omniscript-omniscript-/;
function omniKey(el){ var cur = el, h = 0;
  while (cur && h < OMNI_KEY_MAX_HOPS){
    var t = cur.tagName ? cur.tagName.toLowerCase() : '';
    if (OMNI_KEY_CONTAINER_RX.test(t)) return null;   /* its key names the container, not this control */
    var k = attr(cur,'data-omni-key'); if (k) return k;
    if (OMNI_KEY_ELEMENT_RX.test(t)) return null;     /* the element host itself, keyless */
    cur = up(cur); h++; }
  return cur ? OMNI_KEY_CAP : null; }   /* stopped ON THE CAP, not on a boundary: say which */
function hostChain(el){
  var out = [], r = el.getRootNode ? el.getRootNode() : document, g = 0;
  while (r && r !== document && r.host && g < 12){ out.push(r.host.tagName.toLowerCase()); r = r.host.getRootNode ? r.host.getRootNode() : document; g++; }
  return out;
}
window.__gzDescribe = function(el){
  var d = {};
  try {
    d.tag = el.tagName.toLowerCase();
    d.type = attr(el,'type');
    d.name = attr(el,'name');
    d.id = attr(el,'id');              /* raw: the composer only uses it when the ROW carries the
                                          same value, and the parser strips generated ones (D5) */
    d.aria_label = attr(el,'aria-label');
    d.placeholder = attr(el,'placeholder');
    d.title = attr(el,'title');
    d.role = attr(el,'role');
    d.data_testid = attr(el,'data-testid') || attr(el,'data-test-id');
    var _ok = omniKey(el);             /* OmniProcessElement.Name, off the element HOST */
    d.omni_key = (_ok === OMNI_KEY_CAP) ? null : _ok;
    d.omni_key_capped = (_ok === OMNI_KEY_CAP) ? OMNI_KEY_MAX_HOPS : null;
    d.text = txt(el).slice(0,80);
    var nl = nearestLabel(el);
    d.label = nl[0] || null;
    d.label_source = nl[1];
    d.family = familyOf(el);
    var root = el.getRootNode ? el.getRootNode() : document;
    d.in_shadow = !!(root && root !== document && root.host);
    d.host_chain = hostChain(el);
    var li = labelIndex(el, d.label || d.text, d.family);
    d.label_index = li ? li.index : null;
    d.label_group_size = li ? li.group_size : null;
    d.scan_capped = li ? li.capped : null;
  } catch (e) { d.error = String(e); }
  return d;
};
var NONCE_N = 0;
window.__gzStamp = function(el){
  try {
    var n = 'gz' + (++NONCE_N) + '-' + Date.now().toString(36);
    el.setAttribute('%(attr)s', n);
    setTimeout(function(){ try { if (el.getAttribute('%(attr)s') === n) el.removeAttribute('%(attr)s'); } catch(e){} }, %(ttl)d);
    return n;
  } catch (e) { return null; }
};
})();
""" % {'attr': NONCE_ATTR, 'ttl': NONCE_TTL_MS}


def describe_js(fe_spec: dict) -> str:
    """The page-side describer with the template's formElementLabel block injected."""
    return DESCRIBE_JS_TEMPLATE.replace('__GZ_FE_SPEC__', json.dumps(fe_spec or {}))
# ------------------------------------------------------------------------------------------------
set_generated_rules(GEN_SPEC.get("prefixes"), GEN_SPEC.get("patterns"))   # D5, for attribute_identity
DESCRIBE_JS = describe_js(FE_SPEC)
BUNDLE = "/home/services/ui-recorder/content.bundle.js"
BACKUP = BUNDLE + ".gz-orig"
LOG = "/home/services/log/gz_override.log"
PORT = 18077
CALL = "this.pushStep(r,event,ctx?this.handler.getXPathForElement(ctx):undefined)"
REPL = "window.__gzCompose(this,r,event,ctx)"
JS = r"""
;(function(){var U='http://127.0.0.1:%(port)d';window.__gzQ=Promise.resolve();window.__gzSeen={};window.__gzPending={};window.__gzPendingEl={};var HOLD=900;
function axp(el){if(!el||el.isConnected===false)return null;var p=[];while(el&&el.nodeType===1&&el.tagName.toLowerCase()!=='html'){var i=1,s=el.previousElementSibling;while(s){if(s.tagName===el.tagName)i++;s=s.previousElementSibling}p.unshift(el.tagName.toLowerCase()+'['+i+']');el=el.parentElement}return el?('/html[1]/'+p.join('/')):null}
var ASK_MS=6000;function ask(body){body.frame=(window!==window.top);try{body.frame_path=location.pathname}catch(e){body.frame_path=''}var ctl=(typeof AbortController!=='undefined')?new AbortController():null;var timer=setTimeout(function(){try{ctl&&ctl.abort()}catch(e){}},ASK_MS);return fetch(U+'/compose',{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify(body),signal:ctl?ctl.signal:undefined}).then(function(res){clearTimeout(timer);return res.json()}).catch(function(e){clearTimeout(timer);throw e})}
function enqueue(fn){window.__gzQ=window.__gzQ.then(fn).catch(function(e){console.log('gz queue',e)})}
/* THE IN-BAND OUTCOME. The composer's verdicts are written into the page under test, on TWO
   surfaces, so whichever one a DOM snapshot keeps carries them back out with the next keyword
   reply: a <script type="application/json" id="gz-outcome"> element and the same JSON on
   <html data-gz-outcome>. Read by tools/crt_live/session.py keyword --outcome. */
function gzOutcome(j){try{if(!j||!j.outcome)return;var s=JSON.stringify(j.outcome);var id=j.outcome_id||'gz-outcome';var at=j.outcome_attr||'data-gz-outcome';var r=document.documentElement;if(r&&r.setAttribute)r.setAttribute(at,s);var e=document.getElementById(id);if(!e){e=document.createElement('script');e.type='application/json';e.id=id;(document.head||r).appendChild(e)}e.textContent=s}catch(e){console.log('gz outcome',e)}}
function stampAndDescribe(el){var out={nonce:null,descriptor:null};try{if(el&&el.nodeType===1&&window.__gzStamp){out.nonce=window.__gzStamp(el);out.descriptor=window.__gzDescribe(el)}}catch(e){out.describe_error=String(e)}return out}
window.__gzCompose=function(self,r,event,ctx){window.__gzRec=self;var x=ctx?self.handler.getXPathForElement(ctx):undefined;
 var alt;try{if(ctx&&ctx.nodeType===1){alt=axp(ctx);if(alt){window.__gzSeen[alt]=Date.now();Object.keys(window.__gzPending).forEach(function(k){var pe=window.__gzPendingEl[k];if(k===alt||(pe&&(pe===ctx||pe.contains(ctx)||ctx.contains(pe)))){clearTimeout(window.__gzPending[k]);delete window.__gzPending[k];delete window.__gzPendingEl[k];window.__gzSeen[k]=Date.now()}})}}}catch(e){}
 var mark=stampAndDescribe(ctx);
 enqueue(function(){return ask({rendered:r,xpath:x,alt_xpath:alt,nonce:mark.nonce,descriptor:mark.descriptor}).then(function(j){gzOutcome(j);var line=(j&&typeof j.line==='string')?j.line:r;((j&&j.pre)||[]).forEach(function(pp){self.pushStep(pp,event,x)});if(line!==''){self.pushStep(line,event,x)}((j&&j.backups)||[]).forEach(function(b){self.pushStep(b,event,x)})}).catch(function(e){console.log('gz compose failed',e);self.pushStep(r,event,x)})})};
function safetyNet(ev,kind){try{var tg=ev.composedPath?ev.composedPath()[0]:ev.target;if(!tg||tg.nodeType!==1)return;var el=tg;
 if(kind==='click'){el=tg.closest('button,a,[role="button"],[role="option"],[role="tab"],[role="menuitem"],[role="checkbox"],input,select,option,[class*="zn-arrow"],lightning-button-icon,lightning-button,lightning-icon')||tg}
 var self=window.__gzRec;if(!self){console.log('gz safety-net: no recorder instance yet');return}
 var k=axp(el);if(!k){console.log('gz safety-net: the element is detached; no positional key');return}var now=Date.now();if(window.__gzSeen[k]&&now-window.__gzSeen[k]<1500)return;if(window.__gzPending[k])clearTimeout(window.__gzPending[k]);window.__gzPendingEl[k]=el;
 var value=(kind==='change')?(el.type==='checkbox'?(el.checked?'on':'off'):(el.value!==undefined?String(el.value):'')):undefined;
 var mark=stampAndDescribe(el);
 window.__gzPending[k]=setTimeout(function(){delete window.__gzPending[k];delete window.__gzPendingEl[k];if(window.__gzSeen[k]&&Date.now()-window.__gzSeen[k]<1500+HOLD)return;window.__gzSeen[k]=Date.now();
  enqueue(function(){return ask({rendered:'',xpath:k,synthetic:true,kind:kind,value:value,nonce:mark.nonce,descriptor:mark.descriptor,tag:el.tagName.toLowerCase(),etype:(el.type||''),text:(el.textContent||'').trim().slice(0,80)}).then(function(j){gzOutcome(j);((j&&j.pre)||[]).forEach(function(pp){self.pushStep(pp,ev,k)});if(j&&j.line){self.pushStep(j.line,ev,k)}((j&&j.backups)||[]).forEach(function(b){self.pushStep(b,ev,k)})})})},HOLD)}catch(e){}}
document.addEventListener('click',function(ev){safetyNet(ev,'click')},true);
document.addEventListener('change',function(ev){safetyNet(ev,'change')},true);
try{fetch(U+'/ping').catch(function(){})}catch(e){}})();
"""
STATE = {"version": "2026-09-19n6 inband", "dormant_form": "keyword", "form": "keyword", "org": None, "patched": None,
         "replacements": 0, "served": 0, "decisions": [], "server": None, "error": None}

# ------------------------------------------------------------------ the IN-BAND outcome channel
# The composer's verdicts used to live in ONE place the container never hands back:
# /home/services/log/gz_override.log. A person reading the pane sees lines and no reasons, and the
# only way to ask the library anything was `Gz Override Status`, which needs a Robot step of its
# own. So after every decision the library writes its last GZ_OUTCOME_N (10) decisions INTO THE PAGE
# UNDER TEST -- `<script type="application/json" id="gz-outcome">` plus the same JSON on
# `<html data-gz-outcome>` (two surfaces, because which one a DOM snapshot keeps is the
# serializer's choice, not ours, and this repo has not measured the CRT healing-context
# serializer). The keyword reply's own snapshot then carries it back out:
# `tools/crt_live/session.py keyword --outcome` parses it, and `Gz Override Outcome` returns the
# same JSON to a Robot caller. NO DOM TEXT travels -- the composed line, the reason, the served
# count and the build version, nothing read off the page.
GZ_OUTCOME_ID = "gz-outcome"
GZ_OUTCOME_ATTR = "data-gz-outcome"
GZ_OUTCOME_N = 10
GZ_OUTCOME_WHY_CHARS = 400

# --------------------------------------------------------------- the parser bundle (page with no review)
BUNDLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garzai_parser")
BUNDLE_ENTRY = os.path.join(BUNDLE_DIR, "tools", "recorder", "crt_override")
BUNDLE_VENDOR = os.path.join(BUNDLE_DIR, "tools", "interop", "resources", "pythonDom", "vendor")
PARSER = {"state": "missing", "reason": "no bundle at %s" % BUNDLE_DIR, "proposals": 0}
if os.path.isdir(BUNDLE_ENTRY):
    PARSER["state"], PARSER["reason"] = "present (not imported yet)", None
_CL = None
_CACHE = {}          # compose_live's per-page capture cache: ONE capture per page, not per event


def _log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")
    except Exception:
        pass


def _patch_bundle():
    try:
        if not os.path.exists(BUNDLE):
            STATE["patched"] = "bundle not found"; _log(STATE["patched"]); return
        src = open(BUNDLE, encoding="utf-8", errors="ignore").read()
        if "__gzCompose" in src:
            STATE["patched"] = "already patched"; STATE["replacements"] = src.count(REPL); return
        n = src.count(CALL)
        if n == 0:
            STATE["patched"] = "call site not found (bundle version differs); nothing changed"; _log(STATE["patched"]); return
        if not os.path.exists(BACKUP):
            shutil.copyfile(BUNDLE, BACKUP)
        out = src.replace(CALL, REPL) + DESCRIBE_JS + (JS % {"port": PORT})
        with open(BUNDLE, "w", encoding="utf-8") as f:
            f.write(out)
        STATE["patched"] = "ok"; STATE["replacements"] = n
        _log("patched %d call site(s) at import; chrome pids now: %s" % (n, _chrome_pids()))
    except Exception as exc:
        STATE["patched"] = "error: %s" % exc; _log(traceback.format_exc())


def _chrome_pids():
    try:
        import subprocess
        return subprocess.run(["pgrep", "-f", "/opt/chrome/chrome --"], capture_output=True, text=True).stdout.split()
    except Exception:
        return "?"


def _driver():
    from QWeb.internal import browser as _b
    return _b.get_current_browser()


def _unescape_xpath(step):
    m = re.match(r"\s*ClickElement\s{2,}xpath\\=(.+?)\s*$", step)
    return m.group(1).replace("\\=", "=") if m else None


def _recipe_step_for(drv, target):
    """A corrected recipe's own ClickElement step whose xpath resolves to this element (the
    dual-listbox move arrow lives only inside row 77's recipe, not as a row of its own)."""
    for row in ROWS:
        for step in (row.get("corrected") or "").split(" ;; "):
            xp = _unescape_xpath(step)
            if not xp:
                continue
            try:
                els = drv.find_elements("xpath", xp)
            except Exception:
                continue
            if len(els) == 1 and drv.execute_script("return arguments[0] === arguments[1]", els[0], target):
                return row["n"], "    " + step.strip()
    return None, None


def _parser():
    """The parser bundle, imported on the FIRST event that needs it and never at parse time.

    Robot imports this Library while it reads the Settings table -- long before a browser exists --
    and an import that raises there fails the whole suite. So nothing about the bundle is touched
    until an event arrives that the embedded rows and their recipes cannot name. A missing bundle,
    or one whose import fails (no `lxml` in the container is the obvious candidate: QWeb 3.8.2 does
    not require it), leaves the previous behaviour exactly as it was and says so."""
    global _CL
    if _CL is not None or PARSER["state"] in ("missing", "error"):
        return _CL
    try:
        for p in (BUNDLE_ENTRY, BUNDLE_VENDOR):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        import compose_live as _cl
        _CL = _cl
        PARSER["state"] = "loaded"
        _log("parser bundle loaded from %s" % BUNDLE_DIR)
    except Exception as exc:
        PARSER["state"] = "error"
        PARSER["reason"] = "%s: %s" % (type(exc).__name__, exc)
        _log("parser bundle import failed: " + traceback.format_exc())
    return _CL


def _pseudo_rendered(req):
    """A synthetic event carries no recorder line, and every rule in the composer is keyed on the
    ACTION. So render the event as the line the recorder WOULD have written and let the composer's
    own branches decide: a value change on a <select> is a DropDown, on a checkbox a click, on
    anything else a TypeText; a click carries its visible text so a button resolves by its label
    rather than by an absolute path."""
    kind, val = req.get("kind"), req.get("value")
    etype = (req.get("etype") or "").lower()
    tag = (req.get("tag") or "").lower()
    if kind == "change" and val is not None:
        if tag == "select":
            return "    DropDown    L    %s" % val
        if etype in ("checkbox", "radio"):
            return "    ClickElement    x"
        return "    TypeText    x    %s" % val
    if kind == "click":
        text = (req.get("text") or "").strip()
        return ("    ClickText    %s" % text) if text else ""
    return ""


def _propose(drv, target, rendered, decision, desc=None):
    """No embedded row and no recipe step names this element: compose from OUR OWN capture of the
    live page. Returns (line, backups) -- `None` means the recorder's own line stands, `''` means
    record nothing, and anything else is a PROPOSAL, marked unverified by compose_live itself.

    The descriptor travels with it (build k): a control in a native shadow root is in our capture
    and in the parsed rows, but NO xpath from the driver reaches it, so the `===` identity match
    finds nothing and label + family is the only way it gets a proposal at all (ledger F40)."""
    cl = _parser()
    if cl is None:
        return None, []
    try:
        res = cl.compose_live_element(drv, target, rendered, org=STATE.get("org"), cache=_CACHE,
                                      form=STATE.get("form") or "keyword", descriptor=desc)
    except Exception as exc:
        decision["parser"] = "error: %s" % exc
        _log("parser proposal failed: " + traceback.format_exc())
        return None, []
    decision["parser"] = "%s | rows %s" % (res.get("why"), res.get("rows"))
    row = res.get("row") if isinstance(res.get("row"), dict) else None
    decision["parser_row"] = row.get("n") if row else None     # NOT decision["row"]: that indexes
    line = res.get("line")                                     # the EMBEDDED rows and would make
    if line is None:                                           # _backups answer for a stranger
        return None, []
    if line == "":
        decision["why"] = "parser proposal: record nothing (%s)" % res.get("why")
        return "", []
    PARSER["proposals"] += 1
    decision["why"] = "parser proposal"
    backups = []
    xl = res.get("xpath_line")
    if STATE.get("backups", True) and xl:
        alt = xl.replace(cl.UNVERIFIED, "").strip()
        if alt and alt != line.replace(cl.UNVERIFIED, "").strip():
            indent = line[: len(line) - len(line.lstrip())] or "    "
            backups.append("%s#   backup: %s   (xpath form, unverified: parser proposal)" % (indent, alt))
    return line, backups


# The pane mark for a line whose row was named by the POSITIONAL identity xpath and nothing else.
# A parser proposal says `# unverified: parser proposal`; this is the same disclosure for the other
# unverified door, and it is a Robot comment so the line still runs as written.
POSITIONAL_MARK = "# positional identity: last resort"


def _cells(line):
    # `# ` (hash SPACE) is one of our own trailing marks -- the positional-identity disclosure, the
    # unverified marker, the xpath-form note -- never an argument; a value that merely starts with
    # `#` (a hashtag someone typed) has no space and is kept.
    return [c for c in re.split(r" {2,}|\t", line.strip()) if c != "" and not c.startswith("# ")]


def _our_line(row, rendered):
    """Our line for this row, carrying the value the recorder saw, with the recorder's own
    leading whitespace: the editor inserts only a line that starts like a step (measured 2026-09-18,
    six composed lines arrived at the editor as keyword messages and none reached the pane)."""
    line = _our_line_body(row, rendered)
    if line is None:
        return None
    if line == "":
        return ""  # suppress: the recorder's line is noise for this control
    form = STATE.get("form") or "keyword"
    xp_ok = row.get("xp_verdict") == "VERIFIED-PASS" and row.get("xpath")
    if form in ("xpath", "both") and xp_ok and "xpath\\=" not in line:
        cells = _cells(line)
        if cells and cells[0] in ("TypeText", "ClickText", "ClickCheckbox", "ClickElement"):
            kw = "ClickElement" if cells[0] in ("ClickText", "ClickElement") else cells[0]
            args = [c for c in cells[2:] if not c.startswith("anchor=") and not c.startswith("partial_match=")]
            xline = "    ".join([kw, _xp(row)] + args)
            line = xline if form == "xpath" else line.strip() + "    # xpath form: " + xline
    indent = rendered[: len(rendered) - len(rendered.lstrip())] or "    "
    return indent + line.strip()


def _xp(row):
    return "xpath\\=%s" % row["xpath"].replace("=", "\\=")


def _our_line_body(row, rendered):
    cells = _cells(rendered)
    action = cells[0] if cells else ""
    value = cells[-1] if len(cells) >= 3 else None
    idx = row.get("index") or 1
    grp = row.get("group_size") or 1
    t = row.get("type"); kw = row.get("kw"); loc = row.get("locator") or row.get("label")
    if t == "dual_listbox" and action == "ClickText" and len(cells) >= 2:
        # the dueling-list recipe: click the OPTION the user clicked, exact text; the move-right
        # control and the read-back under Selected are the recipe's next lines
        return "ClickText    %s    partial_match=False" % cells[1]
    xp_ok = row.get("xp_verdict") == "VERIFIED-PASS" and row.get("xpath")
    kw_ok = row.get("kw_verdict") == "VERIFIED-PASS"
    if t == "input_field" and action in ("ClickText", "VerifyText"):
        # the focus click renders the field's current value as ClickText and the tab-out renders
        # the next field's value as VerifyText (measured 2026-09-18, 8 of 17 recorded lines); the
        # TypeText that follows carries the intent
        return ""
    if action == "":
        # a synthetic event: our own listener saw a click or a value change the recorder emitted nothing for
        kind = (row.get("_syn") or {}).get("kind"); sval = (row.get("_syn") or {}).get("value")
        if kind == "change" and t == "input_field" and sval is not None:
            if kw_ok:
                return "TypeText    %s    %s%s" % (loc, sval, ("    anchor=%d" % idx) if grp > 1 else "")
            return ("TypeText    %s    %s" % (_xp(row), sval)) if xp_ok else None
        if kind == "change" and t == "checkbox" and sval is not None:
            return "ClickCheckbox    %s    %s%s" % (loc, sval, ("    anchor=%d" % idx) if grp > 1 else "")
        if kind == "change" and t == "dropdown" and sval is not None:
            return "DropDown    %s    %s%s" % (loc, sval, ("    anchor=%d" % idx) if grp > 1 else "")
        if kind == "click" and t == "input_field":
            return ""  # a focus click; the change event carries the intent
        if kw_ok and loc and t in ("button", "link", "tab"):
            return "ClickText    %s%s    partial_match=False" % (loc, ("    anchor=%d" % idx) if grp > 1 else "")
        if xp_ok:
            return "ClickElement    %s" % _xp(row)
        return None
    if not row.get("locator") and not row.get("label"):
        if xp_ok and action in ("ClickText", "ClickElement", "ClickItem"):
            return "ClickElement    %s" % _xp(row)
        return None
    if t == "input_field" and action == "ClickElement" and xp_ok and not row.get("corrected"):
        return "ClickElement    %s" % _xp(row)
    if row.get("corrected"):
        if action in ("ClickElement", "TypeText"):
            return row["corrected"].split(" ;; ")[0]
        return None  # their text click on an option already passes; keep it
    if t == "input_field" and action in ("TypeText", "TypeSecret") and value is not None:
        if kw_ok:
            return "TypeText    %s    %s%s" % (loc, value, ("    anchor=%d" % idx) if grp > 1 else "")
        if row.get("xpath"):
            return "TypeText    %s    %s" % (_xp(row), value)
        return None
    if t == "checkbox":
        return "ClickCheckbox    %s    on%s" % (loc, ("    anchor=%d" % idx) if grp > 1 else "")
    if t in ("button", "link", "tab") and action in ("ClickText", "ClickElement", "ClickItem"):
        return "ClickText    %s%s    partial_match=False" % (loc, ("    anchor=%d" % idx) if grp > 1 else "")
    if t == "dropdown" and action == "DropDown":
        return None  # theirs already passes
    return None


def _dormant_form(text):
    """A dormant line (`#   backup:`, `#   verify:`, `#   why xpath:`, `#   label repeats`) in the
    form the editor will KEEP. Measured 2026-09-19 (four fsc7f sessions, builds l and m): the
    composer built 2-3 backups per fill and the JSON carried them, yet not one `#` line reached
    the pane -- the same push path had shown them on the wire on 2026-09-18 (k2), so the drop is
    in the editor's step model, not ours. `keyword` (default): the line becomes
    `<indent>Comment    backup: ...`, a real BuiltIn.Comment step that does nothing when run and
    survives the editor; a person makes it live by deleting `Comment    backup: `. `comment`: the
    bare `#` form, for an editor that keeps comments. `Gz Override Dormant Form` switches."""
    if STATE.get("dormant_form", "keyword") != "keyword":
        return text
    stripped = text.lstrip()
    if not stripped.startswith("#"):
        return text
    indent = text[: len(text) - len(stripped)]
    body = stripped.lstrip("#").strip()
    return "%sComment    %s" % (indent, body)


def _backups(row_n, line, rendered):
    """Dormant comment lines pushed under a composed step (user, 2026-09-18: 'a few other high
    confidence back up options ... in the live testing log'): the row's OTHER verified form and
    the anchor texts the ladder saw. Ranked by verdict; nothing unverified is offered as advice;
    at most two lines; never on a suppressed or pass-through line."""
    if not STATE.get("backups", True) or row_n is None or not line or line.strip() == rendered.strip():
        return []
    row = next((r for r in ROWS if r.get("n") == row_n), None)
    if not row:
        return []
    indent = line[: len(line) - len(line.lstrip())] or "    "
    out = []
    cells = _cells(line)
    if not cells:
        return []
    args = [c for c in cells[2:] if not c.startswith(("anchor=", "partial_match=", "clear_key=", "timeout="))]
    value = args[0] if cells[0] == "TypeText" and args else None
    if "xpath\\=" not in line and row.get("xp_verdict") == "VERIFIED-PASS" and row.get("xpath"):
        kw = "ClickElement" if cells[0] in ("ClickText", "ClickElement") else cells[0]
        alt = "    ".join([kw, _xp(row)] + ([value] if value else []))
        out.append("%s#   backup: %s   (xpath form VERIFIED-PASS%s)" % (indent, alt, (" " + str(row["xp_date"])) if row.get("xp_date") else ""))
    elif "xpath\\=" in line and row.get("kw_verdict") == "VERIFIED-PASS" and row.get("locator"):
        alt = "    ".join([cells[0], row["locator"]] + ([value] if value else []) + (["anchor=%d" % (row.get("index") or 1)] if (row.get("group_size") or 1) > 1 else []))
        out.append("%s#   backup: %s   (keyword form VERIFIED-PASS)" % (indent, alt))
    elif "xpath\\=" in line and row.get("kw_verdict") == "CAUGHT-BUG" and row.get("locator"):
        out.append("%s#   why xpath: keyword form '%s' CAUGHT-BUG live%s" % (indent, row["locator"], (": " + row["kw_note"]) if row.get("kw_note") else ""))
    if (row.get("group_size") or 1) > 1 and row.get("anchors"):
        out.append("%s#   label repeats x%d; anchors seen: %s" % (indent, row["group_size"], " | ".join(str(a) for a in row["anchors"])))
    return out[:2]


_LAST = {"el": None, "t": 0.0, "action": None, "label": None, "family": None, "value": None}
_LOCK = threading.Lock()   # the selenium driver is not thread-safe and _CACHE/_LAST are shared


def _action_class(rendered, req=None):
    """click / type / select / verify -- what this event DID, or None when it cannot be told.

    The dedupe is keyed on it: a focus CLICK and the TypeText that follows are two different
    intents on one element, and treating them as the same event lost the typed value."""
    cells = _cells(rendered or "")
    kw = (cells[0] if cells else "").lower()
    if kw.startswith("type"):
        return "type"
    if kw.startswith("click"):
        return "click"
    if kw in ("dropdown", "picklist", "combobox", "select"):
        return "select"
    if kw.startswith("verify"):
        return "verify"
    kind = (req or {}).get("kind")
    if kind == "click":
        return "click"
    if kind == "change":
        if (req.get("tag") or "").lower() == "select":
            return "select"
        if (req.get("etype") or "").lower() in ("checkbox", "radio"):
            return "click"
        return "type"
    return None


def _arm_dedupe(target, out_line, action, desc, value=None):
    """Remember this event ONLY if it put a line in the pane.

    An event composed as '' is noise we deliberately record nothing for -- the recorder's focus
    click on a field, the safety net's synthetic click on one. It used to stamp the window anyway,
    so the TypeText that followed within 2.5 s was declared a duplicate and suppressed too: the
    typed value never reached the pane, and the event with the BETTER line lost by arriving second
    (challenge D10 finding 4, 2026-09-19)."""
    if target is None or (out_line or "").strip() == "":
        return False
    desc = desc or {}
    _LAST.update({"el": target, "t": time.time(), "action": action,
                  "label": desc.get("label") or desc.get("text") or None,
                  "family": desc.get("family"),
                  "value": value if value is not None else _event_value(out_line)})
    return True


def _by_nonce(drv, nonce):
    """(element, how) -- the element the PAGE stamped, found by ONE shadow-piercing walk.

    This is the whole of build k: the composer no longer re-evaluates an xpath to decide which
    element the user touched. The page marked it at event time with `data-gz-ev="<nonce>"`, so the
    walk cannot land on a neighbour, cannot be shifted by an element added since (F44), and reaches
    a control inside an OPEN native shadow root, which no xpath from the driver can (F40).
    A CLOSED shadow root is still unreachable and is reported as such -- never as a miss."""
    if not nonce:
        return None, "no nonce in the event (an old bundle, or the describer never loaded)"
    try:
        el = drv.execute_script(RESOLVE_JS, nonce)
    except Exception as exc:
        return None, "the nonce walk raised: %s" % exc
    if el is None:
        return None, "the nonce walk found nothing (a closed shadow root, an iframe, or the element is gone)"
    return el, "resolved by nonce"


def _identity_kind(row):
    """What the row's identity RESTS on, for a review built before the kind was recorded."""
    k = row.get("identity_kind")
    if k:
        return k
    ix = row.get("identity_xpath") or ""
    return "positional" if ix.startswith("(") else "attribute"


def _same(drv, a, b):
    try:
        return bool(drv.execute_script("return arguments[0] === arguments[1]", a, b))
    except Exception:
        return False


def _match_row(drv, target, desc, decision):
    """The row this element is, and HOW we know -- label, attribute, or position (last resort).

    Order is the point (ledger F42/F44). A label is what a person reads and what the review wrote
    down; an identity xpath that counts nodes over the page answers confidently on the wrong element
    the moment the page gains one. So:
      1. label + family, through the ONE match rule (`pom/match.py` semantics, `descriptor.find_row`),
         a repeated label settled by the page's own count of same-label siblings;
      2. a stable attribute this descriptor and exactly one row agree on;
      3. the positional identity xpath, resolved and `===`-compared -- and SAID so.
    """
    desc = desc or {}
    if desc:
        row, why = find_row(ROWS, desc)
        if row is not None:
            agreed = None
            try:
                els = drv.find_elements("xpath", row["identity_xpath"])
                agreed = (len(els) == 1 and _same(drv, els[0], target))
            except Exception:
                agreed = None
            note = {True: "its identity xpath agrees",
                    False: "its identity xpath DISAGREES -- %s identity, shifted (F44); the label wins" % _identity_kind(row),
                    None: "its identity xpath could not be evaluated"}[agreed]
            decision["identity"] = "label"
            return row, "%s | %s" % (why, note)
        decision["label_why"] = why
        refused = []
        cands = [r for r in ROWS if attribute_identity(desc, r, refused)]
        if refused:
            # D5's forbidden locator refused as an IDENTITY, said out loud rather than read as a miss
            decision["attribute_refused"] = sorted(set(refused))[:3]
        if len(cands) == 1:
            decision["identity"] = "attribute"
            return cands[0], "%s; one row agrees on %s" % (why, attribute_identity(desc, cands[0]))
        if len(cands) > 1:
            decision["label_why"] = "%s; %d rows agree on a stable attribute" % (why, len(cands))
    for row in ROWS:
        try:
            els = drv.find_elements("xpath", row["identity_xpath"])
        except Exception:
            continue
        if len(els) == 1 and _same(drv, els[0], target):
            decision["identity"] = _identity_kind(row)
            return row, "identity xpath (%s), the last resort: %s" % (
                _identity_kind(row), decision.get("label_why") or "no descriptor label matched a row")
    decision["identity"] = None
    return None, decision.get("label_why") or "no row resolves to this element"


# `pom.keys.host_stem`'s own list, in its own order (the sandbox forms first, then the plain ones):
# a stem this computes must be the stem the generator looked up in keys.py's host cache, or the two
# halves of the gate would be asking different questions.
_SF_SUFFIXES = (".sandbox.lightning.force.com", ".sandbox.my.salesforce.com",
                ".sandbox.my.salesforce-setup.com",
                ".lightning.force.com", ".my.salesforce.com", ".my.salesforce-setup.com",
                ".my.site.com", ".vf.force.com", ".visualforce.com")
_SANDBOX_HOST = re.compile(r"--([A-Za-z0-9]+)\.sandbox\.")
_APP_SEGMENT = re.compile(r"^/lightning/app/[A-Za-z0-9]{15,18}(/|$)")


def _partition_for(host):
    """The POM PARTITION of a host -- the org alias for a Salesforce host, the host itself for
    everything else (`pom/keys.py`, and CLAUDE.md's 'the partition is not negotiable').

    Resolved WITHOUT any subprocess or network: a sandbox host names its alias in its own hostname,
    and for everything else the generator embedded the host stems `keys.alias_for_host` resolved to
    the review's partition at build time (`PAGE_HOST_STEMS`). A host we cannot place answers with
    itself, which cannot equal an org alias -- so an unknown host closes the gate rather than
    opening it, which is the safe direction."""
    h = (host or "").lower()
    if not h:
        return ""
    m = _SANDBOX_HOST.search(h)
    if m:
        return m.group(1)
    stem = h
    for suf in _SF_SUFFIXES:
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
            break
    return PAGE_PARTITION if stem in PAGE_HOST_STEMS else h


def _pattern_matches(path):
    """The review's page pattern against a URL path, {id}/{uuid} placeholders matched loosely."""
    pat = PAGE_PATTERN.rstrip("/")
    if not path:
        return False
    if "{" not in pat:
        return path.rstrip("/") == pat or path.startswith(pat + "/")
    rx = "^" + re.escape(pat).replace(r"\{id\}", r"[A-Za-z0-9]{15,18}").replace(r"\{uuid\}", r"[0-9a-fA-F-]{36}") + "(/|$)"
    return bool(re.match(rx, path))


def _key_pattern(url, partition):
    """`pom.keys.page_key(url)['pattern']`, or None when the key module is not reachable.

    The alias is HANDED IN (`org=`), never resolved inside: `keys.alias_for_host` shells out to
    `sf org list` when its host cache is cold, and a page gate that consults the network on every
    recorded event is not a gate. The module travels in the parser bundle; without the bundle this
    answers None and the local rules below stand in."""
    try:
        _parser()                                   # puts the bundle on sys.path if it is there
        from pom import keys as _keys
        return _keys.page_key(url, org=(partition or None)).get("pattern")
    except Exception:
        return None


def _page_verdict(drv):
    """(on the reviewed page, why) -- BOTH halves of the page KEY must agree, never the path alone.

    The gate used to compare the raw PATH only, and the review is org-scoped: a custom tab of the
    same API name in another org -- or on any host at all -- opened the gate and received this
    review's VERIFIED-PASS lines and its confident `#   backup:` advice (challenge D10 finding 1,
    2026-09-19; ledger F42 one level up). And the same path reached INSIDE a Lightning app,
    `/lightning/app/<06m>/n/<tab>`, is the same page to `pom.keys` (D15 keeps the app as its own key
    SEGMENT, not as part of the pattern) and was called off-page by the raw comparison, silently
    downgrading the one page the review exists for (finding 2).

    So: the PARTITION first (an org alias, never a host), then the PATTERN through `pom.keys` when
    the bundle is there, with the raw comparison and an app-segment strip as the local fallbacks."""
    try:
        cur = drv.current_url or ""
        rest = cur.split("://", 1)[1] if "://" in cur else ""
        host = rest.split("/", 1)[0].lower()
        path = "/" + rest.split("/", 1)[1]
        path = path.split("?", 1)[0].split("#", 1)[0]
    except Exception:
        return False, "the URL carries no path"
    part = _partition_for(host)
    if part != PAGE_PARTITION:
        return False, "partition %r (host %r) is not the review's %r" % (part, host, PAGE_PARTITION)
    if _pattern_matches(path):
        return True, "partition %r and pattern %r agree" % (part, PAGE_PATTERN)
    kp = _key_pattern(cur, part)
    if kp is not None and _pattern_matches(kp):
        return True, "partition %r; page_key pattern %r agrees (the raw path did not)" % (part, kp)
    if _APP_SEGMENT.match(path) and _pattern_matches(_APP_SEGMENT.sub("/lightning/", path)):
        return True, "partition %r; app-scoped route of pattern %r" % (part, PAGE_PATTERN)
    return False, "partition %r agrees; path %r is not pattern %r" % (part, path[:80], PAGE_PATTERN)


def _on_reviewed_page(drv):
    """True only when the live browser is on the page the embedded rows describe -- the review's
    PARTITION and its page pattern, both (see `_page_verdict`)."""
    return _page_verdict(drv)[0]


def _event_value(rendered, req=None):
    """What this event says is IN the field, or None when it is not a fill at all. A recorded
    `TypeText` carries it in cell 3; a synthetic `change` carries it as `value`."""
    cells = _cells(rendered or "")
    if len(cells) >= 3 and cells[0].lower().startswith("type"):
        return cells[2]
    v = (req or {}).get("value")
    return None if v is None else str(v)


def _dup_verdict(drv, target, action=None, desc=None, window_s=2.5, value=None):
    """(is a duplicate, why) -- see `_is_duplicate`."""
    if _LAST["el"] is None or time.time() - _LAST["t"] > window_s:
        return False, None
    if not _same(drv, _LAST["el"], target):
        return False, None
    desc = desc or {}
    if _LAST.get("action") and action and _LAST["action"] != action:
        return False, None
    a, b = _LAST.get("label"), (desc.get("label") or desc.get("text") or None)
    if a and b and str(a).strip().casefold() != str(b).strip().casefold():
        return False, None
    fa, fb = _LAST.get("family"), desc.get("family")
    if fa and fb and str(fa).casefold() != str(fb).casefold():
        return False, None
    # THE VALUE IS PART OF THE EVENT (challenge 2026-09-19b case 14). The user types `ab`, the
    # widget commits `abc`, and the safety net posts a synthetic `change` carrying it. Element,
    # action, label and family all agree, so the second event used to be dropped and the pane kept
    # the STALE `ab` -- with a `why` that never mentioned the two disagreed. The later value is the
    # committed one and therefore the better evidence: this is not a duplicate, it SUPERSEDES.
    if action == "type":
        av, bv = _LAST.get("value"), value
        if av is not None and bv is not None and str(av) != str(bv):
            return False, ("not a duplicate: the same element was armed with %r %d ms ago and this "
                           "event commits %r -- the committed value is the later evidence, so this "
                           "line SUPERSEDES the armed one" %
                           (av, int((time.time() - _LAST["t"]) * 1000), bv))
    return True, ("duplicate: the same element, same action and same label was served %d ms ago"
                  % int((time.time() - _LAST["t"]) * 1000))


def _is_duplicate(drv, target, action=None, desc=None, window_s=2.5, value=None):
    """The safety net and the recorder can resolve ONE click to two different elements (the anchor and
    its span), so a path-keyed dedupe in the page misses it (measured 2026-09-18: two lines for one
    Fields & Relationships click). Identity in the DOM within a short window is the rule.

    CORROBORATED, never the page's `===` alone (challenge D10 finding 3, 2026-09-19). That script
    runs in the page and we believed its answer with nothing beside it: a page whose `===` answers
    truthy for any pair -- a stub, a proxy element, a driver returning a truthy value -- suppressed a
    genuinely different control's step, and the only trace was a log line inside the container. So
    the recorded ACTION and the descriptor's label and family must agree too. Either side UNKNOWN is
    agreement (an old bundle sends no descriptor); two KNOWN values that differ are two events.

    `value` is the fourth known-value comparison and the one that was missing: a `type` duplicate
    whose value differs is not a duplicate at all (challenge 2026-09-19b case 14)."""
    return _dup_verdict(drv, target, action, desc, window_s, value)[0]


# --------------------------------------------------------------------------- the OmniStudio pair
# ONE intent, two stock recorder events: a click on an OmniScript combobox's input (written as a
# ~1,200-character positional `ClickElement /html[1]/...`) and then a `ClickText <option>` on an
# `li` of the listbox it opened. The job library already owns that intent as one keyword --
# `resources/garzai_omni.robot` -> `Omni Select`. The pairing is SERVER-SIDE and has exactly three
# moves: a combobox-open click returns line '' and is HELD (its line, the label, the time); the
# next event, if it is that combobox's option click inside %.0f s, returns the composed pair with
# the two stock lines as dormant `#   backup:` lines; ANY other next event first flushes the held
# click as its own pass-through line, ahead of its own (the `pre` list the page pushes first).
# Measured on the user's fsc7f recording, 2026-09-19: 5 pairs, 10 pane lines, 5 of them 1,200
# characters of absolute path.
_OMNI_HOLD = {"held": False, "line": "", "label": None, "t": 0.0, "prefix": None}


def _omni_clear():
    _OMNI_HOLD.update({"held": False, "line": "", "label": None, "t": 0.0, "prefix": None})


def _omni_flush(cl=None):
    """The held line, as a one-item `pre` list, and the hold cleared. A held line that is empty
    flushes nothing -- there is no step to restore.

    The flushed line is the LABEL FORM, not the ~1,200-character positional path the stock recorder
    wrote (user, 2026-09-19 run 5: "Why are absolute paths coming up as backup options?"). An
    unpaired open-and-close -- the recording's Nationality combobox -- pushed that positional line
    as `pre`; it is the same click and it gets the same readable form. Without a label there is no
    label form and the positional line is the only handle, so it stands."""
    if not (_OMNI_HOLD["held"] and (_OMNI_HOLD["line"] or "").strip()):
        _omni_clear()
        return []
    line, label = _OMNI_HOLD["line"], _OMNI_HOLD["label"]
    indent = line[: len(line) - len(line.lstrip())] or "    "
    if cl is not None:
        try:
            body, _why = cl.omni_open_click_line(label, line)
            if body and body.strip():
                line = "%s%s" % (indent, body.strip())
        except Exception:
            pass
    _omni_clear()
    return [line]


# ---------------------------------------------------------------- the OmniStudio date-picker pair
# The user, run 8 (2026-09-19 14:17): "the birthdate thing is not capturing the initial click to
# find the dates, so it's only showing the click to select the date". MEASURED LIVE the same day
# on fsc7f (slot fsc7f@probe): a click on `input[data-id=date-picker-slds-input]` takes the widget
# from closed to `{open:true, month:'September', year:'2026'}` -- A CLICK ON A DATE INPUT IS AN
# OPENING CLICK, NOT A FOCUS CLICK. Rule 1b had been dropping it as noise, so the pane kept the
# day-cell click alone (`ClickText    10    anchor=September`), which on a fresh page has no
# calendar open and fails with `Could not find text using web recognition`.
# Three moves, the same shape as the combobox: the opening click is HELD (its composed line is ''
# because rule 1b already suppressed it, and that is fine -- what is held is the GESTURE); the
# day-cell click joins the hold; and the `Omni Date` line comes out with both stock lines dormant
# beneath it. The calendar's own header renders the MONTH alone, so unless the day cell's
# `aria-label` reached the descriptor the year comes from the input's value after the pick -- the
# authoritative read-back -- and the fill event completes the pair.
# A held opening click with NO day pick composes NOTHING: opening a calendar and closing it again
# is not a step.
_OMNI_DATE = {"held": False, "open_line": "", "day_line": "", "label": None, "key": None,
              "iso": None, "picked": False, "t": 0.0, "prefix": None}


def _omni_date_clear():
    _OMNI_DATE.update({"held": False, "open_line": "", "day_line": "", "label": None, "key": None,
                       "iso": None, "picked": False, "t": 0.0, "prefix": None})


def _omni_date_flush(cl=None):
    """What a lapsed date hold leaves behind. With no day pick that is NOTHING.

    With a day pick but no fill to name the year, BOTH stock lines stand -- the opening click in
    its label form and the day cell -- never the day cell alone (challenge 2026-09-19b case 5c).
    The day cell alone is `ClickText    10` against a calendar nobody opened: the exact line this
    build exists to stop shipping, and it was what a lapsed hold emitted."""
    picked, day_line = _OMNI_DATE["picked"], _OMNI_DATE["day_line"]
    open_line, label = _OMNI_DATE["open_line"], _OMNI_DATE["label"]
    _omni_date_clear()
    if not (picked and (day_line or "").strip()):
        return []
    out = []
    if cl is not None:
        try:
            body, _why = cl.omni_open_click_line(label, open_line)
            if body and body.strip():
                indent = (open_line[: len(open_line) - len(open_line.lstrip())]
                          if (open_line or "").strip() else "") or "    "
                out.append("%s%s" % (indent, body.strip()))
        except Exception:
            pass
    if not out and (open_line or "").strip():
        out.append(open_line)          # no label form available: the positional line is the handle
    out.append(day_line)
    return out


def _omni_date_pair(req, decision, line, backups):
    """(pre, line, backups) or None when this event is not the date picker's business."""
    cl = _parser()
    if cl is None or not hasattr(cl, "omni_date_opener"):
        return None
    rendered = req.get("rendered") or ""
    paths = (req.get("xpath") or "", req.get("alt_xpath") or "")
    desc = req.get("descriptor") or {}
    now = time.time()
    pre = []
    if _OMNI_DATE["held"] and now - _OMNI_DATE["t"] > cl.OMNI_PAIR_WINDOW_S:
        pre = _omni_date_flush(cl)
    # 1. the DAY-CELL pick, while an opening click is held
    if _OMNI_DATE["held"] and not _OMNI_DATE["picked"] and cl.omni_day_cell(rendered, *paths):
        iso, why = cl.omni_day_cell_date(rendered, desc)
        _OMNI_DATE.update({"picked": True, "day_line": line if isinstance(line, str) and line.strip()
                           else rendered, "iso": iso, "t": now})
        if iso:
            out, bks = cl.omni_date_pair_lines(_OMNI_DATE["label"], _OMNI_DATE["key"], iso,
                                               _OMNI_DATE["open_line"], _OMNI_DATE["day_line"])
            if out:
                decision["why"] = ("OmniStudio date pick: the calendar's opening click and the "
                                   "day cell composed as one Omni Date (%s); both stock lines "
                                   "are dormant backups -- %s" % (iso, why))
                decision["omni"] = "date paired"
                _omni_date_clear()
                return pre, out, bks
        decision["why"] = ("OmniStudio date pick: HELD with its opening click; %s" % why)
        decision["omni"] = "date held for the input's own value"
        return pre, "", []
    # 1b. a DAY PICK WITH NO HELD OPENER -- the calendar was already open (challenge 2026-09-19b
    #     case 6). This used to pass through as `ClickText    9`, unreplayable on a fresh page,
    #     while the very same event carried the cell's full aria-label AND the control's
    #     `data-omni-key`: everything `Omni Date` needs, and the keyword opens the calendar itself.
    if not _OMNI_DATE["held"] and cl.omni_day_cell(rendered, *paths):
        iso, why = cl.omni_day_cell_date(rendered, desc)
        key = str(desc.get("omni_key") or "").strip()
        if iso and key:
            stock_day = line if isinstance(line, str) and line.strip() else rendered
            out, bks = cl.omni_date_pair_lines(None, key, iso, "", stock_day)
            if out:
                decision["why"] = ("OmniStudio day cell with NO opening click of its own (the "
                                   "calendar was already open): the cell's own aria-label names "
                                   "the whole date (%s) and the element carries its key, and "
                                   "Omni Date opens the calendar itself -- %s" % (iso, why))
                decision["omni"] = "date composed from an unheld day cell"
                return pre, out, bks
        decision["omni"] = ("a day cell with no held opening click, and %s: the stock line stands"
                            % ("no data-omni-key on the element" if not key else why))
    # 2. the FILL on the same input completes the pair: `_omni_fill` composes the `Omni Date`
    #    line from the value the widget committed, and the two held stock lines go under it.
    if _OMNI_DATE["held"] and _OMNI_DATE["picked"] and cl.omni_fill_line(
            line if isinstance(line, str) else "", *paths, omni_key=desc.get("omni_key"))[0]:
        open_line, _why = cl.omni_open_click_line(_OMNI_DATE["label"], _OMNI_DATE["open_line"])
        extra = [b for b in (open_line, _OMNI_DATE["day_line"]) if (b or "").strip()]
        decision["omni"] = ("date pair completed by the input's own value: the opening click and "
                            "the day cell are dormant backups on this line")
        _omni_date_clear()
        return pre, line, list(backups) + ["    #   backup: %s   (stock recorder line, unverified)"
                                           % b.strip() for b in extra]
    # 2b. A CLICK INSIDE THE HELD PICKER THAT IS NOT A DAY CELL IS PART OF THE GESTURE (challenge
    #     2026-09-19b case 5a). `Next Month` lives inside the widget but outside the day grid, so
    #     neither predicate claimed it and it passed through as its own step -- leaving
    #     `ClickElement <Next Month>` sitting ABOVE an `Omni Date` line that navigates the calendar
    #     itself, and firing at replay against a calendar nobody has opened. The same exemption the
    #     combobox already gives its own synthetic events, keyed on the widget INSTANCE.
    if _OMNI_DATE["held"]:
        first = (_cells(rendered) or [""])[0]
        is_click = (not first) or first.startswith("Click")
        same = None
        try:
            same = cl.omni_same_host(_OMNI_DATE.get("prefix"), *paths, host=cl._OMNI_DATE_PICKER)
        except Exception:
            same = None
        if is_click and same is True:
            decision["omni"] = ("a click inside the HELD date picker that is not a day cell "
                                "(calendar navigation): absorbed into the gesture, not a step of "
                                "its own")
            return pre, "", []
    # 3. the OPENING click itself
    if cl.omni_date_opener(rendered, *paths, family=desc.get("family")):
        pre = pre + _omni_date_flush(cl)
        _OMNI_DATE.update({"held": True, "open_line": line if isinstance(line, str) and line.strip()
                           else rendered, "day_line": "", "picked": False, "iso": None,
                           "label": desc.get("label") or desc.get("aria_label") or desc.get("placeholder"),
                           "key": desc.get("omni_key"), "t": now,
                           "prefix": cl.omni_date_picker_prefix(*paths) if hasattr(cl, "omni_date_picker_prefix") else None})
        decision["why"] = ("OmniStudio date picker OPENED: a click on a date input opens the "
                           "calendar (measured live on fsc7f 2026-09-19), so it is HELD for its "
                           "day-cell pick (up to %.0f s), not dropped as a focus click"
                           % cl.OMNI_PAIR_WINDOW_S)
        decision["omni"] = "date held"
        return pre, "", []
    if pre:
        return pre, line, backups
    return None


def _omni_pair(req, decision, line, backups):
    """(pre, line, backups). `pre` are lines the page pushes BEFORE this event's own."""
    cl = _parser()
    if cl is None:
        return [], line, backups          # no parser bundle: no pairing, stock lines pass through
    handled = _omni_date_pair(req, decision, line, backups)
    if handled is not None:
        return handled
    rendered = req.get("rendered") or ""
    paths = (req.get("xpath") or "", req.get("alt_xpath") or "")
    desc = req.get("descriptor") or {}
    now = time.time()
    pre = []
    if _OMNI_HOLD["held"] and now - _OMNI_HOLD["t"] > cl.OMNI_PAIR_WINDOW_S:
        pre = _omni_flush(cl)             # the option click never came: the held line stands alone
    if _OMNI_HOLD["held"] and cl.omni_combobox_option(rendered, *paths):
        # THE OPTION HAS TO BELONG TO THE HELD COMBOBOX (challenge 2026-09-19b case 9b). This
        # branch used to ask only "is this a ClickText on an `li` under SOME
        # runtime_omnistudio_common-combobox" -- so combobox B's option composed
        # `Omni Select    Phone Type    Australia`: the right option, the WRONG control, stated
        # confidently. F42's class through the pairing door. TRI-STATE: a prefix neither side
        # carries is COULD-NOT-CHECK and the old behaviour stands, said out loud.
        same = None
        try:
            same = cl.omni_same_host(_OMNI_HOLD.get("prefix"), *paths)
        except Exception:
            same = None
        if same is False:
            decision["omni"] = ("the option is inside a DIFFERENT combobox than the held one "
                                "(held ...%s, this option ...%s): the hold is flushed and the "
                                "pick stands alone rather than naming the wrong control"
                                % (str(_OMNI_HOLD.get("prefix"))[-48:],
                                    str(cl.omni_combobox_prefix(*paths))[-48:]))
            return pre + _omni_flush(cl), line, backups
        if same is None:
            decision["omni_pair_identity"] = ("COULD-NOT-CHECK: no combobox host prefix on one "
                                              "side, so the instances were not compared")
        option = _cells(rendered)[1]
        label = _OMNI_HOLD["label"]
        pair, pair_backups = cl.omni_pair_lines(label, option, _OMNI_HOLD["line"], rendered)
        if pair:
            decision["why"] = ("OmniStudio combobox pick: the open click and the option click "
                               "composed as one Omni Select (%r -> %r); the two stock lines are "
                               "dormant backups" % (cl.omni_label(label), option))
            decision["omni"] = "paired"
            _omni_clear()
            return pre, pair, pair_backups
        if pair_backups:
            # THE PLACEHOLDER PICK. `-- No Value --` leaves the control where it began, so the
            # pick is not a step and composes nothing. Measured live on fsc7f 2026-09-19 13:13 --
            # `Omni Select    Salutation    -- No Value --` failed there.
            # THE HOLD SURVIVES IT (challenge 2026-09-19b case 3). Dropping the hold here meant a
            # REAL pick one second later on the same still-open listbox composed a bare
            # `ClickText    Mr.` with no opening click and no backups -- unreplayable against a
            # closed listbox, which is the very shape the user named on run 8. So only the PICK is
            # banked as a dormant backup; the open click stays held for the next pick.
            indent = (line[: len(line) - len(line.lstrip())]
                      if isinstance(line, str) and line.strip() else "") or "    "
            kept = [cl.omni_dormant(rendered, indent)] if (rendered or "").strip() else []
            decision["why"] = ("OmniStudio combobox placeholder pick (%r): picking nothing is not "
                               "a step, so the pick composes no line -- but the OPEN click stays "
                               "HELD, so the next pick on this combobox still pairs with it"
                               % option)
            decision["omni"] = "placeholder pick: nothing composed, the open click still held"
            _OMNI_HOLD["t"] = now
            return pre, "", kept
        # no label to name the control with: a keyword whose first argument is blank is a guess.
        decision["omni"] = "no label on the combobox: the two stock lines stand"
        return pre + _omni_flush(cl), line, backups
    if not req.get("synthetic") and cl.omni_combobox_opener(rendered, *paths,
                                                            family=desc.get("family")):
        pre = pre + _omni_flush(cl)       # two openers in a row: the first one stands alone
        _OMNI_HOLD.update({"held": True, "line": line if isinstance(line, str) else rendered,
                           "label": desc.get("label") or desc.get("aria_label") or desc.get("placeholder"),
                           "prefix": cl.omni_combobox_prefix(*paths) if hasattr(cl, "omni_combobox_prefix") else None,
                           "t": now})
        decision["why"] = "OmniStudio combobox opened: HELD for its option click (up to %.0f s)" % cl.OMNI_PAIR_WINDOW_S
        decision["omni"] = "held"
        return pre, "", []
    if _OMNI_HOLD["held"]:
        # A SYNTHETIC EVENT IS PART OF THE GESTURE, NEVER THE END OF IT (the user, run 8,
        # 2026-09-19: "same at ClickText Australia: it's not capturing the dropdown itself, only
        # the step"). MEASURED LIVE on fsc7f the same day, with capture-phase listeners on the
        # page: picking an option fires, in this order, `mousedown` on the option span, `mouseup`
        # on the option span, **`change` on <runtime_omnistudio_common-combobox>**, and only THEN
        # `click` on the option span. The widget commits on mouseup, so its own change event
        # always arrives BEFORE the click the recorder pairs on. The old rule treated that change
        # as "some other control", flushed the held open click, and `ClickText    Australia` then
        # passed through alone -- decisions 19-24 of the run-8 fixture (a change on the combobox,
        # a click on its <ul>, a click on the omniscript container <div>, and a click back on the
        # input, all synthetic, all inside one pick). Only a REAL event on another control, or the
        # 8 s window, ends a hold.
        if req.get("synthetic"):
            decision["omni"] = ("synthetic %s inside the held combobox gesture: the hold stands "
                                "(the widget commits on mouseup, so its own change event arrives "
                                "before the option click)" % (req.get("kind") or "event"))
            return pre, line, backups
        decision["omni"] = "flushed the held combobox click"
        pre = pre + _omni_flush(cl)
    return pre, line, backups


def _omni_fill(req, decision, line, backups):
    """(line, backups) for a FILL event: the OmniStudio keyword when the element is an OmniStudio
    fill component, and -- always -- the dormant read-back line that belongs after it.

    Routing is by the COMPONENT TAG in the element's own path, and the first argument is the
    element's `data-omni-key` the page-side describer now collects:
      * `runtime_omnistudio_common-date-picker` -> `Omni Date` (a typed value never commits on that
        widget; the user's executed run left the field BLANK, 2026-09-19 12:17);
      * `runtime_omnistudio_common-masked-input` -> `Omni Type` (it reformats on blur);
      * `runtime_omnistudio_common-input`        -> `Omni Type` (TypeText's clear does not clear it:
        `TypeText First Name ads` into a field holding `ads` ended `adsads`, 2026-09-19 12:28).
    No key, or a date this cannot read: the stock line stands and the decision says why.

    THE STEP IS THE ACTION, THE VERDICT IS A SEPARATE LINE (user, 2026-09-19). Whatever the fill
    ends up being, a dormant `#   verify: Verify Input Value    <label>    <value>` follows it, so
    the assertion is a step a person can un-comment -- never validation hidden inside a keyword."""
    cl = _parser()
    if cl is None or not isinstance(line, str) or not line.strip():
        return line, backups
    desc = req.get("descriptor") or {}
    stock = line
    try:
        omni, backup, why = cl.omni_fill_line(
            line, req.get("xpath") or "", req.get("alt_xpath") or "",
            omni_key=desc.get("omni_key"), omni_key_capped=desc.get("omni_key_capped"),
            indent=(line[: len(line) - len(line.lstrip())] or "    "))
    except Exception as exc:
        decision["omni_fill"] = "error: %s" % exc
        omni, backup, why = "", "", None
    if omni:
        decision["omni_fill"] = why
        decision["why"] = "%s; %s" % (decision.get("why") or "", why)
        line, backups = omni, [backup] + list(backups)
    elif backup:
        # AN EMPTY LINE WITH A BACKUP MEANS "RECORD NOTHING, KEEP THE HANDLE" (challenge
        # 2026-09-19b case 7): the all-placeholder mask. The stock line would replay literal
        # underscores into a masked input, so it must not stand -- and nothing was typed, so no
        # verify line belongs under it either.
        decision["omni_fill"] = why
        decision["why"] = "%s; %s" % (decision.get("why") or "", why)
        decision["omni_dropped"] = True
        return "", [backup] + list(backups)
    elif why:
        # SAY IT WHERE THE READER LOOKS (challenge 2026-09-19b case 13). A DECLINED OmniStudio
        # routing used to land only in `omni_fill`, so the `why` column showed a plain TypeText
        # with no sign the routing had been considered -- on a control where TypeText's clear is
        # measured not to clear (the value APPENDS, `adsads`).
        decision["omni_fill"] = why          # named, never a silent miss
        decision["why"] = "%s; %s" % (decision.get("why") or "", why)
    try:
        verify = cl.verify_backup(stock, indent=(stock[: len(stock) - len(stock.lstrip())] or "    "))
    except Exception:
        verify = ""
    if verify:
        backups = list(backups) + [verify]
        decision["verify_line"] = True
    return line, backups


def _outcome_payload():
    """The last GZ_OUTCOME_N decisions, in the shape that travels IN BAND on the page under test.

    WHAT TRAVELS: the composed line (`out`), the reason (`why`), the OmniStudio note when there is
    one, the served count and the build version. NO DOM TEXT -- nothing read off the page, no
    label, no element path, no value the recorder captured beyond the step it composed.

    An elide is DISCLOSED, never silent: a `why` longer than GZ_OUTCOME_WHY_CHARS is cut and the
    row carries `why_chars` (the full length) and `why_full_at` (the log that holds all of it)."""
    rows = []
    for d in STATE["decisions"][-GZ_OUTCOME_N:]:
        why = str(d.get("why") or "")
        row = {"out": d.get("out"), "why": why[:GZ_OUTCOME_WHY_CHARS]}
        if len(why) > GZ_OUTCOME_WHY_CHARS:
            row["why_chars"] = len(why)
            row["why_full_at"] = LOG
        for k in ("omni", "omni_fill", "supersedes", "page"):
            if d.get(k):
                row[k] = str(d[k])[:GZ_OUTCOME_WHY_CHARS]
        rows.append(row)
    return {"version": STATE["version"], "served": STATE["served"], "n": len(rows),
            "of_decisions": len(STATE["decisions"]), "log": LOG, "decisions": rows}


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        self._send({"ok": True, "version": STATE["version"]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            req = {}
        # SERIALISED. This is a ThreadingHTTPServer and everything below drives ONE selenium driver
        # and mutates the shared _CACHE / _LAST / STATE. The page abandons a request at ASK_MS
        # (6 s) and starts the next event's ask() immediately, so two handlers really do overlap --
        # the driver-side cap is now 4 s to shorten that overlap, and this lock removes it
        # (challenge D10 finding 7, 2026-09-19).
        with _LOCK:
            self._compose(req)

    def _compose(self, req):
        STATE["served"] += 1
        rendered = req.get("rendered") or ""
        xp = req.get("xpath")
        desc = req.get("descriptor") or {}
        if desc:
            # The element's OWN path travels with the descriptor: `descriptor.row_may_claim` needs
            # it for the chrome rule (a row in the nav bar may not answer for an element outside
            # it). The page side is unchanged -- this is the path the event already carried.
            desc = dict(desc, xpath=req.get("xpath") or "", alt_xpath=req.get("alt_xpath") or "")
        nonce = req.get("nonce")
        decision = {"in": rendered[:80], "xpath": (xp or "")[-60:], "out": None, "row": None, "why": None,
                    "label": (desc.get("label") or desc.get("text") or None),
                    "label_source": desc.get("label_source"), "family": desc.get("family"),
                    "in_shadow": desc.get("in_shadow"), "resolve": None, "identity": None}
        proposal_backups = []
        try:
            line = None
            if req.get("frame"):
                # build i: an event raised INSIDE an iframe carries a path rooted at the frame's own
                # document; resolving it against the top document finds the wrong element, and the
                # capture that follows freezes a classic Setup page (measured 2026-09-18). Pass through.
                decision["why"] = "event inside an iframe (%s): the composer is top-document only; passed through" % (str(req.get("frame_path") or "?")[:60])
                line = "" if req.get("synthetic") else None
                xp = None; nonce = None
            t = None
            if nonce or xp:
                drv = _driver()
                t, how = _by_nonce(drv, nonce)
                decision["resolve"] = how
                if t is None and xp:
                    # build k keeps the old paths as a FALLBACK, and says when it used one
                    tgt = drv.find_elements("xpath", xp)
                    door = "theirs (the recorder's xpath)"
                    if not tgt and req.get("alt_xpath"):
                        # the recorder's path (shadow-aware, slot segments) often resolves to nothing in the
                        # driver on Lightning pages (3 of 5 on Setup, 2026-09-18); ours is a plain DOM walk
                        tgt = drv.find_elements("xpath", req["alt_xpath"])
                        if tgt:
                            door = "ours (our own alt xpath): their xpath resolved to nothing, ours did"
                    if tgt:
                        t = tgt[0]
                        # NAME THE DOOR. The note used to say "fell back to the recorder's xpath"
                        # even when OUR alt path is what resolved (challenge D10 finding 6).
                        decision["resolve"] += "; the nonce found nothing; resolved by %s" % door
                _act = _action_class(rendered, req)
                _val = _event_value(rendered, req)
                _dup, _dup_why = (_dup_verdict(drv, t, _act, desc, value=_val) if t is not None
                                  else (False, None))
                if t is not None and _dup:
                    line = ""
                    decision["why"] = _dup_why
                    t = None
                elif _dup_why:
                    # not a duplicate BECAUSE the values disagree: this line supersedes the armed
                    # one, and the `why` quotes both (challenge 2026-09-19b case 14)
                    decision["supersedes"] = _dup_why
                if t is None:
                    if not decision["why"]:
                        decision["why"] = "the element could not be resolved: %s" % decision["resolve"]
                elif not _on_reviewed_page(drv):
                    # build k2 (2026-09-18): identity xpaths are POSITIONAL ((//input)[3]) and resolve to one
                    # element on ANY page; without this gate a Lead form's Company field matched the Zoo
                    # page's Amount row with confident backups. Off the reviewed page: parser proposal only.
                    decision["page"] = "off the reviewed page (%s): embedded rows and recipe steps skipped" % PAGE_PATTERN
                    syn = bool(req.get("synthetic"))
                    line, proposal_backups = _propose(drv, t, _pseudo_rendered(req) if syn else rendered, decision, desc)
                    if line is None:
                        if syn:
                            line = ""
                            decision["why"] = "synthetic %s on <%s> %r off the reviewed page: no parser proposal (parser %s); not recorded" % (req.get("kind"), req.get("tag"), (req.get("text") or "")[:40], PARSER["state"])
                        else:
                            decision["why"] = "off the reviewed page; no parser proposal (parser %s)" % PARSER["state"]
                elif t is not None:
                    row, why = _match_row(drv, t, desc, decision)
                    if row is not None:
                        if req.get("synthetic"):
                            row = dict(row, _syn={"kind": req.get("kind"), "value": req.get("value")})
                        line = _our_line(row, rendered)
                        if line and decision.get("identity") == "positional":
                            # SAY IT IN THE PANE. A positional identity is the mechanism F42/F44
                            # retired, reached only when no label and no stable attribute named the
                            # row; the decision log called it "the last resort" and the line a
                            # person reads carried no mark at all (challenge D10 finding 6).
                            line = line + "    " + POSITIONAL_MARK
                        decision["row"] = row["n"]
                        decision["why"] = ("%s match: %s" % (decision.get("identity"), why)) if line \
                            else ("matched row %s by %s, no better line" % (row["n"], decision.get("identity")))
                    else:
                        n, step = _recipe_step_for(drv, t)
                        if step:
                            line = step; decision["row"] = n; decision["identity"] = "recipe step"
                            decision["why"] = "recipe step identity match (%s)" % why
                        else:
                            syn = bool(req.get("synthetic"))
                            line, proposal_backups = _propose(
                                drv, t, _pseudo_rendered(req) if syn else rendered, decision, desc)
                            if line is None:
                                if syn:
                                    line = ""
                                    decision["why"] = "synthetic %s on <%s> %r: %s; no recipe, no parser proposal (parser %s); not recorded" % (req.get("kind"), req.get("tag"), (req.get("text") or "")[:40], why, PARSER["state"])
                                else:
                                    decision["why"] = "%s; no recipe step; no parser proposal (parser %s)" % (why, PARSER["state"])
            elif not decision["why"]:
                decision["why"] = "no nonce and no xpath in event"
            decision["out"] = rendered if line is None else line
            # ARM THE DEDUPE LAST, and only on an event that actually put a line in the pane.
            decision["armed_dedupe"] = _arm_dedupe(t, decision["out"], _action_class(rendered, req),
                                                   desc, _event_value(rendered, req))
        except Exception as exc:
            decision["why"] = "error: %s" % exc; decision["out"] = rendered
        backups = proposal_backups or _backups(decision.get("row"), decision["out"], rendered)
        pre = []
        try:
            pre, out_line, backups = _omni_pair(req, decision, decision["out"], backups)
            out_line, backups = _omni_fill(req, decision, out_line, backups)
            decision["out"] = out_line
        except Exception as exc:
            # the pair is an improvement on top of a decision that is already made: a failure here
            # leaves that decision exactly as it was, and says so
            decision["omni"] = "error: %s" % exc
        decision["backups"] = len(backups); decision["pre"] = len(pre)
        STATE["decisions"].append(decision); STATE["decisions"] = STATE["decisions"][-50:]
        _log(json.dumps(decision))
        backups = [_dormant_form(b) for b in backups]
        self._send({"line": decision["out"], "backups": backups, "pre": pre,
                    "outcome": _outcome_payload(), "outcome_id": GZ_OUTCOME_ID,
                    "outcome_attr": GZ_OUTCOME_ATTR})


def _serve():
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), _H)
        STATE["server"] = "listening on %d" % PORT
        srv.serve_forever()
    except Exception as exc:
        STATE["server"] = "error: %s" % exc; STATE["error"] = traceback.format_exc(); _log(STATE["error"])


_patch_bundle()
threading.Thread(target=_serve, daemon=True, name="gz-composer").start()
_log("import done: patched=%s server=%s parser=%s" % (STATE["patched"], STATE["server"], PARSER["state"]))


class garzai_recorder_override:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def gz_override_status(self):
        st = {k: v for k, v in STATE.items() if k != "error"}
        # BOTH halves of the page key the embedded rows were measured under: a pattern with no
        # partition beside it is what let another org's identically named tab open the gate.
        st["reviewed_page"] = PAGE_PATTERN
        st["reviewed_partition"] = PAGE_PARTITION
        st["reviewed_page_key"] = "%s|%s" % (PAGE_PARTITION, PAGE_PATTERN)
        try:
            drv = _driver()
            st["on_reviewed_page"], st["page_gate"] = _page_verdict(drv)
            cur = drv.current_url or ""
            host = cur.split("://", 1)[1].split("/", 1)[0].lower() if "://" in cur else ""
            st["live_partition"] = _partition_for(host)
            st["live_pattern"] = _key_pattern(cur, st["live_partition"])
        except Exception as exc:
            st["on_reviewed_page"] = None
            st["page_gate"] = "COULD-NOT-CHECK: %s" % exc
        st["describer"] = {"bytes": len(DESCRIBE_JS), "nonce_attr": NONCE_ATTR,
                           "label_rungs": list(LABEL_RUNGS)}
        st["parser"] = PARSER["state"]          # loaded | missing | error | present (not imported yet)
        st["parser_reason"] = PARSER["reason"]
        st["proposals"] = PARSER["proposals"]
        return json.dumps(st, default=str)

    def gz_override_outcome(self):
        """The same JSON the library writes into the page under test (`<script
        type="application/json" id="gz-outcome">` and `<html data-gz-outcome>`), for a Robot
        caller who would rather read it from here than out of a DOM snapshot: the last
        GZ_OUTCOME_N decisions as {out, why, ...}, plus the served count and the build version.
        No DOM text. The client-side twin is `tools/crt_live/session.py keyword --outcome`."""
        return json.dumps(_outcome_payload(), default=str)

    def gz_override_org(self, alias=None):
        """The org alias the parser bundle stamps on the capture it takes of an unreviewed page.
        The POM partition is the ORG for a Salesforce host and the HOST for everything else, and a
        holder's alias never describes a third-party page -- so this is left unset unless the suite
        says otherwise, and an unset alias claims nothing."""
        STATE["org"] = (str(alias).strip() or None) if alias else None
        return STATE["org"]

    def gz_override_form(self, form="keyword"):
        """keyword: the live-verified keyword form, xpath only as backstop (default);
        xpath: the verified xpath form wherever one exists; both: keyword line, xpath as a comment."""
        form = str(form).strip().lower()
        if form not in ("keyword", "xpath", "both"):
            raise ValueError("form must be keyword, xpath or both")
        STATE["form"] = form
        return form

    def gz_override_dormant_form(self, form="keyword"):
        """keyword (default): dormant backup/verify lines are pushed as `Comment    ...` steps the
        editor keeps; comment: bare `#` lines. Returns the form in force."""
        STATE["dormant_form"] = "comment" if str(form).strip().lower().startswith("c") else "keyword"
        return STATE["dormant_form"]

    def gz_override_backups(self, on=True):
        """on: push dormant '#   backup:' comment lines under each composed step (default); off: only the line."""
        STATE["backups"] = str(on).strip().lower() in ("true", "on", "1", "yes")
        return STATE["backups"]

    def gz_container_marker(self):
        """Does the Live Testing container's disk survive between sessions? Writes
        /home/services/log/gz_marker.json on first sight and reads it back on every later sight:
        the answer is `first_seen` (when, by which suite) and `sightings`. Run it as the FIRST step
        of any session. (2026-09-18: a stock session got the local-network prompt, which only our
        patched bundle raises, so the extension directory had survived from an earlier session.)"""
        path = "/home/services/log/gz_marker.json"
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            data = json.load(open(path)) if os.path.exists(path) else {"first_seen": now, "sightings": 0}
        except Exception:
            data = {"first_seen": now, "sightings": 0, "note": "unreadable marker replaced"}
        data["sightings"] = int(data.get("sightings", 0)) + 1
        data["last_seen"] = now
        data["bundle_patched_now"] = "__gzCompose" in open(BUNDLE, encoding="utf-8", errors="ignore").read() if os.path.exists(BUNDLE) else None
        data["backup_present"] = os.path.exists(BACKUP)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(data, open(path, "w"))
        except Exception as exc:
            data["write_error"] = str(exc)
        verdict = "REUSED container: marker first seen %s, %d sightings" % (data["first_seen"], data["sightings"]) if data["sightings"] > 1 else "FRESH container: no earlier marker"
        return json.dumps({"verdict": verdict, **data})

    def gz_override_restore(self):
        if os.path.exists(BACKUP):
            shutil.copyfile(BACKUP, BUNDLE); return "restored"
        return "no backup"
