*** Settings ***
Documentation                   RECORD ON fsc7f WITH THE GARZAI COMPOSER (build 2026-09-18l). No fsc7f page carries
...                              review rows in this library (it embeds the slockard Zoo page), so every composed line
...                              here is the parser's proposal from a live capture (marked "# unverified: parser
...                              proposal") or a pass-through. The store holds eight fsc7f states from the live review of
...                              18 Sep (Person Account: New Task panel, Change Owner modal, New Case and Edit routed
...                              modals; the list view's New flow; the Digital Lending OmniScript's date picker and
...                              salutation listbox). READ-ONLY intent: open and Cancel, never Save on a real record.
...                              Fresh Live Testing session required; run Gz Container Marker first.
Resource                        ../../resources/common.robot
Resource                        ../../resources/garzai_typetext_override.robot    # comment out to record with stock QWeb TypeText
Resource                        ../../resources/garzai_omni.robot    # Omni Type / Omni Select / Omni Date: the lines build m composes for OmniScript controls (missing until 2026-09-19 12:52: 'No keyword with name Omni Type found')
Library                         ../../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  Run Keywords    Gz Override Restore    AND    End suite

*** Variables ***
${GZ_ON_MISMATCH}    warn    # a TypeText mismatch prints CAUGHT-BUG and keeps going; Gz Mismatch Tally lists them at the end

*** Test Cases ***
Status Before Recording
    Gz Login    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}    # the session id stays in ${GZ_TOKEN}; the console shows only PASS: Gz Login
    ${marker}=    Gz Container Marker    # FRESH or REUSED container
    Log To Console    ${marker}
    ${instance}=    GetInstanceUrl
    Gz Override Org    fsc7f
    #Gz Override Backups    off
    ${status}=    Gz Override Status
    Log To Console    ${status}
    # -- suggested pages, in this order; click Allow on the Chrome prompt when the first page opens --
    # 1. ${instance}/lightning/n/GarzAI_Omni_Launcher      the Digital Lending OmniScript: Next, a date, the salutation listbox
    # 2. an Account record (Person Account)                  New Task, Change Owner (Cancel), New Case (Cancel), Edit (Cancel)
    # 3. ${instance}/lightning/o/Account/list               New -> record type -> Next -> Cancel; the list-view picker
    GoTo    ${instance}/lightning/n/GarzAI_Omni_Launcher
    VerifyText    Applicant    timeout=30

Status After Recording
    ${status}=    Gz Override Status
    Log To Console    ${status}
    Gz Mismatch Tally

Restore Stock Recorder
    # RUN THIS SELECTION before stopping the Live Testing session (Live Testing never runs the Suite Teardown)
    ${restored}=    Gz Override Restore
    Log To Console    recorder bundle: ${restored}

*** Keywords ***
Gz Login
    [Documentation]    JwtAuthenticate + JwtLogin with the session id kept in a global variable and
    ...    NOT returned, so the Live Testing console prints `PASS: Gz Login` instead of the raw
    ...    `PASS: JwtAuthenticate 00D...!AQEA...` line (user, 2026-09-19: the pasted logs carried a live
    ...    session id eight times and tripped a content safeguard twice).
    [Arguments]    ${client_id}    ${username}    ${private_key}
    ${token}=    JwtAuthenticate    ${client_id}    ${username}    ${private_key}
    Set Global Variable    ${GZ_TOKEN}    ${token}
    JwtLogin
    Log    Gz Login: session established for ${username} (token held in \${GZ_TOKEN}, not printed)    console=True
