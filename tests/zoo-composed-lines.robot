*** Settings ***
Documentation                   2026-09-18: the 29 lines the CRT recorder's pane received with GarzAI composing
...                              (run 4, build d), executed as recorded, values as typed. Then the three keyword
...                              forms the review never reached (COULD-NOT-CHECK) probed on their own, so the
...                              store can promote them from xpath form to label form. Read-only intent: the
...                              page is the Zoo demo LWC; Save is the page's own button.
Resource                        ../resources/common.robot
Library                         ../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  Run Keywords    Gz Override Restore    AND    End suite    # put the stock recorder bundle back: the patch outlives the session on a reused container (measured 2026-09-18)

*** Test Cases ***
Replay The 29 Composed Lines
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    TypeText    xpath\=(//c-zoo-nightmare-inputs//input[@type\="text"])[2]    12
    TypeText    Renewal Notice (days)    24
    TypeText    Amount    234    anchor=1
    TypeText    Amount    234    anchor=2
    TypeText    Amount    345    anchor=3
    TypeText    Approved Budget    234    anchor=1
    TypeText    xpath\=(//*[normalize-space(text())\="to"]/following::input[@type\="text"])[1]    12341234
    TypeText    Start Date    2026-09-15    anchor=1
    TypeText    End Date    2026-09-22    anchor=1
    VerifyText    Integration Checkpoint — Portland Annex
    ClickText    Add Line    anchor=2    partial_match=False
    ClickElement    xpath\=(//*[normalize-space(text())\="Go-Live Support"]/following::button)[1]
    ClickText    Save    anchor=1    partial_match=False
    ClickText    Save    anchor=2    partial_match=False
    ClickText    Save & New    partial_match=False
    DropDown    Territory    Southwest
    ClickElement    xpath\=(//*[normalize-space(text())\="Territory & Coverage"]/following::input[@type\="text"])[1]
    ClickElement    xpath\=(//*[normalize-space(text())\="Coverage Owner"]/following::input[@type\="text"])[1]
    TypeText    xpath\=(//*[normalize-space(text())\="Coverage Owner"]/following::input[@type\="text"])[1]    123
    ClickElement    xpath\=(//*[normalize-space(text())\="Product Lines Covered"]/following::input[@type\="text"])[1]
    ClickText    Agentforce
    ClickElement    xpath\=(//*[normalize-space(text())\="Support Tier"]/following::input[@type\="text"])[1]
    ClickText    Partner Managed
    ClickText    Standard Success
    DropDown    Escalation Regions    EMEA
    DropDown    Escalation Regions    APAC
    ClickText    Upgrade Advisory
    ClickElement    xpath\=//*[normalize-space(text())\="Entitled Services"]/following::*[contains(@class,"zn-arrow-r")][1]
    ClickText    Release Readiness

Probe The Three Unproven Keyword Forms
    # review rows 71, 72, 74: keyword form COULD-NOT-CHECK on 2026-09-11 (the probe never reached them);
    # xpath form VERIFIED-PASS. A pass here promotes each to label form on the next build.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    # row 71: the second Territory-labelled control, a text input under Territory & Coverage
    TypeText    Territory    Cascadia    anchor=2
    ${v71}=    GetInputValue    Territory    anchor=2
    Log To Console    row71 Territory anchor=2 read-back: ${v71}
    # row 72: Coverage Owner, a text input
    TypeText    Coverage Owner    Dana Reyes
    ${v72}=    GetInputValue    Coverage Owner
    Log To Console    row72 Coverage Owner read-back: ${v72}
    # row 74: Support Tier is a combobox input; typing filters, the option click selects
    TypeText    Support Tier    Partner
    ClickText    Partner Managed
    VerifyText    Partner Managed    timeout=5
    Log To Console    row74 Support Tier: typed Partner, clicked Partner Managed, verified

Status After
    ${status}=    Gz Override Status
    Log To Console    ${status}
