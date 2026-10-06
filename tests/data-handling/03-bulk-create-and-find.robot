*** Settings ***
Documentation       DATA IN BULK: create a batch of records in one block -- here five Leads from the same company --
...                 and find them the way a person would: the "Today's Leads" list view, searched by the company.
...                 A query confirms the database holds exactly five. The teardown deletes the whole batch and
...                 proves each one is gone. Change `${batch_size}` to make the batch bigger; nothing else moves.
...                 Org: slockard. CRT variables: ${client_idSlock} ${usernameSlock} ${private_keySlock}.
Resource            ../../resources/common.robot
Resource            ../../resources/data_handling.robot
Suite Setup         Setup Browser
Suite Teardown      End suite


*** Test Cases ***
Create A Batch Of Leads And Find Them In A List View
    [Teardown]    Delete Created Records    ${created}
    ${created}=    Create List
    Set Test Variable    ${created}
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${batch_size}=    Set Variable    5

    # 1. CREATE THE BATCH -- one shared company ties the batch together; each Lead gets its own name
    ${company}=    FakerLibrary.Company
    ${company}=    Remove String    ${company}    '
    ${last_names}=    Create List
    FOR    ${i}    IN RANGE    ${batch_size}
        ${first}=    FakerLibrary.First Name
        ${last}=    FakerLibrary.Last Name
        ${lead_id}=    Create Record    Lead    FirstName=${first}    LastName=${last}    Company=${company}
        ...    Status=Open - Not Contacted
        Append To List    ${created}    Lead:${lead_id}
        Append To List    ${last_names}    ${last}
    END

    # 2. PROVE IT IN THE DATABASE -- exactly the batch, no more, no fewer
    ${leads}=    QueryRecords    SELECT Id, LastName FROM Lead WHERE Company = '${company}'
    Should Be Equal As Integers    ${leads}[totalSize]    ${batch_size}

    # 3. PROVE IT ON THE SCREEN -- Today's Leads, searched by the company
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/o/Lead/list?filterName\=TodaysLeads    # \= : an unescaped = makes Robot read the URL as a named argument
    VerifyText    Today's Leads    timeout=30
    TypeText    Search this list...    ${company}
    PressKey    Search this list...    {ENTER}
    FOR    ${last}    IN    @{last_names}
        VerifyText    ${last}    timeout=15
    END
