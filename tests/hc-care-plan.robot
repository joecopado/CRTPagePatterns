*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/CarePlan/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CarePlan    Name    Assessment: Diabetes Care Plan for Charles Green
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Case  (1 of 5 same-shape controls -- the same lines with the other label)
    VerifyField    Case    <value>
    #   (1 of 6 same-shape controls -- the same lines with the other label)
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Name  (1 of 19 same-shape controls -- the same lines with the other label)
    VerifyField    Name    <value>
    # Edit Name  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Name    tag=button
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False
    # Show details for Regularly assess the patient's understanding and compliance with medication regimen  (1 of 2 same-shape controls -- the same lines with the other label)
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator Show details for Regularly a…) -- see the XPath form
    # ClickItem    Show details for Regularly assess the patient's understanding and compliance with medication regimen.    tag=a    partial_match=False
    # Regularly assess the patient's understanding and compliance with medication regimen.  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickCheckbox    Regularly assess the patient's understanding and compliance with medication regimen.    on    anchor=1
    # Regularly assess the patient's understanding and compliance with medication regimen.  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickText    Regularly assess the patient's understanding and compliance with medication regimen.    anchor=2    partial_match=False
    #   (1 of 2 same-shape controls -- the same lines with the other label)

XPath form -- /lightning/r/CarePlan/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    CarePlan    Name    Assessment: Diabetes Care Plan for Charles Green
    # New Contact  (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="Edit"]/following::button[@type\="button"])[1]
    # Case  (1 of 5 same-shape controls -- the same lines with the other label)
    # (blank field)
    #   (1 of 6 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Care Plan"]/following::a)[1]
    # Related  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab_carePlan__item"]
    # Name  (1 of 19 same-shape controls -- the same lines with the other label)
    # (blank field)
    # Edit Name  (1 of 13 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Name"]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
    # Show details for Regularly assess the patient's understanding and compliance with medication regimen  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@aria-label\="Show details for Regularly assess the patient's understanding and compliance with medication regimen."]
    # Regularly assess the patient's understanding and compliance with medication regimen.  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//input[@id\="00Ti8000000YEtWEAWinputCheckbox"]
    # Regularly assess the patient's understanding and compliance with medication regimen.  (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@title\="Regularly assess the patient's understanding and compliance with medication regimen."]
    #   (1 of 2 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//*[normalize-space(text())\="Tomorrow"]/following-sibling::*//a
