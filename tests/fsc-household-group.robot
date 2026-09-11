*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/PartyRelationshipGroup/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyRelationshipGroup    Name    Adams Household
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Account  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Adams Household    anchor=Account
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    anchor=1    partial_match=False
    # Record Rollup
    ClickText    Record Rollup    partial_match=False
    # Name  (3 of 14 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Name    Adams Household
    # Edit Name  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Name    tag=button
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickItem    Edit Category    tag=button
    # Edit Type
    ClickItem    Edit Type    tag=button
    # 47 West 13th Street New York, NY 10011 United States
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator 47 West 13th Street New York…) -- see the XPath form
    # ClickText    47 West 13th Street New York, NY 10011 United States    partial_match=False
    # Map of 47 West 13th Street New York NY 10011 United States
    ClickItem    Map of 47 West 13th Street New York NY 10011 United States    tag=iframe    partial_match=False
    # 
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # Log a Call
    ClickItem    LogACall    tag=button
    # View All
    ClickText    View All    partial_match=False
    # 
    # 

XPath form -- /lightning/r/PartyRelationshipGroup/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    PartyRelationshipGroup    Name    Adams Household
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # New Case
    ClickElement    xpath\=//button[@name\="Global.NewCase"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Account  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Adams Household    anchor=Account
    #   (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Party Relationship Group"]/following::a)[1]
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Record Rollup
    ClickElement    xpath\=//a[@id\="flexipage_tab__item"]
    # Name  (3 of 14 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Adams Household    anchor=Name
    # Edit Name  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Name"]/following::a)[1]
    # Category
    # Category -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Category
    ClickElement    xpath\=//button[@title\="Edit Category"]
    # Edit Type
    ClickElement    xpath\=//button[@title\="Edit Type"]
    # 47 West 13th Street New York, NY 10011 United States
    ClickElement    xpath\=//a[@aria-label\="47 West 13th Street
New York, NY 10011
United States"]
    # Map of 47 West 13th Street New York NY 10011 United States
    ClickElement    xpath\=//iframe[@title\="Map of 47 West 13th Street New York NY 10011 United States"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Last Modified By"]/following::a)[1]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Primary Address"]/following::lightning-formatted-address)[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="United States"]/following::lightning-static-map)[1]
