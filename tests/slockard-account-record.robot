*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 17 steps, 0 controls listed as comments (8 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/Account/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Record Page    Account    Name    GZREC Northwind Logistics
    # Follow  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Follow    partial_match=False
    # Edit
    ClickText    Edit    anchor=1    partial_match=False
    # Create New Product Request
    ClickText    Create New Product Request    partial_match=False
    # Show more actions  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Show more actions    partial_match=False
    # View Account Hierarchy  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    View Account Hierarchy    tag=button    partial_match=False
    # Preview
    ClickItem    Preview    tag=button    anchor=1    partial_match=False
    # Change Owner
    ClickItem    Change Owner    tag=button    anchor=1    partial_match=False
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Account Owner  (3 of 25 same-shape controls shown; the others take the same lines with their own label)
    # Account Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone
    # Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Phone  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Phone    tag=button
    # Account Name
    # Account Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Account Name
    ClickItem    Edit Account Name    tag=button
    # Edit Fax
    ClickItem    Edit Fax    tag=button
    # Help Contract Co-Termination
    ClickText    Help Contract Co-Termination    partial_match=False
    # Help Price Hold End
    ClickText    Help Price Hold End    partial_match=False
    # Activity
    ClickText    Activity    anchor=1    partial_match=False
    # New Task
    ClickItem    NewTask    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/Account/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    Open Record Page    Account    Name    GZREC Northwind Logistics
    # Follow  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="More"]/following::button[normalize-space(.)\="Follow"])[1]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Create New Product Request
    ClickElement    xpath\=//button[@name\="Global.new_product_request"]
    # Show more actions  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Book Appointment"]/following::button[@type\="button"])[1]
    # View Account Hierarchy  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="View Account Hierarchy"]
    # Preview
    ClickElement    xpath\=//records-highlights2//button[@title\="Preview"]
    # Change Owner
    ClickElement    xpath\=//records-highlights2//button[@title\="Change Owner"]
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # Account Owner  (3 of 25 same-shape controls shown; the others take the same lines with their own label)
    # Account Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Phone
    # Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Phone  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Phone"]
    # Account Name
    # Account Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Account Name
    ClickElement    xpath\=//button[@title\="Edit Account Name"]
    # Edit Fax
    ClickElement    xpath\=//button[@title\="Edit Fax"]
    # Help Contract Co-Termination
    ClickElement    xpath\=(//*[normalize-space(text())\="Contract Co-Termination"]/following::button[@type\="button"])[1]
    # Help Price Hold End
    ClickElement    xpath\=(//*[normalize-space(text())\="Price Hold End"]/following::button[@type\="button"])[1]
    # Activity
    ClickElement    xpath\=//a[@id\="activityTab__item"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
