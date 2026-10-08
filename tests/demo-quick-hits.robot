*** Settings ***
Documentation                 DEMO QUICK HITS, 2026-10-08 -- one file, each case a plain CRT test with its own recording notes.
...
...                           Every case is preceded by up to four kinds of comment:
...                             # RECORD:       what you click in the CRT recorder (Live Testing), on which org and page.
...                             # EXPLAIN:      two or three sentences to say out loud.
...                             # PROVEN:       the evidence file and date behind a claim.
...                             # NOT-YET-RUN:  what no run has shown yet. Read these before you say it.
...                           PROVEN: locally means the lines ran on this Mac in a headless browser on the org named, nothing saved,
...                           under real QWeb. It did NOT run inside a CRT build: CRT's own ComboBox / PickList / UseModal (QForce,
...                           licensed) cannot run on this Mac, so a local run uses OUR ComboBox / PickList in their place.
...                           The evidence for every local run is in docs/demo-quick-hits-2026-10-08/ in this repo (README.md first).
...
...                           HOW TO RECORD STOCK, THEN OURS, IN THIS ONE FILE
...                             STOCK  : leave the file as it is (no recorder override is imported). Start Live Testing, run the lines
...                                      of a case down to its RECORD HERE comment, switch the recorder on, do the gestures.
...                             OURS   : remove the # from the three TOGGLE lines below (Library, Suite Setup, Suite Teardown), start a
...                                      FRESH Live Testing session, run the first lines of the case, run the keyword Gz Override Org
...                                      with  slockard  (or  healthcloud)  once, then record the same gestures. Before you stop the
...                                      session, select and run the Restore Stock Recorder test at the bottom.
...                           Nothing in this file saves a record: every form is Cancelled, every typed value is page-local.
...
...                           HEALTH CLOUD LOGIN: client_idHealthCloud, usernameHealthCloud and private_keyHealthCloud are project
...                           variables (not the retired HC ones, which belong to the expired health90 trial).
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_navigation.robot
Resource                      ../resources/garzai_typetext_override.robot    # OURS: TypeText that pre-clears a filled field and reads back (build 85956ae). Stock is called by name below: QForce.TypeText
# TOGGLE 1 of 3 -- record with OUR override: remove the leading # on the next line (and on the two lines after it)
#Library                      ../resources/garzai_recorder_override.py
Suite Setup                   Setup Browser
Suite Teardown                End suite
# TOGGLE 2 of 3 -- replaces the Suite Setup line above:     Suite Setup    Setup Browser With Override
# TOGGLE 3 of 3 -- replaces the Suite Teardown line above:  Suite Teardown    Run Keywords    Gz Override Restore    AND    End suite

*** Variables ***
# (the account names are assigned inside each test: ${account} = Edge Communications on slockard, Acme Partners on healthcloud;
#  each is the ONLY Account of that name in its org, SOQL 2026-10-08)

# DEMO ORDER: show the cases in this order. Case number, what it is, the org, then its purpose.
#   01  Lookup, what STOCK records          slockard     an absolute xpath click, then ComboBox keyed on the placeholder
#   02  Lookup, our label line              slockard     ComboBox on the field's own label; what the Test Agent's reader lists
#   03  Lookup, our label line              healthcloud  the same line on a second org and a second object (Contact)
#   04  Picklist, ONE line                  slockard     the line our override records for a pick, nothing else
#   05  Picklist, WITH BACKUPS              slockard     the same line plus every stock line it absorbed, dormant (self-healing)
#   06  Aura picklist, STOCK keyword        slockard     the customer's picklist shape (twin: + > New Case > Status), stock PickList
#   07  Aura picklist, OURS, ONE line       slockard     Aura PickList: the two clicks and a read-back as one keyword line
#   08  Aura picklist, override line, ONE   slockard     what the override records for the Status box, as written
#   09  Aura picklist, override WITH BACKUP slockard     the same line plus its backup: the line fails, the backup heals it
#   10  Test Agent on Zoo Nightmare Inputs  slockard     four prompts to paste, and the lines the agent should end up writing
#   11  TypeText on a pre-filled field      slockard     stock replaces or appends by build; ours pre-clears and reads back
# IF YOU ONLY HAVE FIVE MINUTES: 02, 05, 09, 10.

