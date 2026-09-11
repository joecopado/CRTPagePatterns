*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 16 steps, 11 controls listed as comments (11 buckets)

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
    # (555) 555−0100 -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # First Name
    # First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit First Name
    ClickItem    Edit First Name    tag=button
    # Edit Middle Name
    ClickItem    Edit Middle Name    tag=button
    # (555) 555−0100 -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity
    ClickText    Activity    anchor=1    partial_match=False
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickItem    NewTask    tag=button
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickItem    LogACall    tag=button
    # More Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # (555) 555−0100 -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # First Name
    # First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit First Name
    ClickElement    xpath\=//button[@title\="Edit First Name"]
    # Edit Middle Name
    ClickElement    xpath\=//button[@title\="Edit Middle Name"]
    # (555) 555−0100 -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Created By"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Last Modified By"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity
    ClickElement    xpath\=//a[@id\="activityTab__item"]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # More Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
