*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/CareRequest/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CareRequest    Name    Group Yoga Sessions for Sara Ali    app=Integrated Care Management
    # New Contact  (1 of 15 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Care Request Case  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyField    Care Request Case    <value>
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Member First Name  (1 of 49 same-shape controls -- the same lines with the other label)
    VerifyField    Member First Name    Sara    anchor=2
    # Edit Member First Name  (1 of 47 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Member First Name    tag=button
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/CareRequest/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CareRequest    Name    Group Yoga Sessions for Sara Ali    app=Integrated Care Management
    # New Contact  (1 of 15 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Care Request Case  (1 of 6 same-shape controls -- the same lines with the other label)
    # (blank field)
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Care Request"]/following::a)[1]
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Member First Name  (1 of 49 same-shape controls -- the same lines with the other label)
    VerifyText    Sara    anchor=Member First Name
    # Edit Member First Name  (1 of 47 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Member First Name"]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
