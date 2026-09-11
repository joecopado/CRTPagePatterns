*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 18 steps, 9 controls listed as comments (15 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/Case/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Case    CaseNumber    00001031    app=Health Cloud Console
    # Slack  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Slack    partial_match=False
    # Follow
    ClickText    Follow    partial_match=False
    # Edit
    ClickText    Edit    anchor=1    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Priority  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Medium    anchor=Priority
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Case Number
    # Case Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Feed  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Feed    anchor=1    partial_match=False
    # Related
    ClickText    Related    partial_match=False
    # Post
    ClickText    Post    anchor=1    partial_match=False
    # Most Recent Activity  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Most Recent Activity    partial_match=False
    # Search this feed...
    TypeText    Search this feed...    GZREV Search this feed...
    # Expand all visible posts -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh this feed -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Click to collapse post -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Joseph Garza -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Joseph Garza  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Joseph Garza    anchor=2    partial_match=False
    # August 30, 2026 at 9:30 AM
    ClickText    August 30, 2026 at 9:30 AM    partial_match=False
    # Actions for this Feed Item
    ClickText    Actions for this Feed Item    partial_match=False
    # Comment
    ClickText    Comment    anchor=1    partial_match=False
    # Case Owner  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Case Owner    Joseph Garza    partial_match=True
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Contact Phone
    # Contact Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Case Number
    # Case Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Contact Name  (3 of 14 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Contact Name    tag=button
    # Edit Account Name
    ClickItem    Edit Account Name    tag=button
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Edit Status
    ClickItem    Edit Status    tag=button
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK

XPath form -- /lightning/r/Case/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    Case    CaseNumber    00001031    app=Health Cloud Console
    # Slack  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@data-testid\="open-slack-highlight-button"]
    # Follow
    ClickElement    xpath\=(//*[normalize-space(text())\="Slack in Salesforce"]/following::button[@type\="button"])[1]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Delete"]/following::button[normalize-space(.)\="Show more actions"])[1]
    # Priority  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Medium    anchor=Priority
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Case Number
    # Case Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Feed  (3 of 9 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="collaborateTab__item"]
    # Related
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Post
    ClickElement    xpath\=//a[@title\="Post"]
    # Most Recent Activity  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="Most Recent Activity"]
    # Search this feed...
    TypeText    xpath\=//input[@name\="searchInFeed"]    GZREV Search this feed...
    # Expand all visible posts -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh this feed -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Click to collapse post -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Joseph Garza -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Joseph Garza  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Status Changes"]/following::a[normalize-space(.)\="Joseph Garza"])[1]
    # August 30, 2026 at 9:30 AM
    ClickElement    xpath\=//a[@title\="August 30, 2026 at 9:30 AM"]
    # Actions for this Feed Item
    ClickElement    xpath\=(//*[normalize-space(text())\="Case created"]/following::a)[1]
    # Comment
    ClickElement    xpath\=//a[@title\="Comment"]
    # Case Owner  (3 of 22 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Joseph Garza    anchor=Case Owner
    #   (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Case Owner"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Contact Phone
    # Contact Phone -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Case Number
    # Case Number -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Contact Name  (3 of 14 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Contact Name"]
    # Edit Account Name
    ClickElement    xpath\=//button[@title\="Edit Account Name"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Account Name"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Edit Status
    ClickElement    xpath\=//button[@title\="Edit Status"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Created By"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
