*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/ActionPlan/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    ActionPlan    Name    New Account Opening for Rachel
    # New Contact  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show 7 more actions
    ClickItem    Show 7 more actions    tag=a    partial_match=False
    # Change Owner
    ClickItem    Change Owner    tag=button    partial_match=False
    # Items  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickText    Items    anchor=1    partial_match=False
    # Reorder  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickText    Reorder    anchor=1    partial_match=False
    # Edit Tasks
    ClickItem    Edit Tasks    tag=button

XPath form -- /lightning/r/ActionPlan/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    ActionPlan    Name    New Account Opening for Rachel
    # New Contact  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="New Contact"]
    # Show 7 more actions
    ClickElement    xpath\=//a[@title\="Show 7 more actions"]
    # Change Owner
    ClickElement    xpath\=//button[@title\="Change Owner"]
    # Items  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="Items"]
    # Reorder  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Tasks (1)"]/following::button[@type\="button"])[1]
    # Edit Tasks
    ClickElement    xpath\=//button[@title\="Edit Tasks"]