*** Test Cases ***
01 Lookup -- STOCK recorder lines (slockard, New Opportunity, Account Name)
    [Documentation]    What the stock CRT recorder writes for a lookup, as recorded, as runnable lines.
    # RECORD: slockard. Sales app > Opportunities > New (or run the first lines below). Click the Account Name box, type  Edge
    #         and click  Edge Communications  in the list. STOCK recorder only (no override toggles).
    # EXPLAIN: A lookup is three gestures (click, type, pick) that the stock recorder folds into one ComboBox line. It keys that
    #          line on the box's PLACEHOLDER, "Search Accounts...", which every account lookup on every form shares, and it
    #          precedes it with a click on an absolute path from the top of the page down through 40 levels of components. The
    #          path breaks the day the page layout moves a row; the placeholder cannot tell two account lookups apart.
    # PROVEN: both lines are the stock recorder's own output in the user's sessions: the ComboBox line on slockard, 2026-09-18
    #         (docs/recorder/evidence/crt-live-testing-recorder-network-2026-09-18.md, Part 11, line 473, with the ClickElement
    #         before it) and the same pair on fsc7f, 2026-09-23 (docs/recorder/evidence/sessions/2026-09-23-fsc7f-four-pages-stock-user/
    #         pane.robot, lines 30-33). The slockard harvest cuts the path at 170 characters, so the path below is the fsc7f one;
    #         slockard's New Opportunity layout carries the same layout name (forcegenerated-detailpanel_opportunity___012000000000000aaa___full___create___recordlayout2,
    #         found in the 2026-10-08 slockard capture) with Account Name on row 3 in both. fsc7f also recorded a ClickText on the
    #         label first because its Account Name is required (*Account Name); slockard's is not, so that line is left out.
    # NOT-YET-RUN: replaying these lines in a CRT build. Run locally on 2026-10-08, the ClickElement path did NOT resolve in the
    #         local headless Chrome (native shadow DOM; CRT's Chrome is the one the recorder wrote the path in). So expect this case
    #         to be red here and unproven in CRT: that fragility is the point of the case.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Object Page    Opportunity    new
    VerifyText    Account Name    timeout=30
    # ---- RECORD HERE (stock). The lines below are what the recorder wrote; run them to replay it ----
    UseModal    On
    ClickElement    /html[1]/body[1]/div[4]/div[2]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/records-modal-lwc-detail-panel-wrapper[1]/records-record-layout-event-broker[1]/slot[1]/records-lwc-detail-panel[1]/records-base-record-form[1]/div[1]/div[2]/div[1]/div[1]/records-lwc-record-layout[1]/forcegenerated-detailpanel_opportunity___012000000000000aaa___full___create___recordlayout2[1]/records-record-layout-block[1]/slot[1]/records-record-layout-section[1]/div[1]/div[1]/div[1]/slot[1]/records-record-layout-row[3]/slot[1]/records-record-layout-item[1]/div[1]/span[1]/slot[1]/records-record-layout-lookup[1]/lightning-lookup[1]/lightning-lookup-desktop[1]/lightning-grouped-combobox[1]/div[1]/div[1]/lightning-base-combobox[1]/div[1]/div[1]/div[1]
    ComboBox    Search Accounts...    ${account}
    UseModal    Off
    ClickText    Cancel    partial_match=False
    [Teardown]    UseModal    Off

