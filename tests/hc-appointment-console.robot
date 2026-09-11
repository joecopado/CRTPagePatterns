*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 15 steps, 14 controls listed as comments (11 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/ServiceAppointment/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    ServiceAppointment    AppointmentNumber    SA-0001    app=Appointment Management
    # Edit  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Edit    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Clone
    ClickText    Clone    partial_match=False
    # Show more actions  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Show more actions    partial_match=False
    # Owner  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Joseph Garza    anchor=Owner
    #   (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Parent Record
    # Parent Record -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickText    Related    partial_match=False
    # Details
    ClickText    Details    partial_match=False
    # General Information
    ClickText    General Information    partial_match=False
    # Appointment Number  (3 of 35 same-shape controls shown; the others take the same lines with their own label)
    VerifyField    Appointment Number    SA-0001
    # Description
    # Description -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Description  (3 of 28 same-shape controls shown; the others take the same lines with their own label)
    ClickItem    Edit Description    tag=button
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Edit Earliest Start Permitted
    ClickItem    Edit Earliest Start Permitted    tag=button
    # Edit Contact
    ClickItem    Edit Contact    tag=button
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help Source System Identifier
    ClickText    Help Source System Identifier    partial_match=False
    # Help Source System
    ClickText    Help Source System    anchor=1    partial_match=False
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity
    ClickText    Activity    anchor=1    partial_match=False
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickText    View All    partial_match=False
    # row 130 (unknown) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK

XPath form -- /lightning/r/ServiceAppointment/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    ServiceAppointment    AppointmentNumber    SA-0001    app=Appointment Management
    # Edit  (3 of 11 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@name\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Clone
    ClickElement    xpath\=//button[@name\="Clone"]
    # Show more actions  (3 of 4 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Clone"]/following::button[@type\="button"])[1]
    # Owner  (3 of 6 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    Joseph Garza    anchor=Owner
    #   (3 of 10 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Service Appointment"]/following::a)[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Service Appointment"]/following::*[normalize-space(text())\="Account"])[1]/following::a[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Parent Record
    # Parent Record -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # 
    ClickElement    xpath\=(//*[normalize-space(text())\="Service Appointment"]/following::*[normalize-space(text())\="Parent Record"])[1]/following::a[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Related  (3 of 3 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Details
    ClickElement    xpath\=//a[@id\="detailTab__item"]
    # General Information
    ClickElement    xpath\=(//*[normalize-space(text())\="Details"]/following::button)[1]
    # Appointment Number  (3 of 35 same-shape controls shown; the others take the same lines with their own label)
    VerifyText    SA-0001    anchor=Appointment Number
    # Description
    # Description -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Edit Description  (3 of 28 same-shape controls shown; the others take the same lines with their own label)
    ClickElement    xpath\=//button[@title\="Edit Description"]
    # Account
    # Account -- COULD-NOT-CHECK: no SOQL truth for this label (compound, unmapped, or the probe had no record)
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Edit Earliest Start Permitted
    ClickElement    xpath\=//button[@title\="Edit Earliest Start Permitted"]
    # Edit Contact
    ClickElement    xpath\=//button[@title\="Edit Contact"]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Change Owner -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help Source System Identifier
    ClickElement    xpath\=(//*[normalize-space(text())\="Source System Identifier"]/following::button[@type\="button"])[1]
    # Help Source System
    ClickElement    xpath\=(//*[normalize-space(text())\="Source System"]/following::button[@type\="button"])[1]
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Preview -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Activity
    ClickElement    xpath\=//a[@id\="activityTab__item"]
    # Timeline Settings -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
    # row 130 (unknown) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
