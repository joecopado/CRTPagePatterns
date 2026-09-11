*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/Account/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Account    Name    Ben Green    app=Health Cloud Console
    # Slack  (1 of 12 same-shape controls -- the same lines with the other label)
    ClickText    Slack    partial_match=False
    # Show more actions
    ClickText    Show more actions    anchor=1    partial_match=False
    # Title  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyField    Title    ${EMPTY}
    # (555) 123-4569  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickText    (555) 123-4569    anchor=1    partial_match=False
    # New Task  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewTask    tag=button
    # Show details for Routine Check Up Anna Garcia
    ClickItem    Show details for Routine Check Up Anna Garcia    tag=a    partial_match=False
    # Show more actions - Routine Check Up Anna Garcia
    ClickText    Show more actions - Routine Check Up Anna Garcia    partial_match=False

XPath form -- /lightning/r/Account/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Account    Name    Ben Green    app=Health Cloud Console
    # Slack  (1 of 12 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Note"]/following::button[@type\="button"])[1]
    # Title  (1 of 3 same-shape controls -- the same lines with the other label)
    # (blank field)
    # (555) 123-4569  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Phone (2)"]/following::a)[1]
    # New Task  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Show details for Routine Check Up Anna Garcia
    ClickElement    xpath\=//a[@aria-label\="Show details for Routine Check Up Anna Garcia"]
    # Show more actions - Routine Check Up Anna Garcia
    ClickElement    xpath\=//*[normalize-space(text())\="9:30 AM | Oct 1"]/following-sibling::*//a
