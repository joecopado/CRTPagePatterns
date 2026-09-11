*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/FinancialAccount/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    FinancialAccount    Name    Visa Premium Credit Card
    # Edit  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Edit    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show 3 more actions
    ClickItem    Show 3 more actions    tag=a    partial_match=False
    # Financial Account Number  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyField    Financial Account Number    9893-2830-200-1114
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Information  (1 of 6 same-shape controls -- the same lines with the other label)
    ClickText    Information    partial_match=False
    # Name  (1 of 4 same-shape controls -- the same lines with the other label)
    VerifyField    Name    Visa Premium Credit Card
    # Edit Name  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Name    tag=button
    # Log a Call  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickItem    LogACall    tag=button
    # No Additional Log a Call Actions  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickItem    No Additional Log a Call Actions    tag=button    partial_match=False

XPath form -- /lightning/r/FinancialAccount/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    FinancialAccount    Name    Visa Premium Credit Card
    # Edit  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//a[@title\="Delete"]
    # Show 3 more actions
    ClickElement    xpath\=//a[@title\="Show 3 more actions"]
    # Financial Account Number  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyText    9893-2830-200-1114    anchor=Financial Account Number
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Information  (1 of 6 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Details"]/following::button)[1]
    # Name  (1 of 4 same-shape controls -- the same lines with the other label)
    VerifyText    Visa Premium Credit Card    anchor=Name
    # Edit Name  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # Log a Call  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # No Additional Log a Call Actions  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="No Additional Log a Call Actions"]
