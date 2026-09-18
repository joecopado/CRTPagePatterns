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

Keywords: `Gz Override Status` (what was patched, how many events composed, last decisions),
`Gz Override Restore` (put the original bundle back). Log: /home/services/log/gz_override.log.
"""
import json, os, re, shutil, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROWS = json.loads('[{"n": 0, "label": "Toggle Panel", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-label=\\"Toggle Panel\\" and @title=\\"Menu\\"]", "group_size": 2, "index": 1, "kw": "ClickItem", "locator": "Menu", "xpath": "//button[@aria-label=\\"Toggle Panel\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 1, "label": "Show menu", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @type=\\"button\\" and @value=\\"\\"]", "kw": "ClickText", "locator": "Show menu", "xpath": "(//*[normalize-space(text())=\\"Developer Edition\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 2, "label": "Search...", "type": "button", "identity_xpath": "//button[@aria-label=\\"Search\\" and @type=\\"button\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Search...", "xpath": "//button[@aria-label=\\"Search\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 3, "label": "Add favorite", "type": "button", "identity_xpath": "//button[@aria-label=\\"Add favorite\\" and @aria-pressed=\\"false\\" and @type=\\"button\\"]", "kw": "ClickItem", "locator": "Add favorite", "xpath": "//button[@aria-label=\\"Add favorite\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 4, "label": "Favorites list", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"false\\" and @type=\\"button\\"]", "kw": "ClickText", "locator": "Favorites list", "xpath": "(//*[normalize-space(text())=\\"Add favorite\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 5, "label": "Global Actions", "type": "button", "identity_xpath": "//a[@aria-describedby=\\"\\" and @aria-disabled=\\"false\\" and @aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @aria-labelledby=\\"\\" and @href=\\"javascript:void(0);\\" and @role=\\"button\\" and @tabindex=\\"0\\" and @title=\\"\\"][.//text()[normalize-space(.)=\\"Global Actions\\"]]", "kw": "ClickText", "locator": "Global Actions", "xpath": "(//*[normalize-space(text())=\\"Favorites list\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 6, "label": "Guidance Center", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"dialog\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"Guidance Center\\"]]", "kw": "ClickText", "locator": "Guidance Center", "xpath": "(//*[normalize-space(text())=\\"Global Actions\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 7, "label": "Salesforce Help", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"true\\" and @title=\\"\\" and @type=\\"button\\"]", "kw": "ClickText", "locator": "Salesforce Help", "xpath": "(//*[normalize-space(text())=\\"Guidance Center\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 8, "label": "Setup", "type": "button", "identity_xpath": "//a[@aria-describedby=\\"\\" and @aria-disabled=\\"false\\" and @aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @aria-labelledby=\\"\\" and @href=\\"javascript:void(0);\\" and @role=\\"button\\" and @tabindex=\\"0\\" and @title=\\"\\"][.//text()[normalize-space(.)=\\"Setup\\"]]", "kw": "ClickText", "locator": "Setup", "xpath": "(//*[normalize-space(text())=\\"Salesforce Help\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 9, "label": "Notifications", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"dialog\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"Notifications\\"]]", "kw": "ClickText", "locator": "Notifications", "xpath": "(//*[normalize-space(text())=\\"Setup\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 10, "label": "View profile", "type": "button", "identity_xpath": "//button[@aria-haspopup=\\"true\\" and @type=\\"button\\"][.//text()[normalize-space(.)=\\"View profile\\"]]", "kw": "ClickText", "locator": "View profile", "xpath": "(//*[normalize-space(text())=\\"Notifications\\"]/following::button[@type=\\"button\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 11, "label": "App Launcher", "type": "button", "identity_xpath": "//button[@aria-expanded=\\"false\\" and @aria-haspopup=\\"dialog\\" and @title=\\"App Launcher\\"]", "kw": "ClickItem", "locator": "App Launcher", "xpath": "//button[@title=\\"App Launcher\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 12, "label": "Home", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/page/home\\" and @tabindex=\\"0\\" and @title=\\"Home\\"]", "kw": "ClickText", "locator": "Home", "xpath": "//a[@title=\\"Home\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 13, "label": "Opportunities", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Opportunity/home\\" and @tabindex=\\"0\\" and @title=\\"Opportunities\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Opportunities", "xpath": "//a[@title=\\"Opportunities\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 14, "label": "Opportunities List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Opportunities List\\"]]", "kw": "ClickText", "locator": "Opportunities List", "xpath": "(//*[normalize-space(text())=\\"Opportunities\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 15, "label": "Leads", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Lead/home\\" and @tabindex=\\"0\\" and @title=\\"Leads\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Leads", "xpath": "//a[@title=\\"Leads\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 16, "label": "Leads List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Leads List\\"]]", "kw": "ClickText", "locator": "Leads List", "xpath": "(//*[normalize-space(text())=\\"Leads\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 17, "label": "Tasks", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Task/home\\" and @tabindex=\\"0\\" and @title=\\"Tasks\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Tasks", "xpath": "//a[@title=\\"Tasks\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 18, "label": "Tasks List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Tasks List\\"]]", "kw": "ClickText", "locator": "Tasks List", "xpath": "(//*[normalize-space(text())=\\"Tasks\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 19, "label": "Files", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/ContentDocument/home\\" and @tabindex=\\"0\\" and @title=\\"Files\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Files", "xpath": "//a[@title=\\"Files\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 20, "label": "Files List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Files List\\"]]", "kw": "ClickText", "locator": "Files List", "xpath": "(//*[normalize-space(text())=\\"Files\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 21, "label": "Accounts", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Account/home\\" and @tabindex=\\"0\\" and @title=\\"Accounts\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Accounts", "xpath": "//a[@title=\\"Accounts\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 22, "label": "Accounts List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Accounts List\\"]]", "kw": "ClickText", "locator": "Accounts List", "xpath": "(//*[normalize-space(text())=\\"Accounts\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 23, "label": "Contacts", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Contact/home\\" and @tabindex=\\"0\\" and @title=\\"Contacts\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Contacts", "xpath": "//a[@title=\\"Contacts\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 24, "label": "Contacts List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Contacts List\\"]]", "kw": "ClickText", "locator": "Contacts List", "xpath": "(//*[normalize-space(text())=\\"Contacts\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 25, "label": "Campaigns", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Campaign/home\\" and @tabindex=\\"0\\" and @title=\\"Campaigns\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Campaigns", "xpath": "//a[@title=\\"Campaigns\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 26, "label": "Campaigns List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Campaigns List\\"]]", "kw": "ClickText", "locator": "Campaigns List", "xpath": "(//*[normalize-space(text())=\\"Campaigns\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 27, "label": "Dashboards", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Dashboard/home\\" and @tabindex=\\"0\\" and @title=\\"Dashboards\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Dashboards", "xpath": "//a[@title=\\"Dashboards\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 28, "label": "Dashboards List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Dashboards List\\"]]", "kw": "ClickText", "locator": "Dashboards List", "xpath": "(//*[normalize-space(text())=\\"Dashboards\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 29, "label": "Reports", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Report/home\\" and @tabindex=\\"0\\" and @title=\\"Reports\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Reports", "xpath": "//a[@title=\\"Reports\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 30, "label": "Reports List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Reports List\\"]]", "kw": "ClickText", "locator": "Reports List", "xpath": "(//*[normalize-space(text())=\\"Reports\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 31, "label": "Chatter", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/page/chatter\\" and @tabindex=\\"0\\" and @title=\\"Chatter\\"]", "kw": "ClickText", "locator": "Chatter", "xpath": "//a[@title=\\"Chatter\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 32, "label": "Groups", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/CollaborationGroup/home\\" and @tabindex=\\"0\\" and @title=\\"Groups\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Groups", "xpath": "//a[@title=\\"Groups\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 33, "label": "Groups List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Groups List\\"]]", "kw": "ClickText", "locator": "Groups List", "xpath": "(//*[normalize-space(text())=\\"Groups\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 34, "label": "Calendar", "type": "link", "identity_xpath": "//a[@aria-current=\\"false\\" and @draggable=\\"false\\" and @href=\\"/lightning/o/Event/home\\" and @tabindex=\\"0\\" and @title=\\"Calendar\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Calendar", "xpath": "//a[@title=\\"Calendar\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 35, "label": "Calendar List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Calendar List\\"]]", "kw": "ClickText", "locator": "Calendar List", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::a)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 36, "label": "Zoo \\u00b7 Nightmare inputs", "type": "link", "identity_xpath": "//a[@aria-current=\\"page\\" and @draggable=\\"false\\" and @href=\\"/lightning/n/Zoo_Nightmare_Inputs\\" and @tabindex=\\"0\\" and @title=\\"Zoo \\u00b7 Nightmare inputs\\"]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Zoo \\u00b7 Nightmare inputs", "xpath": "//a[@title=\\"Zoo \\u00b7 Nightmare inputs\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 37, "label": "Zoo \\u00b7 Nightmare inputs List", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"Zoo \\u00b7 Nightmare inputs List\\"]]", "kw": "ClickText", "locator": "Zoo \\u00b7 Nightmare inputs List", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::a[normalize-space(.)=\\"Zoo \\u00b7 Nightmare inputs List\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 38, "label": "Close tab", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Close tab\\"]]", "kw": "ClickText", "locator": "Close tab", "xpath": "(//*[normalize-space(text())=\\"Calendar\\"]/following::button)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 39, "label": "More", "type": "button", "identity_xpath": "//a[@aria-expanded=\\"false\\" and @aria-haspopup=\\"true\\" and @draggable=\\"false\\" and @role=\\"button\\" and @tabindex=\\"0\\"][.//text()[normalize-space(.)=\\"*\\"]]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "More", "xpath": "//a[.//text()[normalize-space(.)=\\"More\\"]]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "COULD-NOT-CHECK"}, {"n": 40, "label": "Personalize your nav bar", "type": "button", "identity_xpath": "//button[@title=\\"Personalize your nav bar\\" and @type=\\"button\\"]", "kw": "ClickItem", "locator": "Personalize your nav bar", "xpath": "//button[@title=\\"Personalize your nav bar\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 41, "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @type=\\"text\\"])[1]", "xpath": "//*[normalize-space(text())=\\"Contract Term\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 42, "label": "Contract Term", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[2]", "group_size": 2, "index": 1, "kw": "TypeText", "locator": "Contract Term", "xpath": "(//c-zoo-nightmare-inputs//input[@type=\\"text\\"])[2]", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS"}, {"n": 43, "label": "Renewal Notice (days)", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[3]", "kw": "TypeText", "locator": "Renewal Notice (days)", "xpath": "(//*[normalize-space(text())=\\"Renewal Notice (days)\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 44, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[4]", "group_size": 3, "index": 1, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"List Price\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 45, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[5]", "group_size": 3, "index": 2, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"Negotiated Discount\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 46, "label": "Amount", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[6]", "group_size": 3, "index": 3, "kw": "TypeText", "locator": "Amount", "xpath": "//*[normalize-space(text())=\\"Net to Customer\\"]/following-sibling::*//input[@type=\\"text\\"]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 47, "label": "Approved Budget", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[7]", "group_size": 2, "index": 1, "kw": "TypeText", "locator": "Approved Budget", "xpath": "(//*[normalize-space(text())=\\"Approved Budget\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 48, "label": "Approved Budget", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[8]", "group_size": 2, "index": 2, "kw": "TypeText", "locator": "Approved Budget", "xpath": "(//*[normalize-space(text())=\\"to\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS"}, {"n": 49, "type": "button", "identity_xpath": "(//button)[13]", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 50, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[9]", "group_size": 4, "index": 1, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 51, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[10]", "group_size": 4, "index": 1, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 52, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[1]", "group_size": 4, "index": 1, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 53, "type": "button", "identity_xpath": "(//button)[14]", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 54, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[11]", "group_size": 4, "index": 2, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 55, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[12]", "group_size": 4, "index": 2, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 56, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[2]", "group_size": 4, "index": 2, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 57, "type": "button", "identity_xpath": "(//button)[15]", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 58, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[13]", "group_size": 4, "index": 3, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 59, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[14]", "group_size": 4, "index": 3, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 60, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[3]", "group_size": 4, "index": 3, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 61, "type": "button", "identity_xpath": "(//button)[16]", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 62, "label": "Start Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[15]", "group_size": 4, "index": 4, "kw": "TypeText", "locator": "Start Date", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 63, "label": "End Date", "type": "input_field", "identity_xpath": "(//input[@type=\\"text\\"])[16]", "group_size": 4, "index": 4, "kw": "TypeText", "locator": "End Date", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::*[normalize-space(text())=\\"End Date\\"])[1]/following::input[@type=\\"text\\"][1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 64, "label": "Billable to customer", "type": "checkbox", "identity_xpath": "(//input[@type=\\"checkbox\\"])[4]", "group_size": 4, "index": 4, "kw": "ClickCheckbox", "locator": "Billable to customer", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::input[@type=\\"checkbox\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 65, "label": "Add Line", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Add Line\\"]])[1]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Add Line", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Add Line\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 66, "label": "Add Line", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Add Line\\"]])[2]", "group_size": 2, "index": 2, "kw": "ClickText", "locator": "Add Line", "xpath": "(//c-zoo-nightmare-inputs//button)[6]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 67, "label": "Save", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Save\\"]])[1]", "group_size": 2, "index": 1, "kw": "ClickText", "locator": "Save", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Save\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 68, "label": "Save & New", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Save & New\\"]]", "kw": "ClickText", "locator": "Save & New", "xpath": "(//*[normalize-space(text())=\\"Go-Live Support\\"]/following::button[normalize-space(.)=\\"Save & New\\"])[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 69, "label": "Save", "type": "button", "identity_xpath": "(//button[.//text()[normalize-space(.)=\\"Save\\"]])[2]", "group_size": 2, "index": 2, "kw": "ClickText", "locator": "Save", "xpath": "(//*[normalize-space(text())=\\"Save & New\\"]/following::button)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 70, "label": "Territory", "type": "dropdown", "identity_xpath": "//select[.//text()[normalize-space(.)=\\"--None--\\"]]", "group_size": 2, "index": 1, "kw": "DropDown", "locator": "Territory", "xpath": "(//*[normalize-space(text())=\\"Territory & Coverage\\"]/following::select)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 71, "label": "Territory", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[1]", "group_size": 2, "index": 2, "kw": "TypeText", "locator": "Territory", "xpath": "(//*[normalize-space(text())=\\"Territory & Coverage\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 72, "label": "Coverage Owner", "type": "input_field", "identity_xpath": "//input[@aria-autocomplete=\\"list\\" and @role=\\"combobox\\" and @type=\\"text\\"]", "kw": "TypeText", "locator": "Coverage Owner", "xpath": "(//*[normalize-space(text())=\\"Coverage Owner\\"]/following::input[@type=\\"text\\"])[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 73, "label": "Product Lines Covered", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[2]", "kw": "TypeText", "locator": "Product Lines Covered", "xpath": "(//*[normalize-space(text())=\\"Revenue Cloud\\"]/following::input[@type=\\"text\\"])[1]", "corrected": "ClickElement    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Product Lines Covered\\"]/following::input[@type\\\\=\\"text\\"])[1] ;; ClickText    Agentforce ;; VerifyText    Agentforce    timeout=5", "kw_verdict": "CAUGHT-BUG", "xp_verdict": "VERIFIED-PASS"}, {"n": 74, "label": "Support Tier", "type": "input_field", "identity_xpath": "(//input[@readonly=\\"\\" and @role=\\"combobox\\" and @type=\\"text\\"])[3]", "kw": "TypeText", "locator": "Support Tier", "xpath": "(//*[normalize-space(text())=\\"Support Tier\\"]/following::input[@type=\\"text\\"])[1]", "corrected": "ClickElement    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Support Tier\\"]/following::input[@type\\\\=\\"text\\"])[1] ;; ClickText    Premier Success ;; VerifyInputValue    xpath\\\\=(//*[normalize-space(text())\\\\=\\"Support Tier\\"]/following::input[@type\\\\=\\"text\\"])[1]    Premier Success", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 75, "label": "Escalation Regions", "type": "dropdown", "identity_xpath": "//select[@multiple=\\"\\" and @size=\\"4\\"]", "kw": "DropDown", "locator": "Escalation Regions", "xpath": "(//*[normalize-space(text())=\\"Escalation Regions\\"]/following::select)[1]", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 76, "label": "Dismiss", "type": "button", "identity_xpath": "//button[.//text()[normalize-space(.)=\\"Dismiss\\"]]", "kw": "ClickText", "locator": "Dismiss", "xpath": "(//*[normalize-space(text())=\\"Just so you know\\"]/following::button)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "COULD-NOT-CHECK"}, {"n": 77, "label": "Entitled Services", "type": "dual_listbox", "identity_xpath": "//div[@data-aura-class=\\"navexDesktopLayoutContainer lafAppLayoutHost forceAccess forceStyle oneOne\\"]", "kw": "Multi Pick List", "locator": "Entitled Services", "corrected": "ClickText    Health Check    partial_match=False ;; ClickElement    xpath\\\\=//*[normalize-space(text())\\\\=\\"Entitled Services\\"]/following::*[contains(@class,\\"zn-arrow-r\\")][1] ;; VerifyText    Health Check    anchor=Selected", "kw_verdict": "VERIFIED-PASS", "xp_verdict": "VERIFIED-PASS"}, {"n": 78, "type": "input_field", "identity_xpath": "//c-zoo-nightmare-inputs", "xpath": "(//*[normalize-space(text())=\\"More\\"]/following::c-zoo-nightmare-inputs)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 79, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Kickoff Workshop\\"]]", "xpath": "(//*[normalize-space(text())=\\"Onsite Schedule\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 80, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Discovery Review\\"]]", "xpath": "(//*[normalize-space(text())=\\"Kickoff Workshop\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 81, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Integration Checkpoint\\"]]", "xpath": "(//*[normalize-space(text())=\\"Discovery Review\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 82, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-row[.//text()[normalize-space(.)=\\"Go-Live Support\\"]]", "xpath": "(//*[normalize-space(text())=\\"Integration Checkpoint\\"]/following::c-zoo-nightmare-row)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}, {"n": 83, "type": "custom_component", "identity_xpath": "//c-zoo-nightmare-combos", "xpath": "(//*[normalize-space(text())=\\"Save & New\\"]/following::c-zoo-nightmare-combos)[1]", "kw_verdict": "COULD-NOT-CHECK", "xp_verdict": "VERIFIED-PASS"}]')
BUNDLE = "/home/services/ui-recorder/content.bundle.js"
BACKUP = BUNDLE + ".gz-orig"
LOG = "/home/services/log/gz_override.log"
PORT = 18077
CALL = "this.pushStep(r,event,ctx?this.handler.getXPathForElement(ctx):undefined)"
REPL = "window.__gzCompose(this,r,event,ctx)"
JS = r"""
;(function(){var U='http://127.0.0.1:%(port)d';window.__gzQ=Promise.resolve();window.__gzSeen={};
function axp(el){var p=[];while(el&&el.nodeType===1&&el.tagName.toLowerCase()!=='html'){var i=1,s=el.previousElementSibling;while(s){if(s.tagName===el.tagName)i++;s=s.previousElementSibling}p.unshift(el.tagName.toLowerCase()+'['+i+']');el=el.parentElement}return '/html[1]/'+p.join('/')}
function ask(body){return fetch(U+'/compose',{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify(body)}).then(function(res){return res.json()})}
window.__gzCompose=function(self,r,event,ctx){window.__gzRec=self;var x=ctx?self.handler.getXPathForElement(ctx):undefined;
 window.__gzQ=window.__gzQ.then(function(){return ask({rendered:r,xpath:x}).then(function(j){var line=(j&&typeof j.line==='string')?j.line:r;if(line!=='')self.pushStep(line,event,x)}).catch(function(e){console.log('gz compose failed',e);self.pushStep(r,event,x)})})};
document.addEventListener('click',function(ev){try{var tg=ev.target;if(!tg||tg.nodeType!==1)return;var el=tg.closest('[class*="zn-arrow"],button,[role="button"]');if(!el||(el.textContent||'').trim()!=='')return;
 var self=window.__gzRec;if(!self){console.log('gz synthetic: no recorder instance yet');return}var x=axp(el);var now=Date.now();if(window.__gzSeen[x]&&now-window.__gzSeen[x]<1500)return;window.__gzSeen[x]=now;
 window.__gzQ=window.__gzQ.then(function(){return ask({rendered:'',xpath:x,synthetic:true}).then(function(j){if(j&&j.line)self.pushStep(j.line,ev,x)}).catch(function(e){console.log('gz synthetic failed',e)})})}catch(e){}},true);
try{fetch(U+'/ping').catch(function(){})}catch(e){}})();
"""
STATE = {"version": "2026-09-18e form-switch", "form": "keyword", "patched": None, "replacements": 0, "served": 0, "decisions": [], "server": None, "error": None}


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
        out = src.replace(CALL, REPL) + (JS % {"port": PORT})
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
    if t == "input_field" and action in ("ClickText", "VerifyText"):
        # the focus click renders the field's current value as ClickText and the tab-out renders
        # the next field's value as VerifyText (measured 2026-09-18, 8 of 17 recorded lines); the
        # TypeText that follows carries the intent
        return ""
    if action == "" and xp_ok:
        # a synthetic event: our own listener saw a click the recorder emits nothing for
        return "ClickElement    %s" % _xp(row)
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
    kw_ok = row.get("kw_verdict") == "VERIFIED-PASS"
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
        decision = {"in": rendered[:80], "xpath": (xp or "")[-60:], "out": None, "row": None, "why": None}
        try:
            line = None
            if xp:
                drv = _driver()
                tgt = drv.find_elements("xpath", xp)
                if tgt:
                    t = tgt[0]
                    for row in ROWS:
                        try:
                            els = drv.find_elements("xpath", row["identity_xpath"])
                        except Exception:
                            continue
                        if len(els) == 1 and drv.execute_script("return arguments[0] === arguments[1]", els[0], t):
                            line = _our_line(row, rendered)
                            decision["row"] = row["n"]; decision["why"] = "identity match" if line else "matched, no better line"
                            break
                    if decision["row"] is None:
                        n, step = _recipe_step_for(drv, t)
                        if step:
                            line = step; decision["row"] = n; decision["why"] = "recipe step identity match"
                        elif req.get("synthetic"):
                            line = ""; decision["why"] = "synthetic click, nothing known; not recorded"
                        else:
                            decision["why"] = "no row resolves to this element"
                else:
                    decision["why"] = "their xpath resolved to nothing"
            else:
                decision["why"] = "no xpath in event"
            decision["out"] = rendered if line is None else line
        except Exception as exc:
            decision["why"] = "error: %s" % exc; decision["out"] = rendered
        STATE["decisions"].append(decision); STATE["decisions"] = STATE["decisions"][-50:]
        _log(json.dumps(decision))
        self._send({"line": decision["out"]})


def _serve():
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), _H)
        STATE["server"] = "listening on %d" % PORT
        srv.serve_forever()
    except Exception as exc:
        STATE["server"] = "error: %s" % exc; STATE["error"] = traceback.format_exc(); _log(STATE["error"])


_patch_bundle()
threading.Thread(target=_serve, daemon=True, name="gz-composer").start()
_log("import done: patched=%s server=%s" % (STATE["patched"], STATE["server"]))


class garzai_recorder_override:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def gz_override_status(self):
        return json.dumps({k: v for k, v in STATE.items() if k != "error"}, default=str)

    def gz_override_form(self, form="keyword"):
        """keyword: the live-verified keyword form, xpath only as backstop (default);
        xpath: the verified xpath form wherever one exists; both: keyword line, xpath as a comment."""
        form = str(form).strip().lower()
        if form not in ("keyword", "xpath", "both"):
            raise ValueError("form must be keyword, xpath or both")
        STATE["form"] = form
        return form

    def gz_override_restore(self):
        if os.path.exists(BACKUP):
            shutil.copyfile(BACKUP, BUNDLE); return "restored"
        return "no backup"
