*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 18 steps, 11 controls listed as comments (14 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/CarePlan/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CarePlan    Name    Assessment: Diabetes Care Plan for Charles Green
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickText    New Contact    partial_match=False
    # New Opportunity
    ClickText    New Opportunity    partial_match=False
    # Edit
    ClickText    Edit    anchor=1    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Case  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    # Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Participant
    # Participant -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    anchor=1    partial_match=False
    # Preview
    ClickText    Preview    anchor=3    partial_match=False
    # Name  (3 of 19 same-shape controls shown; the others take the same lines with their own label)
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Name  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Name    tag=button
    # Description
    # Description -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Description
    ClickItem    Edit Description    tag=button
    # Case
    # Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Case
    ClickItem    Edit Case    tag=button
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Show details for Regularly assess the patient's understanding and compliance with medication regimen  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator Show details for Regularly a…) -- see the XPath form
    # ClickItem    Show details for Regularly assess the patient's understanding and compliance with medication regimen.    tag=a    partial_match=False
    # Regularly assess the patient's understanding and compliance with medication regimen.  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickCheckbox    Regularly assess the patient's understanding and compliance with medication regimen.    on    anchor=1
    # Regularly assess the patient's understanding and compliance with medication regimen.  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Regularly assess the patient's understanding and compliance with medication regimen.    anchor=2    partial_match=False
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    # Show details for Develop a medication schedule or reminder system to help the patient stay on track.
    # keyword form measured CAUGHT-BUG live (inherited from representative row 96: QWebElementNotFoundError: Unable to find element fo…) -- see the XPath form
    # ClickItem    Show details for Develop a medication schedule or reminder system to help the patient stay on track.    tag=a    partial_match=False
    # Develop a medication schedule or reminder system to help the patient stay on track.
    ClickCheckbox    Develop a medication schedule or reminder system to help the patient stay on track.    on    anchor=1
    # Develop a medication schedule or reminder system to help the patient stay on track.
    ClickText    Develop a medication schedule or reminder system to help the patient stay on track.    anchor=2    partial_match=False
    # 

XPath form -- /lightning/r/CarePlan/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CarePlan    Name    Assessment: Diabetes Care Plan for Charles Green
    # New Contact  (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # New Opportunity
    ClickElement    xpath\=//button[@name\="Global.NewOpportunity"]
    # Edit
    ClickElement    xpath\=//button[@name\="Edit"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Case  (3 of 5 same-shape controls shown; the others take the same lines with their own label)
    # Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    #   (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Care Plan"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Participant
    # Participant -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Care Plan"]/following::*[normalize-space(text())\="Participant"])[1]/following::a[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Status
    # Status -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Related  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab_carePlan__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab_carePlan__item"]
    # Preview
    ClickElement    xpath\=//a[@id\="previewTabContent_carePlan__item"]
    # Name  (3 of 19 same-shape controls shown; the others take the same lines with their own label)
    # Name -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Name  (3 of 13 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # Description
    # Description -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Description
    ClickElement    xpath\=//button[@title\="Edit Description"]
    # Case
    # Case -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Case
    ClickElement    xpath\=//button[@title\="Edit Case"]
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Description"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
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
    # Show details for Regularly assess the patient's understanding and compliance with medication regimen  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@aria-label\="Show details for Regularly assess the patient's understanding and compliance with medication regimen."]
    # Regularly assess the patient's understanding and compliance with medication regimen.  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//input[@id\="00Ti8000000YEtWEAWinputCheckbox"]
    # Regularly assess the patient's understanding and compliance with medication regimen.  (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@title\="Regularly assess the patient's understanding and compliance with medication regimen."]
    #   (2 of 2 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//*[normalize-space(text())\="Tomorrow"]/following-sibling::*//a
    # Show details for Develop a medication schedule or reminder system to help the patient stay on track.
    ClickElement    xpath\=//a[@aria-label\="Show details for Develop a medication schedule or reminder system to help the patient stay on track."]
    # Develop a medication schedule or reminder system to help the patient stay on track.
    ClickElement    xpath\=//input[@id\="00Ti8000000YEtZEAWinputCheckbox"]
    # Develop a medication schedule or reminder system to help the patient stay on track.
    ClickElement    xpath\=//a[@title\="Develop a medication schedule or reminder system to help the patient stay on track."]
    # 
    ClickElement    xpath\=//*[normalize-space(text())\="Yesterday"]/following-sibling::*//a
