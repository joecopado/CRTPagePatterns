*** Settings ***
Documentation     OmniStudio (OmniScript + FlexCard) keywords CRT/QForce does not ship -- ported
...               2026-09-18/19 from the agentic-crt-orchestrator repo's
...               tools/qforce-lite/keywords_omni.py (16 Python callables, one shared host
...               resolver for both surfaces) per
...               docs/audit/non-qforce-keywords-inventory-2026-09-18.md section 2's file list.
...               Every keyword below is host-scoped (`data-omni-key` for OmniScript,
...               `data-element-label`/`aria-label`/`placeholder` for FlexCard -- never a
...               page-wide text search) and READS ITS OWN WRITE BACK through `confirm.py` before
...               returning -- a keyword that cannot confirm what it did raises `CouldNotCheck`,
...               never a silent pass. No real QForce/QWeb keyword resolves either OmniStudio
...               shape (both live inside `runtime_omnistudio_*` LWC shadow roots a bare
...               `ClickText`/`TypeText` never reaches).
...
...               WIRING FIX (see resources/garzai_omni/README.md for the full writeup): the
...               source template (tools/qforce-lite/templates/crt/resources/garzai_recorder.robot
...               lines 264-360) wires NINE of these keywords -- Type/Select/Radio/Checkbox/Date/
...               Lookup/Typeahead/Edit Block Add Row/Next Step -- to a READ-ONLY verify call
...               instead of their own setter, so the shipped keyword never actually performs the
...               write its name promises. Each of those nine keywords below is marked
...               "PORT FIX (2026-09-18)" in its own [Documentation] and now calls its real
...               setter. The four keywords that were already wired correctly in the source
...               (Multiselect, Read Output, Verify Output Field, Click Action) are ported
...               unchanged in behaviour.
...
...               NAME COLLISION (see README.md): source `garzai_recorder.robot:361`'s
...               "Omni Verify Output" (wraps `verify_omni_value`, an OmniScript INPUT assert) is
...               renamed here to `Omni Verify Output Legacy` to stop it reading, by eye, as the
...               same thing as `Omni Verify Output Field` (wraps `verify_omni_output`, a FlexCard
...               OUTPUT-field assert -- a different DOM family entirely). Kept, not dropped: both
...               callables are independently proven and address different control shapes.
...
...               Every citation below is copied from
...               docs/audit/non-qforce-keywords-inventory-2026-09-18.md's table, or, where richer
...               evidence exists, from the underlying evidence file itself
...               (docs/recorder/sessions/fsc7f/, docs/recorder/evidence/) -- both cited by exact
...               path. A keyword with no live citation for THIS repo's chosen example org
...               (fsc7f -- health90 has zero OmniStudio hosts, measured, see
...               tests/omnistudio/README.md) says UNPROVEN-ON-FSC7F verbatim rather than
...               implying a proof that was never run against this org.
# This repo's own resources/common.robot declares only QForce/String/DateTime -- every existing
# suite that lands a browser locally does so because it ALSO imports garzai_console.robot or
# garzai_navigation.robot, both of which redundantly `Library QWeb` themselves (measured: a bare
# `Resource common.robot` + `Suite Setup Setup Browser` suite fails local dry-run with "No keyword
# with name 'Open Browser' found" even with no OmniStudio content at all -- reproduced against an
# empty suite during this port's structural check). Following that same established pattern here,
# not editing the shared common.robot: GoTo/VerifyText in the example suites below need QWeb.
Library           QWeb
# Library-importing keywords_omni.py directly (rather than an unrelated file) gets the same
# sys.path side effect the source template relies on (Library-importing keywords_recordtype.py /
# keywords_upload.py there) -- WITH NAME keeps the auto-generated per-function keywords out of the
# unqualified namespace so they cannot collide with the hand-written keywords below sharing the
# same un-prefixed name.
#
# READABILITY (the user, 2026-09-20): "`Run Keyword And Ignore Error` makes more sense than
# `Evaluate __import__` does. That's much more human-readable and puts it more in line."
# Every body below now calls `OmniRaw.<Keyword>` directly. Robot's static library API already
# exposes each module-level function under its spaced name (`omni_type` -> `Omni Type`), so the
# `Evaluate __import__('keywords_omni').<fn>(...)` indirection the source template used was
# doing nothing this import does not already do -- it just hid the call from the reader.
# Argument types are unchanged: a bare `${var}` cell passes the VALUE, so `${TRUE}`, `${NONE}`
# and a list variable all arrive as the Python objects they were, exactly as `$var` did inside
# `Evaluate`. Proven by `robot --dryrun` over every keyword in this file, before and after.
#
# LIBRARIES: nothing else belongs here. The canonical six (QWeb, QForce, Collections, String,
# DateTime, FakerLibrary) are declared on the ENTRY resource, `common.robot`, and a keyword file
# imported by one INHERITS them -- re-declaring them here is the "applied too bluntly" mistake
# the rule itself names. `Library QWeb` below is the one exception and is a WORKAROUND, not a
# pattern: see its own comment.
Library           ${CURDIR}/garzai_omni/keywords_omni.py    WITH NAME    OmniRaw
Library           Collections    # Append To List in Gz Omni Verdict below
Library           ${CURDIR}/garzai_verdicts.py    # F192: the ONE session ledger every verdict line lands in
Resource          ${CURDIR}/garzai_data.robot    # Gz Sentinel Verdict: a read-back that IS a sentinel is CAUGHT-BUG, never a quiet pass


