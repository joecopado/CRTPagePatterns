*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/ServiceAppointment/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    ServiceAppointment    AppointmentNumber    SA-0001    app=Appointment Management
    # Edit  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickText    Edit    partial_match=False
    # Delete -- commits; run it yourself after checking the form:
    # ClickText    Delete    partial_match=False
    # Show more actions  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickText    Show more actions    partial_match=False
    # Owner  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyField    Owner    Joseph Garza    partial_match=True
    #   (1 of 10 same-shape controls -- the same lines with the other label)
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickText    Related    partial_match=False
    # Appointment Number  (1 of 35 same-shape controls -- the same lines with the other label)
    VerifyField    Appointment Number    SA-0001
    # Edit Description  (1 of 28 same-shape controls -- the same lines with the other label)
    ClickItem    Edit Description    tag=button
    # View All
    ClickText    View All    partial_match=False

XPath form -- /lightning/r/ServiceAppointment/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    Open Record Page    ServiceAppointment    AppointmentNumber    SA-0001    app=Appointment Management
    # Edit  (1 of 11 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@name\="Edit"]
    # Delete -- commits; run it yourself after checking the form:
    # ClickElement    xpath\=//button[@name\="Delete"]
    # Show more actions  (1 of 4 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Clone"]/following::button[@type\="button"])[1]
    # Owner  (1 of 6 same-shape controls -- the same lines with the other label)
    VerifyText    Joseph Garza    anchor=Owner
    #   (1 of 10 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=(//*[normalize-space(text())\="Service Appointment"]/following::a)[1]
    # Related  (1 of 3 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//a[@id\="relatedListsTab__item"]
    # Appointment Number  (1 of 35 same-shape controls -- the same lines with the other label)
    VerifyText    SA-0001    anchor=Appointment Number
    # Edit Description  (1 of 28 same-shape controls -- the same lines with the other label)
    ClickElement    xpath\=//button[@title\="Edit Description"]
    # View All
    ClickElement    xpath\=//a[@title\="Show all past activities in a new tab"]
