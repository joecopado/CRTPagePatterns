*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 12 steps, 18 controls listed as comments (13 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/Account/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Account    Name    Ben Green    app=Health Cloud Console
    # Slack  (3 of 12 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Slack    partial_match=False
    # Follow
    ClickText    Follow    partial_match=False
    # Edit
    ClickText    Edit    partial_match=False
    # Show more actions
    ClickText    Show more actions    anchor=1    partial_match=False
    # Title  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    # Title -- blank in the highlights panel (nothing to verify)
    # (555) 123-4569  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickText    (555) 123-4569    anchor=1    partial_match=False
    # Phone -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # (555) 123-4569
    ClickText    (555) 123-4569    anchor=2    partial_match=False
    # Mobile -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Email
    # Email -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # ben.green@example.com
    ClickText    ben.green@example.com    partial_match=False
    # Account Owner
    # Account Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # row 42 (link) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Related -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Details -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Upload Files -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Chatter -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    NewTask    tag=button
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event
    ClickItem    NewEvent    tag=button
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Email
    ClickItem    SendEmail    tag=button
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Show details for Routine Check Up Anna Garcia
    ClickItem    Show details for Routine Check Up Anna Garcia    tag=a    partial_match=False
    # Show more actions - Routine Check Up Anna Garcia
    ClickText    Show more actions - Routine Check Up Anna Garcia    partial_match=False
    # row 75 (unknown) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK

XPath form -- /lightning/r/Account/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Account    Name    Ben Green    app=Health Cloud Console
    # Slack  (3 of 12 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Follow
    ClickElement    xpath\=(//*[normalize-space(text())\="Slack in Salesforce"]/following::button[@type\="button"])[1]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Note"]/following::button[@type\="button"])[1]
    # Title  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    # Title -- blank in the highlights panel (nothing to verify)
    # (555) 123-4569  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Phone (2)"]/following::a)[1]
    # Phone -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # (555) 123-4569
    ClickElement    xpath\=(//*[normalize-space(text())\="Phone"]/following::a)[1]
    # Mobile -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Email
    # Email -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # ben.green@example.com
    ClickElement    xpath\=(//*[normalize-space(text())\="Mobile"]/following::a)[1]
    # Account Owner
    # Account Owner -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # row 42 (link) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Related -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Details -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Upload Files -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Chatter -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Task  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@aria-label\="New Task"]
    # No Additional New Task Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # More New Event Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Email
    ClickElement    xpath\=//button[@aria-label\="Email"]
    # More Email Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # More Log a Call Actions -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Show details for Routine Check Up Anna Garcia
    ClickElement    xpath\=//a[@aria-label\="Show details for Routine Check Up Anna Garcia"]
    # Show more actions - Routine Check Up Anna Garcia
    ClickElement    xpath\=//*[normalize-space(text())\="9:30 AM | Oct 1"]/following-sibling::*//a
    # row 75 (unknown) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
