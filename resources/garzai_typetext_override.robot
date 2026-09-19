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
Library           Collections    # Set To Dictionary below; measured missing in Live Testing 2026-09-19 (every TypeText failed "No keyword with name 'Set To Dictionary' found")
Resource          ${CURDIR}/garzai_data.robot    # Gz Sentinel Verdict: a read-back that IS a sentinel is CAUGHT-BUG, never a quiet pass

*** Variables ***
# THE STEP IS THE ACTION; THE VERDICT IS AN OBSERVATION (user, 2026-09-19: "validations should be
# outside of the executed steps ... when a test step fails I have to click Stop, rehighlight,
# re-execute"). Default `warn`: TypeText types, reads back, prints the verdict WITH the actual
# value to the console (VERIFIED-PASS / CAUGHT-BUG / COULD-NOT-CHECK), keeps it in
# @{GZ_MISMATCHES}, and NEVER stops the run. `Gz Mismatch Tally` prints the list at the end.
# A build that wants the step itself to fail on a mismatch sets `${GZ_ON_MISMATCH}    fail` in its
# Variables, or asserts with the separate `Verify Input Value` line after the step.
${GZ_ON_MISMATCH}    warn
@{GZ_MISMATCHES}


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
        Gz Report Mismatch    COULD-NOT-CHECK    GarzAI TypeText('${locator}'): could not read back a value after typing '${input_text}' through two repair passes -- not a pass.
        RETURN
    END
    # THE SENTINEL-LANDED VERDICT (build n7, 2026-09-19). Checked BEFORE Values Match, because a
    # sentinel that was typed AND read back matches itself perfectly: `Values Match` would return
    # true and this would print VERIFIED-PASS over a record now holding the literal `asdf`. That
    # is the green-signal-is-not-a-correct-result failure in its newest costume, so the read-back
    # gets its own question first -- is this value a SENTINEL? -- and answers CAUGHT-BUG.
    ${landed}=    Gz Sentinel Verdict    GarzAI TypeText('${locator}')    ${actual}
    IF    ${landed}
        RETURN
    END
    ${matches}=    Values Match    ${input_text}    ${actual}
    IF    not ${matches}
        Gz Report Mismatch    CAUGHT-BUG    GarzAI TypeText('${locator}'): value did not land. asked for '${input_text}', field holds '${actual}' -- never re-typed over a non-blank mismatch (D13, CLAUDE.md).
        RETURN
    END
    Log    VERIFIED-PASS: GarzAI TypeText('${locator}'): read back '${actual}' -- matches '${input_text}'.    console=True


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
    # the same sentinel-landed question the TypeText override asks, for the same reason: a
    # sentinel compared against itself matches, and a match here would read as a pass
    ${landed}=    Gz Sentinel Verdict    GarzAI Verify Input Value('${locator}')    ${actual}
    IF    ${landed}
        Fail    CAUGHT-BUG: sentinel landed -- GarzAI Verify Input Value('${locator}'): the field holds the sentinel '${actual}'.
    END
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
    [Documentation]    Lenient-equal (D13, CLAUDE.md), four tiers, first that applies decides:
    ...    1. both sides are ONE number (digits with , . $ % + - and spaces): compare the parsed
    ...       floats, so '25000' == '25,000.00' and '$ 7,876.00' == '$7,876.00';
    ...    2. both sides are a three-part date (digits split by - or /): compare the parts as
    ...       integers, so '09-01-2025' == '09/01/2025' and '1/1/1990' == '01/01/1990';
    ...    3. the expected value is a FORMATTED IDENTIFIER (digits with -, /, (, ) or spaces and
    ...       no letters: a phone, an SSN, a masked input): compare the digit sequences, so
    ...       '(555) 111-2244' == '555-111-2244' and a mask placeholder '(___) ___-____' fails;
    ...    4. trimmed string equality.
    ...    Measured 2026-09-19 on fsc7f (the Digital Lending OmniScript): the earlier two-tier
    ...    version raised ValueError on a dashed date ('09-01-2025' parsed as a float) and read a
    ...    re-rendered phone as a mismatch. Never rescues a blank actual -- TypeText routes a blank
    ...    read-back to the repair pass instead of calling this.
    [Arguments]    ${expected}    ${actual}
    ${e}=    Evaluate    str($expected).strip()
    ${a}=    Evaluate    str($actual).strip()
    ${both_numbers}=    Evaluate    bool(re.fullmatch(r'[\s$+-]*[0-9][0-9,]*(\.[0-9]+)?\s*%?', $e) and re.fullmatch(r'[\s$+-]*[0-9][0-9,]*(\.[0-9]+)?\s*%?', $a))    modules=re
    IF    ${both_numbers}
        ${result}=    Evaluate    float(re.sub(r'[^0-9.+-]', '', $e)) == float(re.sub(r'[^0-9.+-]', '', $a))    modules=re
        RETURN    ${result}
    END
    ${both_dates}=    Evaluate    bool(re.fullmatch(r'[0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,4}', $e) and re.fullmatch(r'[0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{1,4}', $a))    modules=re
    IF    ${both_dates}
        ${result}=    Evaluate    [int(x) for x in re.split(r'[-/]', $e)] == [int(x) for x in re.split(r'[-/]', $a)]    modules=re
        RETURN    ${result}
    END
    ${formatted}=    Evaluate    bool(re.search(r'[0-9]', $e) and not re.search(r'[A-Za-z]', $e) and re.search(r'[-/() ]', $e))    modules=re
    IF    ${formatted}
        ${result}=    Evaluate    re.sub(r'[^0-9]', '', $e) == re.sub(r'[^0-9]', '', $a)    modules=re
        RETURN    ${result}
    END
    ${result}=    Evaluate    $e == $a
    RETURN    ${result}


Gz Report Mismatch
    [Documentation]    One place a TypeText verdict other than a pass is delivered. Prints the
    ...    EXPANDED message to the console first (the Fail template used to reach the console with
    ...    its variables unexpanded, so the field's actual value was invisible there). Then, by
    ...    ${GZ_ON_MISMATCH}: fail -> Fail (default); warn -> keep the message in @{GZ_MISMATCHES},
    ...    log it at WARN and CONTINUE.
    [Arguments]    ${verdict}    ${message}
    Log To Console    ${verdict}: ${message}
    IF    '${GZ_ON_MISMATCH}' == 'warn'
        Append To List    ${GZ_MISMATCHES}    ${verdict}: ${message}
        Set Suite Variable    ${GZ_MISMATCHES}
        Log    ${verdict}: ${message}    level=WARN
    ELSE
        Fail    ${verdict}: ${message}
    END


Gz Mismatch Tally
    [Documentation]    Prints every mismatch kept while ${GZ_ON_MISMATCH} was warn, and returns the
    ...    count -- run it as the last step of a recording session.
    ${n}=    Get Length    ${GZ_MISMATCHES}
    Log To Console    GarzAI TypeText mismatches this session: ${n}
    FOR    ${m}    IN    @{GZ_MISMATCHES}
        Log To Console    - ${m}
    END
    RETURN    ${n}
