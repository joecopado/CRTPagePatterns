*** Settings ***
Documentation       DATA PREPARATION BY API: build the records a test needs in seconds instead of clicking them in.
...                 One Account, two Contacts on it, an Opportunity on it, and a contact role tying one Contact to
...                 the Opportunity -- each record created with the Id of the one it belongs to, so the data points
...                 depend on each other the way real data does. The test proves the set two ways: the database
...                 (queries, including the relationship itself) and the screen (the Account's related lists).
...                 The teardown deletes everything it made, children first, and proves each record is gone.
...                 Org: slockard. CRT variables: ${client_idSlock} ${usernameSlock} ${private_keySlock}.
Resource            ../../resources/common.robot
Resource            ../../resources/data_handling.robot
Suite Setup         Setup Browser
Suite Teardown      End suite


*** Test Cases ***
Build A Related Data Set By API And Prove It
    [Teardown]    Delete Created Records    ${created}
    ${created}=    Create List
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin

    # 1. PREPARE -- parent first, then the records that point at it
    ${account_name}=    FakerLibrary.Company
    ${account_name}=    Remove String    ${account_name}    '
    ${account_id}=    Create Record    Account    Name=${account_name}    Type=Prospect    Industry=Consulting
    Append To List    ${created}    Account:${account_id}

    ${first_1}=    FakerLibrary.First Name
    ${last_1}=    FakerLibrary.Last Name
    ${contact_1}=    Create Record    Contact    AccountId=${account_id}    FirstName=${first_1}    LastName=${last_1}
    Append To List    ${created}    Contact:${contact_1}
    ${first_2}=    FakerLibrary.First Name
    ${last_2}=    FakerLibrary.Last Name
    ${contact_2}=    Create Record    Contact    AccountId=${account_id}    FirstName=${first_2}    LastName=${last_2}
    Append To List    ${created}    Contact:${contact_2}

    ${amount}=    FakerLibrary.Random Int    min=5000    max=50000
    ${close_date}=    Get Current Date    increment=30 days    result_format=%Y-%m-%d
    ${opp_id}=    Create Record    Opportunity    AccountId=${account_id}    Name=${account_name} Renewal
    ...    StageName=Prospecting    CloseDate=${close_date}    Amount=${amount}
    Append To List    ${created}    Opportunity:${opp_id}

    ${role_id}=    Create Record    OpportunityContactRole    OpportunityId=${opp_id}    ContactId=${contact_1}
    ...    Role=Decision Maker    IsPrimary=true
    Append To List    ${created}    OpportunityContactRole:${role_id}

    # 2. PROVE IT IN THE DATABASE -- the counts, and the relationship itself
    ${contacts}=    QueryRecords    SELECT Id FROM Contact WHERE AccountId = '${account_id}'
    Should Be Equal As Integers    ${contacts}[totalSize]    2
    ${role}=    QueryRecords    SELECT Role, Contact.LastName, Opportunity.Account.Name FROM OpportunityContactRole WHERE Id = '${role_id}'
    Should Be Equal    ${role}[records][0][Role]    Decision Maker
    Should Be Equal    ${role}[records][0][Contact][LastName]    ${last_1}
    Should Be Equal    ${role}[records][0][Opportunity][Account][Name]    ${account_name}

    # 3. PROVE IT ON THE SCREEN -- the Account page, then each related list
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/r/Account/${account_id}/view
    VerifyText    ${account_name}    timeout=30
    GoTo    ${instance}/lightning/r/Account/${account_id}/related/Contacts/view
    VerifyText    ${first_1} ${last_1}    timeout=30
    VerifyText    ${first_2} ${last_2}
    GoTo    ${instance}/lightning/r/Account/${account_id}/related/Opportunities/view
    VerifyText    ${account_name} Renewal    timeout=30
