*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/Account/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Record Page    Account    Name    GZREC Northwind Logistics
    # Follow  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickText    Follow    partial_match=False
    # Show more actions  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickText    Show more actions    partial_match=False
    # View Account Hierarchy  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickItem    View Account Hierarchy    tag=button    partial_match=False
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Account Owner  (1 of 25 same-shape controls -- the same lines with the other label)
    VerifyField    Account Owner    <value>
    # Edit Phone  (1 of 22 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Phone    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/Account/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Record Page    Account    Name    GZREC Northwind Logistics
    # Follow  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="More"]/following::button[normalize-space(.)\="Follow"])[1]
    # Show more actions  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Book Appointment"]/following::button[@type\="button"])[1]
    # View Account Hierarchy  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="View Account Hierarchy"]
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Account Owner  (1 of 25 same-shape controls -- the same lines with the other label)
    # (blank field)
    # Edit Phone  (1 of 22 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Phone"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
