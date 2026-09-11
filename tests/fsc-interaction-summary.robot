*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 16 steps, 7 controls listed as comments (12 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/InteractionSummary/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InteractionSummary    Name    New Savings Account Discussion    app=Commercial Banking
    # New Contact  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Interaction  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # Interaction -- blank in the highlights panel (nothing to verify)
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Interaction Purpose
    # Interaction Purpose -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Interaction Attendees  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Interaction Attendees    partial_match=False
    # Share
    ClickText    Share    partial_match=False
    # Related
    ClickText    Related    anchor=1    partial_match=False
    # Title  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Title    New Savings Account Discussion
    # Edit Title  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Title    tag=button
    # Interaction
    # Interaction -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Interaction
    ClickItem    Edit Interaction    tag=button
    # Meeting Notes
    # Meeting Notes -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Meeting Notes
    ClickItem    Edit Meeting Notes    tag=button
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Tag Category
    # keyword form measured CAUGHT-BUG live (pick_list trigger xpath found nothing: QWebElementNotFoundError: Unable to find element f…) -- see the XPath form
    # PickList    Tag Category    GZREV Tag Category
    # Interest Tag
    TypeText    Interest Tag    GZREV Interest Tag 1    anchor=1
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickItem    NewTask    tag=button
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickItem    LogACall    tag=button
    # No Additional Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InteractionSummary/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InteractionSummary    Name    New Savings Account Discussion    app=Commercial Banking
    # New Contact  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # New Case
    ClickElement    xpath\=//button[@name\="Global.NewCase"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Interaction  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # Interaction -- blank in the highlights panel (nothing to verify)
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Interaction Summary"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Interaction Purpose
    # Interaction Purpose -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Interaction Attendees  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="interactionAttendeeTab__item"]
    # Share
    ClickElement    xpath\=//a[@id\="shareTab__item"]
    # Related
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Title  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    New Savings Account Discussion    anchor=Title
    # Edit Title  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Title"]
    # Interaction
    # Interaction -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Interaction
    ClickElement    xpath\=//button[@title\="Edit Interaction"]
    # Meeting Notes
    # Meeting Notes -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Meeting Notes
    ClickElement    xpath\=//button[@title\="Edit Meeting Notes"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="More Details"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Tag Category
    ClickElement    xpath\=//button[@aria-label\="Tag Category"]
    ClickText    GZREV Tag Category
    # Interest Tag
    TypeText    xpath\=//input[@aria-label\="Interest Tag"]    GZREV Interest Tag 1
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # No Additional Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
