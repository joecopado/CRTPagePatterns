*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

*** Test Cases ***
Keyword form -- /lightning/r/InteractionSummary/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    GoTo    ${login_url}/lightning/r/InteractionSummary/8BVhk000000TLnRGAW/view

XPath form -- /lightning/r/InteractionSummary/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    GoTo    ${login_url}/lightning/r/InteractionSummary/8BVhk000000TLnRGAW/view