*** Variables ***
# THE STEP IS THE ACTION, THE VERDICT IS A LINE (user, 2026-09-19; the same rule
# garzai_typetext_override.robot already follows). Measured on fsc7f run 5 (2026-09-19 13:13):
# `Omni Type` returned in ~30 ms SEVEN times and nothing in the Live Testing console said whether
# any value had landed -- the run log could not tell a pass from a silent miss, so every one of
# them was COULD-NOT-CHECK. The three setters below now print ONE verdict line each and never stop
# the run for a mismatch.
@{GZ_OMNI_VERDICTS}


*** Keywords ***
Gz Omni Verdict
    [Documentation]    The one place an OmniStudio setter's verdict is delivered. The keyword's
    ...                own Python already reads the value back through the SAME `data-omni-key`
    ...                resolver and raises on a mismatch (`confirm.typed_value`) or on an
    ...                unreadable control (`confirm.CouldNotCheck`); this turns that raise into a
    ...                console LINE so the step itself still runs to completion.
    ...                `${GZ_ON_MISMATCH}` is honoured when the suite defines it (the typetext
    ...                override's own variable) and defaults to `warn`: print, keep in
    ...                @{GZ_OMNI_VERDICTS}, log at WARN, CONTINUE. `fail` makes the step fail.
    ...                It NEVER upgrades a verdict -- a pass is only ever printed for a read-back
    ...                the Python actually returned.
    [Arguments]    ${keyword}    ${key}    ${asked}    ${status}    ${result}
    # THE SENTINEL-LANDED VERDICT (build n7, 2026-09-19), checked BEFORE the PASS branch: an
    # `asdf` that was typed AND read back matches itself, so the Python's own read-back returns
    # PASS and this would print VERIFIED-PASS over a record now holding the literal sentinel.
    # It never upgrades a verdict; it only refuses to let one through.
    ${landed}=    Gz Sentinel Verdict    ${keyword}('${key}')    ${result}
    IF    ${landed}
        RETURN    ${NONE}
    END
    IF    '${status}' == 'PASS'
        Log To Console    VERIFIED-PASS: ${keyword}('${key}'): read back '${result}' -- matches '${asked}'
        Gz Record Verdict    VERIFIED-PASS    ${keyword}('${key}')    ${result}
        RETURN    ${result}
    END
    ${verdict}=    Set Variable    CAUGHT-BUG
    IF    'CouldNotCheck' in $result or 'could not read back' in $result or 'could not verify' in $result or 'reporting UNKNOWN' in $result
        ${verdict}=    Set Variable    COULD-NOT-CHECK
    END
    ${line}=    Set Variable    ${keyword}('${key}'): asked '${asked}' -- ${result}
    Log To Console    ${verdict}: ${line}
    # F192: the ONE session ledger. The value read back is what the Python's message quotes
    # (`displays '<v>'` / `read back '<v>'`), blank when it could not read one.
    ${got}=    Evaluate    (re.search(r"(?:displays|read back|holds) '([^']*)'", str($result)) or [None, ''])[1]    modules=re
    Gz Record Verdict    ${verdict}    ${keyword}('${key}')    ${got}
    ${mode}=    Get Variable Value    ${GZ_ON_MISMATCH}    warn
    IF    '${mode}' == 'warn'
        Append To List    ${GZ_OMNI_VERDICTS}    ${verdict}: ${line}
        Set Suite Variable    ${GZ_OMNI_VERDICTS}
        Log    ${verdict}: ${line}    level=WARN
    ELSE
        Fail    ${verdict}: ${line}
    END
    RETURN    ${NONE}

Gz Omni Verdict Tally
    [Documentation]    THE ONE TALLY (F192): the same table `Gz Mismatch Tally` prints -- every
    ...                verdict class of the session, Omni verdicts included, plus every step
    ...                Robot saw raise or get stopped -- and the red-step count it returns.
    ${n}=    Gz Verdict Tally
    RETURN    ${n}
Omni Type
    [Documentation]    Set any OmniStudio free-text/number/currency/email/phone control by its
    ...                `data-omni-key` (equals `OmniProcessElement.Name`, an author-controlled,
    ...                metadata-joined id present on 23/23 elements measured on dev1). Never a
    ...                page-wide text search -- a page-wide option scan was once measured clicking
    ...                "Agentforce" in the nav bar and reporting a pass. Currency/Telephone
    ...                REFORMAT on blur (`250000` -> `$ 250,000.00`), so the read-back is
    ...                family-normalised (`${family}`), not a raw string compare.
    ...                PORT FIX (2026-09-18): the source template's `Omni Type` called
    ...                `Omni Verify Output` (a read-only compare) instead of this setter -- see
    ...                resources/garzai_omni/README.md.
    ...                PROOF: dev1, `Zoo_Omni_Intake`, 7/7 controls, two runs (module docstring,
    ...                docs/crt-train/evidence/omnistudio-zoo-keyword-pass.py). Cross-org on
    ...                fsc7f (Digital Lending loan-calculator FlexCard, 2026-09-06,
    ...                docs/recorder/evidence/omni-fsc7f-flexcard-2026-09-06.json): "Loan Amount"
    ...                (currency, `250000` -> `$250,000.00`) and "Interest Rate" (number, `7.5`)
    ...                both VERIFIED-PASS, value held after 4 further keyword calls.
    ...                VERDICT LINE (2026-09-19, build n2): prints one
    ...                `VERIFIED-PASS: Omni Type('<key>'): read back '<v>' -- matches '<value>'`
    ...                (or CAUGHT-BUG / COULD-NOT-CHECK) to the console and never stops the run.
    ...                The read-back behind it is a SECOND, independent call through the same
    ...                `data-omni-key` resolver -- until build n2 `omni_type` returned the
    ...                `inp.value` it read inside the SAME JS that wrote it, which is the vacuous
    ...                self-referential check `omni_date`'s own docstring names.
    [Arguments]    ${key}    ${value}    ${family}=omni-text
    ${status}    ${v}=    Run Keyword And Ignore Error
    ...    OmniRaw.Omni Type    ${key}    ${value}    ${family}
    ${v}=    Gz Omni Verdict    Omni Type    ${key}    ${value}    ${status}    ${v}
    RETURN    ${v}

Omni Select
    [Documentation]    Commit an OmniStudio Select via the full pointer sequence
    ...                (mouseover/mousedown/mouseup/click) on the deepest node whose text is the
    ...                option, scoped to this combobox's OWN listbox (`aria-controls`) -- a bare
    ...                `.click()` on the option leaves the field EMPTY (measured twice). Sends
    ...                Escape afterwards so the open listbox cannot intercept the next control.
    ...                PORT FIX (2026-09-18): the source template's `Omni Select` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: dev1, asked `Bravo`, read back `Bravo`, two runs (module docstring).
    ...                Cross-org fsc7f (loan-calculator FlexCard, 2026-09-06): "Repayment Type" ->
    ...                "Amortization" VERIFIED-PASS, held after 4 further calls. Also CAUGHT a
    ...                real bug on this same card: "Loan Term" -> "30" read back correctly
    ...                IMMEDIATELY but empty on a LATER sweep after a sibling radio group
    ...                (LoanTermSelection) changed -- the card's own reactive logic resets a
    ...                dependent field; not a resolver defect. Do not assume a Select value
    ...                survives a later change to a sibling control on this card.
    ...                VERDICT LINE (2026-09-19, build n2): one console line per call, same form
    ...                as `Omni Type`. `omni_select` already re-reads the combobox input in its
    ...                own round trip after the commit, so the line reports a real second read.
    [Arguments]    ${key}    ${value}
    ${status}    ${v}=    Run Keyword And Ignore Error
    ...    OmniRaw.Omni Select    ${key}    ${value}
    ${v}=    Gz Omni Verdict    Omni Select    ${key}    ${value}    ${status}    ${v}
    RETURN    ${v}

Omni Radio
    [Documentation]    OmniStudio radio groups carry NO `label[for]` and no accessible name --
    ...                the `value` attribute on the input is the only handle, found via the
    ...                group's own `data-omni-key`.
    ...                PORT FIX (2026-09-18): the source template's `Omni Radio` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: dev1, 2026-09-05 (module docstring). fsc7f, DigitalLendingDF/
    ...                ApplicantIntakeSecured (docs/recorder/sessions/fsc7f/
    ...                omni-elements-additional-2026-09-07.json): `FSC_DL_v1_Additional_Income`
    ...                (asked No), `FSC_DL_v1_Additional_Expense` (asked No),
    ...                `FSC_DL_v1_Add_Assets` (asked Yes) -- all 3 VERIFIED-PASS. Also fsc7f
    ...                loan-calculator FlexCard: `LoanTermSelection` -> "Years" VERIFIED-PASS,
    ...                `data-element-label` the ONLY anchor reaching this group (no aria-label, no
    ...                legend text).
    [Arguments]    ${key}    ${value}
    ${v}=    OmniRaw.Omni Radio    ${key}    ${value}
    RETURN    ${v}

Omni Checkbox
    [Documentation]    The Checkbox element renders with no label element at all -- `data-omni-key`
    ...                is the entire locator.
    ...                PORT FIX (2026-09-18): the source template's `Omni Checkbox` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: dev1, 2026-09-05 (module docstring). fsc7f, DigitalLendingDF/
    ...                ApplicantIntakeSecured (docs/recorder/sessions/fsc7f/
    ...                omni-elements-additional-2026-09-07.json): `FSC_DL_v1_Auto_Pay_Enrollment`
    ...                (asked ${TRUE}) and `FSC_DL_v1_Does_Lien_Exist` (asked ${FALSE}) -- both
    ...                VERIFIED-PASS.
    [Arguments]    ${key}    ${checked}=${TRUE}
    ${v}=    OmniRaw.Omni Checkbox    ${key}    ${checked}
    RETURN    ${v}

Omni Date
    [Documentation]    Drives the SLDS calendar widget itself -- the Date element renders a TEXT
    ...                input (`[data-id=date-picker-slds-input]`) that a plain native-value write
    ...                never commits on. Opens the picker, selects the year from its own
    ...                `<select>`, clicks prevMonth/nextMonth until the header shows the target
    ...                month (polling the actual rendered day-cell year, not the `<select>`'s own
    ...                value -- a same-day-as-displayed edge case was measured stale otherwise),
    ...                then clicks the day cell whose `aria-label` matches
    ...                `Date().toDateString()`. `value` is `YYYY-MM-DD`; the widget commits
    ...                `MM-DD-YYYY`, normalised on both sides before comparison.
    ...                PORT FIX (2026-09-18): the source template's `Omni Date` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: fsc7f, DigitalLendingDF/ApplicantIntakeSecured v2, 2026-09-07
    ...                (docs/recorder/sessions/fsc7f/omni-date-calendar-fix-2026-09-07.json):
    ...                `FSC_DL_v1_Date_Of_Birth` (asked 1990-04-17, committed 04-17-1990),
    ...                `FSC_DL_v1_Start_Date` (asked 2020-01-01 -- the same-month regression
    ...                case), `FSC_DL_v1_Employment_Start_Date` (asked 2015-06-01) -- all 3
    ...                VERIFIED-PASS. CAVEAT measured on the fsc7f loan-calculator FlexCard
    ...                (different surface, 2026-09-06): a typed date read back correctly AT THE
    ...                TIME of the call but ALL date inputs on that card read empty on a later
    ...                sweep -- that FlexCard's date picker appears to only persist a value chosen
    ...                through its own calendar UI, which is exactly the mechanism this keyword
    ...                already drives; flagged so a caller does not assume every FlexCard date
    ...                instance survives re-render, only that the calendar-widget route (used
    ...                here) is the correct one.
    ...                VERDICT LINE (2026-09-19, build n2): one console line per call, same form
    ...                as `Omni Type`. `omni_date` already reads back through `get_omni_value`,
    ...                the independent path that caught its original vacuous green.
    [Arguments]    ${key}    ${value}
    ${status}    ${v}=    Run Keyword And Ignore Error
    ...    OmniRaw.Omni Date    ${key}    ${value}
    ${v}=    Gz Omni Verdict    Omni Date    ${key}    ${value}    ${status}    ${v}
    RETURN    ${v}

Omni Multiselect
    [Documentation]    Tick a set of options on an OmniStudio Multi-select and read the ticked set
    ...                back. Every checkbox carries `name=OmniProcessElement.Name`, the whole
    ...                locator -- an OmniStudio multiselect has no label association at all.
    ...                Wiring unchanged from the source template (already correct there).
    ...                PROOF: dev1, `Zoo_Omni_Intake`, 2026-09-05 (asked Red|Blue, read back
    ...                Red|Blue). UNPROVEN-ON-FSC7F: a SOQL census of
    ...                DigitalLendingDF/ApplicantIntakeSecured's own OmniProcessElement rows found
    ...                no Multi-select element anywhere in that script's metadata
    ...                (docs/recorder/sessions/fsc7f/omni-elements-additional-2026-09-07.json,
    ...                catalogue_note) -- not driven live on the example org this repo ships.
    [Arguments]    ${key}    ${values}
    ${v}=    OmniRaw.Omni Multiselect    ${key}    ${values}
    RETURN    ${v}

Omni Lookup
    [Documentation]    Server-backed SObject lookup: types locally, waits for the round trip
    ...                (a real network call -- a timeout is COULD-NOT-CHECK, never a pass), then
    ...                commits through the shared select-commit half.
    ...                PORT FIX (2026-09-18): the source template's `Omni Lookup` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: fsc7f (module docstring). Directly exercised on
    ...                DigitalLendingDF/ApplicantIntakeSecured, `PrimaryOwner`, asked search
    ...                `GZREF` (docs/recorder/sessions/fsc7f/omni-elements-additional-2026-09-07
    ...                .json): the TYPE half drove correctly (input wrote and read back `GZREF`,
    ...                a keyup event fired) but the server-backed listbox returned ZERO options
    ...                after a 1.5s wait -- COULD-NOT-CHECK, a data/timing gap in this script's
    ...                own Party-creation sequence at this point in the flow, not a keyword
    ...                defect (the shared commit half is separately proven by `Omni Select`/
    ...                `Omni Typeahead` on the same script and FlexCard).
    [Arguments]    ${key}    ${search}    ${choose}=${NONE}
    ${v}=    OmniRaw.Omni Lookup    ${key}    ${search}    ${choose}
    RETURN    ${v}

Omni Typeahead
    [Documentation]    A Type Ahead Block opens its listbox on TYPING, never on a click -- clicking
    ...                the trigger leaves the option list empty, which a select-shaped keyword
    ...                would misreport as "no options". Commits through the same shared half as
    ...                `Omni Select`/`Omni Lookup`.
    ...                PORT FIX (2026-09-18): the source template's `Omni Typeahead` called
    ...                `Omni Verify Output` (read-only) instead of this setter.
    ...                PROOF: dev1, 2026-09-05 -- this is the CAUGHT-BUG that produced the
    ...                keyword (module docstring). UNPROVEN-ON-FSC7F: no Type Ahead Block element
    ...                was reached live on DigitalLendingDF/ApplicantIntakeSecured this session
    ...                (docs/recorder/sessions/fsc7f/omni-elements-additional-2026-09-07.json
    ...                lists it in the script's own element census but the live drive did not
    ...                reach it) -- the shared commit half IS proven live on fsc7f through
    ...                `Omni Select`, above.
    [Arguments]    ${key}    ${search}    ${choose}=${NONE}
    ${v}=    OmniRaw.Omni Typeahead    ${key}    ${search}    ${choose}
    RETURN    ${v}

Omni Edit Block Add Row
    [Documentation]    Add one repeatable row to an Edit Block and PROVE the row count rose.
    ...                CAUGHT-BUG fixed in the source: the original oracle counted
    ...                `[data-omni-key]` descendants scoped to the ONE block instance the key
    ...                resolves, but Add renders a whole new SIBLING block ("Employment 2", ...)
    ...                that is not a descendant of that host, so a host-scoped count never moves.
    ...                Fixed to count the page-wide `[aria-label^="Delete the block named"]`
    ...                buttons instead, which the runtime renders exactly one of per block,
    ...                anywhere on the page.
    ...                PORT FIX (2026-09-18): the source template's `Omni Edit Block Add Row`
    ...                called `Omni Verify Output` (read-only) instead of this setter -- meaning
    ...                the shipped keyword never clicked Add at all.
    ...                PROOF: fsc7f, DigitalLendingDF/ApplicantIntakeSecured, `EmploymentBlock`,
    ...                2026-09-07 (docs/recorder/sessions/fsc7f/
    ...                omni-elements-additional-2026-09-07.json): CAUGHT-BUG then VERIFIED-PASS
    ...                same session, block count 5 -> 6 after one Add click.
    [Arguments]    ${key}
    ${v}=    OmniRaw.Omni Edit Block Add Row    ${key}
    RETURN    ${v}

Omni Next Step
    [Documentation]    Advance the script and CHECK THE LANDING CHANGED. v1 shipped a vacuous
    ...                green -- it asserted only that the step chart reported SOME aria-current
    ...                step, which it always does, and returned VERIFIED-PASS with index 0 after
    ...                a click that never left step 1. v2 compares the chart index against the
    ...                index taken BEFORE the click. A SECOND fix was needed for scripts whose
    ...                step-chart buttons never carry `aria-current="step"` at all (index is -1
    ...                both before and after a genuine advance, a permanent false negative for the
    ...                index-only oracle) -- falls back to the page's own "Progress: N%" text,
    ...                clearly labelled `oracle: progress-percent` in the return value so the
    ...                fallback is never silently substituted for a working chart-index read.
    ...                PORT FIX (2026-09-18): the source template's `Omni Next Step` called
    ...                `Omni Verify Output` (read-only) instead of this setter -- meaning the
    ...                shipped keyword never clicked Next at all.
    ...                PROOF: dev1, index 0 -> 1 after the v2 fix (module docstring). fsc7f,
    ...                DigitalLendingDF/ApplicantIntakeSecured, 2026-09-07 (docs/recorder/
    ...                sessions/fsc7f/omni-date-calendar-fix-2026-09-07.json,
    ...                task_4_omni_next_step_oracle_fix): 9 consecutive clicks, Progress read
    ...                0 -> 7.14 -> 14.29 -> 21.43 -> 28.57 -> 35.71 -> 42.86 -> 50 -> 57.14 ->
    ...                64.29 (%), every call via the progress-percent fallback (this script's
    ...                chart index never resolves). VERIFIED-PASS.
    [Arguments]    ${label}=Next
    ${v}=    OmniRaw.Omni Next Step    ${label}
    RETURN    ${v}

Omni Verify Output Legacy
    [Documentation]    Read one OmniScript INPUT control back and assert it, format-aware. The
    ...                label-equality guard (a value that IS its own rendered label is this
    ...                project's six-times bug) applies to every family EXCEPT the option families
    ...                (radio/checkbox/multi-select/select), where the value legitimately IS an
    ...                option's rendered label -- applying it there raised a false SilentWrongValue
    ...                on a correct read, measured and fixed on dev1.
    ...                RENAMED (2026-09-18) from the source template's `Omni Verify Output`
    ...                (garzai_recorder.robot:361) -- see resources/garzai_omni/README.md's "name
    ...                collision" section. This keyword's own wiring was ALREADY correct in the
    ...                source (it always called `verify_omni_value`); only its NAME collided in a
    ...                reader's eye with `Omni Verify Output Field` below, which wraps a
    ...                DIFFERENT function reading a DIFFERENT DOM family (FlexCard OUTPUT fields,
    ...                not OmniScript INPUT controls). Kept, not dropped -- both are independently
    ...                proven and address different shapes.
    ...                PROOF: dev1/fsc7f, shared by every `Omni Type`/`Omni Select`/`Omni Radio`/
    ...                etc. read-back above (module docstring).
    [Arguments]    ${key}    ${expected}    ${family}=omni-text
    ${v}=    OmniRaw.Verify Omni Value    ${key}    ${expected}    ${family}
    RETURN    ${v}

Get Omni Value
    [Documentation]    Read one OmniScript control's CURRENT value with no assertion -- the raw
    ...                getter every `Omni Verify *` keyword above calls internally. Still routes
    ...                through `confirm.py`'s six-times-bug guard (a value identical to its own
    ...                rendered label raises) and the tri-state rule: an unreadable control raises
    ...                `CouldNotCheck`, it never returns `''` as if that were a real read.
    ...                ADDED FOR PARITY (2026-09-18): not an independent keyword in the source
    ...                template (the source only ever calls this function internally, from
    ...                `verify_omni_value`) -- added here because an example suite frequently
    ...                needs to READ a value without also asserting a specific expectation
    ...                (see tests/omnistudio/ for a live use). The underlying callable
    ...                (`get_omni_value`) is the same one every `Omni Verify *` proof above
    ...                already exercises; this wrapper adds no new behaviour.
    [Arguments]    ${key}    ${family}=omni-text
    ${v}=    OmniRaw.Get Omni Value    ${key}    ${family}
    RETURN    ${v}

Omni Read Output
    [Documentation]    Read an OmniStudio OUTPUT FIELD's rendered value by its rendered LABEL.
    ...                `runtime_omnistudio_common-output-field` carries NO key attribute at all
    ...                (217/217 hosts across the committed fsc7f captures carry only a generated
    ...                `data-style-id`), so `Omni Verify Output Legacy` above (which resolves
    ...                through `data-omni-key`/`data-element-label`) can never reach this family --
    ...                it reads OmniScript INPUT controls, not FlexCard outputs. FOUR shapes exist
    ...                and only 90 of 217 measured hosts are readable: 90 label+value, 29
    ...                labelled-but-blank (COULD-NOT-CHECK, never `''`), 45 unlabelled-and-blank,
    ...                53 CAPTION-only rich text ('Application Form', 'Email') -- a reader that
    ...                fell back to "first span in the host" would return the caption, exactly
    ...                `get_field_value("Stage") -> "Stage"` again; caption hosts are excluded
    ...                structurally.
    ...                Wiring unchanged from the source template (already correct there).
    ...                PROOF: fsc7f, `/lightning/app/06mhk000000z9rhAAA/r/ApplicationFormProduct/
    ...                13Zhk0000001KxZEAU/view`, 2026-09-07 (docs/recorder/evidence/
    ...                industry-omni-families-2026-09-07.md section 2a), VERIFIED-PASS, 7/7 steps
    ...                as designed: `First Name` -> `Jane`, `Phone` -> `(867) 542-3435`,
    ...                `Birth Date` -> `7/1/1993`, `lastname` (norm-matched) -> `Smith`; a caption
    ...                host ("Application Form") and a nonexistent label both correctly raised
    ...                `OmniElementNotFound` rather than returning a caption's own text.
    [Arguments]    ${label}
    ${v}=    OmniRaw.Omni Read Output    ${label}
    RETURN    ${v}

Omni Verify Output Field
    [Documentation]    Assert an OmniStudio OUTPUT FIELD's rendered value by its rendered LABEL --
    ...                the assert half of `Omni Read Output`. The longer name is deliberate (see
    ...                the source's own note, carried forward): `Omni Verify Output Legacy` is the
    ...                OmniScript-INPUT assert and can never reach this family; until 2026-09-07 in
    ...                the source project the callable behind THIS keyword had no keyword surface
    ...                at all and an exporter mapped it onto `Omni Read Output`, turning a recorded
    ...                VERIFY into a read that could never fail. An expected value of `''` is an
    ...                explicit blank assertion (opts into `allow_empty`).
    ...                Wiring unchanged from the source template (already correct there).
    ...                PROOF: fsc7f, same page and session as `Omni Read Output` above
    ...                (docs/recorder/evidence/industry-omni-families-2026-09-07.md section 2a):
    ...                `verify_omni_output("First Name", "Jane")` -> `'Jane'` VERIFIED-PASS;
    ...                `verify_omni_output("First Name", "Wrong")` raised
    ...                `SilentWrongValue: typed 'Wrong' into First Name (omni-output) -- field
    ...                holds 'Jane'.` -- the guard SEEN FIRING, not merely claimed.
    [Arguments]    ${label}    ${expected}
    ${v}=    OmniRaw.Verify Omni Output    ${label}    ${expected}
    RETURN    ${v}

Omni Click Action
    [Documentation]    Click an OmniStudio FlexCard ACTION and REQUIRE THE LANDING TO CHANGE.
    ...                Host is `runtime_omnistudio_flexcards-flex-action`, matched on
    ...                `data-element-label` or the inner clickable node's `aria-label`. TWO
    ...                clickable shapes measured: 15/18 an `a.slds-action_item` whose visible text
    ...                is record DATA (a record number, an email), and 3/18 a nested
    ...                `runtime_omnistudio_common-button` two shadow roots deep (the `editaction`
    ...                shape) -- a locator that knew only the first misses the card's most
    ...                important action. `runtime_omnistudio_common-action` (58 measured hosts,
    ...                every one attribute-free, wrapping an empty `<slot name="action">`) is
    ...                REFUSED BY NAME -- there is nothing clickable inside one. Read-back: the
    ...                URL must change, or the count of VISIBLE content-bearing modals must rise
    ...                (a raw `querySelectorAll` count is not an oracle here -- one action host
    ...                pre-renders an empty modal, so the count is already >=1 before any click);
    ...                neither moving within `timeout` is COULD-NOT-CHECK, never a pass.
    ...                Wiring unchanged from the source template (already correct there).
    ...                PROOF: fsc7f, same page as `Omni Read Output` above (docs/recorder/
    ...                evidence/industry-omni-families-2026-09-07.md section 2b): host resolution
    ...                + decoy refusal VERIFIED-PASS (`omni_click_action("NoSuchActionW9")`
    ...                correctly raised `OmniElementNotFound`, listing the 6 real labels offered
    ...                -- `appformvalue`, `emailvalue`, `contactvalue`, `partyprofilevalue`,
    ...                `accountvalue`, `editaction` -- and naming the 4 decoy hosts as deliberately
    ...                excluded). LANDING is COULD-NOT-CHECK for `partyprofilevalue`: the host and
    ...                its `a.slds-action_item` resolved and were clicked (full pointer sequence,
    ...                retried), but neither the URL nor the visible-modal count moved within 8s --
    ...                the keyword correctly refused to report a pass rather than guess whether the
    ...                action is a genuine no-op on this card.
    [Arguments]    ${key}
    ${v}=    OmniRaw.Omni Click Action    ${key}
    RETURN    ${v}