02 Lookup -- OURS, one line (slockard, New Opportunity, Account Name)
    [Documentation]    The label form of the same gesture: one ComboBox line on the field's own label.
    # RECORD: slockard, the same form and the same three gestures, with the OVERRIDE toggles on. Then read what the pane wrote.
    #         DO NOT promise the pane will show the line below: see NOT-YET-RUN.
    # EXPLAIN: The label is what a person sees: ComboBox, Account Name, the record. No path, no placeholder, and it stays correct if
    #          the form is rearranged. This is also exactly what our page reader (Gz Read Page, the keyword the Test Agent calls)
    #          lists for this field: the control as a lookup, with this line.
    # PROVEN: locally, slockard, 2026-10-08: ComboBox Account Name Edge Communications selected the record; VerifyInputValue read
    #         back "Edge Communications" and Gz Verify said VERIFIED-PASS (docs/demo-quick-hits-2026-10-08/README.md, screenshot
    #         slockard-lookup.png). Earlier: slockard 1/1 and dev1 1/1, 2026-09-22 (docs/HANDOFF-2026-09-23-RESUME.md, "the three-pick
    #         proof"). The page reader lists it: offline over a 2026-10-08 slockard capture, "30. Account Name [lookup]
    #         ComboBox    Account Name    <record name>" (docs/demo-quick-hits-2026-10-08/gz-read-page-offline.txt).
    # NOT-YET-RUN: (1) the recorder override does NOT write this line today. Measured twice: the user's own fsc7f session on the
    #         shipped build, 2026-09-23 (docs/recorder/evidence/sessions/2026-09-23-fsc7f-four-pages-override-n13-user/README.md,
    #         CAUGHT-BUG: stock's absolute ClickElement and the placeholder ComboBox came through unchanged), and an offline replay of
    #         the shipped build over slockard's Opportunity New capture on 2026-10-08 (it composed only ClickText Account Name for that
    #         row). So say "our reader names the lookup by its label", not "our recorder fixed it". (2) CRT's own ComboBox on a label.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Object Page    Opportunity    new
    VerifyText    Account Name    timeout=30
    UseModal    On
    # ---- the line ----
    ComboBox    Account Name    ${account}
    # ---- the verdict, as its own line ----
    VerifyInputValue    Account Name    ${account}
    ClickText    Cancel    partial_match=False
    UseModal    Off
    [Teardown]    UseModal    Off
    # (No "with backups" twin for this case: the shipped override writes no composed lookup line, so there are no backup lines of
    #  its own to copy. Case 05 shows the pair for the picklist, which it does write.)

03 Lookup -- OURS, one line (healthcloud, New Contact, Account Name)
    [Documentation]    The same label line on another org and another object.
    # RECORD: healthcloud. Contacts > New. Click Account Name, type  Acme,  click  Acme Partners.  Stock first, then the override.
    #         The same form has two more lookups (Reports To, Individual): their placeholders are Search Contacts... and
    #         Search Individuals..., so a placeholder key does tell THEM apart. It cannot tell a second ACCOUNT lookup apart.
    # EXPLAIN: Second org, second object, same line. The stock recorder would write the pair from case 01 here too, with this
    #          form's own layout path (below, as the recorder's path rule gives it). Ours is one line on the label.
    # PROVEN: locally, healthcloud, 2026-10-08: ComboBox Account Name Acme Partners selected the record and the read-back matched
    #         (docs/demo-quick-hits-2026-10-08/README.md, healthcloud-lookup.png). Login: the credential's JwtLogin proof
    #         VERIFIED-PASS 2026-10-08 (crt-jwt-setup local --verify-only).
    # NOT-YET-RUN: the stock recorder's lines on healthcloud: nobody recorded this form. The path in the comment below is DERIVED from
    #         the live DOM with the recorder's own path rule (same widget as slockard and fsc7f), not recorded. Also not run: login
    #         inside a CRT build with these variables.
    ${token}=    JwtAuthenticate    ${client_idHealthCloud}    ${usernameHealthCloud}    ${private_keyHealthCloud}
    JwtLogin
    ${account}=    Set Variable    Acme Partners
    Open Object Page    Contact    new
    VerifyText    Account Name    timeout=30
    # stock would write (derived, not recorded):
    #   ClickElement    /html[1]/body[1]/div[4]/div[2]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/records-modal-lwc-detail-panel-wrapper[1]/records-record-layout-event-broker[1]/slot[1]/records-lwc-detail-panel[1]/records-base-record-form[1]/div[1]/div[2]/div[1]/div[1]/records-lwc-record-layout[1]/forcegenerated-detailpanel_contact___012aj00000egjlbaab___full___create___recordlayout2[1]/records-record-layout-block[1]/slot[1]/records-record-layout-section[1]/div[1]/div[1]/div[1]/slot[1]/records-record-layout-row[2]/slot[1]/records-record-layout-item[1]/div[1]/span[1]/slot[1]/records-record-layout-lookup[1]/lightning-lookup[1]/lightning-lookup-desktop[1]/lightning-grouped-combobox[1]/div[1]/div[1]/lightning-base-combobox[1]/div[1]/div[1]/div[1]
    #   ComboBox    Search Accounts...    Acme Partners
    UseModal    On
    # ---- the line ----
    ComboBox    Account Name    ${account}
    VerifyInputValue    Account Name    ${account}
    ClickText    Cancel    partial_match=False
    UseModal    Off
    [Teardown]    UseModal    Off

