*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 16 steps, 10 controls listed as comments (10 buckets)

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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Product
    # Product -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickItem    Edit Category    tag=button
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickItem    NewTask    tag=button
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickItem    LogACall    tag=button
    # No Additional Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickText    View All    partial_match=False
    # Cancel and close -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK

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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Name
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Product
    # Product -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="IPC-00000001"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickElement    xpath\=//button[@title\="Edit Category"]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # No Additional Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
    # Cancel and close -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
