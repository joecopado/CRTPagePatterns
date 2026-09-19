*** Settings ***
Documentation                   SETUP RECORDING PROBE, OVERRIDE (2026-09-18): the same Setup steps with the
...                              GarzAI composer patched into the recorder (build 2026-09-18h). Setup pages have
...                              NO review rows, so every composed line here is the parser's proposal from a live
...                              capture, marked "# unverified: parser proposal", or a pass-through. The Permission
...                              Sets content is Visualforce inside an iframe: this is the first live test of the
...                              composer across that boundary. Fresh Live Testing session required (a refresh
...                              reconnects the old container). READ-ONLY: never Save on a Setup page.
Resource                        ../../resources/common.robot
Library                         ../../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Setup Pages With The GarzAI Composer
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    Gz Override Org    slockard
    ${status}=    Gz Override Status
    Log To Console    ${status}
    GoTo    ${instance}/lightning/setup/PermSets/home
    VerifyText    Permission Sets    timeout=30
    # -- turn the recorder ON here and follow the run sheet; click Allow on the Chrome prompt first --

Status After Recording
    ${status}=    Gz Override Status
    Log To Console    ${status}
