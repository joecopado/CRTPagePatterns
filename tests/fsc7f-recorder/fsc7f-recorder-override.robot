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
Library                         ../../resources/garzai_recorder_override.py
Suite Setup                     Setup Browser
Suite Teardown                  Run Keywords    Gz Override Restore    AND    End suite

*** Test Cases ***
Status Before Recording
    ${token}=    JwtAuthenticate    ${client_idFSC}    ${usernameFSC}    ${private_keyFSC}
    JwtLogin
    ${marker}=    Gz Container Marker    # FRESH or REUSED container
    Log To Console    ${marker}
    ${instance}=    GetInstanceUrl
    Gz Override Org    fsc7f
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

Restore Stock Recorder
    # RUN THIS SELECTION before stopping the Live Testing session (Live Testing never runs the Suite Teardown)
    ${restored}=    Gz Override Restore
    Log To Console    recorder bundle: ${restored}
