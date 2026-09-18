*** Settings ***
Documentation                   EXPERIMENT (2026-09-18): record on the Zoo Nightmare Inputs page with GarzAI composing
...                              the recorder's lines. The Library below runs at parse time, BEFORE Suite Setup opens
...                              the browser: it patches the cloud recorder extension's pushStep call sites to consult
...                              a composer inside this Robot process, which matches each recorded element by DOM
...                              identity against our live-verified rows for the page and answers with our line.
...                              Anything it cannot match passes through unchanged. Read-only: nothing is saved.
Resource                        ../resources/common.robot
Library                         ../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  End suite

*** Test Cases ***
Record On Zoo With GarzAI Composition
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    ${status}=    Gz Override Status
    Log To Console    ${status}
    # now turn the recorder on in Live Testing and interact with the page; the lines that land in
    # the editor are composed by GarzAI where a row matched, and are the recorder's own otherwise.
    # Afterwards, run `Gz Override Status` again to see every decision the composer made.
