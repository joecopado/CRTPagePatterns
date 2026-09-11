*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/AssessmentTask/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    AssessmentTask    Name    PPE Safety Inspection
    # New Contact  (1 of 8 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Task Type  (1 of 2 same-shape controls -- the same lines with the other label)
    VerifyField    Task Type    Inspection Checklist
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Name  (1 of 12 same-shape controls -- the same lines with the other label)
    VerifyField    Name    PPE Safety Inspection
    # Edit Name  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Name    tag=button
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/AssessmentTask/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    AssessmentTask    Name    PPE Safety Inspection
    # New Contact  (1 of 8 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Task Type  (1 of 2 same-shape controls -- the same lines with the other label)
    VerifyText    Inspection Checklist    anchor=Task Type
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Name  (1 of 12 same-shape controls -- the same lines with the other label)
    VerifyText    PPE Safety Inspection    anchor=Name
    # Edit Name  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Assessment Task Definition"]/following::a)[1]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
