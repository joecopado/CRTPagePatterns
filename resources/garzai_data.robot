*** Settings ***
Documentation     GarzAI generated data (build n10, 2026-09-20) -- FakerLibrary generates, this
...               resource keeps the four things FakerLibrary does not do: a valid picklist value
...               (`Gz Pick`), the tally of every generated value (`Gz Generated Tally`), the
...               cleanup SOQL a person runs (`Gz Cleanup Hint`), and the sentinel-landed verdict
...               (`Gz Sentinel Verdict`).
...
...               WHY THIS EXISTS (user, 2026-09-19): "Every value is hard-coded, so the second run
...               fails on duplication rules." A recorded fill whose typed value is a SENTINEL
...               (`asdf`, or the one plain override `@@<provider>`) composes a VARIABLE line above
...               the fill -- `${lead_first_name}=    FakerLibrary.First Name` -- and the fill uses
...               the variable, so a later verify step reuses the SAME value.
...
...               THE USER'S RULE (2026-09-20, twice): "don't like the friggin dates and crazy
...               reinvention of randomized data. That shit is way too complicated and FakerLibrary
...               does so well already as long as it's treated properly." So build n10 RETIRED the
...               in-house generators (Gz Unique Text, Gz Email, Gz Phone, Gz Number, Gz Date,
...               Gz Text, Gz Run Stamp) and the argument grammar (`@@date+N`, `@@unique <base>`,
...               `@@int a b`, `@@text n`). NO RUN STAMP IN ANY VISIBLE VALUE: a company reads like a
...               company. Traceability is the tally at the end and the cleanup hint's SOQL
...               (`CreatedById = <user> AND CreatedDate = TODAY`); nothing here deletes anything.
...
...               EVERY GENERATED VALUE IS LOGGED TO THE CONSOLE ONCE by the listener library
...               `garzai_data_tally.py` (it sees every `FakerLibrary.*` keyword end and reads the
...               assigned variable back), because a generated value that nobody can read is a
...               value nobody can check. `print()` is invisible in Live Testing, so the log goes
...               through the console logger.
...
...               COULD-NOT-CHECK IS A REAL ANSWER. `Gz Pick` with no options it can trust FAILS
...               with the word COULD-NOT-CHECK in the message. It never invents a picklist value:
...               an invented option is the quiet-wrong-answer failure this repo is built around.
...
...               The composer-side twin of the sentinel table is
...               `tools/recorder/crt_override/compose_live.py` (`sentinel_spec`,
...               `sentinel_landed`); `Gz Is Sentinel` below must agree with `sentinel_landed`,
...               and `tools/recorder/tests/test_crt_override_faker_2026_09_20.py` asserts it.
Library           Collections
Library           ${CURDIR}/garzai_verdicts.py    # F192: the ONE session ledger a sentinel landing is recorded in
Library           FakerLibrary
Library           ${CURDIR}/garzai_data_tally.py


*** Variables ***
# Path to a JSON file the suite ships with, read by `Gz Field Options`. Two shapes are accepted:
# the flat `{"Lead": {"Salutation": ["Mr.", "Ms."]}}`, and an org-map projection
# `{"objects": {"Lead": {"inventory": {"fields": {"value": {"Salutation": {"picklist_values": [...],
# "label": "Salutation"}}}}}}}` -- the same file `discover.py` writes. Empty means COULD-NOT-CHECK,
# never an invented option.
${GZ_FIELD_OPTIONS}      ${EMPTY}
# The object `Gz Pick` looks a bare label up under when the caller gave no options.
${GZ_DEFAULT_OBJECT}     ${EMPTY}


*** Keywords ***
Gz Log Generated
    [Documentation]    One console line per generated value, kept in the tally so
    ...    `Gz Generated Tally` can print the whole run's data at the end. FakerLibrary values
    ...    reach the tally through the listener without this; `Gz Pick` calls it.
    [Arguments]    ${keyword}    ${value}
    Gz Note Generated    ${keyword}    ${value}
    RETURN    ${value}


Gz Generated Tally
    [Documentation]    Prints every value generated this run -- every `FakerLibrary.*` assignment
    ...    the listener saw and every `Gz Pick` -- and returns the count. Run it as a step at the
    ...    end, before `Gz Cleanup Hint`, so the pane shows what the run put into the org.
    ${values}=    Gz Generated Values
    ${n}=    Get Length    ${values}
    Log To Console    GarzAI data: ${n} generated values this run
    FOR    ${v}    IN    @{values}
        Log To Console    - ${v}
    END
    RETURN    ${n}


