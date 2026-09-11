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
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Primary Email  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    jsmith96@gmail.com    anchor=Primary Email
    # Primary Phone
    # Primary Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Last Profile Review Date
    # Last Profile Review Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    anchor=1    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Party Profile Name  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Party Profile Name    John Smith
    # Edit Party Profile Name  (3 of 17 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Party Profile Name    tag=button
    # Owner Name
    # Owner Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    # First Name
    # First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit First Name
    ClickItem    Edit First Name    tag=button
    # Edit Middle Name
    ClickItem    Edit Middle Name    tag=button
    # 
    # 
    # Activity
    ClickText    Activity    anchor=1    partial_match=False
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # Log a Call
    ClickItem    LogACall    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/PartyProfile/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyProfile    Name    John Smith
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # New Case
    ClickElement    xpath\=//button[@name\="Global.NewCase"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Primary Email  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    jsmith96@gmail.com    anchor=Primary Email
    # Primary Phone
    # Primary Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Last Profile Review Date
    # Last Profile Review Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Party Profile Name  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    John Smith    anchor=Party Profile Name
    # Edit Party Profile Name  (3 of 17 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Party Profile Name"]
    # Owner Name
    # Owner Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Owner Name"]/following::a)[1]
    # First Name
    # First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit First Name
    ClickElement    xpath\=//button[@title\="Edit First Name"]
    # Edit Middle Name
    ClickElement    xpath\=//button[@title\="Edit Middle Name"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Created By"]/following::a)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Last Modified By"]/following::a)[1]
    # Activity
    ClickElement    xpath\=//a[@id\="activityTab__item"]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
