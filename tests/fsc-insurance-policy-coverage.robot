*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/InsurancePolicyCoverage/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicyCoverage    Name    IPC-00000001    app=Insurance Agent Console
    # New Contact  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Insurance Policy  (1 of 5 same-shape controls -- the same lines with the other label)
    VerifyField    Insurance Policy    4341 Health Platinum    partial_match=True
    #   (1 of 4 same-shape controls -- the same lines with the other label)
    # Related  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Coverage Name  (1 of 24 same-shape controls -- the same lines with the other label)
    VerifyField    Coverage Name    Medical
    # Edit Coverage Name  (1 of 24 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Coverage Name    tag=button
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InsurancePolicyCoverage/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicyCoverage    Name    IPC-00000001    app=Insurance Agent Console
    # New Contact  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Insurance Policy  (1 of 5 same-shape controls -- the same lines with the other label)
    VerifyText    4341 Health Platinum    anchor=Insurance Policy
    #   (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Insurance Policy Coverage"]/following::a)[1]
    # Related  (1 of 5 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Coverage Name  (1 of 24 same-shape controls -- the same lines with the other label)
    VerifyText    Medical    anchor=Coverage Name
    # Edit Coverage Name  (1 of 24 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Coverage Name"]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
