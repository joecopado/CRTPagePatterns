*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 20 steps, 0 controls listed as comments (10 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/FinancialAccount/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    FinancialAccount    Name    Visa Premium Credit Card
    # Edit  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Edit    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Change Owner
    ClickText    Change Owner    partial_match=False
    # Show 3 more actions
    ClickItem    Show 3 more actions    tag=a    partial_match=False
    # Financial Account Number  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    9893-2830-200-1114    anchor=Financial Account Number
    # Type
    # Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Information  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Information    partial_match=False
    # Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Name    Visa Premium Credit Card
    # Edit Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Name    tag=button
    # Financial Account Number
    # Financial Account Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Financial Account Number
    ClickItem    Edit Financial Account Number    tag=button
    # Type
    # Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Type
    ClickItem    Edit Type    tag=button
    # Activity
    ClickText    Activity    anchor=1    partial_match=False
    # Log a Call  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    LogACall    tag=button
    # No Additional Log a Call Actions  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    No Additional Log a Call Actions    tag=button    partial_match=False
    # Email
    ClickItem    SendEmail    tag=button
    # More Email Actions
    ClickItem    More Email Actions    tag=button    partial_match=False
    # Timeline Settings
    ClickItem    Timeline Settings    tag=button    partial_match=False
    # Refresh
    ClickText    Refresh    partial_match=False
    # Expand All
    ClickText    Expand All    partial_match=False
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/FinancialAccount/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    FinancialAccount    Name    Visa Premium Credit Card
    # Edit  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//a[@title\="Delete"]
    # Change Owner
    ClickElement    xpath\=//a[@title\="Change Owner"]
    # Show 3 more actions
    ClickElement    xpath\=//a[@title\="Show 3 more actions"]
    # Financial Account Number  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    9893-2830-200-1114    anchor=Financial Account Number
    # Type
    # Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Information  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Details"]/following::button)[1]
    # Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Visa Premium Credit Card    anchor=Name
    # Edit Name  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # Financial Account Number
    # Financial Account Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Financial Account Number
    ClickElement    xpath\=//button[@title\="Edit Financial Account Number"]
    # Type
    # Type -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Type
    ClickElement    xpath\=//button[@title\="Edit Type"]
    # Activity
    ClickElement    xpath\=//a[@id\="activityTab__item"]
    # Log a Call  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
    # No Additional Log a Call Actions  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="No Additional Log a Call Actions"]
    # Email
    ClickElement    xpath\=//button[@aria-label\="Email"]
    # More Email Actions
    ClickElement    xpath\=//button[@title\="More Email Actions"]
    # Timeline Settings
    ClickElement    xpath\=//button[@title\="Timeline Settings"]
    # Refresh
    ClickElement    xpath\=//button[@title\="Refresh"]
    # Expand All
    ClickElement    xpath\=//button[@aria-label\="Expand All. Show details for activities in the timeline."]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
