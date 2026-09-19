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
FE_SPEC = json.loads('{"_why": "2026-09-10 (user, Zoo_Nightmare_Inputs): the standard SLDS form element -- <div class=slds-form-element><div class=slds-form-element__label-wrapper><label class=slds-form-element__label>X</label></div><div class=slds-form-element__control>...<input></div></div> -- carries NO for= and the label is neither an ancestor nor a descendant of the control, so standard_label/label_span never read it: every one of the page\'s 26 inputs, selects and checkboxes parsed with no label (review raw_had: cousin labels x19). The rung climbs to the nearest form-element ancestor and reads its label element; a form element with no label of its own (the Approved Budget from/to pair) climbs to the next one. An input INSIDE the label wrapper (the readonly helper beside Contract Term) is not the control and gets no label.", "containerClassFragment": "slds-form-element", "excludeContainerClassFragments": ["slds-form-element__control", "slds-form-element__label-wrapper", "slds-form-element__help", "slds-form-element__icon", "slds-form-element__static", "slds-form-element__row"], "labelClassFragments": ["slds-form-element__label", "slds-checkbox__label", "slds-radio__label"], "targetInsideExcludedClassFragments": ["slds-form-element__label-wrapper", "slds-form-element__help-preview"], "climbWhenUnlabelled": true, "maxClimb": 8, "containerRowsNeverClaimIt": true, "targetTags": ["input", "select", "textarea"], "_why_targetTags": "2026-09-10 late (twelve industry-page audits): the rung labelled the inline-edit PENCIL with the field\'s name -- <button title=\\"Edit Name\\"> inside the field\'s slds-form-element read \'Name\' (56 rows on 4 pages, measured CAUGHT-BUG live: click_text(\'Name\', index=2) lands elsewhere) and every output field gained a phantom group_size 2. The rung is for the CONTROL the label names: a native form control, or a custom wrapper around exactly one. Buttons and links inside a form element keep their own title/text.", "wrapperMayBeTarget": true}')  # the template's own formElementLabel block, for the page-side describer

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


def find_row(rows, desc: dict, get=_default_get):
    """(row, why) -- the row this descriptor names, by label + family, or (None, why not).

    A label that occurs once names its row outright. A label that repeats is settled by the
    descriptor's `label_index`: the element's 1-based position among the same-label, family-
    compatible controls in DOM order, counted BY THE PAGE, against the row's own `index` (the
    parser's position among the same-label matches). When the two disagree, or the page could not
    count, nothing is returned -- an ambiguous label is a COULD-NOT-DISAMBIGUATE, never a guess.
    """
    if not rows or not desc:
        return None, 'no descriptor'
    fam = desc.get('family')
    tried = []
    for text, rung in label_candidates(desc):
        want = norm_label(text)
        if not want:
            continue
        cands = [r for r in rows
                 if norm_label(get(r)[0]) == want and families_compatible(fam, get(r)[1])]
        tried.append('%s=%r -> %d' % (rung, text[:40], len(cands)))
        if not cands:
            continue
        if len(cands) == 1:
            return cands[0], 'label (%s) %r' % (rung, text[:40])
        idx = desc.get('label_index')
        if idx:
            hits = [r for r in cands if (get(r)[2] or 1) == idx]
            if len(hits) == 1:
                return hits[0], 'label (%s) %r + page index %d of %s' % (
                    rung, text[:40], idx, desc.get('label_group_size'))
        return None, ('COULD-NOT-DISAMBIGUATE: %d rows carry label %r and the page counted index %r'
                      % (len(cands), text[:40], idx))
    return None, 'no row carries this descriptor label (%s)' % ('; '.join(tried) or 'none offered')


