*** Settings ***
Documentation             The shared teardown for the data-handling examples (tests/data-handling/). Each test keeps
...                       its own list `${created}` of "SObject:Id" entries -- one `Append To List` after every
...                       `Create Record` -- and its [Teardown] hands that list here. QForce's own record keywords,
...                       on the session the test's JwtAuthenticate opened.
Library                   QForce
Library                   Collections
Library                   String


*** Keywords ***
Delete Created Records
    [Documentation]       TEARDOWN: delete every record the test created, newest first (children before their
    ...                   parents), and prove each one is gone with a query. A record the test already deleted
    ...                   itself (in the UI) is skipped, not failed -- the query says it is gone either way.
    [Arguments]           ${created}
    ${count}=             Get Length    ${created}
    FOR    ${i}    IN RANGE    ${count}-1    -1    -1
        ${sobject}    ${record_id}=    Split String    ${created}[${i}]    :
        ${found}=         QueryRecords    SELECT Id FROM ${sobject} WHERE Id = '${record_id}'
        IF    ${found}[totalSize] > 0
            Delete Record    ${sobject}    ${record_id}
        END
        ${after}=         QueryRecords    SELECT Id FROM ${sobject} WHERE Id = '${record_id}'
        Should Be Equal As Integers    ${after}[totalSize]    0    ${sobject} ${record_id} still exists after the teardown
        Log To Console    teardown: ${sobject} ${record_id} deleted, a query confirms it is gone
    END

Restore Field Baseline
    [Documentation]       TEARDOWN for data the test may change but may not delete: write each field back to the
    ...                   value it held before the test (`&{baseline}`, read by a query before the change), then
    ...                   query again and prove every field is restored. An empty baseline (the test stopped
    ...                   before it read one) restores nothing.
    [Arguments]           ${sobject}    ${record_id}    &{baseline}
    ${size}=              Get Length    ${baseline}
    IF    ${size} == 0
        Log To Console    baseline: nothing to restore (no baseline was read)
        RETURN
    END
    Update Record         ${sobject}    ${record_id}    &{baseline}
    ${fields}=            Get Dictionary Keys    ${baseline}
    ${field_list}=        Catenate    SEPARATOR=,${SPACE}    @{fields}
    ${after}=             QueryRecords    SELECT ${field_list} FROM ${sobject} WHERE Id = '${record_id}'
    FOR    ${field}    IN    @{fields}
        Should Be Equal    ${after}[records][0][${field}]    ${baseline}[${field}]    ${field} was not restored
    END
    Log To Console        baseline restored on ${sobject} ${record_id}: ${field_list}
