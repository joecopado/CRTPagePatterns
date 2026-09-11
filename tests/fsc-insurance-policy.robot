*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/InsurancePolicy/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicy    Name    4341 Health Platinum    app=Insurance Agent Console
    # New Contact  (3 of 15 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Effective From Date  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    2026-01-01    anchor=Effective From Date
    # Effective To Date
    # Effective To Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Premium Amount
    # Premium Amount -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    anchor=1    partial_match=False
    # Split Mgmt
    ClickText    Split Mgmt    partial_match=False
    # Policy Number  (3 of 49 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Policy Number    4341 Health Platinum
    # Edit Policy Number  (3 of 47 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Policy Number    tag=button
    # Name Insured
    # Name Insured -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Name Insured
    ClickItem    Edit Name Insured    tag=button
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    # Policy Name
    # Policy Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Policy Name
    ClickItem    Edit Policy Name    tag=button
    # 
    # 
    # Insurance Policy Billing Information (0)
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator Insurance Policy Billing Inf…) -- see the XPath form
    # ClickText    Insurance Policy Billing Information (0)    partial_match=False
    # Show actions for Insurance Policy Billing Information
    # keyword form measured CAUGHT-BUG live (ClickText resolution landed on a DIFFERENT node) -- see the XPath form
    # ClickText    Show actions for Insurance Policy Billing Information    partial_match=False
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # Log a Call
    ClickItem    LogACall    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InsurancePolicy/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicy    Name    4341 Health Platinum    app=Insurance Agent Console
    # New Contact  (3 of 15 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # New Case
    ClickElement    xpath\=//button[@name\="Global.NewCase"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Effective From Date  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    2026-01-01    anchor=Effective From Date
    # Effective To Date
    # Effective To Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Premium Amount
    # Premium Amount -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Split Mgmt
    ClickElement    xpath\=//a[@id\="flexipage_tab__item"]
    # Policy Number  (3 of 49 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    4341 Health Platinum    anchor=Policy Number
    # Edit Policy Number  (3 of 47 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Policy Number"]
    # Name Insured
    # Name Insured -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Name Insured
    ClickElement    xpath\=//button[@title\="Edit Name Insured"]
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Name Insured"]/following::a)[1]
    # Policy Name
    # Policy Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Policy Name
    ClickElement    xpath\=//button[@title\="Edit Policy Name"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Billing Carrier Account"]/following::a)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Writing Carrier Account"]/following::a)[1]
    # Insurance Policy Billing Information (0)
    ClickElement    xpath\=(//*[normalize-space(text())\="Audit Term"]/following::a)[1]
    # Show actions for Insurance Policy Billing Information
    ClickElement    xpath\=(//*[normalize-space(text())\="Insurance Policy Billing Information"]/following::a)[1]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