def attribute_identity(desc, row):
    """The stable attribute this descriptor and this row AGREE on, or None. Never a generated
    value: a row's own identity is built with generated values stripped (review_table.is_generated),
    so an agreement here is on a value the parser already judged stable."""
    attrs = (row.get('attrs') or {}) if isinstance(row, dict) else {}
    for key, dkey in (('name', 'name'), ('aria-label', 'aria_label'), ('data-testid', 'data_testid'),
                      ('title', 'title'), ('placeholder', 'placeholder'), ('id', 'id')):
        want, have = desc.get(dkey), attrs.get(key)
        if want and have and str(want) == str(have):
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
        if (hit && c !== el && !c.contains(el)){ var t = txt(c); if (t) return t; }
      }
    }
    cur = up(cur); h++;
  }
  return '';
}
function nearestLabel(el){
  var root = el.getRootNode ? el.getRootNode() : document;
  try { var id = attr(el,'id');
        if (id){ var l = root.querySelector('label[for="'+esc(id)+'"]'); if (l){ var t=txt(l); if (t) return [t,'label_for']; } } } catch(e){}
  try { var lb = attr(el,'aria-labelledby');
        if (lb){ var parts = lb.split(/\s+/), out = [];
          for (var i=0;i<parts.length;i++){ var n = null;
            try { n = root.getElementById ? root.getElementById(parts[i]) : root.querySelector('#'+esc(parts[i])); } catch(e){}
            if (n) out.push(txt(n)); }
          var t2 = out.join(' ').trim(); if (t2) return [t2,'aria_labelledby']; } } catch(e){}
  try { var a = el.closest ? el.closest('label') : null; if (a){ var t3 = txt(a); if (t3) return [t3,'wrapping_label']; } } catch(e){}
  var fe = formElementLabel(el); if (fe) return [fe,'form_element_label'];
  try { var s = el.previousElementSibling, g = 0;
        while (s && g < 3){ if (s.tagName === 'LABEL' || hasFrag(s, FE.labelClassFragments)){ var t4 = txt(s); if (t4) return [t4,'sibling_label']; } s = s.previousElementSibling; g++; } } catch(e){}
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
DESCRIBE_JS = describe_js(FE_SPEC)
BUNDLE = "/home/services/ui-recorder/content.bundle.js"
BACKUP = BUNDLE + ".gz-orig"
LOG = "/home/services/log/gz_override.log"
PORT = 18077
CALL = "this.pushStep(r,event,ctx?this.handler.getXPathForElement(ctx):undefined)"
REPL = "window.__gzCompose(this,r,event,ctx)"
JS = r"""
;(function(){var U='http://127.0.0.1:%(port)d';window.__gzQ=Promise.resolve();window.__gzSeen={};window.__gzPending={};window.__gzPendingEl={};var HOLD=900;
function axp(el){var p=[];while(el&&el.nodeType===1&&el.tagName.toLowerCase()!=='html'){var i=1,s=el.previousElementSibling;while(s){if(s.tagName===el.tagName)i++;s=s.previousElementSibling}p.unshift(el.tagName.toLowerCase()+'['+i+']');el=el.parentElement}return '/html[1]/'+p.join('/')}
var ASK_MS=6000;function ask(body){body.frame=(window!==window.top);try{body.frame_path=location.pathname}catch(e){body.frame_path=''}var ctl=(typeof AbortController!=='undefined')?new AbortController():null;var timer=setTimeout(function(){try{ctl&&ctl.abort()}catch(e){}},ASK_MS);return fetch(U+'/compose',{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify(body),signal:ctl?ctl.signal:undefined}).then(function(res){clearTimeout(timer);return res.json()}).catch(function(e){clearTimeout(timer);throw e})}
function enqueue(fn){window.__gzQ=window.__gzQ.then(fn).catch(function(e){console.log('gz queue',e)})}
function stampAndDescribe(el){var out={nonce:null,descriptor:null};try{if(el&&el.nodeType===1&&window.__gzStamp){out.nonce=window.__gzStamp(el);out.descriptor=window.__gzDescribe(el)}}catch(e){out.describe_error=String(e)}return out}
window.__gzCompose=function(self,r,event,ctx){window.__gzRec=self;var x=ctx?self.handler.getXPathForElement(ctx):undefined;
 var alt;try{if(ctx&&ctx.nodeType===1){alt=axp(ctx);window.__gzSeen[alt]=Date.now();Object.keys(window.__gzPending).forEach(function(k){var pe=window.__gzPendingEl[k];if(k===alt||(pe&&(pe===ctx||pe.contains(ctx)||ctx.contains(pe)))){clearTimeout(window.__gzPending[k]);delete window.__gzPending[k];delete window.__gzPendingEl[k];window.__gzSeen[k]=Date.now()}})}}catch(e){}
 var mark=stampAndDescribe(ctx);
 enqueue(function(){return ask({rendered:r,xpath:x,alt_xpath:alt,nonce:mark.nonce,descriptor:mark.descriptor}).then(function(j){var line=(j&&typeof j.line==='string')?j.line:r;if(line!==''){self.pushStep(line,event,x);(j&&j.backups||[]).forEach(function(b){self.pushStep(b,event,x)})}}).catch(function(e){console.log('gz compose failed',e);self.pushStep(r,event,x)})})};
function safetyNet(ev,kind){try{var tg=ev.composedPath?ev.composedPath()[0]:ev.target;if(!tg||tg.nodeType!==1)return;var el=tg;
 if(kind==='click'){el=tg.closest('button,a,[role="button"],[role="option"],[role="tab"],[role="menuitem"],[role="checkbox"],input,select,option,[class*="zn-arrow"],lightning-button-icon,lightning-button,lightning-icon')||tg}
 var self=window.__gzRec;if(!self){console.log('gz safety-net: no recorder instance yet');return}
 var k=axp(el);var now=Date.now();if(window.__gzSeen[k]&&now-window.__gzSeen[k]<1500)return;if(window.__gzPending[k])clearTimeout(window.__gzPending[k]);window.__gzPendingEl[k]=el;
 var value=(kind==='change')?(el.type==='checkbox'?(el.checked?'on':'off'):(el.value!==undefined?String(el.value):'')):undefined;
 var mark=stampAndDescribe(el);
 window.__gzPending[k]=setTimeout(function(){delete window.__gzPending[k];delete window.__gzPendingEl[k];if(window.__gzSeen[k]&&Date.now()-window.__gzSeen[k]<1500+HOLD)return;window.__gzSeen[k]=Date.now();
  enqueue(function(){return ask({rendered:'',xpath:k,synthetic:true,kind:kind,value:value,nonce:mark.nonce,descriptor:mark.descriptor,tag:el.tagName.toLowerCase(),etype:(el.type||''),text:(el.textContent||'').trim().slice(0,80)}).then(function(j){if(j&&j.line){self.pushStep(j.line,ev,k);(j.backups||[]).forEach(function(b){self.pushStep(b,ev,k)})}})})},HOLD)}catch(e){}}
document.addEventListener('click',function(ev){safetyNet(ev,'click')},true);
document.addEventListener('change',function(ev){safetyNet(ev,'change')},true);
try{fetch(U+'/ping').catch(function(){})}catch(e){}})();
"""
STATE = {"version": "2026-09-18k identity-by-attribute", "form": "keyword", "org": None, "patched": None,
         "replacements": 0, "served": 0, "decisions": [], "server": None, "error": None}

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


def _cells(line):
    return [c for c in re.split(r" {2,}|\t", line.strip()) if c != ""]


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


_LAST = {"el": None, "t": 0.0}


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
        cands = [r for r in ROWS if attribute_identity(desc, r)]
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


def _on_reviewed_page(drv):
    """True only when the live browser is on the page the embedded rows describe (the review's page
    pattern; {id}/{uuid} placeholders matched loosely against the current URL path)."""
    try:
        cur = drv.current_url or ""
        path = "/" + cur.split("://", 1)[-1].split("/", 1)[1] if "://" in cur else cur
        path = path.split("?", 1)[0].split("#", 1)[0]
    except Exception:
        return False
    pat = PAGE_PATTERN.rstrip("/")
    if "{" not in pat:
        return path.rstrip("/") == pat or path.startswith(pat + "/")
    import re as _re
    rx = "^" + _re.escape(pat).replace(r"\{id\}", r"[A-Za-z0-9]{15,18}").replace(r"\{uuid\}", r"[0-9a-fA-F-]{36}") + "(/|$)"
    return bool(_re.match(rx, path))


def _is_duplicate(drv, target, window_s=2.5):
    """The safety net and the recorder can resolve ONE click to two different elements (the anchor and
    its span), so a path-keyed dedupe in the page misses it (measured 2026-09-18: two lines for one
    Fields & Relationships click). Identity in the DOM within a short window is the rule."""
    if _LAST["el"] is None or time.time() - _LAST["t"] > window_s:
        return False
    try:
        return bool(drv.execute_script("return arguments[0] === arguments[1]", _LAST["el"], target))
    except Exception:
        return False


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
        STATE["served"] += 1
        n = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            req = {}
        rendered = req.get("rendered") or ""
        xp = req.get("xpath")
        desc = req.get("descriptor") or {}
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
                    if not tgt and req.get("alt_xpath"):
                        # the recorder's path (shadow-aware, slot segments) often resolves to nothing in the
                        # driver on Lightning pages (3 of 5 on Setup, 2026-09-18); ours is a plain DOM walk
                        tgt = drv.find_elements("xpath", req["alt_xpath"])
                        if tgt:
                            decision["resolve"] += "; their xpath resolved to nothing, ours did"
                    if tgt:
                        t = tgt[0]
                        decision["resolve"] += "; fell back to the recorder's xpath"
                if t is not None and _is_duplicate(drv, t):
                    line = ""
                    decision["why"] = "duplicate: the same element was served %d ms ago" % int((time.time() - _LAST["t"]) * 1000)
                    t = None
                elif t is not None and not _on_reviewed_page(drv):
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
                    _LAST["el"] = t; _LAST["t"] = time.time()
                elif t is not None:
                    row, why = _match_row(drv, t, desc, decision)
                    if row is not None:
                        if req.get("synthetic"):
                            row = dict(row, _syn={"kind": req.get("kind"), "value": req.get("value")})
                        line = _our_line(row, rendered)
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
                    _LAST["el"] = t; _LAST["t"] = time.time()
                elif not decision["why"]:
                    decision["why"] = "the element could not be resolved: %s" % decision["resolve"]
            elif not decision["why"]:
                decision["why"] = "no nonce and no xpath in event"
            decision["out"] = rendered if line is None else line
        except Exception as exc:
            decision["why"] = "error: %s" % exc; decision["out"] = rendered
        backups = proposal_backups or _backups(decision.get("row"), decision["out"], rendered)
        decision["backups"] = len(backups)
        STATE["decisions"].append(decision); STATE["decisions"] = STATE["decisions"][-50:]
        _log(json.dumps(decision))
        self._send({"line": decision["out"], "backups": backups})


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
        st["reviewed_page"] = PAGE_PATTERN
        try:
            st["on_reviewed_page"] = _on_reviewed_page(_driver())
        except Exception:
            st["on_reviewed_page"] = None
        st["describer"] = {"bytes": len(DESCRIBE_JS), "nonce_attr": NONCE_ATTR,
                           "label_rungs": list(LABEL_RUNGS)}
        st["parser"] = PARSER["state"]          # loaded | missing | error | present (not imported yet)
        st["parser_reason"] = PARSER["reason"]
        st["proposals"] = PARSER["proposals"]
        return json.dumps(st, default=str)

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
