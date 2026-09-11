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
    # New Contact  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Insurance Policy  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    4341 Health Platinum    anchor=Insurance Policy
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    # Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Product
    # Product -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Related  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Benefits
    ClickText    Benefits    partial_match=False
    # Coverage Name  (3 of 24 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Coverage Name    Medical
    # Edit Coverage Name  (3 of 24 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Coverage Name    tag=button
    # Insurance Policy
    # Insurance Policy -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Insurance Policy
    ClickItem    Edit Insurance Policy    tag=button
    # 
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickItem    Edit Category    tag=button
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # Log a Call
    ClickItem    LogACall    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InsurancePolicyCoverage/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicyCoverage    Name    IPC-00000001    app=Insurance Agent Console
    # New Contact  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # New Case
    ClickElement    xpath\=//button[@name\="Global.NewCase"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Insurance Policy  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    4341 Health Platinum    anchor=Insurance Policy
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Insurance Policy Coverage"]/following::a)[1]
    # Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Product
    # Product -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="IPC-00000001"]/following::a)[1]
    # Related  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Benefits
    ClickElement    xpath\=//a[@id\="flexipage_tab__item"]
    # Coverage Name  (3 of 24 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Medical    anchor=Coverage Name
    # Edit Coverage Name  (3 of 24 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Coverage Name"]
    # Insurance Policy
    # Insurance Policy -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Insurance Policy
    ClickElement    xpath\=//button[@title\="Edit Insurance Policy"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Coverage Name"]/following::a)[1]
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickElement    xpath\=//button[@title\="Edit Category"]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
