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
    # New Contact  (3 of 15 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # Edit
    ClickText    Edit    anchor=1    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Care Request Case  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # Care Request Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    # Member ID
    # Member ID -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Member First Name
    # Member First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Member First Name  (3 of 49 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Member First Name    Sara    anchor=2
    # Edit Member First Name  (3 of 47 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Member First Name    tag=button
    # Member Last Name
    # Member Last Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Member Last Name
    ClickItem    Edit Member Last Name    tag=button
    # Member ID
    # Member ID -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Member ID
    ClickItem    Edit Member ID    tag=button
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

XPath form -- /lightning/r/CareRequest/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CareRequest    Name    Group Yoga Sessions for Sara Ali    app=Integrated Care Management
    # New Contact  (3 of 15 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Care Request Case  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # Care Request Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Care Request"]/following::a)[1]
    # Member ID
    # Member ID -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Member First Name
    # Member First Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Member First Name  (3 of 49 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Sara    anchor=Member First Name
    # Edit Member First Name  (3 of 47 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Member First Name"]
    # Member Last Name
    # Member Last Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Member Last Name
    ClickElement    xpath\=//button[@title\="Edit Member Last Name"]
    # Member ID
    # Member ID -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Member ID
    ClickElement    xpath\=//button[@title\="Edit Member ID"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Source System Identifier"]/following::a)[1]
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
