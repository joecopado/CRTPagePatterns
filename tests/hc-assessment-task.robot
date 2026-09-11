*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/AssessmentTask/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    AssessmentTask    Name    PPE Safety Inspection
    # New Contact  (3 of 8 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # Edit
    ClickText    Edit    anchor=1    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Task Type  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Inspection Checklist    anchor=Task Type
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Name  (3 of 12 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Name    PPE Safety Inspection
    # Edit Name  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Name    tag=button
    # Task Type
    # Task Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Assessment Task Definition
    # Assessment Task Definition -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Assessment Task Definition
    ClickItem    Edit Assessment Task Definition    tag=button
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    # Edit Parent
    ClickItem    Edit Parent    tag=button
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

XPath form -- /lightning/r/AssessmentTask/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    AssessmentTask    Name    PPE Safety Inspection
    # New Contact  (3 of 8 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Task Type  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Inspection Checklist    anchor=Task Type
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Name  (3 of 12 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    PPE Safety Inspection    anchor=Name
    # Edit Name  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # Task Type
    # Task Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Assessment Task Definition
    # Assessment Task Definition -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Assessment Task Definition
    ClickElement    xpath\=//button[@title\="Edit Assessment Task Definition"]
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Assessment Task Definition"]/following::a)[1]
    # Edit Parent
    ClickElement    xpath\=//button[@title\="Edit Parent"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Parent"]/following::a)[1]
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
