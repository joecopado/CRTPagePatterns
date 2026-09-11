*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/Case/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Case    CaseNumber    00001031    app=Health Cloud Console
    # Slack  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickText    Slack    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Priority  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyField    Priority    Medium
    # Feed  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickText    Feed    anchor=1    partial_match=False
    # Most Recent Activity  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickText    Most Recent Activity    partial_match=False
    # Search this feed...
    TypeText    Search this feed...    GZREV Search this feed...
    # Joseph Garza  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickText    Joseph Garza    anchor=2    partial_match=False
    # Actions for this Feed Item
    ClickText    Actions for this Feed Item    partial_match=False
    # Case Owner  (1 of 22 same-shape controls -- the same lines with the other label)
    VerifyField    Case Owner    Joseph Garza    partial_match=True
    #   (1 of 4 same-shape controls -- the same lines with the other label)
    # Edit Contact Name  (1 of 14 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Contact Name    tag=button

XPath form -- /lightning/r/Case/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Case    CaseNumber    00001031    app=Health Cloud Console
    # Slack  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Delete"]/following::button[normalize-space(.)\="Show more actions"])[1]
    # Priority  (1 of 3 same-shape controls -- the same lines with the other label)
    VerifyText    Medium    anchor=Priority
    # Feed  (1 of 9 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="collaborateTab__item"]
    # Most Recent Activity  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="Most Recent Activity"]
    # Search this feed...
    TypeText    xpath\=//input[@name\="searchInFeed"]    GZREV Search this feed...
    # Joseph Garza  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Status Changes"]/following::a[normalize-space(.)\="Joseph Garza"])[1]
    # Actions for this Feed Item
    ClickElement    xpath\=(//*[normalize-space(text())\="Case created"]/following::a)[1]
    # Case Owner  (1 of 22 same-shape controls -- the same lines with the other label)
    VerifyText    Joseph Garza    anchor=Case Owner
    #   (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Case Owner"]/following::a)[1]
    # Edit Contact Name  (1 of 14 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Contact Name"]
