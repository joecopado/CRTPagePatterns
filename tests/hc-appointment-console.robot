*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/ServiceAppointment/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    GoTo    ${login_url}/lightning/r/ServiceAppointment/08pi800000015TtAAI/view

XPath form -- /lightning/r/ServiceAppointment/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # Health Cloud (proposed suffix; values from ~/crt-jwt-credentials/health90) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idHC}    ${usernameHC}    ${private_keyHC}
    JwtLogin
    GoTo    ${login_url}/lightning/r/ServiceAppointment/08pi800000015TtAAI/view