04 Picklist -- ONE line (slockard, New Opportunity, Stage)
    [Documentation]    The line our override writes for a picklist pick: nothing else.
    # RECORD: slockard, Opportunities > New. Click the Stage box, click  Prospecting.  Override toggles on.
    # EXPLAIN: A pick is two clicks (open the list, click the option). Ours writes ONE line: PickList, the label, the option.
    #          This is the line a tester reads and maintains.
    # PROVEN: the override's own output, replayed offline on a 2026-10-08 slockard capture of this exact modal with the shipped
    #         build 2026-09-23n13 (docs/demo-quick-hits-2026-10-08/override-replay-excerpts.txt; the replay's stand-in option
    #         "Gz Replay Option" is replaced by Prospecting below). The line ran locally on slockard 2026-10-08 (PickList Stage
    #         Prospecting) and on 2026-09-22 (docs/HANDOFF-2026-09-23-RESUME.md).
    # NOT-YET-RUN: a fresh recording of this gesture with the override on (the offline replay is not a session); this case in a CRT build.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Object Page    Opportunity    new
    VerifyText    Stage    timeout=30
    UseModal    On
    PickList    Stage    Prospecting    # unverified: parser proposal
    ClickText    Cancel    partial_match=False
    UseModal    Off
    [Teardown]    UseModal    Off

05 Picklist -- WITH BACKUPS (slockard, New Opportunity, Stage)
    [Documentation]    The same line followed by the dormant backups, exactly as the override writes them.
    # RECORD: as case 04. The pane shows the line, then the Comment lines under it.
    # EXPLAIN: The single line is what a tester reads; the backups are what makes it self-healing. Each backup is a stock line the
    #          override absorbed, or the same step in another form. If the PickList line ever stops working, un-comment ONE backup
    #          (or the opener and the option as a pair). Order is strongest first: the stock recorder's own opener, the keyword form,
    #          the xpath form, then the option.
    # PROVEN: every line below is the override's own output (offline replay of build 2026-09-23n13 over the 2026-10-08 slockard
    #         Opportunity New capture; only the replay's stand-in option text is replaced by Prospecting). Run locally on slockard,
    #         2026-10-08, under real QWeb, each opener followed by ClickText Prospecting and a read-back: the stock opener
    #         (ClickText --None-- anchor=Stage) VERIFIED-PASS; the keyword form (ClickText Stage) VERIFIED-PASS; the xpath form
    #         did NOT resolve in the local headless Chrome (native shadow DOM), so it is unproven here.
    # NOT-YET-RUN: a recording session on this build that produces these exact lines on this exact page; the xpath backup in CRT.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Object Page    Opportunity    new
    VerifyText    Stage    timeout=30
    UseModal    On
    PickList    Stage    Prospecting    # unverified: parser proposal
    Comment    backup: ClickText    --None--    anchor=Stage    # stock recorder line, unverified
    Comment    backup: ClickText    Stage    # keyword form, unverified: composed from the label
    Comment    backup: ClickElement    xpath\=//label[normalize-space(.)\="Stage"]/following::*[@role\="combobox"][1]    # xpath form, unverified: composed from the label
    Comment    backup: ClickText    Prospecting    # stock recorder line, unverified
    ClickText    Cancel    partial_match=False
    UseModal    Off
    [Teardown]    UseModal    Off

