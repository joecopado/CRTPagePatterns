*** Settings ***
Documentation     URL-first navigation for CRT (GarzAI, 2026-09-11; user: "make this URL thing stable, solid,
...               capable, dynamic"). Nothing here hard-codes an instance, an app id or a record id: the instance comes
...               from GetInstanceUrl after JwtLogin, the app from its LABEL through AppDefinition, the record from its
...               name-field value through SOQL (QueryRecords). Every keyword reads the landing back from the URL.
...               UNMEASURED in CRT until a build runs it; the URL shapes are the ones the GarzAI loop drove live.
Library           QWeb
Library           QForce


*** Keywords ***
Resolve App Prefix
    [Documentation]    "" when no app is named; otherwise "/app/<DurableId>" for the Lightning app with that label.
    ...                A label that matches nothing or several apps fails with the count, never a guess.
    [Arguments]    ${app}=${EMPTY}
    IF    '${app}' == ''    RETURN    ${EMPTY}
    ${q}=    QueryRecords    SELECT DurableId, Label FROM AppDefinition WHERE Label = '${app}' AND UiType = 'Lightning'
    Should Be True    ${q}[totalSize] == 1    msg=App "${app}": ${q}[totalSize] Lightning apps carry that label (want exactly 1)
    RETURN    /app/${q}[records][0][DurableId]


Resolve Record Id
    [Documentation]    The 18-char Id of the ONE ${object} whose ${name_field} equals ${value} (Name, CaseNumber,
    ...                ContractNumber ... -- the object's name field, which the exporter takes from the org layer).
    ...                Zero or several matches fail with the count.
    [Arguments]    ${object}    ${name_field}    ${value}
    ${q}=    QueryRecords    SELECT Id FROM ${object} WHERE ${name_field} = '${value}' LIMIT 2
    Should Be True    ${q}[totalSize] == 1    msg=${object} where ${name_field} = "${value}": ${q}[totalSize] records (want exactly 1)
    RETURN    ${q}[records][0][Id]


Verify Landed On
    [Documentation]    The browser's URL contains ${fragment} within ${timeout} s -- the read-back every navigation
    ...                keyword here ends with (a GoTo that "worked" on the wrong host or a redirected record is the
    ...                plausible-looking success this catches).
    [Arguments]    ${fragment}    ${timeout}=30
    Wait Until Keyword Succeeds    ${timeout}s    0.5s    Url Should Contain    ${fragment}


Url Should Contain
    [Documentation]    One read of the browser URL compared with ${fragment}; Verify Landed On retries it.
    [Arguments]    ${fragment}
    ${url}=    GetUrl
    Should Contain    ${url}    ${fragment}    msg=Did not land on "${fragment}"; URL is ${url}


Open Record Page
    [Documentation]    Open a record by its name-field value, optionally inside a named app (a console app opens it
    ...                as a workspace tab). Example: Open Record Page    Case    CaseNumber    00001031    app=Health Cloud Console
    [Arguments]    ${object}    ${name_field}    ${value}    ${app}=${EMPTY}    ${action}=view
    ${base}=    GetInstanceUrl
    ${prefix}=    Resolve App Prefix    ${app}
    ${id}=    Resolve Record Id    ${object}    ${name_field}    ${value}
    GoTo    ${base}/lightning${prefix}/r/${object}/${id}/${action}
    Verify Landed On    /${id}/${action}


Open Object Page
    [Documentation]    Open an object's list, new form or home: Open Object Page    Contact    new    app=Sales
    [Arguments]    ${object}    ${action}=list    ${app}=${EMPTY}
    ${base}=    GetInstanceUrl
    ${prefix}=    Resolve App Prefix    ${app}
    GoTo    ${base}/lightning${prefix}/o/${object}/${action}
    Verify Landed On    /o/${object}/${action}


Open Nav Tab
    [Documentation]    Open a custom tab (a Lightning page / Visualforce tab) by its API name: Open Nav Tab    Zoo_Nightmare_Inputs
    [Arguments]    ${tab}    ${app}=${EMPTY}
    ${base}=    GetInstanceUrl
    ${prefix}=    Resolve App Prefix    ${app}
    GoTo    ${base}/lightning${prefix}/n/${tab}
    Verify Landed On    /n/${tab}


Open Lightning Path
    [Documentation]    The fallback: any path under the instance, verbatim (kept for pages the other keywords cannot name).
    [Arguments]    ${path}
    ${base}=    GetInstanceUrl
    GoTo    ${base}${path}
    Verify Landed On    ${path}
