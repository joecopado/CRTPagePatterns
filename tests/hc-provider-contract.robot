*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/Contract/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Contract    ContractNumber    00000101
    # Navigation Mode
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Click Table Cell    Navigation Mode    anchor=1
    # Name  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    # Start Date
    # End Date
    #   (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    Click Table Cell
    # Start Date  (3 of 21 same-shape controls shown; the others take the same lines with their own label)
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Start Date
    # End Date
    # keyword form measured CAUGHT-BUG live (inherited from representative row 9: Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    End Date
    # Status
    # keyword form measured CAUGHT-BUG live (inherited from representative row 9: Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Status
    # Show Actions  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Show Actions
    # 
    Click Table Cell
    # Show Actions
    # keyword form measured CAUGHT-BUG live (inherited from representative row 12: Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Show Actions
    # 
    Click Table Cell
    # Show Actions
    # keyword form measured CAUGHT-BUG live (inherited from representative row 12: Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Show Actions
    # Date
    # keyword form measured CAUGHT-BUG live (Set Table Cell resolution landed on a DIFFERENT node) -- see the XPath form
    # Set Table Cell    Date
    # Joseph Garza
    Click Table Cell    Joseph Garza
    # 
    Click Table Cell
    # Slack  (3 of 8 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Slack    partial_match=False
    # Open in Slack
    ClickText    Open in Slack    partial_match=False
    # Edit
    ClickText    Edit    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Account Name  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    # Account Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Contract Start Date
    # Contract Start Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # In Approval Process  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    In Approval Process    partial_match=False
    # Activated
    ClickText    Activated    partial_match=False
    # Draft
    ClickText    Draft    partial_match=False
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewEvent    tag=button
    # New Task
    ClickItem    NewTask    tag=button
    # Log a Call
    ClickItem    LogACall    tag=button

XPath form -- /lightning/r/Contract/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Contract    ContractNumber    00000101
    # Navigation Mode
    ClickElement    xpath\=(//*[normalize-space(text())\="New"]/following::lightning-datatable)[1]
    # Name  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//th[@aria-label\="Name"]
    # Start Date
    ClickElement    xpath\=//th[@aria-label\="Start Date"]
    # End Date
    ClickElement    xpath\=//th[@aria-label\="End Date"]
    #   (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="End Date"]/following::a)[1]
    # Start Date  (3 of 21 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Preventive Care Agreement"]/following::td)[1]
    # End Date
    ClickElement    xpath\=(//article[@aria-label\="Contract Payment Agreements"]//td)[2]
    # Status
    ClickElement    xpath\=(//article[@aria-label\="Contract Payment Agreements"]//td)[3]
    # Show Actions  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Preventive Care Agreement"]/following::td[normalize-space(.)\="Show Actions"])[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Preventive Care Agreement"]/following::a)[1]
    # Show Actions
    ClickElement    xpath\=(//*[normalize-space(text())\="12/31/2027, 8:00 AM"]/following::td[normalize-space(.)\="Show Actions"])[1]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="12/31/2027, 8:00 AM"]/following::a)[1]
    # Show Actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Bundled Care Fee Agreement"]/following::td[normalize-space(.)\="Show Actions"])[1]
    # Date
    ClickElement    xpath\=(//*[normalize-space(text())\="New Value"]/following::th)[1]
    # Joseph Garza
    ClickElement    xpath\=//a[@title\="Joseph Garza"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="New"]/following::table)[1]
    # Slack  (3 of 8 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Open in Slack
    ClickElement    xpath\=//button[@name\="OpenSlackRecordChannel"]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Delete"]/following::button[@type\="button"])[1]
    # Account Name  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    # Account Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Contract Start Date
    # Contract Start Date -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # In Approval Process  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="In Approval Process"]
    # Activated
    ClickElement    xpath\=//a[@title\="Activated"]
    # Draft
    ClickElement    xpath\=//a[@title\="Draft"]
    # New Event  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # New Task
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # Log a Call
    ClickElement    xpath\=//button[@aria-label\="Log a Call"]
