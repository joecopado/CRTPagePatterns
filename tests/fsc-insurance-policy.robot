*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/InsurancePolicy/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicy    Name    4341 Health Platinum    app=Insurance Agent Console
    # New Contact  (1 of 15 same-shape controls -- the same lines with the other label)
    ClickText    New Contact    partial_match=False
    # Show more actions
    ClickText    Show more actions    partial_match=False
    # Effective From Date  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyField    Effective From Date    2026-01-01
    # Related  (1 of 6 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Policy Number  (1 of 49 same-shape controls -- the same lines with the other label)
    VerifyField    Policy Number    4341 Health Platinum
    # Edit Policy Number  (1 of 47 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Policy Number    tag=button
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    # Insurance Policy Billing Information (0)
    # keyword form measured CAUGHT-BUG live (QWebElementNotFoundError: Unable to find element for locator Insurance Policy Billing Inf…) -- see the XPath form
    # ClickText    Insurance Policy Billing Information (0)    partial_match=False
    # Show actions for Insurance Policy Billing Information
    # keyword form measured CAUGHT-BUG live (ClickText resolution landed on a DIFFERENT node) -- see the XPath form
    # ClickText    Show actions for Insurance Policy Billing Information    partial_match=False
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickItem    NewEvent    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/InsurancePolicy/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    InsurancePolicy    Name    4341 Health Platinum    app=Insurance Agent Console
    # New Contact  (1 of 15 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Global.NewContact"]
    # Show more actions
    ClickElement    xpath\=(//*[normalize-space(text())\="New Case"]/following::button[@type\="button"])[1]
    # Effective From Date  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyText    2026-01-01    anchor=Effective From Date
    # Related  (1 of 6 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Policy Number  (1 of 49 same-shape controls -- the same lines with the other label)
    VerifyText    4341 Health Platinum    anchor=Policy Number
    # Edit Policy Number  (1 of 47 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Policy Number"]
    #   (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Name Insured"]/following::a)[1]
    # Insurance Policy Billing Information (0)
    ClickElement    xpath\=(//*[normalize-space(text())\="Audit Term"]/following::a)[1]
    # Show actions for Insurance Policy Billing Information
    ClickElement    xpath\=(//*[normalize-space(text())\="Insurance Policy Billing Information"]/following::a)[1]
    # New Event  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@aria-label\="New Event"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
