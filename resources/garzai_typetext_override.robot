*** Settings ***
Documentation     GarzAI TypeText override (2026-09-18): shadows the library's own TypeText with a
...               clear-then-verify wrapper, shipped as a single RESOURCE file (not a Library) --
...               Robot Framework lets a keyword defined in an imported RESOURCE shadow a LIBRARY
...               keyword of the same name with no ambiguity error, while two LIBRARIES that both
...               publish a keyword named TypeText raise "Multiple keywords with name 'TypeText'
...               found, please use full library name". A Python-library form of this override would
...               hit exactly that the moment QForce/QWeb and the override library were both loaded.
...
...               *** IMPORT THIS RESOURCE TO MAKE EVERY TypeText IN THE SUITE CLEAR-THEN-VERIFY. ***
...               *** COMMENT THE Resource LINE OUT TO GET STOCK QForce/QWeb TypeText BACK.        ***
...
...               Only QForce is explicitly `Library`-imported by resources/common.robot (verified by
...               grepping its Settings section, 2026-09-18) -- every call below to the real, wrapped
...               keyword is therefore fully qualified `QForce.TypeText`, both so it resolves
...               unambiguously and so it does NOT recurse into this same override (an unqualified
...               `TypeText` call from inside this keyword would call itself, not the library).
...               `GetInputValue` and `PressKey` are not shadowed by this file, so they are left
...               unqualified and resolve through the suite's own Library Search Order.
...
...               WHY THIS EXISTS (sources: tools/qforce-lite/qforce_lite.py `type_text_clearing`
...               ~line 1177, its docstring in full; tools/qforce-lite/chains.py `_text_family`
...               ~line 338 and `_m_qweb_type_text_clear_key` ~line 1169; tools/qforce-lite/confirm.py
...               `typed_value`/`lenient_equal`/`CouldNotCheck`; docs/errors/entries/576d7e8859.json):
...               real QWeb TypeText's own documented fix for a pre-populated input, clear_key=
...               {CONTROL + a}, is NOT enough on every Lightning input shape, measured live twice:
...                 1. 2026-07-29: a percent-formatted numeric field (Probability) grew 25% ->
...                    2,025% -> 202,525% across repeated attempts WITH clear_key applied -- the
...                    chord did not clear, so each retry's keystrokes landed on top of the last.
...                 2. 2026-09-10 (error ledger 576d7e8859, slockard Zoo_Forms_Advanced, macOS
...                    holder): neither {CONTROL + a} NOR the macOS {COMMAND + a} variant cleared a
...                    reactive lightning-input at all -- typing "GZREV Phone" into a field already
...                    holding "GZREV Phone" read back "GZREV PhoneGZREV Phone", a plain append, not
...                    a formatting-driven growth. CRT's own TypeText has no answer to either case
...                    beyond the one clear_key chord -- this is the gap the user named ("this is
...                    clearly an area CRT missed").
...               D13 (CLAUDE.md, the repo's own decision log): the repair pass fires ONLY on a
...               BLANK read-back; a NON-blank mismatch is reported and the field is never re-typed.
...               That rule is why the 25% -> 2,025% -> 202,525% growth is a fixable-by-not-retrying
...               bug, not a fixable-by-retrying one: retrying on a non-blank mismatch is exactly how
...               each retyped attempt landed on top of the last.
Library           QForce


*** Keywords ***
TypeText
    [Documentation]    OVERRIDE of the library's own TypeText. clear (real TypeText's own
    ...    clear_key\={CONTROL + a}, merged in unless the caller already passed a clear_key of their
    ...    own) -> type -> read back (GetInputValue) -> lenient-equal pass; on a BLANK read-back only,
    ...    one two-step repair (the macOS clear_key variant, then a raw select-all+backspace+retype);
    ...    on a NON-blank mismatch, a loud FAIL naming expected vs actual -- never a re-type (D13).
    ...    Same signature QForce/QWeb's own TypeText publishes (locator, input_text, anchor=1,
    ...    timeout=0, **kwargs), so importing this resource is a drop-in: no caller changes.
    [Arguments]    ${locator}    ${input_text}    ${anchor}=1    ${timeout}=0    &{kwargs}
    IF    'clear_key' not in $kwargs
        Set To Dictionary    ${kwargs}    clear_key={CONTROL + a}
    END
    QForce.TypeText    ${locator}    ${input_text}    anchor=${anchor}    timeout=${timeout}    &{kwargs}
    ${actual}=    Read Input Value Or Blank    ${locator}    ${anchor}
    ${is_blank}=    Evaluate    $actual in (None, '') or str($actual).strip() == ''
    IF    ${is_blank}
        Log    GarzAI TypeText: blank read-back on '${locator}' after typing '${input_text}' -- running the repair pass (D13: a repair fires only on a blank read-back).    console=True
        # repair 1: the macOS clear_key variant, {COMMAND + a}, as its OWN attempt (never chained
        # onto the failed {CONTROL + a} chord -- error ledger 576d7e8859 measured both failing
        # together on a macOS holder; this is the "smart switch" the user asked for, one variation
        # tried at a time so which one actually worked stays legible in the log above).
        QForce.TypeText    ${locator}    ${input_text}    anchor=${anchor}    timeout=${timeout}    clear_key={COMMAND + a}
        ${actual}=    Read Input Value Or Blank    ${locator}    ${anchor}
        ${is_blank}=    Evaluate    $actual in (None, '') or str($actual).strip() == ''
        IF    ${is_blank}
            # repair 2: the proven raw mechanism (qforce_lite.py type_text_clearing's own repair
            # pass, measured live 2026-07-29/2026-08-30) -- select all, delete, plain retype with no
            # clear_key chord at all.
            PressKey    ${locator}    {CONTROL + a}
            PressKey    ${locator}    {BACKSPACE}
            QForce.TypeText    ${locator}    ${input_text}    anchor=${anchor}    timeout=${timeout}
            ${actual}=    Read Input Value Or Blank    ${locator}    ${anchor}
            ${is_blank}=    Evaluate    $actual in (None, '') or str($actual).strip() == ''
        END
    END
    IF    ${is_blank}
        Fail    GarzAI TypeText('${locator}'): could not read back a value after typing '${input_text}' through two repair passes -- COULD-NOT-CHECK, not a pass.
    END
    ${matches}=    Values Match    ${input_text}    ${actual}
    IF    not ${matches}
        Fail    GarzAI TypeText('${locator}'): value did not land. asked for '${input_text}', field holds '${actual}' -- never re-typed over a non-blank mismatch (D13, CLAUDE.md).
    END
    Log    GarzAI TypeText('${locator}'): read back '${actual}' -- matches '${input_text}'.    console=True


