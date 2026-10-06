*** Settings ***
Documentation       INLINE DATA, THROUGH THE UI: the test makes its own record the way a person would, changes it,
...                 and deletes it from the record's own page. Every step is proved twice -- on the screen and by
...                 a query: after the save the record exists with the typed values; after the edit the database
...                 holds the new value; after the delete the page is reloaded and the record is no longer there.
...                 The teardown is a safety net only: if the test stops before its own delete, the API removes
...                 the record so no data is left behind.
...                 Org: slockard. CRT variables: ${client_idSlock} ${usernameSlock} ${private_keySlock}.
Resource            ../../resources/common.robot
Resource            ../../resources/data_handling.robot
Resource            ../../resources/garzai_typetext_override.robot    # TypeText clears first and reads back what landed (stock TypeText appends to a filled field)
Suite Setup         Setup Browser
Suite Teardown      End suite


*** Test Cases ***
Create Update And Delete An Account In The UI
    [Teardown]    Delete Created Records    ${created}
    ${created}=    Create List
    Set Test Variable    ${created}
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl

    # 1. CREATE -- the New Account form, filled and saved
    ${account_name}=    FakerLibrary.Company
    ${account_name}=    Remove String    ${account_name}    '
    GoTo    ${instance}/lightning/o/Account/new
    UseModal    On
    TypeText    Account Name    ${account_name}
    ClickText    Save    partial_match=False
    UseModal    Off
    VerifyText    was created    timeout=30
    VerifyText    ${account_name}
    ${account_id}=    GetRecordIDFromUrl
    Append To List    ${created}    Account:${account_id}
    ${saved}=    QueryRecords    SELECT Name FROM Account WHERE Id = '${account_id}'
    Should Be Equal    ${saved}[records][0][Name]    ${account_name}

    # 2. UPDATE -- edit one field, then read it back on the page and in the database
    # a fixed US shape on purpose: FakerLibrary.Phone Number can add an extension or another format that
    # Salesforce displays differently, and the line after the save checks the value as shown on screen
    ${phone}=    FakerLibrary.Numerify    text=(###) ###-####
    ClickText    Edit    partial_match=False
    UseModal    On
    TypeText    Phone    ${phone}
    ClickText    Save    partial_match=False
    UseModal    Off
    VerifyText    was saved    timeout=30
    VerifyText    ${phone}
    ${updated}=    QueryRecords    SELECT Phone FROM Account WHERE Id = '${account_id}'
    Should Be Equal    ${updated}[records][0][Phone]    ${phone}

    # 3. DELETE -- on the record's own page, from its actions menu, confirmed in the dialog
    GoTo    ${instance}/lightning/r/Account/${account_id}/view
    VerifyText    ${account_name}    timeout=30
    ClickText    Show more actions    partial_match=False
    ClickText    Delete    partial_match=False
    UseModal    On
    VerifyText    Are you sure you want to delete this account?    timeout=15
    ClickText    Delete    partial_match=False
    UseModal    Off
    VerifyText    was deleted    timeout=30

    # 4. REFRESH AND PROVE IT IS GONE -- the record's page again, and the database
    GoTo    ${instance}/lightning/r/Account/${account_id}/view
    VerifyNoText    ${account_name}    timeout=15
    ${gone}=    QueryRecords    SELECT Id FROM Account WHERE Id = '${account_id}'
    Should Be Equal As Integers    ${gone}[totalSize]    0
