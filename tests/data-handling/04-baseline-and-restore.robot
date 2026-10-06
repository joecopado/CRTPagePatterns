*** Settings ***
Documentation       WHEN THE DATA CANNOT BE DELETED: a test that has to change a record it does not own -- a shared
...                 customer, a configuration row, a record other tests depend on -- takes a BASELINE of the
...                 fields it will touch before it touches them, makes its change through the UI, and its teardown
...                 writes the baseline back by API and proves every field is restored. Nothing is deleted.
...                 So the example runs anywhere, the suite setup creates a stand-in "shared" Account first; in a
...                 real org, point `${shared_id}` at the existing record and drop the stand-in lines.
...                 Org: slockard. CRT variables: ${client_idSlock} ${usernameSlock} ${private_keySlock}.
Resource            ../../resources/common.robot
Resource            ../../resources/data_handling.robot
Resource            ../../resources/garzai_typetext_override.robot    # TypeText clears first and reads back what landed (stock TypeText appends to a filled field)
Suite Setup         Setup Browser
Suite Teardown      End suite


*** Test Cases ***
Change A Shared Record And Restore Its Baseline
    [Teardown]    Run Keywords    Restore Field Baseline    Account    ${shared_id}    &{baseline}
    ...    AND    Delete Created Records    ${created}
    ${created}=    Create List
    Set Test Variable    ${created}
    &{baseline}=    Create Dictionary
    Set Test Variable    &{baseline}
    Set Test Variable    ${shared_id}    ${EMPTY}
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin

    # 0. THE STAND-IN for a record the test does not own -- in a real org, delete the four lines below and set
    #    ${shared_id} to the existing record's Id instead (Set Test Variable    ${shared_id}    <its Id>)
    ${shared_name}=    FakerLibrary.Company
    ${shared_id}=    Create Record    Account    Name=${shared_name}    Industry=Banking    Rating=Warm    Phone=(415) 555-0100
    Append To List    ${created}    Account:${shared_id}
    Set Test Variable    ${shared_id}

    # 1. BASELINE -- read the fields this test will change, before changing them
    ${before}=    QueryRecords    SELECT Industry, Rating, Phone FROM Account WHERE Id = '${shared_id}'
    &{baseline}=    Create Dictionary    Industry=${before}[records][0][Industry]    Rating=${before}[records][0][Rating]
    ...    Phone=${before}[records][0][Phone]
    Set Test Variable    &{baseline}

    # 2. THE TEST'S OWN CHANGE -- through the UI, as a person would make it
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/r/Account/${shared_id}/view
    VerifyText    ${shared_name}    timeout=30
    ClickText    Edit    partial_match=False
    UseModal    On
    PickList    Industry    Consulting
    PickList    Rating    Hot
    TypeText    Phone    (212) 555-0199
    ClickText    Save    partial_match=False
    UseModal    Off
    VerifyText    was saved    timeout=30
    ${changed}=    QueryRecords    SELECT Industry, Rating, Phone FROM Account WHERE Id = '${shared_id}'
    Should Be Equal    ${changed}[records][0][Industry]    Consulting
    Should Be Equal    ${changed}[records][0][Rating]    Hot
    Should Be Equal    ${changed}[records][0][Phone]    (212) 555-0199
    # ... the rest of the test would exercise whatever depends on the changed values ...

