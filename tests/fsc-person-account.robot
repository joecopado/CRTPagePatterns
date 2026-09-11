*** Settings ***
Resource                      ../resources/common.robot
Resource                      ../resources/garzai_console.robot
Resource                      ../resources/garzai_navigation.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite

# coverage: 0 steps, 41 controls listed as comments (15 buckets)

*** Test Cases ***
Keyword form -- /lightning/r/Account/{id}/view
    # every action a person takes on this page, resolved by what a person sees (label, heading, index)
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    Account    Name    Nigel Adams
    # row 31 (button) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # row 32 (output_field) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # search-box -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Life Events -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Predefined Order -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # All Years -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Birth -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Graduation -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Job -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Marriage -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Relocation -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Car -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Home -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Baby -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Diagnosis -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Retirement -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # POLICIES -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # CLAIMS -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # ACCOUNT DETAILS -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Premium Paid -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # total policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Up for Renewal -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search Policies, Insured Items... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Show only inactive policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All Policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh Alerts -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # refresh -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Post -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Poll -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Question -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Share an update... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Share -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Sort by: -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search this feed... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh this feed -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Dismiss -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # row 71 (button) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK

XPath form -- /lightning/r/Account/{id}/view
    # the same actions through the xpath backup: anchored on unique text, never an absolute path
    # FSC (proposed suffix; values from ~/crt-jwt-credentials/fsc7f) -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    Open Record Page    Account    Name    Nigel Adams
    # row 31 (button) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # row 32 (output_field) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # search-box -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Life Events -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Predefined Order -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # All Years -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # New Event -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Birth -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Graduation -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Job -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Marriage -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Relocation -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Car -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Home -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Baby -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Diagnosis -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Retirement -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # POLICIES -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # CLAIMS -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # ACCOUNT DETAILS -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Premium Paid -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # total policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Up for Renewal -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search Policies, Insured Items... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Show only inactive policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # View All Policies -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh Alerts -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Help -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # refresh -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Post -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Poll -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Question -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Share an update... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Share -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Sort by: -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Search this feed... -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Refresh this feed -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # Dismiss -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
    # row 71 (button) -- not exported: keyword COULD-NOT-CHECK / xpath COULD-NOT-CHECK
