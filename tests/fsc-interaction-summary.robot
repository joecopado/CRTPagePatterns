*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/InteractionSummary/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InteractionSummary    Name    New Savings Account Discussion    app=Commercial Banking
    # New Contact  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Interaction  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyField    Interaction    ${EMPTY}
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    # Interaction Attendees  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickText    Interaction Attendees    partial_match=False
    # Title  (1 of 11 same-shape controls -- the same lines with the other label)
    VerifyField    Title    New Savings Account Discussion
    # Edit Title  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Title    tag=button
    # Tag Category
    # keyword form measured CAUGHT-BUG live (pick_list trigger xpath found nothing: QWebElementNotFoundError: Unable to find element f…) -- see the XPath form
    # PickList    Tag Category    GZREV Tag Category
    # Interest Tag
    TypeText    Interest Tag    GZREV Interest Tag 1    anchor=1
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InteractionSummary/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InteractionSummary    Name    New Savings Account Discussion    app=Commercial Banking
    # New Contact  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Interaction  (1 of 6 same-shape controls -- the same lines with the other label)
    # (blank field)
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Interaction Summary"]/following::a)[1]
    # Interaction Attendees  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="interactionAttendeeTab__item"]
    # Title  (1 of 11 same-shape controls -- the same lines with the other label)
    VerifyText    New Savings Account Discussion    anchor=Title
    # Edit Title  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Title"]
    # Tag Category
    ClickElement    xpath\=//button[@aria-label\="Tag Category"]
    ClickText    GZREV Tag Category
    # Interest Tag
    TypeText    xpath\=//input[@aria-label\="Interest Tag"]    GZREV Interest Tag 1
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
