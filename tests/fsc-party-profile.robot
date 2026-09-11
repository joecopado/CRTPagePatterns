*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/PartyProfile/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyProfile    Name    John Smith
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Primary Email  (1 of 4 same-shape controls -- the same lines with the other label)
    VerifyField    Primary Email    jsmith96@gmail.com
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Related    anchor=1    partial_match=False
    # Party Profile Name  (1 of 22 same-shape controls -- the same lines with the other label)
    VerifyField    Party Profile Name    John Smith
    # Edit Party Profile Name  (1 of 17 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Party Profile Name    tag=button
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/PartyProfile/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyProfile    Name    John Smith
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Primary Email  (1 of 4 same-shape controls -- the same lines with the other label)
    VerifyText    jsmith96@gmail.com    anchor=Primary Email
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Party Profile Name  (1 of 22 same-shape controls -- the same lines with the other label)
    VerifyText    John Smith    anchor=Party Profile Name
    # Edit Party Profile Name  (1 of 17 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Party Profile Name"]
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Owner Name"]/following::a)[1]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
