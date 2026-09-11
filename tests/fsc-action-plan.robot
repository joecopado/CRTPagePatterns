*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 11 steps, 3 controls listed as comments (8 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/ActionPlan/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    ActionPlan    Name    New Account Opening for Rachel
    # Show Actions Show Actions Show Actions Show Actions -- not exported: keyword not probed / xpath not probed
    # Show Actions Show Actions -- not exported: keyword not probed / xpath not probed
    # New Contact  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # New Case
    ClickText    New Case    partial_match=False
    # Show 7 more actions
    ClickItem    Show 7 more actions    tag=a    partial_match=False
    # Joseph Garza -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner
    ClickItem    Change Owner    tag=button    partial_match=False
    # Items  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Items    anchor=1    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # Reorder  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Reorder    anchor=1    partial_match=False
    # Edit Tasks
    ClickItem    Edit Tasks    tag=button
    # New
    ClickText    New    anchor=1    partial_match=False
    # Reorder
    ClickText    Reorder    anchor=2    partial_match=False

XPath form -- /lightning/r/ActionPlan/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    ActionPlan    Name    New Account Opening for Rachel
    # Show Actions Show Actions Show Actions Show Actions -- not exported: keyword not probed / xpath not probed
    # Show Actions Show Actions -- not exported: keyword not probed / xpath not probed
    # New Contact  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="New Contact"]
    # New Opportunity
    ClickElement    xpath\=//a[@title\="New Opportunity"]
    # New Case
    ClickElement    xpath\=//a[@title\="New Case"]
    # Show 7 more actions
    ClickElement    xpath\=//a[@title\="Show 7 more actions"]
    # Joseph Garza -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner
    ClickElement    xpath\=//button[@title\="Change Owner"]
    # Items  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="Items"]
    # Details
    ClickElement    xpath\=//a[@title\="Details"]
    # Reorder  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Tasks (1)"]/following::button[@type\="button"])[1]
    # Edit Tasks
    ClickElement    xpath\=//button[@title\="Edit Tasks"]
    # New
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit Tasks"]/following::button[@type\="button"])[1]
    # Reorder
    ClickElement    xpath\=(//*[normalize-space(text())\="Document Checklist Items (2)"]/following::button[@type\="button"])[1]