06 Aura picklist -- STOCK keyword line (slockard twin of the customer's picklist)
    [Documentation]    The customer's Aura picklist shape, on our org: global action New Case, field Status.
    # RECORD: slockard, Sales app, the Edge Communications Account record. Click the + (Global Actions) in the top bar > New Case.
    #         In the panel click the Status box (it reads New) and click Working. Stock recorder first. Write down the lines the pane
    #         gives you: nobody has measured what the stock recorder writes for this picklist.
    # EXPLAIN: The customer's picklist (their quote and opportunity forms) is not a Lightning combobox: Salesforce draws it with the
    #          older Aura components (a link with role combobox, options in a popup list). Any org that creates records from a quick
    #          action gets this shape, so we found the same one on our own org: the global New Case panel, field Status. Stock's
    #          PickList keyword is written for the Lightning shape.
    # PROVEN: the twin is real. Capture of slockard's New Case panel, 2026-10-08: class "uiInput uiInputSelect forceInputPicklist",
    #         label class uiPicklistLabel, trigger <a role="combobox" class="select" aria-expanded="false"> reading "New" (the
    #         customer's own capture has the same classes: docs/dom-captures/customer-cpq/02-new-opportunity-modal.html,
    #         docs/recorder/CUSTOMER-CPQ-SIGNATURES.md). Our brain's pick_list set it to Working and read back "Working"
    #         (docs/demo-quick-hits-2026-10-08/README.md, slockard-aura-status.png). The same panel carries an Aura lookup
    #         (Contact Name, Search Contacts...).
    # NOT-YET-RUN: what CRT's own PickList does on this shape (the line below). The customer's report is that it misbehaves; no run
    #         of ours has measured it. A local run passes this case only because it runs OUR PickList in place of CRT's. If CRT's works,
    #         say so: this case then shows nothing and case 07 is the answer to "what if it does not".
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Record Page    Account    Name    ${account}
    ClickText    Global Actions
    ClickText    New Case    partial_match=False
    VerifyText    Contact Name    timeout=30
    # ---- the stock keyword line ----
    PickList    Status    Working

07 Aura picklist -- OURS, one line (Aura PickList, slockard New Case, Status)
    [Documentation]    The Aura two-click as one keyword line.
    # RECORD: as case 06, with the override toggles on.
    # EXPLAIN: One keyword, same shape as PickList: the label, the option. Inside it is the gesture the customer's tester does by hand
    #          (click the current value next to the label, click the option) plus a read-back. It is defined at the bottom of this file;
    #          the same body lives in our recorder library (tools/recorder/library/garzai_recorder.robot).
    # PROVEN: the body (three lines of stock QWeb) ran locally under real QWeb on slockard, 2026-10-08: Aura PickList Status Working New
    #         passed, all three lines (docs/demo-quick-hits-2026-10-08/README.md).
    # NOT-YET-RUN: in a CRT build; and on the CUSTOMER's org (neo4j-acpdev is capture-only: its open-popup gesture was never confirmed,
    #         docs/recorder/CUSTOMER-CPQ-SIGNATURES.md "CAUGHT-BUG"); the customer's picklist reads --None-- when unset, here it reads New.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Record Page    Account    Name    ${account}
    ClickText    Global Actions
    ClickText    New Case    partial_match=False
    VerifyText    Contact Name    timeout=30
    # ---- the line ----
    Aura PickList    Status    Working    New

08 Aura picklist -- override line, ONE line (slockard New Case, Status)
    [Documentation]    The one line the recorder override writes for a click on the Status box, as written.
    # RECORD: as case 06, override on. Read the pane at the click on the Status box.
    # EXPLAIN: The honest picture of the override today. For the Status box it writes ClickText Status New. It does not yet know the box
    #          is a picklist, so it does not pair the two clicks into one PickList-style line the way it does for Stage in case 04. And
    #          as a single line it does not resolve on this control (below): that is what the backup in case 09 is for.
    # PROVEN: the line is the override's own output (offline replay of build 2026-09-23n13 over the 2026-10-08 capture of the New Case
    #         panel, row "Status New"; docs/demo-quick-hits-2026-10-08/override-replay-excerpts.txt), and the shipped page reader lists
    #         the same control the same way ("95. Status New [link] ClickText    Status New    partial_match=False"). Run locally,
    #         slockard, 2026-10-08, under real QWeb: the line did NOT resolve (Unable to find element for locator Status New).
    # NOT-YET-RUN: a recording session of this gesture with the override on; whether it resolves in CRT's Chrome. The step is wrapped so
    #         this case reports the outcome and stays green either way: it is a measurement, not a test of the product.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Record Page    Account    Name    ${account}
    ClickText    Global Actions
    ClickText    New Case    partial_match=False
    VerifyText    Contact Name    timeout=30
    # ---- the line, exactly as the override wrote it:  ClickText    Status New    partial_match=False    # unverified: parser proposal ----
    ${status}    ${error}=    Run Keyword And Ignore Error    ClickText    Status New    partial_match=False
    Log To Console    the override's line for the Status box: ${status} ${error}

09 Aura picklist -- override line WITH BACKUP (slockard New Case, Status)
    [Documentation]    The same line followed by its backup, as the override wrote them: the backup runs when the line fails.
    # RECORD: as case 08. Read the pane: the line, then the Comment line under it.
    # EXPLAIN: This is the self-healing, live: the single line is what a tester reads; the backup under it is what makes it recoverable.
    #          When the line stops working a person un-comments the backup. Here the guard below does that for you: it runs the backup
    #          only if the line failed, then picks Working and reads it back.
    # PROVEN: both lines are the override's own output (same replay as case 08). Run locally, slockard, 2026-10-08, under real QWeb:
    #         the line failed, the xpath backup resolved, ClickText Working picked the option and VerifyText Working anchored on Status
    #         passed (docs/demo-quick-hits-2026-10-08/README.md).
    # NOT-YET-RUN: a recording session of this gesture; this case in a CRT build, where the line itself may resolve (then the guard skips the backup).
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${account}=    Set Variable    Edge Communications
    Open Record Page    Account    Name    ${account}
    ClickText    Global Actions
    ClickText    New Case    partial_match=False
    VerifyText    Contact Name    timeout=30
    # ---- the line and its backup, exactly as the override wrote them ----
    #   ClickText    Status New    partial_match=False    # unverified: parser proposal
    #   Comment    backup: ClickElement    xpath\=(//*[normalize-space(text())\="Status"]/following::a)[1]    # xpath form, unverified: parser proposal
    ${status}    ${error}=    Run Keyword And Ignore Error    ClickText    Status New    partial_match=False
    IF    '${status}' == 'FAIL'
        ClickElement    xpath\=(//*[normalize-space(text())\="Status"]/following::a)[1]    # the backup, un-commented because the line failed
    END
    ClickText    Working    partial_match=False
    VerifyText    Working    anchor=Status

10 Test Agent -- Zoo Nightmare Inputs (three Amount inputs with one label)
    [Documentation]    Paste the prompts below into the Test Agent, in order, in a Live Testing session on this page.
    # SETUP: Open this test in the QEditor, start Live Testing, select the lines from JwtAuthenticate to VerifyText and run them (the page
    #        is open when VerifyText passes), then open the Test Agent panel. Use a fresh session: a restarted one loses the page.
    # PROMPT 1 (read the page):
    #   Run Gz Read Page with try_keyword, then call read_executor_output and quote the last console line word for word.
    # PROMPT 2 (name the three apart):
    #   There are three inputs labelled Amount on this page. Run Gz Show    Amount with try_keyword, then read_executor_output, and tell me which heading each one sits under.
    # PROMPT 3 (fill one by its index, verify it):
    #   Type 25000 into the third Amount field, then run Gz Verify    Amount    25000    index=3 with try_keyword. Use read_executor_output and quote Gz Verify's last console line word for word. Do not save anything.
    # PROMPT 4 (our reader against the agent's own):
    #   Do not use Gz Read Page. Use your own read_page on this page and list every input labelled Amount that you can see, with the label each one carries. Then say how many of the page's controls read_page showed you.
    # BONUS PROMPT 5 (the verdict that is not a pass):
    #   Run Gz Verify    Amount    99999    index=3 with try_keyword (do not type anything first). Tell me whether try_keyword passed or failed, then quote Gz Verify's last console line word for word.
    # EXPLAIN: The agent's own read_page hands the model the first 40,000 characters of a 99 KB list: 44 of 78 elements, the rest never reach
    #          it, and on this page it showed none of the real inputs with their labels. Gz Read Page hands it the page as 38 plain lines,
    #          one per control, each with the exact call to use, and the three Amounts apart by index. Gz Verify then reads the value back
    #          and says VERIFIED-PASS or CAUGHT-BUG; try_keyword alone only says passed.
    # PROVEN: prompts 1, 3 and 5 are the user's own wording from the live session of 2026-10-06 in this editor; replies and screenshots:
    #         docs/audit/test-agent-pack-2026-10/evidence/live-2026-10-06/ (27-zoo-read.png: Gz Read Page; 29-verify.png: VERIFIED-PASS reads
    #         '25000'; 30-wrong.png: try_keyword passed while Gz Verify said CAUGHT-BUG). The numbers in EXPLAIN: docs/recorder/evidence/
    #         crt-test-agent-dom-2026-10-01.md. The lines below ran locally, slockard, 2026-10-08, under real QWeb: Gz Read Page (both pages),
    #         Gz Show Amount, TypeText Amount 25000 anchor=3 (our TypeText emptied the filled 136,100.00 first), Gz Verify VERIFIED-PASS,
    #         and the 99999 verify passed the step with its CAUGHT-BUG line. Gz Show Amount lists the three members with the anchors
    #         List Price, Negotiated Discount, Net to Customer (docs/demo-quick-hits-2026-10-08/gz-read-page-offline.txt).
    # NOT-YET-RUN: prompts 2 and 4 have not been typed to the live agent (Gz Show and read_page were measured offline and on the wire, not
    #         through these exact prompts). The agent writes its own lines: expect variations of the ones below and check them. In a job
    #         BUILD (not Live Testing) Gz Read Page needs lxml, which the build container lacked on 2026-10-07 (build 6195617); Live Testing
    #         had it on 2026-10-06.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Nightmare_Inputs
    VerifyText    Renewal Notice (days)    timeout=30
    # ---- the lines the Test Agent should end up writing ----
    Gz Read Page
    Gz Read Page    page=2
    Gz Show    Amount
    TypeText    Amount    25000    anchor=3
    Gz Verify    Amount    25000    index=3
    Gz Verify    Amount    99999    index=3    on_mismatch=warn

11 TypeText on a pre-filled field -- stock, then ours (slockard, Renewal Notice)
    [Documentation]    Renewal Notice (days) loads holding 90. Type 24.
    # RECORD: slockard, the Zoo Nightmare Inputs tab. Click Renewal Notice (days), select all and type 24.
    # EXPLAIN: Stock TypeText types where the cursor is: on a field that already holds a value, some builds replace it and some append, and
    #          the step passes either way. Our TypeText empties a filled field first, types, reads the value back and prints VERIFIED-PASS or
    #          CAUGHT-BUG. An earlier build of ours APPENDED on a filled field (9090) in the CRT test; this build fixes it. Say that out
    #          loud: it is the honest version.
    # PROVEN: locally, slockard 10 of 10 typed steps and dev1 3 of 3: the old override appended, the fixed one replaced
    #         (docs/recorder/evidence/override-proof-2026-10-07/). Run again locally on 2026-10-08 with these exact lines: the field held 90,
    #         stock read back 24, ours emptied 90 first and read back 24 VERIFIED-PASS. In CRT job 205089, build 6195635 (override OFF)
    #         stock replaced 5 of 5; build 6195651 (override ON, the old file) appended 5 of 5 (errors ledger e05f886897). In Live Testing on
    #         2026-10-06 stock TypeText APPENDED on the first Amount: 148,500.0015000 (docs/audit/test-agent-pack-2026-10/evidence/live-2026-10-06/img/31-unprompted.png).
    # NOT-YET-RUN: in a CRT build with the fixed override (resources/garzai_typetext_override.robot, 85956ae). The container proof is one build
    #         of job 205089 with EXPERIMENTAL_OVERRIDES on.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Nav Tab    Zoo_Nightmare_Inputs
    VerifyText    Renewal Notice (days)    timeout=30
    ${held}=    GetInputValue    Renewal Notice (days)
    Log To Console    Renewal Notice (days) holds before typing: ${held}
    # ---- STOCK, called by name ----
    QForce.TypeText    Renewal Notice (days)    24
    ${stock}=    GetInputValue    Renewal Notice (days)
    Log To Console    STOCK read back: ${stock} (24 where stock replaces, 9024 or 2490 where it appends)
    # ---- reload so the field holds 90 again, then OURS ----
    Open Nav Tab    Zoo_Nightmare_Inputs
    VerifyText    Renewal Notice (days)    timeout=30
    TypeText    Renewal Notice (days)    24
    Gz Verify    Renewal Notice (days)    24

Restore Stock Recorder
    [Documentation]    Only after recording with the override toggles on: select and run this BEFORE you stop Live Testing.
    # the keyword name is held in a variable so this file also parses when the override Library line is not imported
    ${restore}=    Set Variable    Gz Override Restore
    ${status}    ${restored}=    Run Keyword And Ignore Error    ${restore}
    Log To Console    recorder bundle: ${status} ${restored}

*** Keywords ***
Aura PickList
    [Documentation]    An Aura picklist (class forceInputPicklist: a link with role combobox, options in a popup list). Same
    ...                shape as PickList: the label, the option. The third argument is what the box shows now (--None-- when
    ...                unset; New on the Case Status). Body is the one in tools/recorder/library/garzai_recorder.robot.
    [Arguments]        ${label}    ${value}    ${currentValue}=--None--
    ClickText          ${currentValue}    anchor=${label}
    ClickText          ${value}    partial_match=False
    VerifyText         ${value}    anchor=${label}