Gz Cleanup Hint
    [Documentation]    Prints the SOQL a person runs to find what this run created -- by the
    ...    creating user and today's date, because no generated value carries a tag any more --
    ...    and returns it. NOTHING IS DELETED BY THIS KEYWORD: run the query, look at the rows,
    ...    delete them yourself. `user` is the running user's Id (`005...`) or username; with
    ...    neither given the query names the placeholder so nobody pastes it blind.
    [Arguments]    ${object}    ${user}=${EMPTY}
    ${by}=    Evaluate    ("CreatedBy.Username = '%s'" % $user) if '@' in str($user) else ("CreatedById = '%s'" % (str($user).strip() or '<your user id>'))
    ${soql}=    Set Variable    SELECT Id, Name, CreatedDate FROM ${object} WHERE ${by} AND CreatedDate = TODAY
    Log To Console    GarzAI cleanup hint: the records this run created are the ones a person finds with
    Log To Console    ${SPACE * 4}${soql}
    Log To Console    ${SPACE * 4}-- nothing is deleted by this keyword; run the query, check the rows, delete them yourself.
    RETURN    ${soql}


Gz Pick
    [Documentation]    A valid value for a picklist, chosen from the options GIVEN, or -- when
    ...    none are -- from `Gz Field Options ${GZ_DEFAULT_OBJECT} <label>`. The listbox's own
    ...    "nothing chosen" entries (`-- None --`, `-- No Value --`, `Select an Option`, ...) are
    ...    never chosen: picking one leaves the field where it began, which is not a step
    ...    (measured live on fsc7f 2026-09-19 13:13).
    ...    WITH NOTHING TO CHOOSE FROM IT FAILS, naming COULD-NOT-CHECK. It never invents an
    ...    option -- an invented picklist value is rejected by the org, or worse, accepted.
    [Arguments]    ${label}    @{options}
    ${usable}=    Gz Usable Options    @{options}
    ${n}=    Get Length    ${usable}
    IF    ${n} == 0
        ${usable}=    Gz Field Options    ${GZ_DEFAULT_OBJECT}    ${label}
        ${n}=    Get Length    ${usable}
    END
    IF    ${n} == 0
        Fail    COULD-NOT-CHECK: Gz Pick('${label}'): no usable option was given and none was found in ${GZ_FIELD_OPTIONS} -- an option is never invented.
    END
    ${value}=    Evaluate    random.choice($usable)    modules=random
    ${value}=    Gz Log Generated    Gz Pick('${label}')    ${value}
    RETURN    ${value}


Gz Usable Options
    [Documentation]    The given options with blanks, duplicates and every "nothing chosen"
    ...    placeholder removed, in the order they arrived.
    [Arguments]    @{options}
    ${out}=    Evaluate    [o for o in dict.fromkeys(re.sub(r'\\s+', ' ', str(x)).strip() for x in $options) if o and o.casefold() not in ('-- no value --', '--none--', '-- none --', 'none', 'select an option', 'select...', 'select', '--select--', '-- select --', '--select an option--')]    modules=re
    RETURN    ${out}


