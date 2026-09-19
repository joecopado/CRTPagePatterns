*** Settings ***
Documentation                   EXPERIMENT (2026-09-18): record on the Zoo Nightmare Inputs page with GarzAI composing
...                              the recorder's lines. The Library below runs at parse time, BEFORE Suite Setup opens
...                              the browser: it patches the cloud recorder extension's pushStep call sites to consult
...                              a composer inside this Robot process, which matches each recorded element by DOM
...                              identity against our live-verified rows for the page and answers with our line.
...                              Anything it cannot match passes through unchanged. Read-only: nothing is saved.
Resource                        ../resources/common.robot
Resource                        ../resources/garzai_typetext_override.robot    # comment out to record/run with stock QWeb TypeText
Library                         ../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  Run Keywords    Gz Override Restore    AND    End suite    # put the stock recorder bundle back: the patch outlives the session on a reused container (measured 2026-09-18)

*** Test Cases ***
Record On Zoo With GarzAI Composition
    # Slockard -- the suite's own variables; values live in CRT, never in this file
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${marker}=    Gz Container Marker    # FRESH or REUSED container: does the disk survive between sessions?
    Log To Console    ${marker}
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    ${status}=    Gz Override Status
    Log To Console    ${status}
    # now turn the recorder on in Live Testing and interact with the page; the lines that land in
    # the editor are composed by GarzAI where a row matched, and are the recorder's own otherwise.
    # Afterwards, run `Gz Override Status` again to see every decision the composer made.

Restore Stock Recorder
    # RUN THIS SELECTION before stopping the Live Testing session: Live Testing runs the highlighted
    # steps only and never the Suite Teardown, so the patched extension would outlive the session on a
    # reused container (measured 2026-09-18: a stock recording got the Allow prompt).
    ${restored}=    Gz Override Restore
    Log To Console    recorder bundle: ${restored}
