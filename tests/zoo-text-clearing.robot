*** Settings ***
Documentation     2026-09-18: the clearing variations CRT's own TypeText misses, driven live on the
...               Zoo Nightmare Inputs page's reactive inputs (the page the user calls "the nightmare
...               inputs page"). Each test types a baseline value first, then retypes a DIFFERENT
...               value into the same field -- an honest append shows up immediately as the two
...               numbers concatenated (24 into a field holding 90 reads back '9024', not '24').
...
...               resources/garzai_typetext_override.robot is imported below; comment that ONE line
...               out and every bare `TypeText` call in this file reverts to stock QForce/QWeb
...               TypeText for the whole suite -- both test cases under "With The Override" would
...               then append exactly like "Baseline" does. Each test that wants to show the stock,
...               override-free behaviour WITHOUT commenting the import out calls the fully qualified
...               `QForce.TypeText` directly instead (that bypasses the override on purpose, since a
...               Resource import is file-scoped and cannot be toggled per test case) -- the two paths
...               are documented against each other line by line below.
...
...               Sources (see resources/garzai_typetext_override.robot's own Documentation for the
...               full citation list): tools/qforce-lite/qforce_lite.py `type_text_clearing` (the
...               25% -> 2,025% -> 202,525% growth, 2026-07-29); docs/errors/entries/576d7e8859.json
...               (neither {CONTROL + a} nor {COMMAND + a} cleared a reactive input, 2026-09-10).
Resource          ../resources/common.robot
# Comment the line below out to restore stock QForce/QWeb TypeText for every BARE `TypeText` call
# in this file (the explicit `QForce.TypeText` calls below are unaffected either way -- they always
# bypass this override on purpose, to make the "no override" case visible without a second file).
Resource          ../resources/garzai_typetext_override.robot
Suite Setup       Setup Browser
Suite Teardown    End suite


*** Test Cases ***
Baseline -- Stock TypeText Appends On Renewal Notice (days)
    [Documentation]    The documented known failure, reproduced deliberately: real QForce/QWeb
    ...    TypeText's own clear_key fix is not engaged here at all -- QForce.TypeText is called FULLY
    ...    QUALIFIED so it bypasses the override resource above regardless of whether that Resource
    ...    line is commented out. Renewal Notice (days) has no sibling with the same label
    ...    (group_size null, review.json row 43), so this is the plainest possible reproduction: one
    ...    field, one label, two writes.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    # baseline value
    QForce.TypeText    Renewal Notice (days)    90
    # the retype CRT's own TypeText was measured to append, not clear -- watch the console line below
    QForce.TypeText    Renewal Notice (days)    24
    ${actual}=    GetInputValue    Renewal Notice (days)
    Log To Console    Baseline (no override): Renewal Notice (days) reads back '${actual}' after typing 90 then 24 -- an append reads '9024', a clean clear reads '24'.


With The Override -- TypeText Clears First On Renewal Notice (days)
    [Documentation]    The SAME field, the SAME two values, this time through the bare `TypeText`
    ...    keyword -- which resolves to the override in resources/garzai_typetext_override.robot as
    ...    long as that Resource line above stays uncommented. The override clears (real TypeText's
    ...    own clear_key\={CONTROL + a}), reads back, and would FAIL LOUDLY on a non-blank mismatch
    ...    rather than silently reporting a pass on an appended value (D13: it never re-types over a
    ...    mismatch, so a genuine failure here stops the suite instead of reading back plausible).
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    # same baseline, still via the qualified call so the field starts non-blank on purpose
    QForce.TypeText    Renewal Notice (days)    90
    # the overridden TypeText: clear -> type -> read back -> lenient-equal pass or a loud, named FAIL
    TypeText    Renewal Notice (days)    24
    ${actual}=    Verify Input Value    Renewal Notice (days)    24
    Log To Console    With override: Renewal Notice (days) reads back '${actual}' -- matches '24', the old '90' is gone.


With The Override -- Amount anchor=1..3 (the page's three same-label reactive inputs)
    [Documentation]    review.json rows 44-46: 'Amount' repeats 3 times on this page with identical
    ...    shape (group_size 3), disambiguated by QWeb's numeric anchor. Same baseline-then-retype
    ...    proof as above, once per member, all through the override.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    FOR    ${idx}    IN RANGE    1    4
        QForce.TypeText    Amount    90    anchor=${idx}
        TypeText    Amount    24    anchor=${idx}
        ${v}=    Verify Input Value    Amount    24    anchor=${idx}
        Log To Console    Amount anchor=${idx} reads back '${v}' after 90 then 24 through the override.
    END


Type Text Select All -- The clear_key Mechanics Alone, No Read-Back
    [Documentation]    The lighter level: real TypeText's own documented clear_key fix, merged in
    ...    automatically, with no verification round trip. Useful for a caller that wants the
    ...    select-all-then-type mechanics and will check the result itself (as the next line here
    ...    does, explicitly, through Verify Input Value -- composing the two levels is the point).
    ...    Approved Budget (review.json rows 47-48, group_size 2) is the target so this exercises a
    ...    disambiguated member too, not just the singular Renewal Notice field above.
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}
    JwtLogin
    ${instance}=    GetInstanceUrl
    GoTo    ${instance}/lightning/n/Zoo_Nightmare_Inputs
    VerifyText    Nightmare    timeout=30
    QForce.TypeText    Approved Budget    130000    anchor=1
    Type Text Select All    Approved Budget    75000    anchor=1
    ${v}=    Verify Input Value    Approved Budget    75000    anchor=1
    Log To Console    Approved Budget anchor=1 reads back '${v}' after Type Text Select All (no built-in read-back -- this line checked it separately).