Gz Field Options
    [Documentation]    The active picklist values of `<object>.<field>` read from the JSON file at
    ...    `${GZ_FIELD_OPTIONS}` -- the org map is the input (CLAUDE.md), never a live describe
    ...    from inside a test. `field` matches the API name OR the rendered label.
    ...    Returns an EMPTY list, with the reason on the console, when the suite carries no map
    ...    path or the field is not in it: the caller turns that into COULD-NOT-CHECK. It never
    ...    invents an option.
    [Arguments]    ${object}    ${field}
    ${none}=    Create List
    IF    $GZ_FIELD_OPTIONS in (None, '')
        Log To Console    GarzAI data: COULD-NOT-CHECK: Gz Field Options('${object}', '${field}'): this suite carries no ${GZ_FIELD_OPTIONS} path, so no option list is known.
        RETURN    ${none}
    END
    ${data}=    Evaluate    json.loads(pathlib.Path($GZ_FIELD_OPTIONS).read_text())    modules=json, pathlib
    # the org-map projection nests the object under `objects`; the flat shape does not
    ${obj}=    Evaluate    ($data.get('objects') or {}).get(str($object)) or $data.get(str($object)) or {}
    # ... and the fields under inventory.fields.value; the flat shape IS the field table
    ${fields}=    Evaluate    ((($obj.get('inventory') or {}).get('fields') or {}).get('value')) or $obj
    ${want}=    Evaluate    re.sub(r'\\s+', ' ', str($field)).strip().strip('*').strip().casefold()    modules=re
    # By API name first, then by the RENDERED label -- the composer only ever knows the label.
    # THE INDEXES ARE BUILT FIRST AND LOOKED UP SECOND, deliberately. A `next((v for k, v in
    # $fields.items() if ... == $want), None)` reads correctly and FAILS at run time: Robot injects
    # `$want` as a local, and a generator expression opens a scope that cannot see the enclosing
    # locals, so Robot raises "variable '$want' is used in a scope where it cannot be seen".
    # `--dryrun` does not execute expressions, so it passed; the real run is what found it
    # (2026-09-19, building n7). A dict comprehension over `$fields` alone is safe -- the outermost
    # iterable is the one thing such a scope CAN see.
    ${by_label}=    Evaluate    {str(v.get('label') or '').strip().casefold(): v for k, v in $fields.items() if isinstance(v, dict)}
    ${by_name}=    Evaluate    {str(k).casefold(): v for k, v in $fields.items()}
    ${entry}=    Evaluate    $fields.get(str($field)) or $by_label.get($want) or $by_name.get($want) or {}
    ${opts}=    Evaluate    [str(x) for x in (($entry.get('picklist_values') if isinstance($entry, dict) else $entry) or []) if str(x).strip()]
    ${opts}=    Gz Usable Options    @{opts}
    ${n}=    Get Length    ${opts}
    IF    ${n} == 0
        Log To Console    GarzAI data: COULD-NOT-CHECK: Gz Field Options('${object}', '${field}'): ${GZ_FIELD_OPTIONS} carries no picklist values for it.
    END
    RETURN    ${opts}


Gz Is Sentinel
    [Documentation]    True when a value IS a sentinel -- the bare `asdf` (case-insensitive,
    ...    surrounding whitespace ignored) or ANYTHING starting with `@@` (`@@company`, `@@pick`,
    ...    and a malformed `@@nope` alike: a person never means `@@x` as data, so a value that
    ...    still carries the prefix after the fill was never generated). NOTHING ELSE:
    ...    `asdfasdf`, `test`, `qwer` are values a person typed on purpose, and treating one as a
    ...    sentinel would silently replace data they meant.
    ...    The composer's own `compose_live.sentinel_landed` is the twin of this rule.
    [Arguments]    ${value}
    ${hit}=    Evaluate    bool(re.fullmatch(r'(?i)\\s*(asdf|@@\\S.*?)\\s*', str($value)))    modules=re
    RETURN    ${hit}


Gz Sentinel Verdict
    [Documentation]    THE SENTINEL-LANDED VERDICT. A value read back off the page that is ITSELF
    ...    a sentinel means the generated-data rule never fired for that field and the literal
    ...    `asdf` (or a `@@...`) went into the record -- `CAUGHT-BUG: sentinel landed`, never a
    ...    quiet pass. Returns True when it fired, so the caller can stop before printing a pass.
    ...    Honours `${GZ_ON_MISMATCH}` the same way the TypeText override does (default `warn`:
    ...    print, keep, continue).
    [Arguments]    ${where}    ${actual}
    ${landed}=    Gz Is Sentinel    ${actual}
    IF    not ${landed}
        RETURN    ${False}
    END
    ${line}=    Set Variable    ${where}: the value read back is the SENTINEL '${actual}' -- the generated-data rule never fired for this field, so a literal sentinel went into the record.
    Log To Console    CAUGHT-BUG: sentinel landed -- ${line}
    Gz Record Verdict    CAUGHT-BUG    ${where}    sentinel landed: '${actual}'
    ${mode}=    Get Variable Value    ${GZ_ON_MISMATCH}    warn
    IF    '${mode}' == 'warn'
        Log    CAUGHT-BUG: sentinel landed -- ${line}    level=WARN
    ELSE
        Fail    CAUGHT-BUG: sentinel landed -- ${line}
    END
    RETURN    ${True}