Type Text Select All
    [Documentation]    The clear_key mechanics alone, no read-back -- for a caller that wants only
    ...    real TypeText's own documented select-all-then-type fix without the verification round
    ...    trip the TypeText override above adds. Merges clear_key\={CONTROL + a} in unless the
    ...    caller already passed one of their own.
    [Arguments]    ${locator}    ${input_text}    ${anchor}=1    ${timeout}=0    &{kwargs}
    IF    'clear_key' not in $kwargs
        Set To Dictionary    ${kwargs}    clear_key={CONTROL + a}
    END
    QForce.TypeText    ${locator}    ${input_text}    anchor=${anchor}    timeout=${timeout}    &{kwargs}


Verify Input Value
    [Documentation]    The lenient read-back alone (GetInputValue + Values Match) -- no typing, no
    ...    repair -- for a suite that wants to assert on a value it (or an earlier step) already set.
    [Arguments]    ${locator}    ${expected}    ${anchor}=1
    ${actual}=    GetInputValue    ${locator}    anchor=${anchor}
    ${matches}=    Values Match    ${expected}    ${actual}
    IF    not ${matches}
        Fail    GarzAI Verify Input Value('${locator}'): expected '${expected}', field holds '${actual}'.
    END
    RETURN    ${actual}


Read Input Value Or Blank
    [Documentation]    GetInputValue, but a resolution failure reads back as blank ('') instead of
    ...    raising -- the caller already treats a blank read-back as could-not-check on its own.
    [Arguments]    ${locator}    ${anchor}=1
    ${status}    ${value}=    Run Keyword And Ignore Error    GetInputValue    ${locator}    anchor=${anchor}
    IF    '${status}' == 'FAIL'
        RETURN    ${EMPTY}
    END
    RETURN    ${value}


Values Match
    [Documentation]    Lenient-equal (D13, CLAUDE.md): trim both sides; if BOTH sides, once trimmed,
    ...    look like a number (only digits/separators: 0-9 , . $ % + -), compare DIGITS ONLY so a
    ...    numeric field's own re-render ('25000' rendered back as '25,000.00') still passes. Never
    ...    rescues a blank actual -- TypeText above routes a blank read-back to the repair pass
    ...    instead of calling this. '25' != '202,525%' either way: neither trimmed-string equality
    ...    nor digits-only equality holds.
    [Arguments]    ${expected}    ${actual}
    ${result}=    Evaluate    __import__('re').sub(r'[^0-9.+-]','',str($expected))==__import__('re').sub(r'[^0-9.+-]','',str($actual)) if (__import__('re').fullmatch(r'[\s0-9,.$%+-]+',str($expected).strip()) and __import__('re').fullmatch(r'[\s0-9,.$%+-]+',str($actual).strip())) else str($expected).strip()==str($actual).strip()
    RETURN    ${result}
